# ── Stage 1: base ─────────────────────────────────────────────────────────────
FROM python:3.12-alpine AS base

# ca-certificates + openssl fix MongoDB Atlas TLS on Alpine musl
RUN apk add --no-cache \
        ffmpeg \
        gcc \
        musl-dev \
        libffi-dev \
        ca-certificates \
        openssl \
    && update-ca-certificates

WORKDIR /app

# ── Stage 2: dependencies ─────────────────────────────────────────────────────
FROM base AS deps

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 3: final image ──────────────────────────────────────────────────────
FROM deps AS final

# Copy source code (excludes files listed in .dockerignore)
COPY . .

# Use system ffmpeg/ffprobe — override the Windows .exe paths from .env
ENV FFMPEG_PATH=ffmpeg
ENV FFPROBE_PATH=ffprobe

# Temp download directory (overridable at runtime)
ENV DOWNLOAD_DIR=/tmp/tiktok_downloads

# Non-root user for security (Alpine uses adduser)
RUN adduser -D -u 1000 botuser && chown -R botuser /app
USER botuser

CMD ["python", "main.py"]
