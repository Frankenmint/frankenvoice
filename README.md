# ⚡ FrankenVoice ⚡

### *Look through the noise. Hear the voice inside it.*

**OpenAI-compatible composite text-to-speech assembled one word at a time from many different sources.**

![frankenvoice audio stereogram](https://github.com/Frankenmint/frankenvoice/blob/main/assets/hero.jpg?raw=true)

## What is FrankenVoice?

FrankenVoice creates Bumblebee-style speech. Every final word is an independently selected audio fragment from one shared global corpus. The same sentence can sound different every time.

```text
"I am trying to reach you"

I       → source 3, clip 14
am      → source 8, clip 2
trying  → source 1, clip 9
reach   → Qwen-derived single-word clip
you     → source 5, clip 4

five independent clips → punctuation-aware stitch → shared filter → WAV
```

**Qwen never generates the final sentence.** Alibaba Cloud Model Studio is dataset-building compute:

- Qwen3-ASR timestamps long-form source audio.
- FrankenVoice cuts those timestamps from the original recording into real word clips.
- Coverage analysis finds missing or underrepresented words.
- Qwen3-TTS generates isolated vocabulary variants for the shared corpus.
- Derived clips are stored with `qwen_derived` provenance.
- Final `/api/speech/generate` and `/v1/audio/speech` output always comes from the fragment composer.

## Pipeline

```text
YouTube or audio source
→ audio extraction
→ Qwen ASR or local Whisper timestamps
→ original word clips
→ shared SQLite corpus
→ coverage analysis
→ Qwen isolated-word enrichment
→ source-diverse clip selection per word
→ punctuation-aware stitching + shared filter
→ FrankenVoice WAV / MP3
```

## Requirements

- Node.js 20+
- Python 3.11+
- FFmpeg
- `yt-dlp`
- `espeak-ng` for last-resort isolated-word fallback
- Rubber Band CLI for optional prosody matching
- Alibaba Cloud Model Studio API key for Qwen enrichment

## Qwen configuration

```bash
export DASHSCOPE_API_KEY="sk-your-key"
export QWEN_ASR_MODEL="qwen3-asr-flash"
export QWEN_TTS_MODEL="qwen3-tts-flash"
export QWEN_TTS_VOICES="Cherry"
```

See `.env.example` for endpoints and timeout settings.

Provider status:

```bash
curl http://localhost:8000/api/providers/status
```

Expected strategy:

```json
{
  "speech_strategy": "composite_only",
  "final_speech": {
    "whole_sentence_cloud_tts": false
  }
}
```

## Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app:app --reload
```

API: `http://localhost:8000`

### Generate composite speech

```bash
curl -X POST http://localhost:8000/api/speech/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I am trying to reach you through this damaged transmission.",
    "filter_preset": "robot_radio",
    "speed": 1.0,
    "pause_scale": 1.0
  }' \
  --output frankenvoice.wav
```

### Check vocabulary coverage

```bash
curl -X POST http://localhost:8000/api/dataset/coverage \
  -H "Content-Type: application/json" \
  -d '{"text":"I am trying to reach you","target_variants":3}'
```

### Enrich the shared corpus

```bash
curl -X POST http://localhost:8000/api/dataset/enrich \
  -H "Content-Type: application/json" \
  -d '{
    "text":"reach transmission navigation",
    "target_variants":3
  }'
```

Each generated item is a separate reusable clip in the global `Qwen Derived Corpus`.

### Conversation Reader

```text
POST /api/conversation/chunks
```

The frontend cleans Markdown, splits long responses into short chunks, prefetches upcoming audio, and provides play, pause, replay, skip, stop, progress, and cancellation controls.

## OpenAI-compatible endpoint

```text
POST /v1/audio/speech
```

The endpoint accepts OpenAI-style TTS requests, but `voice` is intentionally ignored because FrankenVoice is one changing composite voice.

## Frontend

```bash
npm install
npm run dev
```

UI: `http://localhost:5173`

## Alibaba Cloud deployment

A reproducible Alibaba ECS deployment package is included at:

```text
deploy/alibaba/
```

It contains Dockerfiles, Docker Compose, same-origin Nginx proxy configuration, an environment template, architecture notes, and submission verification URLs.

See [Alibaba Cloud deployment proof](deploy/alibaba/README.md).

## QA

```bash
pip install -r requirements-test.txt
python -m compileall backend tests
python -m pytest -q
npm install
npm run build
```

CI uses mocks and never requires a real cloud key.

## License

FrankenVoice is released under the [MIT License](LICENSE).

## Future work

- Personal voice-cloning fork after the hackathon
- Per-word reroll wired to backend clip IDs
- Source job progress polling
- Waveform editing
- Better syllable fallback for words that cannot be generated
