import re
import time
from pathlib import Path
from typing import Iterable

from backend import db
from backend.qwen_cloud import QwenCloudError, synthesize_word

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


def enrich_missing_words(
    source_id: int,
    words: Iterable[str],
    target_variants: int = 3,
) -> dict:
    source = db.get_source(source_id)
    if not source:
        raise ValueError(f"Source {source_id} does not exist")
    voice_id = (source.get("qwen_voice_id") or "").strip()
    if not voice_id:
        raise ValueError("Source does not have a Qwen voice profile")

    normalized_words = list(dict.fromkeys(word.lower() for word in words if word.strip()))
    counts = db.get_word_counts(normalized_words)
    created: list[dict] = []
    failures: list[dict] = []

    for word in normalized_words:
        missing = max(0, target_variants - counts.get(word, 0))
        for variant_index in range(missing):
            try:
                segment = synthesize_word(word, voice_id)
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
                        "voice_profile_id": voice_id,
                    }
                )
                created.append({"word": word, "clip_id": clip_id})
            except QwenCloudError as exc:
                failures.append({"word": word, "reason": str(exc)})
                break

    return {
        "source_id": source_id,
        "voice_profile_id": voice_id,
        "created": created,
        "failures": failures,
    }
