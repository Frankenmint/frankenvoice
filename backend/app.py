from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import db
import engine
import io

app = FastAPI()

class GenerateRequest(BaseModel):
    text: str
    seed: int = None
    filter_preset: str = "robot_radio"

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

@app.post("/api/speech/generate")
def generate_speech_endpoint(req: GenerateRequest):
    audio_buffer = engine.generate_speech(req.text, req.seed, req.filter_preset)
    return StreamingResponse(audio_buffer, media_type="audio/wav", headers={
        "Content-Disposition": "attachment; filename=frankenvoice_output.wav"
    })

@app.get("/api/dataset/stats")
def stats():
    return db.get_stats()

@app.get("/api/words/{word}")
def get_word_variants(word: str):
    return db.get_clips_for_word(word)
