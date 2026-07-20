# FrankenVoice Production Deployment Runbook

This document is the long-term operations guide for deploying and maintaining FrankenVoice at:

```text
https://frankenvoice.frankenmint.com
```

The hackathon-specific proof document remains at [`deploy/alibaba/README.md`](deploy/alibaba/README.md). This file is the broader production and recovery runbook.

## Production topology

```text
Cloudflare DNS and proxy
        |
        v
Alibaba Cloud ECS public IPv4
        |
        v
Host Nginx on ports 80 and 443
        |
        v
http://127.0.0.1:8088
        |
        v
Frontend Nginx container
        |-- serves the React/Vite application
        |-- proxies /api/* to FastAPI
        |-- proxies /v1/* to FastAPI
        |-- proxies /health, /docs, and /openapi.json
        |
        v
FastAPI backend container
        |-- Qwen Autopilot workflow planning
        |-- human approval checkpoints
        |-- Qwen3-ASR and Qwen3-TTS integration
        |-- FFmpeg, yt-dlp, and composite speech tools
        |-- persistent corpus and agent run state
        |
        v
Alibaba Cloud Model Studio / DashScope
```

The public browser communicates only with `https://frankenvoice.frankenmint.com`. React and FastAPI therefore share one origin, avoiding a production CORS split.

## Repository deployment files

```text
deploy/alibaba/
├── backend.Dockerfile
├── frontend.Dockerfile
├── docker-compose.yml
├── nginx.conf
├── .env.example
└── README.md
```

The Docker Compose stack exposes only the frontend container on ECS loopback:

```text
127.0.0.1:8088 -> frontend:80
```

The backend is reachable only through the private Compose network at `backend:8000`.

Persistent application data is stored in the Docker volume:

```text
alibaba_frankenvoice_data
```

which is mounted at `/app/data` inside the backend container.

---

# 1. ECS provisioning

Recommended baseline:

```text
Region: Singapore
Operating system: Ubuntu 24.04 LTS
CPU: 2 vCPU or greater
Memory: 4 GB or greater
System disk: 40 GB or greater
Public IPv4: enabled
```

Inbound security-group rules:

```text
TCP 22  from the administrator's IP only
TCP 80  from 0.0.0.0/0
TCP 443 from 0.0.0.0/0
```

Do not expose ports `8000` or `8088` publicly. Host Nginx is the only public application entry point.

Connect using Alibaba Workbench or SSH.

---

# 2. Install host dependencies

Run as `root`, or prefix commands with `sudo`:

```bash
apt update
apt install -y \
  docker.io \
  docker-compose-v2 \
  git \
  nginx \
  certbot \
  python3-certbot-nginx \
  jq \
  curl

systemctl enable --now docker
systemctl enable --now nginx
```

Verify:

```bash
docker --version
docker compose version
nginx -v
```

For a non-root deployment user:

```bash
usermod -aG docker "$USER"
```

Log out and reconnect before using Docker without `sudo`.

---

# 3. Clone and configure FrankenVoice

```bash
cd /root
git clone https://github.com/Frankenmint/frankenvoice.git
cd frankenvoice/deploy/alibaba

cp .env.example .env
chmod 600 .env
nano .env
```

At minimum, set:

```dotenv
DASHSCOPE_API_KEY=sk-your-real-key
```

Expected Singapore Model Studio defaults:

```dotenv
QWEN_COMPATIBLE_ENDPOINT=https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions
QWEN_AGENT_MODEL=qwen-plus

QWEN_ASR_ENDPOINT=https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions
QWEN_ASR_MODEL=qwen3-asr-flash

QWEN_TTS_ENDPOINT=https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation
QWEN_TTS_MODEL=qwen3-tts-flash
QWEN_TTS_VOICES=Cherry
QWEN_LANGUAGE=English
QWEN_TIMEOUT_SECONDS=45
```

Never commit `.env`, print the API key to logs, or include it in screenshots.

---

# 4. First container deployment

From `deploy/alibaba`:

```bash
docker compose up -d --build
```

The first backend build may take several minutes because it installs audio-processing dependencies.

Check container state:

```bash
docker compose ps
```

Expected services:

```text
backend   Up
frontend  Up
```

Check logs:

```bash
docker compose logs --tail=100 backend
docker compose logs --tail=100 frontend
```

Verify the private application endpoint:

```bash
curl http://127.0.0.1:8088/health
curl http://127.0.0.1:8088/api/providers/status | jq
curl -I http://127.0.0.1:8088/
```

Expected essentials:

```text
/health returns {"status":"ok"}
frontend returns HTTP 200
provider status reports Qwen as configured
```

---

# 5. Host Nginx configuration

Create the host virtual host:

```bash
nano /etc/nginx/sites-available/frankenvoice
```

Use:

```nginx
server {
    listen 80;
    listen [::]:80;

    server_name frankenvoice.frankenmint.com;

    client_max_body_size 100m;

    location / {
        proxy_pass http://127.0.0.1:8088;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 60s;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

Enable it:

```bash
ln -s /etc/nginx/sites-available/frankenvoice \
  /etc/nginx/sites-enabled/frankenvoice

rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl reload nginx
```

Test from ECS:

```bash
curl -I -H 'Host: frankenvoice.frankenmint.com' http://127.0.0.1/
```

---

# 6. Cloudflare DNS

In the Cloudflare zone for `frankenmint.com`, create:

```text
Type: A
Name: frankenvoice
IPv4 address: <ECS public IPv4>
TTL: Auto
Proxy status: DNS only initially
```

Verify resolution from another machine:

```bash
dig +short frankenvoice.frankenmint.com
```

The result must be the ECS public IPv4 before requesting the certificate.

Test HTTP:

```bash
curl -I http://frankenvoice.frankenmint.com
```

---

# 7. TLS with Let's Encrypt

Keep the Cloudflare DNS record in **DNS only** mode while issuing the certificate.

On ECS:

```bash
certbot --nginx -d frankenvoice.frankenmint.com
```

Choose the HTTP-to-HTTPS redirect when prompted.

Verify:

```bash
curl -I https://frankenvoice.frankenmint.com
certbot renew --dry-run
```

After direct HTTPS works:

1. Enable the orange Cloudflare proxy.
2. Set Cloudflare **SSL/TLS encryption mode** to **Full (strict)**.
3. Never use Flexible SSL for this deployment.

Public verification URLs:

```text
https://frankenvoice.frankenmint.com/
https://frankenvoice.frankenmint.com/health
https://frankenvoice.frankenmint.com/docs
https://frankenvoice.frankenmint.com/openapi.json
https://frankenvoice.frankenmint.com/api/providers/status
```

---

# 8. Autopilot smoke test

Create a small Qwen-planned run:

```bash
PLAN=$(curl -sS \
  -X POST https://frankenvoice.frankenmint.com/api/autopilot/plan \
  -H 'Content-Type: application/json' \
  -d '{
    "goal":"Prepare enough vocabulary and generate a final composite reading.",
    "target_text":"FrankenVoice plans, asks permission, then assembles speech.",
    "source_urls":[],
    "target_variants":1
  }')

echo "$PLAN" | jq
```

Capture the run ID:

```bash
RUN_ID=$(echo "$PLAN" | jq -r '.id')
echo "$RUN_ID"
```

The run should initially remain at an approval checkpoint.

Approve cloud enrichment without source imports:

```bash
curl -sS \
  -X POST "https://frankenvoice.frankenmint.com/api/autopilot/runs/${RUN_ID}/approve" \
  -H 'Content-Type: application/json' \
  -d '{
    "allow_source_imports":false,
    "allow_cloud_enrichment":true
  }' | jq
```

Poll status:

```bash
watch -n 2 \
  "curl -sS https://frankenvoice.frankenmint.com/api/autopilot/runs/${RUN_ID} | jq '{status,events,result,error}'"
```

Final audio endpoint:

```text
https://frankenvoice.frankenmint.com/api/autopilot/runs/<RUN_ID>/audio
```

---

# 9. Alibaba Workbench deployment evidence

For deployment evidence or incident documentation, keep the Workbench/ECS interface visible and run:

```bash
cd /root/frankenvoice/deploy/alibaba
pwd
docker compose ps
curl http://127.0.0.1:8088/health
curl http://127.0.0.1:8088/api/providers/status | jq
```

A useful screenshot should show:

- Alibaba Workbench or ECS instance context;
- the FrankenVoice repository path;
- both containers running;
- a healthy backend response;
- Qwen configured;
- no API key or secret value.

---

# 10. Routine application updates

```bash
cd /root/frankenvoice
git fetch origin
git switch main
git pull --ff-only

cd deploy/alibaba
docker compose up -d --build
```

Verify after every update:

```bash
docker compose ps
curl http://127.0.0.1:8088/health
curl -I https://frankenvoice.frankenmint.com/
```

Remove unused image layers only after confirming the deployment is healthy:

```bash
docker image prune -f
```

Do not run `docker volume prune` on this host; it can destroy the persistent FrankenVoice corpus.

---

# 11. Logs and troubleshooting

Container overview:

```bash
cd /root/frankenvoice/deploy/alibaba
docker compose ps
```

Backend logs:

```bash
docker compose logs --tail=200 backend
docker compose logs -f backend
```

Frontend logs:

```bash
docker compose logs --tail=200 frontend
docker compose logs -f frontend
```

Host Nginx:

```bash
nginx -t
systemctl status nginx --no-pager
journalctl -u nginx -n 200 --no-pager
```

Listening ports:

```bash
ss -lntp
```

Common symptoms:

### Frontend container is restarting

```bash
docker compose logs --tail=100 frontend
```

Typical cause: invalid `deploy/alibaba/nginx.conf`.

### Host Nginx returns 502

```bash
curl http://127.0.0.1:8088/health
docker compose ps
```

If loopback fails, repair the containers before changing host Nginx.

### Qwen is not configured

```bash
grep -n '^DASHSCOPE_API_KEY=' .env
```

Confirm the line exists without printing or sharing the secret value. Restart the backend after changing `.env`:

```bash
docker compose up -d --force-recreate backend
```

### Qwen returns 401 or a model error

Verify that:

- the key belongs to the Singapore Model Studio workspace;
- the `dashscope-intl.aliyuncs.com` endpoints are used;
- each configured model is available to the account.

### Certificate failure

Temporarily set the Cloudflare record to **DNS only**, verify ports 80 and 443 are open, and retry Certbot.

---

# 12. Persistent-data backup

List volumes:

```bash
docker volume ls | grep frankenvoice
```

Create a backup directory:

```bash
mkdir -p /root/frankenvoice-backups
```

Back up the persistent volume:

```bash
docker run --rm \
  -v alibaba_frankenvoice_data:/data:ro \
  -v /root/frankenvoice-backups:/backup \
  alpine \
  sh -c 'cd /data && tar czf /backup/frankenvoice-data-$(date +%Y%m%d-%H%M%S).tar.gz .'
```

Inspect backups:

```bash
ls -lh /root/frankenvoice-backups
```

Copy backups off the ECS host periodically. A backup stored only on the same instance is not disaster recovery.

---

# 13. Restore persistent data

Stop the application first:

```bash
cd /root/frankenvoice/deploy/alibaba
docker compose down
```

Restore a selected archive:

```bash
docker run --rm \
  -v alibaba_frankenvoice_data:/data \
  -v /root/frankenvoice-backups:/backup \
  alpine \
  sh -c 'rm -rf /data/* && tar xzf /backup/<BACKUP_FILE>.tar.gz -C /data'
```

Restart and verify:

```bash
docker compose up -d
docker compose ps
curl http://127.0.0.1:8088/health
```

---

# 14. Application rollback

Find a known-good revision:

```bash
cd /root/frankenvoice
git log --oneline --decorate -20
```

Check out the known-good commit:

```bash
git switch --detach <COMMIT_SHA>
cd deploy/alibaba
docker compose up -d --build
```

Verify the rollback before changing DNS or restoring data.

Return to the current release later:

```bash
cd /root/frankenvoice
git switch main
git pull --ff-only
cd deploy/alibaba
docker compose up -d --build
```

Application rollback and data rollback are separate operations. Do not restore an older data volume unless the data itself is damaged or incompatible.

---

# 15. Security hardening

Minimum production controls:

- Restrict SSH port 22 to the administrator's IP.
- Prefer an SSH key over password login after initial setup.
- Keep `.env` mode at `600`.
- Never expose the backend or port 8088 publicly.
- Use Cloudflare **Full (strict)** TLS.
- Keep Ubuntu, Docker, Nginx, and Certbot updated.
- Do not place API keys in frontend variables or browser code.
- Do not show secrets in Workbench screenshots or shell history.
- Rotate the DashScope key immediately if it is exposed.

Basic host updates:

```bash
apt update
apt upgrade -y
```

Reboot when required, then verify Docker and Nginx:

```bash
reboot
```

After reconnecting:

```bash
systemctl status docker --no-pager
systemctl status nginx --no-pager
cd /root/frankenvoice/deploy/alibaba
docker compose ps
```

---

# 16. Monitoring suggestions

At minimum monitor:

- `https://frankenvoice.frankenmint.com/health`;
- HTTP status and response time for the homepage;
- Docker container restart counts;
- disk usage;
- memory pressure;
- certificate expiration;
- Qwen request failures and quota errors.

Useful manual checks:

```bash
df -h
free -h
docker stats --no-stream
docker compose ps
certbot certificates
```

A lightweight uptime monitor should alert when `/health` is not HTTP 200.

---

# 17. Incident recovery sequence

Use this order during an outage:

1. Confirm DNS resolves to the intended ECS address.
2. Check Cloudflare status and SSL mode.
3. Test the ECS origin over loopback:
   ```bash
   curl http://127.0.0.1:8088/health
   ```
4. Check container state and logs.
5. Validate host Nginx with `nginx -t`.
6. Confirm ports 80 and 443 are listening.
7. Rebuild containers only when configuration and logs justify it.
8. Restore persistent data only when the volume is known to be damaged.
9. Document the incident, root cause, and exact recovery commit.

---

# 18. Clean undeployment

Stop the application while preserving data:

```bash
cd /root/frankenvoice/deploy/alibaba
docker compose down
```

Stop and permanently remove the persistent data volume only after a verified backup:

```bash
docker compose down -v
```

Remove the host Nginx site:

```bash
rm -f /etc/nginx/sites-enabled/frankenvoice
rm -f /etc/nginx/sites-available/frankenvoice
nginx -t
systemctl reload nginx
```

Remove the Cloudflare DNS record only after the application is intentionally retired or moved.

---

# Operational quick reference

```bash
cd /root/frankenvoice/deploy/alibaba

# Status
docker compose ps

# Health
curl http://127.0.0.1:8088/health

# Qwen provider state
curl http://127.0.0.1:8088/api/providers/status | jq

# Logs
docker compose logs --tail=200 backend
docker compose logs --tail=200 frontend

# Deploy current main
cd /root/frankenvoice
git switch main
git pull --ff-only
cd deploy/alibaba
docker compose up -d --build

# Validate public deployment
curl -I https://frankenvoice.frankenmint.com/
curl https://frankenvoice.frankenmint.com/health
```
