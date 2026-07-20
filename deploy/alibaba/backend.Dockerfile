FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DENO_INSTALL=/usr/local/deno \
    PATH=/usr/local/deno/bin:$PATH

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    unzip \
    ffmpeg \
    espeak-ng \
    rubberband-cli \
    libsndfile1 \
    git \
    && curl -fsSL https://deno.land/install.sh | sh \
    && deno --version \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && mv /usr/local/bin/yt-dlp /usr/local/bin/yt-dlp-real

COPY deploy/alibaba/yt-dlp-guard /usr/local/bin/yt-dlp
RUN chmod 0755 /usr/local/bin/yt-dlp

COPY backend ./backend
RUN mkdir -p \
    /app/data/autopilot/runs \
    /app/data/dataset/clips \
    /app/data/sources

EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
