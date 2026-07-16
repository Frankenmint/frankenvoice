import numpy as np
from pydub import AudioSegment
from pydub.effects import normalize


def apply_filter_chain(audio: AudioSegment, preset: str = "robot_radio") -> AudioSegment:
    if preset == "clean":
        return normalize(audio, headroom=2.0)
    if preset == "telephone":
        return apply_telephone_filter(audio)
    if preset == "damaged_tape":
        return apply_tape_filter(audio)
    return apply_radio_filter(audio)


def apply_radio_filter(audio: AudioSegment) -> AudioSegment:
    return normalize(audio.high_pass_filter(300).low_pass_filter(3400), headroom=1.0)


def apply_telephone_filter(audio: AudioSegment) -> AudioSegment:
    return normalize(audio.high_pass_filter(600).low_pass_filter(2500), headroom=0.5)


def apply_tape_filter(audio: AudioSegment) -> AudioSegment:
    audio = normalize(audio.low_pass_filter(5000), headroom=3.0).set_sample_width(2)
    samples = np.asarray(audio.get_array_of_samples(), dtype=np.int16)
    noise_samples = np.random.normal(0, 500, samples.size).astype(np.int16)
    noise = AudioSegment(
        data=noise_samples.tobytes(),
        sample_width=2,
        frame_rate=audio.frame_rate,
        channels=audio.channels,
    )
    return audio.overlay(noise - 20)
