import numpy as np
import librosa
import pyrubberband as pyrb
from pydub import AudioSegment
import subprocess
import os

def generate_espeak_fallback(text: str) -> AudioSegment:
    """Generate a fallback word using espeak-ng"""
    temp_wav = "temp_fallback.wav"
    try:
        # Check if espeak-ng is available
        cmd = ["espeak-ng", "-v", "en-us", "-w", temp_wav, text]
        subprocess.run(cmd, check=True, capture_output=True)
        
        seg = AudioSegment.from_wav(temp_wav)
        # Normalize to dataset standards (16kHz Mono)
        seg = seg.set_frame_rate(16000).set_channels(1).normalize(headroom=2.0)
        
        # Cleanup
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
            
        return seg
    except Exception as e:
        print(f"Espeak failed: {e}")
        # Return silent segment if espeak fails
        return AudioSegment.silent(duration=len(text) * 100)

def match_prosody(prev_clip_path: str, current_clip_path: str, sr=16000):
    """
    Adjusts the pitch of current_clip to match the ending pitch of prev_clip.
    Returns the audio array of the current clip, pitch-shifted.
    """
    # Initialize return variable to None
    shifted_y = None
    
    try:
        # Load audio
        prev_y, _ = librosa.load(prev_clip_path, sr=sr)
        curr_y, _ = librosa.load(current_clip_path, sr=sr)
        
        # Safety check: if audio is empty, return original
        if len(curr_y) == 0:
            return curr_y
            
        # Get Pitch Contours
        prev_f0 = librosa.yin(prev_y, fmin=50, fmax=500)
        curr_f0 = librosa.yin(curr_y, fmin=50, fmax=500)
        
        # Get average pitch of last 25% of prev word
        prev_end_pitch = np.nanmedian(prev_f0[-len(prev_f0)//4:])
        
        # Get average pitch of first 25% of curr word
        curr_start_pitch = np.nanmedian(curr_f0[:len(curr_f0)//4])
        
        # Calculate shift only if both pitches are valid (> 0)
        if prev_end_pitch > 0 and curr_start_pitch > 0:
            semitones = 12 * np.log2(prev_end_pitch / curr_start_pitch)
            
            # Clamp to avoid chipmunk/demon effects
            semitones = np.clip(semitones, -2.5, 2.5)
            
            # Apply shift with formant preservation
            shifted_y = pyrb.pitch_shift(curr_y, sr, n_steps=semitones)
            
    except Exception as e:
        print(f"Prosody matching failed: {e}")
        
    # If shifting failed or wasn't needed, return the original current audio
    if shifted_y is None:
        try:
            # Reload just to be safe if curr_y wasn't defined due to early error
            curr_y, _ = librosa.load(current_clip_path, sr=sr)
            return curr_y
        except:
            # Ultimate fallback: return empty array if all else fails
            return np.array([])
            
    return shifted_y
