import io
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend import db, engine
from backend.enrichment import (
    coverage_for_text,
    enrich_missing_words,
    tokenize,
    transcribe_source_with_qwen,
)
from backend.speech_service import generate_composite_speech, get_provider_status


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="FrankenVoice", version="0.3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    text: str = Field(min_length=1)
    voice_id: str = "default"
    seed: Optional[int] = None
    filter_preset: Literal["clean", "robot_radio", "telephone", "damaged_tape"] = (
        "robot_radio"
    )


class OpenAITTSRequest(BaseModel):
    model: str = "frankenvoice-1"
    input: str = Field(min_length=1)
    voice: str = "default"
    response_format: Literal["wav", "mp3"] = "wav"
    speed: float = Field(default=1.0, ge=0.25, le=4.0)


class CoverageRequest(BaseModel):
    text: str = Field(min_length=1)
    target_variants: int = Field(default=3, ge=1, le=20)


class EnrichmentRequest(CoverageRequest):
    source_id: int


class VoiceProfileRequest(BaseModel):
    voice_id: str = Field(min_length=1)


class QwenTranscriptionRequest(BaseModel):
    audio_url: str = Field(min_length=1)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/providers/status")
def provider_status() -> dict:
    return get_provider_status()


@app.post("/api/speech/generate")
def generate_speech_endpoint(req: GenerateRequest):
    result = generate_composite_speech(
        text=req.text,
        voice_id=req.voice_id,
        seed=req.seed,
        filter_preset=req.filter_preset,
    )
    return StreamingResponse(
        result.audio_buffer,
        media_type="audio/wav",
        headers={
            "Content-Disposition": "attachment; filename=frankenvoice.wav",
            "X-FrankenVoice-Provider": "composite",
        },
    )


@app.post("/v1/audio/speech")
def openai_tts_endpoint(req: OpenAITTSRequest):
    try:
        result = generate_composite_speech(
            text=req.input,
            voice_id=req.voice,
            filter_preset="robot_radio",
        )
        audio_buffer = result.audio_buffer
        if req.response_format == "mp3":
            from pydub import AudioSegment

            segment = AudioSegment.from_wav(audio_buffer)
            output = io.BytesIO()
            segment.export(output, format="mp3")
            output.seek(0)
            audio_buffer = output
        media_type = "audio/mpeg" if req.response_format == "mp3" else "audio/wav"
        return StreamingResponse(
            audio_buffer,
            media_type=media_type,
            headers={"X-FrankenVoice-Provider": "composite"},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/sources/youtube", status_code=202)
def import_youtube(url: str, background_tasks: BackgroundTasks):
    path = engine.ingest_youtube(url)
    if not path:
        raise HTTPException(status_code=502, detail="Unable to download source audio")
    source_id = db.create_source(url, "youtube", path, "processing")
    background_tasks.add_task(engine.process_audio_file, path, source_id)
    return {"status": "processing", "source_id": source_id}


@app.post("/api/sources/{source_id}/qwen-transcribe")
def qwen_transcribe_source(source_id: int, req: QwenTranscriptionRequest):
    try:
        return transcribe_source_with_qwen(source_id, req.audio_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/sources/{source_id}/voice-profile")
def set_voice_profile(source_id: int, req: VoiceProfileRequest):
    if not db.get_source(source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    db.set_source_voice_profile(source_id, req.voice_id.strip())
    return {"source_id": source_id, "voice_id": req.voice_id.strip()}


@app.post("/api/dataset/coverage")
def dataset_coverage(req: CoverageRequest):
    return coverage_for_text(req.text, req.target_variants)


@app.post("/api/dataset/enrich")
def dataset_enrich(req: EnrichmentRequest):
    try:
        return enrich_missing_words(
            source_id=req.source_id,
            words=tokenize(req.text),
            target_variants=req.target_variants,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/dataset/stats")
def stats():
    return db.get_stats()


@app.get("/api/words/{word}")
def get_word_variants(word: str):
    return db.get_clips_for_word(word)
