import os
import subprocess
import tempfile

import numpy as np
from pydub import AudioSegment


def generate_espeak_fallback(text: str) -> AudioSegment:
    """Generate a fallback word using espeak-ng, or silence when unavailable."""
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = temp_file.name

        subprocess.run(
            ["espeak-ng", "-v", "en-us", "-w", temp_path, text],
            check=True,
            capture_output=True,
        )
        return (
            AudioSegment.from_wav(temp_path)
            .set_frame_rate(16000)
            .set_channels(1)
            .normalize(headroom=2.0)
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"espeak-ng fallback unavailable: {exc}")
        return AudioSegment.silent(duration=max(100, len(text) * 100), frame_rate=16000)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def match_prosody(prev_clip_path: str, current_clip_path: str, sr: int = 16000):
    """Pitch-shift current clip toward previous clip; return float audio samples."""
    try:
        import librosa
        import pyrubberband as pyrb

        prev_y, _ = librosa.load(prev_clip_path, sr=sr)
        curr_y, _ = librosa.load(current_clip_path, sr=sr)
        if len(curr_y) == 0:
            return curr_y

        prev_f0 = librosa.yin(prev_y, fmin=50, fmax=500)
        curr_f0 = librosa.yin(curr_y, fmin=50, fmax=500)
        prev_end_pitch = np.nanmedian(prev_f0[-max(1, len(prev_f0) // 4) :])
        curr_start_pitch = np.nanmedian(curr_f0[: max(1, len(curr_f0) // 4)])

        if (
            np.isfinite(prev_end_pitch)
            and np.isfinite(curr_start_pitch)
            and prev_end_pitch > 0
            and curr_start_pitch > 0
        ):
            semitones = float(
                np.clip(12 * np.log2(prev_end_pitch / curr_start_pitch), -2.5, 2.5)
            )
            return pyrb.pitch_shift(curr_y, sr, n_steps=semitones)
        return curr_y
    except Exception as exc:
        print(f"Prosody matching unavailable: {exc}")
        try:
            import librosa

            curr_y, _ = librosa.load(current_clip_path, sr=sr)
            return curr_y
        except Exception:
            return np.array([], dtype=np.float32)
