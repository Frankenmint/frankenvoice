import io
import wave

import pytest
from fastapi.testclient import TestClient
from pydub import AudioSegment

from backend import db, engine
from backend.app import app


@pytest.fixture(autouse=True)
def temp_database(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "metadata.sqlite")
    db.init_db()


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


def test_api_health_and_generation(monkeypatch):
    monkeypatch.setattr(
        "backend.app.generate_speech",
        lambda *args, **kwargs: engine.generate_speech("", filter_preset="clean"),
    )
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        response = client.post("/api/speech/generate", json={"text": "hello"})
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("audio/wav")
        assert response.content[:4] == b"RIFF"


def test_openai_endpoint_rejects_unsupported_format():
    with TestClient(app) as client:
        response = client.post(
            "/v1/audio/speech",
            json={"input": "hello", "response_format": "exe"},
        )
        assert response.status_code == 422
