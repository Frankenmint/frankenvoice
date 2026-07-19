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
    speed: float = 1.0,
    pause_scale: float = 1.0,
) -> GenerationResult:
    """Always synthesize final speech from independently selected word clips."""
    return GenerationResult(
        audio_buffer=engine.generate_speech(
            text=text,
            voice_id=voice_id,
            seed=seed,
            filter_preset=filter_preset,
            speed=speed,
            pause_scale=pause_scale,
        )
    )


def get_provider_status() -> dict:
    config = QwenCloudConfig.from_env()
    return {
        "speech_strategy": "composite_only",
        "final_speech": {
            "provider": "frankenvoice_fragment_engine",
            "whole_sentence_cloud_tts": False,
            "voice_count": 1,
        },
        "qwen_enrichment": {
            "configured": config.configured,
            "asr_model": config.asr_model,
            "tts_model": config.tts_model,
            "voices": list(config.voices),
            "strategy": "transcribe_sources_and_expand_shared_vocabulary",
        },
    }
