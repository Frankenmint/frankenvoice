import re
import time
from pathlib import Path
from typing import Iterable

from pydub import AudioSegment

from backend import db
from backend.qwen_cloud import (
    QwenCloudConfig,
    QwenCloudError,
    synthesize_word,
    transcribe_audio_url,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[A-Za-z0-9']+", text)]


def coverage_for_text(text: str, target_variants: int = 3) -> dict:
    words = tokenize(text)
    counts = db.get_word_counts(words)
    rows = [
        {
            "word": word,
            "variants": counts.get(word, 0),
            "needed": max(0, target_variants - counts.get(word, 0)),
        }
        for word in dict.fromkeys(words)
    ]
    return {
        "target_variants": target_variants,
        "complete": all(row["needed"] == 0 for row in rows),
        "words": rows,
    }


def transcribe_source_with_qwen(source_id: int, audio_url: str) -> dict:
    """Use Qwen for timestamps, then cut real words from the local source recording."""
    source = db.get_source(source_id)
    if not source:
        raise ValueError(f"Source {source_id} does not exist")
    source_path = Path(source["file_path"])
    if not source_path.is_absolute():
        source_path = PROJECT_ROOT / source_path
    if not source_path.exists():
        raise ValueError("Local source audio is unavailable")

    rows = transcribe_audio_url(audio_url)
    recording = AudioSegment.from_file(source_path).set_channels(1).set_frame_rate(16000)
    created: list[dict] = []

    for row in rows:
        word = str(row.get("word", "")).strip()
        normalized = tokenize(word)
        if not normalized:
            continue
        try:
            start = max(0.0, float(row.get("start", 0.0)))
            end = max(start, float(row.get("end", start)))
            confidence = float(row.get("confidence", 1.0))
        except (TypeError, ValueError):
            continue
        if end <= start:
            continue

        padded_start_ms = max(0, int((start - 0.05) * 1000))
        padded_end_ms = min(len(recording), int((end + 0.05) * 1000))
        segment = recording[padded_start_ms:padded_end_ms]
        if len(segment) < 80:
            continue

        canonical_word = normalized[0]
        rel_path = db.get_clip_path_hash(canonical_word, source_id, start)
        full_path = PROJECT_ROOT / "data" / "dataset" / "clips" / f"{rel_path}.wav"
        full_path.parent.mkdir(parents=True, exist_ok=True)
        segment.export(full_path, format="wav")
        clip_id = db.add_clip(
            {
                "word": word,
                "normalized_word": canonical_word,
                "source_id": source_id,
                "start": start,
                "end": end,
                "confidence": confidence,
                "duration": len(segment),
                "provenance": "original",
            }
        )
        created.append({"word": canonical_word, "clip_id": clip_id})

    db.set_source_transcription_provider(source_id, "qwen_asr")
    db.update_source_status(source_id, "complete")
    return {"source_id": source_id, "provider": "qwen_asr", "created": created}


def enrich_missing_words(
    words: Iterable[str],
    target_variants: int = 3,
) -> dict:
    """Add missing single-word variants to one shared FrankenVoice corpus."""
    normalized_words = list(dict.fromkeys(word.lower() for word in words if word.strip()))
    counts = db.get_word_counts(normalized_words)
    source_id = db.get_or_create_derived_source()
    config = QwenCloudConfig.from_env()
    created: list[dict] = []
    failures: list[dict] = []

    for word in normalized_words:
        missing = max(0, target_variants - counts.get(word, 0))
        for variant_index in range(missing):
            voice = config.voices[variant_index % len(config.voices)]
            try:
                segment = synthesize_word(word, voice, config=config)
                start_marker = time.time() + variant_index / 1000
                rel_path = db.get_clip_path_hash(word, source_id, start_marker)
                full_path = PROJECT_ROOT / "data" / "dataset" / "clips" / f"{rel_path}.wav"
                full_path.parent.mkdir(parents=True, exist_ok=True)
                segment.export(full_path, format="wav")
                clip_id = db.add_clip(
                    {
                        "word": word,
                        "normalized_word": word,
                        "source_id": source_id,
                        "start": start_marker,
                        "end": start_marker + len(segment) / 1000,
                        "confidence": 1.0,
                        "duration": len(segment),
                        "provenance": "qwen_derived",
                        "voice_profile_id": voice,
                    }
                )
                created.append({"word": word, "clip_id": clip_id, "voice": voice})
            except QwenCloudError as exc:
                failures.append({"word": word, "reason": str(exc)})
                break

    return {
        "source_id": source_id,
        "corpus": db.DERIVED_SOURCE_TITLE,
        "created": created,
        "failures": failures,
    }
