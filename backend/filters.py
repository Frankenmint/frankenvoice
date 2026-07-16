# Inside app.py or a dedicated synthesizer module

from pydub import AudioSegment
from pydub.effects import normalize
import random
import io
from db import get_clips_for_word
from filters import apply_radio_filter # Defined below

def generate_speech(text: str, seed: int = None, filter_preset: str = "robot_radio"):
    if seed:
        random.seed(seed)
        
    tokens = text.split()
    final_audio = AudioSegment.silent(duration=0)
    
    for token in tokens:
        clean_token = token.lower().strip(".,!?;:\"'")
        
        # 1. Try to find clip
        clips = get_clips_for_word(clean_token)
        
        if clips:
            # Select random clip
            selected = random.choice(clips)
            clip_path = selected['file_path']
            try:
                seg = AudioSegment.from_wav(clip_path)
                # Trim silence from edges of clip for tighter stitching
                seg = seg.strip_silence(silence_thresh=-40, padding=10)
            except Exception as e:
                print(f"Error loading clip {clip_path}: {e}")
                seg = generate_fallback_tts(token) # Fallback
        else:
            # 2. Fallback TTS (Mocked for MVP, would use pyttsx3 or similar)
            seg = generate_fallback_tts(token)
            
        # Add small pause between words (randomized slightly for human feel)
        pause_len = random.randint(50, 150) 
        final_audio += seg + AudioSegment.silent(duration=pause_len)

    # 3. Apply Global Filter
    if filter_preset == "robot_radio":
        final_audio = apply_radio_filter(final_audio)
        
    # 4. Export to Bytes
    out_buf = io.BytesIO()
    final_audio.export(out_buf, format="wav")
    out_buf.seek(0)
    return out_buf

def generate_fallback_tts(text):
    """Simple fallback using system TTS or silent placeholder"""
    # For hackathon MVP, we might just return a silent beep or use pyttsx3
    # Here returning a generated tone for demonstration
    return AudioSegment.silent(duration=len(text)*100) 

# In filters.py
def apply_radio_filter(audio: AudioSegment) -> AudioSegment:
    # High Pass Filter (remove rumble)
    audio = audio.high_pass_filter(300)
    # Low Pass Filter (telephone effect)
    audio = audio.low_pass_filter(3000)
    # Compression (squash dynamics)
    # Pydub doesn't have native complex compression, so we normalize heavily
    audio = normalize(audio, headroom=1.0)
    # Add slight static noise (optional)
    return audio
