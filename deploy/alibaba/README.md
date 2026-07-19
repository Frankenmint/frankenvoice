# Alibaba Cloud deployment proof

This directory contains the reproducible deployment package for the FrankenVoice hackathon submission.

## Architecture

```text
frankenvoice.frankenmint.com
        |
        v
Alibaba Cloud ECS
        |
        v
HTTPS reverse proxy
        |
        v
React/Vite frontend container
        |
        +--> FastAPI backend container
                  |
                  +--> SQLite fragment corpus
                  +--> FFmpeg audio pipeline
                  +--> Alibaba Cloud Model Studio / DashScope
                       - Qwen3-ASR source transcription
                       - Qwen3-TTS isolated-word enrichment
```

Qwen expands the shared word corpus. Final speech is always assembled by FrankenVoice from independently selected fragments.

## Deployment files

- `backend.Dockerfile` builds the FastAPI and audio-processing service.
- `frontend.Dockerfile` builds the React/Vite application and serves it with Nginx.
- `nginx.conf` proxies frontend API requests to FastAPI on the same origin.
- `docker-compose.yml` runs the frontend and backend on an Alibaba ECS instance.
- `.env.example` documents the required Alibaba Model Studio settings without secrets.

## ECS deployment

Recommended demonstration host:

- Alibaba Cloud ECS running Ubuntu
- Docker Engine and the Docker Compose plugin
- A public IPv4 address
- HTTP and HTTPS allowed by the ECS security group

Clone the repository on the ECS host, then prepare the environment file:

```bash
git clone https://github.com/Frankenmint/frankenvoice.git
cd frankenvoice/deploy/alibaba
cp .env.example .env
```

Set `DASHSCOPE_API_KEY` in the private `.env` file on the server. Never commit that file.

Start the stack:

```bash
docker compose up -d --build
```

The Compose stack binds the application to the ECS loopback interface at `127.0.0.1:8088`. Configure the host's HTTPS reverse proxy to send traffic for `frankenvoice.frankenmint.com` to that address.

## Verification

From the ECS host:

```bash
curl http://127.0.0.1:8088/health
curl http://127.0.0.1:8088/api/providers/status
```

Public judging URLs after DNS and HTTPS configuration:

```text
https://frankenvoice.frankenmint.com/
https://frankenvoice.frankenmint.com/health
https://frankenvoice.frankenmint.com/docs
https://frankenvoice.frankenmint.com/api/providers/status
```

The provider-status response should show that Qwen enrichment is configured while final speech remains composite-only.

## Submission links

Use this file for the submission field requesting proof of Alibaba Cloud deployment:

```text
https://github.com/Frankenmint/frankenvoice/blob/main/deploy/alibaba/README.md
```

The direct Qwen/DashScope API implementation is here:

```text
https://github.com/Frankenmint/frankenvoice/blob/main/backend/qwen_cloud.py
```

## Demo safety and cost control

For the judging deployment:

- preload a representative fragment corpus;
- keep the DashScope key only on the backend;
- restrict unrestricted source ingestion;
- limit public text length and request rate where practical;
- keep the demonstration online through judging, then reduce or stop the instance if ongoing cost is not desired.
