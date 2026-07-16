from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import io
from engine import generate_speech
from filters import apply_filter_chain # Import your filter logic

app = FastAPI()


class GenerateRequest(BaseModel):
    text: str
    voice_id: str = "default"
    seed: Optional[int] = None
    filter_preset: str = "robot_radio"

class OpenAITTSRequest(BaseModel):
    model: str = "frankenvoice-1"
    input: str
    voice: str = "default"
    response_format: str = "wav"
    speed: float = 1.0

@app.post("/api/speech/generate")
def generate_speech_endpoint(req: GenerateRequest):
    audio_buffer = generate_speech(req.text, req.voice_id, req.seed, req.filter_preset)
    return StreamingResponse(audio_buffer, media_type="audio/wav")

@app.post("/v1/audio/speech")
async def openai_tts_endpoint(req: OpenAITTSRequest):
    """OpenAI Compatible Endpoint"""
    try:
        # Map OpenAI voice names to your presets if needed
        preset = req.voice 
        
        audio_buffer = generate_speech(
            text=req.input, 
            voice_id=preset, 
            filter_preset=preset # Using voice name as preset key for simplicity
        )
        
        # Handle format conversion if not wav
        if req.response_format != "wav":
            from pydub import AudioSegment
            seg = AudioSegment.from_wav(audio_buffer)
            out_buf = io.BytesIO()
            seg.export(out_buf, format=req.response_format)
            out_buf.seek(0)
            audio_buffer = out_buf

        mime_types = {"wav": "audio/wav", "mp3": "audio/mpeg"}
        return StreamingResponse(
            audio_buffer, 
            media_type=mime_types.get(req.response_format, "audio/wav")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
def startup():
    db.init_db()

@app.post("/api/sources/youtube")
def import_youtube(url: str, background_tasks: BackgroundTasks):
    # Simplified: In real app, return job ID immediately
    path = engine.ingest_youtube(url)
    # Mock source ID creation
    source_id = 1 
    background_tasks.add_task(engine.process_audio_file, path, source_id)
    return {"status": "processing", "source_id": source_id}


@app.get("/api/dataset/stats")
def stats():
    return db.get_stats()

@app.get("/api/words/{word}")
def get_word_variants(word: str):
    return db.get_clips_for_word(word)
