import io
from dataclasses import dataclass
from typing import Literal, Optional

from pydub import AudioSegment

from backend import engine
from backend.filters import apply_filter_chain
from backend.qwen_cloud import QwenCloudConfig, QwenCloudError, synthesize_qwen


ProviderPreference = Literal["auto", "qwen_cloud", "local"]


@dataclass
class GenerationResult:
    audio_buffer: io.BytesIO
    provider: Literal["qwen_cloud", "local"]
    fallback_reason: Optional[str] = None


def _export_cloud_audio(
    audio: AudioSegment,
    filter_preset: str,
) -> io.BytesIO:
    normalized = audio.set_channels(1).set_frame_rate(16000)
    filtered = apply_filter_chain(normalized, filter_preset)
    output = io.BytesIO()
    filtered.export(output, format="wav")
    output.seek(0)
    return output


def generate_speech_with_fallback(
    text: str,
    voice_id: str = "default",
    seed: Optional[int] = None,
    filter_preset: str = "robot_radio",
    provider: ProviderPreference = "auto",
    qwen_voice: Optional[str] = None,
) -> GenerationResult:
    fallback_reason = None

    if provider in ("auto", "qwen_cloud"):
        try:
            cloud_audio = synthesize_qwen(text, qwen_voice or voice_id)
            return GenerationResult(
                audio_buffer=_export_cloud_audio(cloud_audio, filter_preset),
                provider="qwen_cloud",
            )
        except QwenCloudError as exc:
            fallback_reason = str(exc)

    local_audio = engine.generate_speech(
        text=text,
        voice_id=voice_id,
        seed=seed,
        filter_preset=filter_preset,
    )
    return GenerationResult(
        audio_buffer=local_audio,
        provider="local",
        fallback_reason=fallback_reason,
    )


def get_provider_status() -> dict:
    config = QwenCloudConfig.from_env()
    return {
        "default": "auto",
        "strategy": "qwen_cloud_first_local_fallback",
        "qwen_cloud": {
            "configured": config.configured,
            "model": config.model,
            "voice": config.voice,
            "endpoint": config.endpoint,
        },
        "local": {"available": True},
    }
