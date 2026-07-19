import io
import wave

import pytest
from fastapi.testclient import TestClient
from pydub import AudioSegment

from backend import db, engine, speech_service
from backend.app import app
from backend.qwen_cloud import QwenCloudError, _extract_audio_url
from backend.speech_service import GenerationResult


@pytest.fixture(autouse=True)
def temp_database(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "metadata.sqlite")
    db.init_db()


def silent_wav(duration: int = 120) -> io.BytesIO:
    output = io.BytesIO()
    AudioSegment.silent(duration=duration, frame_rate=16000).export(
        output, format="wav"
    )
    output.seek(0)
    return output


def test_database_round_trip():
    source_id = db.create_source("demo", "local_file", "/tmp/demo.wav", "complete")
    clip_id = db.add_clip(
        {
            "word": "Buffalo",
            "normalized_word": "buffalo",
            "source_id": source_id,
            "start": 0.1,
            "end": 0.5,
            "confidence": 0.98,
            "duration": 400,
        }
    )
    clips = db.get_clips_for_word("BUFFALO")
    assert clips[0]["id"] == clip_id
    assert db.get_stats() == {"total_clips": 1, "unique_words": 1}


def test_generate_speech_produces_valid_wav(monkeypatch):
    monkeypatch.setattr(
        engine,
        "generate_espeak_fallback",
        lambda _: AudioSegment.silent(duration=120, frame_rate=16000),
    )
    audio = engine.generate_speech("hello world", seed=0, filter_preset="clean")
    with wave.open(io.BytesIO(audio.read()), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getframerate() == 16000
        assert wav.getnframes() > 0


def test_cloud_is_primary_when_available(monkeypatch):
    monkeypatch.setattr(
        speech_service,
        "synthesize_qwen",
        lambda *args, **kwargs: AudioSegment.silent(
            duration=120, frame_rate=24000
        ),
    )
    monkeypatch.setattr(
        engine,
        "generate_speech",
        lambda *args, **kwargs: pytest.fail("local fallback should not run"),
    )

    result = speech_service.generate_speech_with_fallback(
        "hello cloud",
        filter_preset="clean",
        provider="auto",
    )

    assert result.provider == "qwen_cloud"
    assert result.fallback_reason is None
    with wave.open(io.BytesIO(result.audio_buffer.read()), "rb") as wav:
        assert wav.getframerate() == 16000


def test_cloud_failure_falls_back_locally(monkeypatch):
    def fail_cloud(*args, **kwargs):
        raise QwenCloudError("cloud unavailable")

    monkeypatch.setattr(speech_service, "synthesize_qwen", fail_cloud)
    monkeypatch.setattr(
        engine,
        "generate_speech",
        lambda *args, **kwargs: silent_wav(),
    )

    result = speech_service.generate_speech_with_fallback(
        "hello local",
        provider="auto",
    )

    assert result.provider == "local"
    assert result.fallback_reason == "cloud unavailable"
    assert result.audio_buffer.read(4) == b"RIFF"


def test_qwen_response_audio_url():
    payload = {
        "output": {
            "audio": {
                "url": "https://example.invalid/generated.wav",
            }
        }
    }
    assert _extract_audio_url(payload).endswith("generated.wav")


def test_api_health_generation_and_provider_header(monkeypatch):
    monkeypatch.setattr(
        "backend.app.generate_speech_with_fallback",
        lambda *args, **kwargs: GenerationResult(
            audio_buffer=silent_wav(),
            provider="qwen_cloud",
        ),
    )
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        response = client.post("/api/speech/generate", json={"text": "hello"})
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("audio/wav")
        assert response.headers["x-frankenvoice-provider"] == "qwen_cloud"
        assert response.content[:4] == b"RIFF"


def test_provider_status_reports_cloud_configuration(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    with TestClient(app) as client:
        response = client.get("/api/providers/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["strategy"] == "qwen_cloud_first_local_fallback"
    assert payload["qwen_cloud"]["configured"] is True
    assert payload["local"]["available"] is True


def test_openai_endpoint_rejects_unsupported_format():
    with TestClient(app) as client:
        response = client.post(
            "/v1/audio/speech",
            json={"input": "hello", "response_format": "exe"},
        )
    assert response.status_code == 422
