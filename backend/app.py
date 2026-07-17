import io
import re
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend import db, engine
from backend.speech_service import (
    GenerationResult,
    generate_speech_with_fallback,
    get_provider_status,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="FrankenVoice", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-FrankenVoice-Provider",
        "X-FrankenVoice-Fallback",
    ],
)


class GenerateRequest(BaseModel):
    text: str = Field(min_length=1)
    voice_id: str = "default"
    seed: Optional[int] = None
    filter_preset: Literal["clean", "robot_radio", "telephone", "damaged_tape"] = (
        "robot_radio"
    )
    provider: Literal["auto", "qwen_cloud", "local"] = "auto"
    qwen_voice: Optional[str] = None


class OpenAITTSRequest(BaseModel):
    model: str = "frankenvoice-1"
    input: str = Field(min_length=1)
    voice: str = "default"
    response_format: Literal["wav", "mp3"] = "wav"
    speed: float = Field(default=1.0, ge=0.25, le=4.0)


def _safe_header(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"[^A-Za-z0-9 ._:/-]", " ", value)[:240]


def _result_headers(result: GenerationResult) -> dict[str, str]:
    headers = {"X-FrankenVoice-Provider": result.provider}
    if result.fallback_reason:
        headers["X-FrankenVoice-Fallback"] = _safe_header(result.fallback_reason)
    return headers


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/providers/status")
def provider_status() -> dict:
    return get_provider_status()


@app.post("/api/speech/generate")
def generate_speech_endpoint(req: GenerateRequest):
    result = generate_speech_with_fallback(
        text=req.text,
        voice_id=req.voice_id,
        seed=req.seed,
        filter_preset=req.filter_preset,
        provider=req.provider,
        qwen_voice=req.qwen_voice,
    )
    headers = {
        "Content-Disposition": "attachment; filename=frankenvoice.wav",
        **_result_headers(result),
    }
    return StreamingResponse(
        result.audio_buffer,
        media_type="audio/wav",
        headers=headers,
    )


@app.post("/v1/audio/speech")
def openai_tts_endpoint(req: OpenAITTSRequest):
    try:
        provider = "local" if req.model == "frankenvoice-local" else "auto"
        result = generate_speech_with_fallback(
            text=req.input,
            voice_id=req.voice,
            filter_preset="robot_radio",
            provider=provider,
            qwen_voice=req.voice,
        )
        audio_buffer = result.audio_buffer
        if req.response_format == "mp3":
            from pydub import AudioSegment

            segment = AudioSegment.from_wav(audio_buffer)
            out_buf = io.BytesIO()
            segment.export(out_buf, format="mp3")
            out_buf.seek(0)
            audio_buffer = out_buf
        media_type = "audio/mpeg" if req.response_format == "mp3" else "audio/wav"
        return StreamingResponse(
            audio_buffer,
            media_type=media_type,
            headers=_result_headers(result),
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


@app.get("/api/dataset/stats")
def stats():
    return db.get_stats()


@app.get("/api/words/{word}")
def get_word_variants(word: str):
    return db.get_clips_for_word(word)
