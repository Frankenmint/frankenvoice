import io
import json
import os
from dataclasses import dataclass
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydub import AudioSegment


DEFAULT_ENDPOINT = (
    "https://dashscope-intl.aliyuncs.com/api/v1/services/"
    "aigc/multimodal-generation/generation"
)


class QwenCloudError(RuntimeError):
    """Raised when Qwen Cloud synthesis cannot produce usable audio."""


@dataclass(frozen=True)
class QwenCloudConfig:
    api_key: str
    endpoint: str = DEFAULT_ENDPOINT
    model: str = "qwen3-tts-flash"
    voice: str = "Cherry"
    language_type: str = "English"
    timeout_seconds: float = 45.0

    @classmethod
    def from_env(cls) -> "QwenCloudConfig":
        timeout_value = os.getenv("QWEN_TTS_TIMEOUT_SECONDS", "45")
        try:
            timeout_seconds = max(1.0, float(timeout_value))
        except ValueError:
            timeout_seconds = 45.0

        return cls(
            api_key=os.getenv("DASHSCOPE_API_KEY", "").strip(),
            endpoint=os.getenv("QWEN_TTS_ENDPOINT", DEFAULT_ENDPOINT).strip()
            or DEFAULT_ENDPOINT,
            model=os.getenv("QWEN_TTS_MODEL", "qwen3-tts-flash").strip()
            or "qwen3-tts-flash",
            voice=os.getenv("QWEN_TTS_VOICE", "Cherry").strip() or "Cherry",
            language_type=os.getenv("QWEN_TTS_LANGUAGE", "English").strip()
            or "English",
            timeout_seconds=timeout_seconds,
        )

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.endpoint)


def _extract_audio_url(payload: dict[str, Any]) -> str:
    output = payload.get("output")
    if not isinstance(output, dict):
        return ""

    audio = output.get("audio")
    if isinstance(audio, dict):
        url = audio.get("url")
        if isinstance(url, str):
            return url

    for key in ("audio_url", "url"):
        value = output.get(key)
        if isinstance(value, str):
            return value

    return ""


def _request_json(
    request: Request,
    timeout_seconds: float,
) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise QwenCloudError(
            f"Qwen Cloud returned HTTP {exc.code}: {detail}"
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise QwenCloudError(f"Qwen Cloud request failed: {exc}") from exc

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QwenCloudError("Qwen Cloud returned invalid JSON") from exc

    if not isinstance(payload, dict):
        raise QwenCloudError("Qwen Cloud returned an unexpected response")

    code = payload.get("code")
    if code:
        message = payload.get("message") or code
        raise QwenCloudError(f"Qwen Cloud rejected synthesis: {message}")

    return payload


def _download_audio(url: str, timeout_seconds: float) -> bytes:
    request = Request(url, method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            audio_bytes = response.read()
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise QwenCloudError(f"Unable to download Qwen audio: {exc}") from exc

    if not audio_bytes:
        raise QwenCloudError("Qwen Cloud returned empty audio")
    return audio_bytes


def synthesize_qwen(
    text: str,
    voice_id: Optional[str] = None,
    config: Optional[QwenCloudConfig] = None,
) -> AudioSegment:
    config = config or QwenCloudConfig.from_env()
    if not config.configured:
        raise QwenCloudError("DASHSCOPE_API_KEY is not configured")

    voice = (
        voice_id.strip()
        if voice_id and voice_id.strip() and voice_id != "default"
        else config.voice
    )
    body = {
        "model": config.model,
        "input": {
            "text": text,
            "voice": voice,
            "language_type": config.language_type,
        },
    }
    request = Request(
        config.endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    payload = _request_json(request, config.timeout_seconds)
    audio_url = _extract_audio_url(payload)
    if not audio_url:
        raise QwenCloudError("Qwen Cloud response did not include an audio URL")

    audio_bytes = _download_audio(audio_url, config.timeout_seconds)
    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    except Exception as exc:
        raise QwenCloudError("Qwen Cloud returned unreadable audio") from exc

    return audio.set_channels(1).set_frame_rate(16000)
