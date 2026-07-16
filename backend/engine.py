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
            raise RuntimeError(
                "faster-whisper is required for source transcription"
            ) from exc
        whisper_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return whisper_model


def ingest_youtube(url: str) -> Optional[str]:
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    output_template = str(SOURCES_DIR / "%(id)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format",
        "wav",
        "--postprocessor-args",
        "ffmpeg:-ar 16000 -ac 1",
        "-o",
        output_template,
        url,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        wav_files = sorted(
            SOURCES_DIR.glob("*.wav"), key=lambda path: path.stat().st_mtime, reverse=True
        )
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
        segments, _ = model.transcribe(
            file_path, word_timestamps=True, language="en"
        )
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

                db.add_clip(
                    {
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
                    }
                )
        db.update_source_status(source_id, "complete")
    except Exception:
        db.update_source_status(source_id, "failed")
        raise


def rank_clips(clips: list, recently_used: list, rng: random.Random):
    if not clips:
        return None
    available = [clip for clip in clips if clip["id"] not in recently_used] or clips
    available.sort(key=lambda clip: clip.get("confidence") or 0.0, reverse=True)
    return rng.choice(available[: min(3, len(available))])


def _audio_segment_from_float(samples: np.ndarray, sr: int = 16000) -> AudioSegment:
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    return AudioSegment(
        data=pcm.tobytes(), sample_width=2, frame_rate=sr, channels=1
    )


def generate_speech(
    text: str,
    voice_id: str = "default",
    seed: Optional[int] = None,
    filter_preset: str = "robot_radio",
):
    del voice_id
    rng = random.Random(seed)
    tokens = re.findall(r"[A-Za-z0-9']+", text)
    final_audio = AudioSegment.silent(duration=0, frame_rate=16000)
    last_clip_path: Optional[Path] = None
    recently_used = []

    for token in tokens:
        clips = db.get_clips_for_word(token.lower())
        selected_clip = rank_clips(clips, recently_used, rng)
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
                recently_used = recently_used[-10:]

        if seg is None:
            seg = generate_espeak_fallback(token)
            last_clip_path = None

        final_audio += seg + AudioSegment.silent(
            duration=rng.randint(30, 80), frame_rate=16000
        )

    if len(final_audio) == 0:
        final_audio = AudioSegment.silent(duration=100, frame_rate=16000)
    final_audio = apply_filter_chain(final_audio, filter_preset)

    out_buf = io.BytesIO()
    final_audio.export(out_buf, format="wav")
    out_buf.seek(0)
    return out_buf
