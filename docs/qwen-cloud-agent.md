# Qwen Cloud Autopilot Agent proof

FrankenVoice is submitted to **Track 4: Autopilot Agent**.

The agent is code-based because Alibaba Cloud Model Studio's Singapore console application builder is restricted for newer accounts. FrankenVoice calls Qwen models through Alibaba Cloud Model Studio / DashScope APIs and implements orchestration, tool execution, persistence, and human approval in the public repository.

## Agent architecture

```text
Ambiguous user goal + target text + optional media sources
                         |
                         v
              Qwen Cloud planning model
                 (QWEN_AGENT_MODEL)
                         |
              constrained JSON tool plan
                         |
                         v
             Persistent Autopilot run file
                         |
                  HUMAN CHECKPOINT
             approve imports / cloud calls
                         |
                         v
                 Workflow executor
        +----------------+----------------+
        |                |                |
   yt-dlp/FFmpeg    corpus coverage   Qwen3-TTS
   source import       analysis        enrichment
        |                |                |
        +----------------+----------------+
                         |
                         v
              Composite speech engine
                         |
                         v
               final WAV + run report
```

## Qwen Cloud services used

- **Qwen planning model** through the OpenAI-compatible Chat Completions endpoint.
- **Qwen3-ASR** for timestamped source transcription.
- **Qwen3-TTS** for isolated-word vocabulary enrichment.

Qwen does not synthesize the final sentence. Final speech remains an independently selected, word-by-word FrankenVoice composite.

## Agent behavior

1. `POST /api/autopilot/plan` sends the goal, source list, target text, and current corpus coverage to Qwen.
2. Qwen returns a constrained JSON plan using only approved FrankenVoice tools.
3. The plan is persisted under `data/autopilot/runs/` with status `awaiting_approval`.
4. The UI shows estimated external actions and requires a human decision before source downloads or paid Qwen enrichment.
5. `POST /api/autopilot/runs/{run_id}/approve` records the decision and launches execution.
6. The executor imports approved sources, recalculates coverage, enriches approved vocabulary gaps, generates composite audio, and persists a final report.
7. The frontend polls `GET /api/autopilot/runs/{run_id}` and plays the completed result from `/api/autopilot/runs/{run_id}/audio`.

## Code evidence

- Qwen planning and API calls: [`backend/qwen_cloud.py`](../backend/qwen_cloud.py)
- Persistent workflow and tool executor: [`backend/autopilot.py`](../backend/autopilot.py)
- HTTP lifecycle and approval endpoints: [`backend/app.py`](../backend/app.py)
- Human-in-the-loop interface: [`src/components/AutopilotAgent.tsx`](../src/components/AutopilotAgent.tsx)
- Approval and execution tests: [`tests/test_backend.py`](../tests/test_backend.py)

## Required configuration

```bash
export DASHSCOPE_API_KEY="sk-your-key"
export QWEN_AGENT_MODEL="qwen-plus"
export QWEN_ASR_MODEL="qwen3-asr-flash"
export QWEN_TTS_MODEL="qwen3-tts-flash"
```

See [`.env.example`](../.env.example) for endpoint configuration.

## Verification

Start the backend and frontend, open the **AUTOPILOT** tab, and:

1. Enter a goal and target text.
2. Ask Qwen to plan.
3. Inspect the returned tool steps and external-action estimate.
4. Approve or reject source imports and Qwen vocabulary enrichment independently.
5. Watch the persisted event log update while tools execute.
6. Play the generated FrankenVoice result.

The provider status endpoint also exposes the agent model and approval requirement:

```bash
curl http://localhost:8000/api/providers/status
```
