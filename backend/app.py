import io
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend import db, engine
from backend.engine import generate_speech


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="FrankenVoice", version="0.1.0", lifespan=lifespan)
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


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/speech/generate")
def generate_speech_endpoint(req: GenerateRequest):
    audio_buffer = generate_speech(
        req.text, req.voice_id, req.seed, req.filter_preset
    )
    return StreamingResponse(
        audio_buffer,
        media_type="audio/wav",
        headers={"Content-Disposition": "attachment; filename=frankenvoice.wav"},
    )


@app.post("/v1/audio/speech")
def openai_tts_endpoint(req: OpenAITTSRequest):
    try:
        audio_buffer = generate_speech(
            text=req.input,
            voice_id=req.voice,
            filter_preset="robot_radio",
        )
        if req.response_format == "mp3":
            from pydub import AudioSegment

            segment = AudioSegment.from_wav(audio_buffer)
            out_buf = io.BytesIO()
            segment.export(out_buf, format="mp3")
            out_buf.seek(0)
            audio_buffer = out_buf
        media_type = "audio/mpeg" if req.response_format == "mp3" else "audio/wav"
        return StreamingResponse(audio_buffer, media_type=media_type)
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
