import os
import subprocess
import json
import librosa
import numpy as np
from faster_whisper import WhisperModel
from pydub import AudioSegment
from db import init_db, add_clip

# Configuration
MODEL_SIZE = "base.en" # Use 'medium' or 'large' for better accuracy, 'base' for speed
CLIPS_DIR = os.path.join(os.getcwd(), "data", "dataset", "clips")
SOURCES_DIR = os.path.join(os.getcwd(), "data", "sources")

# Initialize Whisper Model (Lazy load in real app)
whisper_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        print("Loading Whisper model...")
        whisper_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return whisper_model

def ingest_youtube(url: str) -> str:
    """Download audio from YouTube using yt-dlp"""
    os.makedirs(SOURCES_DIR, exist_ok=True)
    output_template = os.path.join(SOURCES_DIR, "%(title)s.%(ext)s")
    
    cmd = [
        "yt-dlp",
        "-x", "--audio-format", "wav",
        "--postprocessor-args", "ffmpeg:-ar 16000 -ac 1", # Normalize to 16kHz Mono
        "-o", output_template,
        url
    ]
    subprocess.run(cmd, check=True)
    # Return the path of the downloaded file (simplified logic)
    files = [f for f in os.listdir(SOURCES_DIR) if f.endswith('.wav')]
    return os.path.join(SOURCES_DIR, files[-1]) if files else None

def process_audio_file(file_path: str, source_id: int):
    """Main pipeline: Transcribe -> Segment -> Save Clips"""
    model = get_whisper_model()
    
    # 1. Transcribe with Word Timestamps
    segments, info = model.transcribe(file_path, word_timestamps=True, language="en")
    
    # Load audio for slicing
    audio_data, sr = librosa.load(file_path, sr=16000)
    
    os.makedirs(CLIPS_DIR, exist_ok=True)

    for segment in segments:
        for word_obj in segment.words:
            word_text = word_obj.word.strip()
            if not word_text: continue
            
            # Normalize for indexing
            normalized = word_text.lower().strip(".,!?;:\"'")
            
            # Calculate padding (ms)
            pad_start = 0.05 # 50ms
            pad_end = 0.05
            
            start_sample = int((word_obj.start - pad_start) * sr)
            end_sample = int((word_obj.end + pad_end) * sr)
            
            # Boundary checks
            start_sample = max(0, start_sample)
            end_sample = min(len(audio_data), end_sample)
            
            # Extract snippet
            snippet = audio_data[start_sample:end_sample]
            
            # Simple features
            duration_ms = (len(snippet) / sr) * 1000
            # Pitch estimation (simplified)
            try:
                pitches, magnitudes = librosa.piptrack(y=snippet, sr=sr)
                pitch_hz = float(np.median(pitches[magnitudes > np.median(magnitudes)])) if np.any(magnitudes > np.median(magnitudes)) else 0.0
            except:
                pitch_hz = 0.0

            # Save File
            safe_word = "".join([c for c in normalized if c.isalnum()])
            folder = os.path.join(CLIPS_DIR, safe_word)
            os.makedirs(folder, exist_ok=True)
            
            filename = f"{source_id}_{int(word_obj.start*1000)}.wav"
            filepath = os.path.join(folder, filename)
            
            # Write WAV using librosa
            import soundfile as sf
            sf.write(filepath, snippet, sr)
            
            # Store Metadata
            add_clip({
                "word": word_text,
                "normalized_word": normalized,
                "source_id": source_id,
                "start": word_obj.start,
                "end": word_obj.end,
                "path": filepath,
                "confidence": word_obj.probability if hasattr(word_obj, 'probability') else 1.0,
                "duration": duration_ms,
                "pitch": pitch_hz,
                "loudness": -20.0, # Placeholder, calculate RMS
                "ctx_before": "",
                "ctx_after": ""
            })
