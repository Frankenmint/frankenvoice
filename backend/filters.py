from pydub import AudioSegment
from pydub.effects import normalize
import numpy as np
import random

def apply_filter_chain(audio: AudioSegment, preset: str = "robot_radio") -> AudioSegment:
    """Router for audio presets"""
    if preset == "clean":
        return normalize(audio, headroom=2.0)
    
    elif preset == "robot_radio":
        return apply_radio_filter(audio)
    
    elif preset == "telephone":
        return apply_telephone_filter(audio)
        
    elif preset == "damaged_tape":
        return apply_tape_filter(audio)
        
    else:
        # Default fallback
        return apply_radio_filter(audio)

def apply_radio_filter(audio: AudioSegment) -> AudioSegment:
    # Bandpass for radio sound
    audio = audio.high_pass_filter(300)
    audio = audio.low_pass_filter(3400)
    # Heavy compression via normalization
    audio = normalize(audio, headroom=1.0)
    return audio

def apply_telephone_filter(audio: AudioSegment) -> AudioSegment:
    # Narrower bandpass
    audio = audio.high_pass_filter(600)
    audio = audio.low_pass_filter(2500)
    audio = normalize(audio, headroom=0.5)
    return audio

def apply_tape_filter(audio: AudioSegment) -> AudioSegment:
    # Simulate wow/flutter by slightly shifting speed (simplified)
    # And add some noise floor
    audio = audio.low_pass_filter(5000)
    audio = normalize(audio, headroom=3.0)
    
    # Add simple static noise
    noise = AudioSegment.silent(duration=len(audio))
    # Generate random noise data
    noise_samples = np.random.normal(0, 500, len(audio.get_array_of_samples()))
    noise = audio._spawn(noise_samples.astype(np.int16).tobytes())
    
    # Mix noise at low volume
    audio = audio.overlay(noise - 20)
    return audio
