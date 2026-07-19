import io
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydub import AudioSegment

DEFAULT_ASR_ENDPOINT = (
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
)
DEFAULT_TTS_ENDPOINT = (
    "https://dashscope-intl.aliyuncs.com/api/v1/services/"
    "aigc/multimodal-generation/generation"
)


class QwenCloudError(RuntimeError):
    """Raised when Qwen dataset enrichment cannot complete."""


@dataclass(frozen=True)
class QwenCloudConfig:
    api_key: str
    asr_endpoint: str = DEFAULT_ASR_ENDPOINT
    tts_endpoint: str = DEFAULT_TTS_ENDPOINT
    asr_model: str = "qwen3-asr-flash"
    tts_model: str = "qwen3-tts-flash"
    language_type: str = "English"
    timeout_seconds: float = 45.0

    @classmethod
    def from_env(cls) -> "QwenCloudConfig":
        try:
            timeout = max(1.0, float(os.getenv("QWEN_TIMEOUT_SECONDS", "45")))
        except ValueError:
            timeout = 45.0
        return cls(
            api_key=os.getenv("DASHSCOPE_API_KEY", "").strip(),
            asr_endpoint=os.getenv("QWEN_ASR_ENDPOINT", DEFAULT_ASR_ENDPOINT).strip()
            or DEFAULT_ASR_ENDPOINT,
            tts_endpoint=os.getenv("QWEN_TTS_ENDPOINT", DEFAULT_TTS_ENDPOINT).strip()
            or DEFAULT_TTS_ENDPOINT,
            asr_model=os.getenv("QWEN_ASR_MODEL", "qwen3-asr-flash").strip()
            or "qwen3-asr-flash",
            tts_model=os.getenv("QWEN_TTS_MODEL", "qwen3-tts-flash").strip()
            or "qwen3-tts-flash",
            language_type=os.getenv("QWEN_LANGUAGE", "English").strip() or "English",
            timeout_seconds=timeout,
        )

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


def _request_json(request: Request, timeout: float) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise QwenCloudError(f"Qwen returned HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise QwenCloudError(f"Qwen request failed: {exc}") from exc
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QwenCloudError("Qwen returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise QwenCloudError("Qwen returned an unexpected response")
    if payload.get("code"):
        raise QwenCloudError(str(payload.get("message") or payload["code"]))
    return payload


def _download_audio(url: str, timeout: float) -> bytes:
    try:
        with urlopen(Request(url, method="GET"), timeout=timeout) as response:
            data = response.read()
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise QwenCloudError(f"Unable to download derived clip: {exc}") from exc
    if not data:
        raise QwenCloudError("Qwen returned empty audio")
    return data


def _content_json(payload: dict[str, Any]) -> Any:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise QwenCloudError("Qwen ASR response did not include choices")
    message = choices[0].get("message", {})
    content = message.get("content", "")
    if isinstance(content, list):
        content = "".join(
            item.get("text", "") for item in content if isinstance(item, dict)
        )
    if not isinstance(content, str):
        raise QwenCloudError("Qwen ASR returned unreadable content")
    match = re.search(r"\{.*\}|\[.*\]", content, flags=re.DOTALL)
    try:
        return json.loads(match.group(0) if match else content)
    except json.JSONDecodeError as exc:
        raise QwenCloudError("Qwen ASR did not return timestamp JSON") from exc


def transcribe_audio_url(
    audio_url: str,
    config: Optional[QwenCloudConfig] = None,
) -> list[dict[str, Any]]:
    """Return word-level transcript rows for a remotely reachable source audio URL."""
    config = config or QwenCloudConfig.from_env()
    if not config.configured:
        raise QwenCloudError("DASHSCOPE_API_KEY is not configured")
    body = {
        "model": config.asr_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "audio_url", "audio_url": {"url": audio_url}},
                    {
                        "type": "text",
                        "text": (
                            "Transcribe this audio. Return JSON only as an array of "
                            "objects with word, start, end, and confidence fields."
                        ),
                    },
                ],
            }
        ],
    }
    request = Request(
        config.asr_endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    rows = _content_json(_request_json(request, config.timeout_seconds))
    if not isinstance(rows, list):
        raise QwenCloudError("Qwen ASR transcript must be an array")
    return [row for row in rows if isinstance(row, dict) and row.get("word")]


def synthesize_word(
    word: str,
    voice_id: str,
    config: Optional[QwenCloudConfig] = None,
) -> AudioSegment:
    """Generate exactly one reusable word clip for a source-specific Qwen voice."""
    config = config or QwenCloudConfig.from_env()
    normalized = word.strip()
    if not normalized or len(normalized.split()) != 1:
        raise QwenCloudError("Derived clip synthesis accepts exactly one word")
    if not config.configured:
        raise QwenCloudError("DASHSCOPE_API_KEY is not configured")
    if not voice_id.strip():
        raise QwenCloudError("A source voice profile is required")
    body = {
        "model": config.tts_model,
        "input": {
            "text": normalized,
            "voice": voice_id,
            "language_type": config.language_type,
        },
    }
    request = Request(
        config.tts_endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    payload = _request_json(request, config.timeout_seconds)
    output = payload.get("output", {})
    audio = output.get("audio", {}) if isinstance(output, dict) else {}
    url = audio.get("url") if isinstance(audio, dict) else None
    if not url and isinstance(output, dict):
        url = output.get("audio_url") or output.get("url")
    if not isinstance(url, str) or not url:
        raise QwenCloudError("Qwen TTS response did not include an audio URL")
    try:
        segment = AudioSegment.from_file(io.BytesIO(_download_audio(url, config.timeout_seconds)))
    except Exception as exc:
        raise QwenCloudError("Qwen returned unreadable word audio") from exc
    return segment.set_channels(1).set_frame_rate(16000)
