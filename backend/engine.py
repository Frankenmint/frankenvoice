# backend/engine.py

import os
import subprocess
import io
import random
import numpy as np
import librosa
import soundfile as sf
from faster_whisper import WhisperModel
from pydub import AudioSegment

# Internal imports
from backend import db
from backend.audio_processing import generate_espeak_fallback, match_prosody
from backend.filters import apply_filter_chain

# Configuration
MODEL_SIZE = "base.en" 
CLIPS_DIR = os.path.join(os.getcwd(), "data", "dataset", "clips")
SOURCES_DIR = os.path.join(os.getcwd(), "data", "sources")

# Initialize Whisper Model (Lazy load)
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
        "--postprocessor-args", "ffmpeg:-ar 16000 -ac 1", 
        "-o", output_template,
        url
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        files = [f for f in os.listdir(SOURCES_DIR) if f.endswith('.wav')]
        if files:
            files.sort(key=lambda x: os.path.getmtime(os.path.join(SOURCES_DIR, x)), reverse=True)
            return os.path.join(SOURCES_DIR, files[0])
    except Exception as e:
        print(f"YT-DLP Error: {e}")
    return None

def process_audio_file(file_path: str, source_id: int):
    """Main pipeline: Transcribe -> Segment -> Save Clips"""
    model = get_whisper_model()
    print(f"Processing {file_path}...")
    
    # 1. Transcribe
    segments, info = model.transcribe(file_path, word_timestamps=True, language="en")
    
    # Load audio for slicing
    audio_data, sr = librosa.load(file_path, sr=16000)
    
    base_clips_dir = os.path.join(os.getcwd(), "data", "dataset", "clips")
    clip_count = 0
    
    for segment in segments:
        for word_obj in segment.words:
            word_text = word_obj.word.strip()
            if not word_text: continue
            
            normalized = word_text.lower().strip(".,!?;:\"'")
            if not normalized: continue

            # Calculate padding
            pad_start = 0.05 
            pad_end = 0.05
            
            start_sample = int((word_obj.start - pad_start) * sr)
            end_sample = int((word_obj.end + pad_end) * sr)
            
            # Boundary checks
            start_sample = max(0, start_sample)
            end_sample = min(len(audio_data), end_sample)
            
            # Extract snippet
            snippet = audio_data[start_sample:end_sample]
            
            # Skip if too short
            if len(snippet) < sr * 0.1: continue
                
            duration_ms = (len(snippet) / sr) * 1000
            
            # Pitch estimation
            pitch_hz = 0.0
            try:
                pitches, magnitudes = librosa.piptrack(y=snippet, sr=sr)
                threshold = np.median(magnitudes)
                valid_pitches = pitches[magnitudes > threshold]
                if valid_pitches.size > 0:
                    pitch_hz = float(np.median(valid_pitches))
            except:
                pass

            # NEW: Hash-based pathing
            rel_path = db.get_clip_path_hash(normalized, source_id, word_obj.start)
            full_path = os.path.join(base_clips_dir, rel_path + ".wav")
            
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Save snippet
            sf.write(full_path, snippet, sr)
            
            # Store Metadata
            db.add_clip({
                "word": word_text,
                "normalized_word": normalized,
                "source_id": source_id,
                "start": word_obj.start,
                "end": word_obj.end,
                "path": os.path.join("data", "dataset", "clips", rel_path + ".wav"),
                "confidence": word_obj.probability if hasattr(word_obj, 'probability') else 1.0,
                "duration": duration_ms,
                "pitch": pitch_hz,
                "loudness": -20.0,
                "ctx_before": "",
                "ctx_after": ""
            })
            clip_count += 1

    print(f"Extraction complete. {clip_count} clips added.")

def rank_clips(clips: list, context_token: str, recently_used: list):
    if not clips: return None
    available = [c for c in clips if c['id'] not in recently_used]
    if not available: available = clips 
    
    available.sort(key=lambda x: x['confidence'], reverse=True)
    top_n = min(3, len(available))
    return random.choice(available[:top_n])

def generate_speech(text: str, voice_id: str = "default", seed: int = None, filter_preset: str = "robot_radio"):
    if seed:
        random.seed(seed)
        
    tokens = text.split()
    final_audio = AudioSegment.silent(duration=0)
    last_clip_path = None
    
    for i, token in enumerate(tokens):
        clean_token = token.lower().strip(".,!?;:\"'")
        if not clean_token: continue
        
        clips = db.get_clips_for_word(clean_token)
        seg = None
        
        if clips:
            selected_clip = rank_clips(clips, token, []) 
            clip_rel_path = selected_clip['file_path']
            clip_abs_path = os.path.join(os.getcwd(), clip_rel_path)
            
            if os.path.exists(clip_abs_path):
                # Prosody Matching
                if last_clip_path and os.path.exists(last_clip_path):
                    try:
                        shifted_array = match_prosody(last_clip_path, clip_abs_path)
                        seg = AudioSegment(
                            shifted_array.tobytes(), 
                            frame_rate=16000, 
                            sample_width=2, 
                            channels=1
                        )
                    except Exception as e:
                        print(f"Prosody fail: {e}")
                        seg = AudioSegment.from_wav(clip_abs_path)
                else:
                    seg = AudioSegment.from_wav(clip_abs_path)
                
                last_clip_path = clip_abs_path
            else:
                seg = generate_espeak_fallback(token)
        else:
            seg = generate_espeak_fallback(token)
            last_clip_path = None 

        if seg:
            pause_len = random.randint(30, 80) 
            final_audio += seg + AudioSegment.silent(duration=pause_len)

    if final_audio.duration_seconds > 0:
        final_audio = apply_filter_chain(final_audio, filter_preset)
    
    out_buf = io.BytesIO()
    final_audio.export(out_buf, format="wav")
    out_buf.seek(0)
    return out_buf
