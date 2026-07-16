# ⚡ FrankenVoice ⚡

### *Look through the noise. Hear the voice inside it.*

**Local-first composite speech synthesis built from real recorded words.**

![frankenvoice audio stereogram](https://github.com/Frankenmint/frankenvoice/blob/main/assets/hero.jpeg?raw=true)

# What is FrankenVoice?

FrankenVoice reconstructs speech from **real recorded audio** instead of generating it from scratch.

Feed it long-form recordings—interviews, podcasts, YouTube videos, speeches—and it:

- Transcribes every spoken word
- Builds a searchable database of clips
- Finds matching words across every recording
- Stitches real human recordings into new sentences
- Applies one shared effects chain so fragments sound like one transmission

## Demo workflow

```text
YouTube or local audio
→ audio extraction
→ Whisper word timestamps
→ indexed word clips
→ clip selection
→ audio stitching
→ shared filter chain
→ FrankenVoice WAV
```

## Requirements

- Node.js 20+
- Python 3.11+
- FFmpeg
- `yt-dlp`
- `espeak-ng` for missing-word fallback
- Rubber Band CLI for optional prosody matching

## Backend

From repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app:app --reload
```

API: `http://localhost:8000`

Health check:

```bash
curl http://localhost:8000/health
```

## Frontend

```bash
npm install
npm run dev
```

UI: `http://localhost:5173`

Set a different backend URL with:

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## QA

```bash
pip install -r requirements-test.txt
python -m compileall backend tests
python -m pytest -q
npm install
npm run build
```

GitHub Actions runs backend smoke tests and frontend production builds on every pull request.

## Current WIP

- Per-word reroll wired to backend clip IDs
- Voice dataset filtering
- Source job progress
- Waveform editing
- Expanded OpenAI-compatible response formats
