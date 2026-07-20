# Alibaba Cloud deployment proof

FrankenVoice is submitted to **Track 4: Autopilot Agent**. Its FastAPI agent backend runs on Alibaba Cloud ECS and uses Alibaba Cloud Model Studio / DashScope for Qwen planning, Qwen3-ASR, and isolated-word Qwen3-TTS enrichment.

## Production architecture

```text
https://frankenvoice.frankenmint.com
        |
        v
Cloudflare DNS / proxy
        |
        v
Alibaba Cloud ECS host Nginx (TLS origin)
        |
        v
127.0.0.1:8088
        |
        v
React/Nginx container
        | same-origin /api and /v1 proxy
        v
FastAPI Autopilot container
        |-- persistent run state and event logs
        |-- SQLite fragment corpus
        |-- FFmpeg / yt-dlp / composite engine
        `-- Alibaba Cloud Model Studio / DashScope
             |-- Qwen workflow planning
             |-- Qwen3-ASR source transcription
             `-- Qwen3-TTS isolated vocabulary enrichment
```

The browser uses one public origin, so the deployed application does not require cross-origin API requests.

## Files

- `backend.Dockerfile` builds the FastAPI agent and audio-processing runtime.
- `frontend.Dockerfile` builds the React application and serves it with Nginx.
- `nginx.conf` proxies `/api`, `/v1`, health, and API documentation to FastAPI.
- `docker-compose.yml` runs both services and persists `/app/data`.
- `.env.example` documents required Qwen Cloud settings without secrets.

## ECS deployment

After merging the PR, connect to the ECS instance through Alibaba Workbench and run:

```bash
git clone https://github.com/Frankenmint/frankenvoice.git
cd frankenvoice/deploy/alibaba
cp .env.example .env
```

Set `DASHSCOPE_API_KEY` in the private `.env` file, then start the stack:

```bash
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8088/health
curl http://127.0.0.1:8088/api/providers/status
```

The application is intentionally bound to ECS loopback port `8088`. A host-level Nginx virtual host proxies `frankenvoice.frankenmint.com` to `http://127.0.0.1:8088`.

## Cloudflare DNS

Create an `A` record:

```text
Type: A
Name: frankenvoice
Target: <ECS public IPv4>
Proxy: DNS only while issuing the origin certificate; proxied after verification
```

Configure HTTPS on the ECS host, verify the origin directly, and then enable the Cloudflare proxy. Use **Full (strict)** SSL mode once the origin certificate is valid.

## Verification URLs

```text
https://frankenvoice.frankenmint.com/
https://frankenvoice.frankenmint.com/health
https://frankenvoice.frankenmint.com/docs
https://frankenvoice.frankenmint.com/api/providers/status
```

The Autopilot UI demonstrates:

1. ambiguous goal submission;
2. Qwen-generated workflow planning;
3. persisted plan and coverage preflight;
4. human approval before downloads or cloud enrichment;
5. autonomous tool execution and event reporting;
6. final playable composite audio.

## Submission evidence

Use this file for the code proof field:

```text
https://github.com/Frankenmint/frankenvoice/blob/main/deploy/alibaba/README.md
```

Direct Qwen API integration:

```text
https://github.com/Frankenmint/frankenvoice/blob/main/backend/qwen_cloud.py
```

Agent orchestration and approval workflow:

```text
https://github.com/Frankenmint/frankenvoice/blob/main/backend/autopilot.py
```

For the required deployment screenshot, show Alibaba Workbench with:

- the ECS instance connection visible;
- `docker compose ps` showing both containers running;
- a successful `/health` or `/api/autopilot/plan` response;
- the FrankenVoice repository path in the terminal.
