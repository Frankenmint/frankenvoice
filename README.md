# ⚡ FrankenVoice ⚡

### *Look through the noise. Hear the voice inside it.*

**A Qwen-powered Autopilot Agent that builds and operates a composite text-to-speech corpus.**

![frankenvoice audio stereogram](https://github.com/Frankenmint/frankenvoice/blob/main/assets/hero.jpg?raw=true)

## Track 4: Autopilot Agent

FrankenVoice automates an end-to-end speech-production workflow from an ambiguous goal to a completed composite audio file.

```text
User goal + target text + optional sources
→ Qwen Cloud plans the workflow
→ FrankenVoice persists the plan
→ human reviews external actions
→ approved tools execute
→ corpus coverage improves
→ final composite audio + execution report
```

The human checkpoint separately controls:

- downloading and processing supplied media sources;
- paid Qwen Cloud requests for vocabulary enrichment.

See [Qwen Cloud Autopilot Agent proof](docs/qwen-cloud-agent.md) for the complete architecture, API lifecycle, and direct code links.

## What is FrankenVoice?

FrankenVoice creates Bumblebee-style speech. Every final word is independently selected from one shared global corpus, so the same sentence can sound different every time.

```text
"I am trying to reach you"

I       → source 3, clip 14
am      → source 8, clip 2
trying  → source 1, clip 9
reach   → Qwen-derived single-word clip
you     → source 5, clip 4

five independent clips → punctuation-aware stitch → shared filter → WAV
```

Qwen never generates the final sentence. Qwen Cloud serves three agent capabilities:

- **Qwen planning model** converts ambiguous goals into constrained tool plans.
- **Qwen3-ASR** timestamps long-form source audio.
- **Qwen3-TTS** creates isolated vocabulary variants for the shared corpus.

Final `/api/speech/generate` and `/v1/audio/speech` output always comes from the local fragment composer.

## Autopilot workflow

```text
Qwen plan
→ check shared-corpus coverage
→ optionally import media with yt-dlp + FFmpeg
→ optionally enrich missing words with Qwen3-TTS
→ generate composite speech
→ persist event log, coverage report, and WAV
```

Agent endpoints:

```text
POST /api/autopilot/plan
GET  /api/autopilot/runs/{run_id}
POST /api/autopilot/runs/{run_id}/approve
GET  /api/autopilot/runs/{run_id}/audio
```

Example plan request:

```bash
curl -X POST http://localhost:8000/api/autopilot/plan \
  -H "Content-Type: application/json" \
  -d '{
    "goal":"Make this response fully speakable and generate the final audio",
    "target_text":"FrankenVoice checks its corpus before it speaks.",
    "source_urls":[],
    "target_variants":3
  }'
```

The returned run remains `awaiting_approval` until a person approves its external actions.

## Requirements

- Node.js 20+
- Python 3.11+
- FFmpeg
- `yt-dlp`
- `espeak-ng` for last-resort isolated-word fallback
- Rubber Band CLI for optional prosody matching
- Alibaba Cloud Model Studio API key

## Qwen Cloud configuration

```bash
export DASHSCOPE_API_KEY="sk-your-key"
export QWEN_AGENT_MODEL="qwen-plus"
export QWEN_ASR_MODEL="qwen3-asr-flash"
export QWEN_TTS_MODEL="qwen3-tts-flash"
export QWEN_TTS_VOICES="Cherry"
```

See `.env.example` for endpoint and timeout settings.

Provider status:

```bash
curl http://localhost:8000/api/providers/status
```

The response identifies the Track 4 agent model, its planning role, and the mandatory human approval rule.

## Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app:app --reload
```

API: `http://localhost:8000`

## Frontend

```bash
npm install
npm run dev
```

UI: `http://localhost:5173`

The default **AUTOPILOT** tab demonstrates:

- Qwen workflow planning;
- constrained tool selection;
- persistent run state;
- external-action estimates;
- human-in-the-loop approval;
- live execution events;
- final composite playback.

The existing **COMPOSER** and **READER** tabs remain available for direct use.

## Public Alibaba Cloud deployment

The submission deployment runs the full frontend and FastAPI Autopilot backend on Alibaba Cloud ECS behind one public origin:

```text
https://frankenvoice.frankenmint.com
→ Cloudflare
→ Alibaba ECS host Nginx
→ React/Nginx container
→ same-origin /api and /v1 proxy
→ FastAPI Autopilot container
→ Qwen Cloud APIs
```

Because the browser only communicates with `https://frankenvoice.frankenmint.com`, the public deployment does not require cross-origin browser requests.

For complete first-deploy, Nginx, Cloudflare, TLS, backup, update, rollback, monitoring, and incident procedures, see [`DEPLOYMENT.md`](DEPLOYMENT.md). Submission-specific deployment proof remains under [`deploy/alibaba/`](deploy/alibaba/README.md).

## Direct composite API

```bash
curl -X POST http://localhost:8000/api/speech/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text":"I am trying to reach you through this damaged transmission.",
    "filter_preset":"robot_radio",
    "speed":1.0,
    "pause_scale":1.0
  }' \
  --output frankenvoice.wav
```

The OpenAI-compatible endpoint remains:

```text
POST /v1/audio/speech
```

Its `voice` field is intentionally ignored because FrankenVoice is one changing composite voice.

## QA

```bash
pip install -r requirements-test.txt
python -m compileall backend tests
python -m pytest -q
npm install
npm run build
```

Cloud calls are mocked in CI; no real API key is exposed.

## License

FrankenVoice is released under the [MIT License](LICENSE).

## Future work

- Personal voice-cloning fork after the hackathon
- Per-word reroll wired to backend clip IDs
- Source job progress polling
- Waveform editing
- Better syllable fallback for words that cannot be generated
