# ⚡ FrankenVoice ⚡

### *Look through the noise. Hear the voice inside it.*

**Qwen Cloud-first speech generation with automatic local composite fallback.**

![frankenvoice audio stereogram](https://github.com/Frankenmint/frankenvoice/blob/main/assets/hero.jpeg?raw=true)

# What is FrankenVoice?

FrankenVoice builds voices from fragments instead of relying on one synthesis path.

Default generation strategy:

```text
Text
→ Qwen3-TTS on Alibaba Cloud Model Studio
→ shared FrankenVoice transmission filter
→ WAV

Any missing key, timeout, API failure, or unusable cloud response
→ local indexed word clips
→ espeak-ng for missing words
→ shared FrankenVoice transmission filter
→ WAV
```

Long-form recordings still become the reusable local voice dataset:

- Transcribe recordings with local Whisper
- Extract word-level clips
- Build a searchable SQLite dataset
- Stitch real recorded words into new sentences
- Keep generation available when cloud access fails

## Why Qwen Cloud-first?

Qwen3-TTS performs primary speech generation. FrankenVoice keeps its fragment engine as a resilient, private fallback. Every API response reports which provider produced the audio through:

- `X-FrankenVoice-Provider: qwen_cloud`
- `X-FrankenVoice-Provider: local`
- `X-FrankenVoice-Fallback: <reason>` when cloud generation falls back

## Requirements

- Node.js 20+
- Python 3.11+
- FFmpeg
- `yt-dlp`
- `espeak-ng` for missing-word local fallback
- Rubber Band CLI for optional local prosody matching
- Alibaba Cloud Model Studio API key for Qwen Cloud generation

## Qwen Cloud configuration

Copy `.env.example` values into your shell or local environment:

```bash
export DASHSCOPE_API_KEY="sk-your-key"
export QWEN_TTS_MODEL="qwen3-tts-flash"
export QWEN_TTS_VOICE="Cherry"
export QWEN_TTS_LANGUAGE="English"
```

Default endpoint uses Alibaba Cloud Model Studio's Singapore endpoint. For a workspace-specific endpoint:

```bash
export QWEN_TTS_ENDPOINT="https://YOUR_WORKSPACE_ID.ap-southeast-1.maas.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
```

Cloud configuration remains optional. Without a key, `provider=auto` immediately uses the local fragment engine.

Provider status:

```bash
curl http://localhost:8000/api/providers/status
```

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

Generate using cloud-first automatic fallback:

```bash
curl -X POST http://localhost:8000/api/speech/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I am trying to reach you through this damaged transmission.",
    "provider": "auto",
    "filter_preset": "robot_radio"
  }' \
  --output frankenvoice.wav
```

Force local generation:

```json
{
  "text": "Buffalo buffalo Buffalo buffalo.",
  "provider": "local"
}
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

UI reports:

- whether Qwen Cloud is configured
- Qwen model selected
- provider used for each generation
- reason local fallback was activated

## OpenAI-compatible endpoint

```text
POST /v1/audio/speech
```

- `model: frankenvoice-1` → Qwen Cloud first, local fallback
- `model: frankenvoice-local` → local fragment engine only

## QA

```bash
pip install -r requirements-test.txt
python -m compileall backend tests
python -m pytest -q
npm install
npm run build
```

Cloud tests use mocks. CI never requires or exposes a real API key.

## Current WIP

- Per-word reroll wired to backend clip IDs
- Cloud-generated fallback words mixed into local fragment sentences
- Voice dataset filtering
- Source job progress
- Waveform editing
- Expanded OpenAI-compatible response formats
