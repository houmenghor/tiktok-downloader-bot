# ── Stage 1: base ─────────────────────────────────────────────────────────────
# Alpine is ~50 MB vs ~130 MB for slim. Uses musl libc — fully compatible here.
FROM python:3.12-alpine AS base

# Install ffmpeg + build deps for any C-extension pip packages
RUN apk add --no-cache \
        ffmpeg \
        gcc \
        musl-dev \
        libffi-dev

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

# Non-root user for security (Alpine uses adduser, not useradd)
RUN adduser -D -u 1000 botuser && chown -R botuser /app
USER botuser

CMD ["python", "main.py"]
