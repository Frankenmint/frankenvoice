import io
import wave

import pytest
from fastapi.testclient import TestClient
from pydub import AudioSegment

from backend import db, engine, enrichment, speech_service
from backend.app import app, chunk_conversation, clean_markdown_for_speech
from backend.qwen_cloud import QwenCloudError, synthesize_word
from backend.speech_service import GenerationResult


@pytest.fixture(autouse=True)
def temp_database(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "metadata.sqlite")
    monkeypatch.setattr(enrichment, "PROJECT_ROOT", tmp_path)
    db.init_db()


def silent_wav(duration: int = 120) -> io.BytesIO:
    output = io.BytesIO()
    AudioSegment.silent(duration=duration, frame_rate=16000).export(output, format="wav")
    output.seek(0)
    return output


def test_database_round_trip_and_provenance():
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
            "provenance": "original",
        }
    )
    clips = db.get_clips_for_word("BUFFALO")
    assert clips[0]["id"] == clip_id
    assert clips[0]["provenance"] == "original"
    assert db.get_stats() == {
        "total_clips": 1,
        "unique_words": 1,
        "derived_clips": 0,
    }


def test_generate_speech_produces_valid_composite_wav(monkeypatch):
    monkeypatch.setattr(
        engine,
        "generate_espeak_fallback",
        lambda _: AudioSegment.silent(duration=120, frame_rate=16000),
    )
    audio = engine.generate_speech(
        "hello, world.\n\nAgain!",
        seed=0,
        filter_preset="clean",
        speed=1.25,
        pause_scale=1.2,
    )
    with wave.open(io.BytesIO(audio.read()), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getframerate() == 16000
        assert wav.getnframes() > 0


def test_speech_service_never_calls_qwen(monkeypatch):
    monkeypatch.setattr(engine, "generate_speech", lambda *args, **kwargs: silent_wav())
    result = speech_service.generate_composite_speech("hello fragments")
    assert result.provider == "composite"
    assert result.audio_buffer.read(4) == b"RIFF"


def test_coverage_reports_missing_variants():
    source_id = db.create_source("demo", "local_file", "/tmp/demo.wav", "complete")
    db.add_clip(
        {
            "word": "hello",
            "normalized_word": "hello",
            "source_id": source_id,
            "start": 0.1,
            "end": 0.2,
            "duration": 100,
        }
    )
    coverage = enrichment.coverage_for_text("hello world", target_variants=2)
    assert coverage["complete"] is False
    assert coverage["words"] == [
        {"word": "hello", "variants": 1, "needed": 1},
        {"word": "world", "variants": 0, "needed": 2},
    ]


def test_enrichment_creates_global_single_word_clips(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("QWEN_TTS_VOICES", "Cherry,Serena")
    monkeypatch.setattr(
        enrichment,
        "synthesize_word",
        lambda word, voice_id, config=None: AudioSegment.silent(duration=100, frame_rate=16000),
    )
    result = enrichment.enrich_missing_words(["signal"], target_variants=2)
    assert result["corpus"] == db.DERIVED_SOURCE_TITLE
    assert len(result["created"]) == 2
    clips = db.get_clips_for_word("signal")
    assert {clip["provenance"] for clip in clips} == {"qwen_derived"}
    assert {clip["voice_profile_id"] for clip in clips} == {"Cherry", "Serena"}


def test_qwen_word_synthesis_rejects_sentences():
    with pytest.raises(QwenCloudError, match="exactly one word"):
        synthesize_word("not a word", "Cherry")


def test_markdown_cleanup_and_chunking():
    source = "## Result\n\nUse [the docs](https://example.com).\n\n```python\nprint('skip')\n```\n\nDone."
    cleaned = clean_markdown_for_speech(source, skip_code_blocks=True)
    assert "https://" not in cleaned
    assert "print" not in cleaned
    assert "the docs" in cleaned
    chunks = chunk_conversation(cleaned, max_characters=120)
    assert chunks
    assert all(len(chunk) <= 120 for chunk in chunks)


def test_api_generation_is_composite_only(monkeypatch):
    monkeypatch.setattr(
        "backend.app.generate_composite_speech",
        lambda *args, **kwargs: GenerationResult(audio_buffer=silent_wav()),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/speech/generate",
            json={"text": "hello", "speed": 1.25, "pause_scale": 1.1},
        )
    assert response.status_code == 200
    assert response.headers["x-frankenvoice-provider"] == "composite"
    assert response.content[:4] == b"RIFF"


def test_conversation_endpoint_returns_chunks():
    with TestClient(app) as client:
        response = client.post(
            "/api/conversation/chunks",
            json={"text": "# Heading\n\nFirst sentence. Second sentence."},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1
    assert payload["chunks"]


def test_provider_status_describes_one_shared_voice(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    with TestClient(app) as client:
        response = client.get("/api/providers/status")
    payload = response.json()
    assert payload["speech_strategy"] == "composite_only"
    assert payload["final_speech"]["whole_sentence_cloud_tts"] is False
    assert payload["final_speech"]["voice_count"] == 1
    assert payload["qwen_enrichment"]["configured"] is True


def test_openai_endpoint_rejects_unsupported_format():
    with TestClient(app) as client:
        response = client.post(
            "/v1/audio/speech",
            json={"input": "hello", "response_format": "exe"},
        )
    assert response.status_code == 422
