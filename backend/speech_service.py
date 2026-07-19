import io
from dataclasses import dataclass
from typing import Optional

from backend import engine
from backend.qwen_cloud import QwenCloudConfig


@dataclass
class GenerationResult:
    audio_buffer: io.BytesIO
    provider: str = "composite"
    fallback_reason: Optional[str] = None


def generate_composite_speech(
    text: str,
    voice_id: str = "default",
    seed: Optional[int] = None,
    filter_preset: str = "robot_radio",
) -> GenerationResult:
    """Always synthesize final speech from independently selected word clips."""
    return GenerationResult(
        audio_buffer=engine.generate_speech(
            text=text,
            voice_id=voice_id,
            seed=seed,
            filter_preset=filter_preset,
        )
    )


def get_provider_status() -> dict:
    config = QwenCloudConfig.from_env()
    return {
        "speech_strategy": "composite_only",
        "final_speech": {
            "provider": "frankenvoice_fragment_engine",
            "whole_sentence_cloud_tts": False,
        },
        "qwen_enrichment": {
            "configured": config.configured,
            "asr_model": config.asr_model,
            "tts_model": config.tts_model,
            "strategy": "transcribe_sources_and_fill_missing_words",
        },
    }
