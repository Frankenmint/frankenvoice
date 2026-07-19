# ⚡ FrankenVoice ⚡

### *Look through the noise. Hear the voice inside it.*

**Composite text-to-speech assembled one word at a time from many different sources.**

![frankenvoice audio stereogram](https://github.com/Frankenmint/frankenvoice/blob/main/assets/hero.jpg?raw=true)

# What is FrankenVoice?

FrankenVoice creates Bumblebee-style speech. Every word in the final sentence is an independently selected audio fragment.

```text
"I am trying to reach you"

I       → source 3, clip 14
am      → source 8, clip 2
trying  → source 1, clip 9
reach   → Qwen-derived single-word clip
six independent clips → stitch → shared filter → WAV
```

**Qwen never generates the final sentence.** Qwen Cloud is dataset-building compute:

- Qwen ASR timestamps long-form source audio.
- FrankenVoice cuts those timestamps from the original recording into real word clips.
- Coverage analysis finds missing or underrepresented words.
- Qwen TTS generates only one missing word at a time with a source-specific voice profile.
- Derived words are stored beside original clips with provenance metadata.
- Final `/api/speech/generate` and `/v1/audio/speech` output always comes from the fragment composer.

## Pipeline

```text
YouTube or audio source
→ local audio extraction
→ Qwen ASR or local Whisper timestamps
→ original word clips
→ searchable SQLite dataset
→ coverage analysis
→ Qwen single-word gap filling
→ independent clip selection per word
→ stitching + shared transmission filter
→ FrankenVoice WAV
```

## Requirements

- Node.js 20+
- Python 3.11+
- FFmpeg
- `yt-dlp`
- `espeak-ng` for last-resort single-word fallback
- Rubber Band CLI for optional prosody matching
- Alibaba Cloud Model Studio API key for Qwen enrichment

## Qwen configuration

```bash
export DASHSCOPE_API_KEY="sk-your-key"
export QWEN_ASR_MODEL="qwen3-asr-flash"
export QWEN_TTS_MODEL="qwen3-tts-flash"
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
    "filter_preset": "robot_radio"
  }' \
  --output frankenvoice.wav
```

The response includes:

```text
X-FrankenVoice-Provider: composite
```

### Check vocabulary coverage

```bash
curl -X POST http://localhost:8000/api/dataset/coverage \
  -H "Content-Type: application/json" \
  -d '{"text":"I am trying to reach you","target_variants":3}'
```

### Qwen ASR source processing

Import a source first, then supply a directly reachable audio URL for Qwen ASR:

```bash
curl -X POST http://localhost:8000/api/sources/1/qwen-transcribe \
  -H "Content-Type: application/json" \
  -d '{"audio_url":"https://example.com/source.wav"}'
```

Qwen returns word timestamps; FrankenVoice cuts the matching words from its local copy of the original recording.

### Link a source voice profile

```bash
curl -X PUT http://localhost:8000/api/sources/1/voice-profile \
  -H "Content-Type: application/json" \
  -d '{"voice_id":"source-voice-profile-id"}'
```

### Fill missing words

```bash
curl -X POST http://localhost:8000/api/dataset/enrich \
  -H "Content-Type: application/json" \
  -d '{
    "source_id":1,
    "text":"reach transmission",
    "target_variants":3
  }'
```

Each generated item is a separate reusable word clip marked `qwen_derived`.

## OpenAI-compatible endpoint

```text
POST /v1/audio/speech
```

It behaves like a TTS service, but its audio is still assembled word-by-word by FrankenVoice.

## Frontend

```bash
npm install
npm run dev
```

UI: `http://localhost:5173`

The UI separates:

- **Composite generation** — always the final speech path
- **Qwen ASR** — builds original clips from source timestamps
- **Coverage checking** — identifies missing variants
- **Qwen enrichment** — creates missing single-word clips

## QA

```bash
pip install -r requirements-test.txt
python -m compileall backend tests
python -m pytest -q
npm install
npm run build
```

CI uses mocks and never requires a real cloud key.

## Current WIP

- Automated Qwen voice-profile creation from clean source excerpts
- Per-word reroll wired to backend clip IDs
- Source job progress polling
- Waveform editing
- Better syllable fallback for words that cannot be generated
