import io
import random
import re
import subprocess
from pathlib import Path
from typing import Optional

import numpy as np
from pydub import AudioSegment

from backend import db
from backend.audio_processing import generate_espeak_fallback, match_prosody
from backend.filters import apply_filter_chain

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLIPS_DIR = PROJECT_ROOT / "data" / "dataset" / "clips"
SOURCES_DIR = PROJECT_ROOT / "data" / "sources"
MODEL_SIZE = "base.en"
whisper_model = None


def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("faster-whisper is required for source transcription") from exc
        whisper_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return whisper_model


def ingest_youtube(url: str) -> Optional[str]:
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    output_template = str(SOURCES_DIR / "%(id)s.%(ext)s")
    cmd = [
        "yt-dlp", "-x", "--audio-format", "wav",
        "--postprocessor-args", "ffmpeg:-ar 16000 -ac 1",
        "-o", output_template, url,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        wav_files = sorted(SOURCES_DIR.glob("*.wav"), key=lambda path: path.stat().st_mtime, reverse=True)
        return str(wav_files[0]) if wav_files else None
    except (OSError, subprocess.CalledProcessError) as exc:
        stderr = getattr(exc, "stderr", "")
        print(f"yt-dlp failed: {stderr or exc}")
        return None


def process_audio_file(file_path: str, source_id: int) -> None:
    if not file_path or not Path(file_path).exists():
        db.update_source_status(source_id, "failed")
        raise FileNotFoundError(f"Audio source not found: {file_path}")
    try:
        import librosa
        import soundfile as sf

        model = get_whisper_model()
        db.update_source_status(source_id, "processing")
        segments, _ = model.transcribe(file_path, word_timestamps=True, language="en")
        audio_data, sr = librosa.load(file_path, sr=16000)
        CLIPS_DIR.mkdir(parents=True, exist_ok=True)
        for segment in segments:
            for word_obj in segment.words or []:
                word_text = word_obj.word.strip()
                normalized = word_text.lower().strip(".,!?;:\"'")
                if not normalized:
                    continue
                start_sample = max(0, int((word_obj.start - 0.05) * sr))
                end_sample = min(len(audio_data), int((word_obj.end + 0.05) * sr))
                snippet = audio_data[start_sample:end_sample]
                if len(snippet) < sr * 0.1:
                    continue
                pitch_hz = 0.0
                try:
                    pitches, magnitudes = librosa.piptrack(y=snippet, sr=sr)
                    threshold = np.median(magnitudes)
                    valid_pitches = pitches[magnitudes > threshold]
                    if valid_pitches.size:
                        pitch_hz = float(np.median(valid_pitches))
                except Exception:
                    pass
                rel_path = db.get_clip_path_hash(normalized, source_id, word_obj.start)
                full_path = CLIPS_DIR / f"{rel_path}.wav"
                full_path.parent.mkdir(parents=True, exist_ok=True)
                sf.write(full_path, snippet, sr)
                db.add_clip({
                    "word": word_text,
                    "normalized_word": normalized,
                    "source_id": source_id,
                    "start": word_obj.start,
                    "end": word_obj.end,
                    "confidence": getattr(word_obj, "probability", 1.0),
                    "duration": (len(snippet) / sr) * 1000,
                    "pitch": pitch_hz,
                    "loudness": -20.0,
                    "ctx_before": "",
                    "ctx_after": "",
                })
        db.update_source_status(source_id, "complete")
    except Exception:
        db.update_source_status(source_id, "failed")
        raise


def rank_clips(
    clips: list,
    recently_used: list[int],
    recent_sources: list[int],
    rng: random.Random,
    variation: int = 50,
    source_diversity: int = 50,
):
    if not clips:
        return None
    unused = [clip for clip in clips if clip["id"] not in recently_used] or clips
    if source_diversity > 0 and recent_sources:
        diverse = [clip for clip in unused if clip.get("source_id") not in recent_sources]
        if diverse and rng.random() < source_diversity / 100:
            unused = diverse
    unused.sort(key=lambda clip: clip.get("confidence") or 0.0, reverse=True)
    pool_size = max(1, min(len(unused), 1 + round((variation / 100) * (len(unused) - 1))))
    return rng.choice(unused[:pool_size])


def _audio_segment_from_float(samples: np.ndarray, sr: int = 16000) -> AudioSegment:
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    return AudioSegment(data=pcm.tobytes(), sample_width=2, frame_rate=sr, channels=1)


def _pause_for(separator: str, rng: random.Random, pause_scale: float) -> int:
    if "\n\n" in separator:
        base = rng.randint(550, 850)
    elif re.search(r"[.!?]", separator):
        base = rng.randint(280, 450)
    elif re.search(r"[:;]", separator):
        base = rng.randint(160, 240)
    elif "," in separator:
        base = rng.randint(100, 180)
    else:
        base = rng.randint(30, 80)
    return max(0, int(base * pause_scale))


def _apply_speed(audio: AudioSegment, speed: float) -> AudioSegment:
    if abs(speed - 1.0) < 0.01:
        return audio
    altered = audio._spawn(audio.raw_data, overrides={"frame_rate": max(1000, int(audio.frame_rate * speed))})
    return altered.set_frame_rate(16000)


def _apply_glitch(audio: AudioSegment, glitch: int, rng: random.Random) -> AudioSegment:
    if glitch <= 0 or len(audio) < 120:
        return audio
    intensity = min(100, max(0, glitch)) / 100
    event_count = max(1, round((len(audio) / 1000) * intensity * 2.5))
    result = audio
    for _ in range(event_count):
        if len(result) < 100:
            break
        start = rng.randint(0, max(0, len(result) - 80))
        width = rng.randint(20, min(90, len(result) - start))
        fragment = result[start:start + width]
        if rng.random() < 0.55:
            repeats = 1 + round(intensity * 3)
            result = result[:start] + (fragment * repeats) + result[start + width:]
        else:
            result = result[:start] + AudioSegment.silent(duration=width, frame_rate=16000) + result[start + width:]
    return result


def generate_speech(
    text: str,
    voice_id: str = "default",
    seed: Optional[int] = None,
    filter_preset: str = "robot_radio",
    speed: float = 1.0,
    pause_scale: float = 1.0,
    variation: int = 50,
    source_diversity: int = 50,
    glitch: int = 0,
):
    del voice_id
    rng = random.Random(seed)
    matches = list(re.finditer(r"[A-Za-z0-9']+", text))
    final_audio = AudioSegment.silent(duration=0, frame_rate=16000)
    last_clip_path: Optional[Path] = None
    recently_used: list[int] = []
    recent_sources: list[int] = []

    for index, match in enumerate(matches):
        token = match.group(0)
        clips = db.get_clips_for_word(token.lower())
        selected_clip = rank_clips(
            clips, recently_used, recent_sources, rng,
            variation=variation, source_diversity=source_diversity,
        )
        seg = None
        if selected_clip:
            clip_path = Path(selected_clip["file_path"])
            clip_path = clip_path if clip_path.is_absolute() else PROJECT_ROOT / clip_path
            if clip_path.exists():
                if last_clip_path and last_clip_path.exists():
                    shifted = match_prosody(str(last_clip_path), str(clip_path))
                    if shifted.size:
                        seg = _audio_segment_from_float(shifted)
                if seg is None:
                    seg = AudioSegment.from_wav(clip_path)
                last_clip_path = clip_path
                recently_used.append(selected_clip["id"])
                recently_used = recently_used[-12:]
                source_id = selected_clip.get("source_id")
                if source_id is not None:
                    recent_sources.append(source_id)
                    recent_sources = recent_sources[-3:]
        if seg is None:
            seg = generate_espeak_fallback(token)
            last_clip_path = None
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        separator = text[match.end():next_start]
        final_audio += seg + AudioSegment.silent(duration=_pause_for(separator, rng, pause_scale), frame_rate=16000)

    if len(final_audio) == 0:
        final_audio = AudioSegment.silent(duration=100, frame_rate=16000)
    final_audio = apply_filter_chain(final_audio, filter_preset)
    final_audio = _apply_speed(final_audio, min(2.0, max(0.5, speed)))
    final_audio = _apply_glitch(final_audio, glitch, rng)

    out_buf = io.BytesIO()
    final_audio.export(out_buf, format="wav")
    out_buf.seek(0)
    return out_buf
