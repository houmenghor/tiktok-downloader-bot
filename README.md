# TikTok Downloader — Telegram Bot

A self-hosted Telegram bot that downloads TikTok videos, audio, and photo slideshows and sends them directly back to you — or saves them to a folder on your machine for batch downloads.

**Developer:** Hou Menghor  
**Contact:** [@houmenghor](https://t.me/houmenghor)

---

## Features

| Feature | Details |
|---|---|
| 🎬 Video download | 1080p or 1440p — best available quality |
| 🎵 Audio extraction | MP3 at 192 kbps |
| 🖼 Photo slideshow | Downloads all photos and sends as album |
| 📄 Batch `.txt` upload | One link per line — hundreds at a time |
| 📂 Batch save to folder | Choose Desktop / Downloads / Telegram Desktop — no Telegram upload |
| ✂️ Auto file splitting | Videos > 45 MB are split and sent in order |
| 👥 Multi-user queue | Fair FIFO queue with 3 parallel workers |
| 🌐 Bilingual UI | English and Khmer (ខ្មែរ) |
| 📊 Stats | `/stats` shows total users and downloads |
| 📋 Queue status | `/status` shows how many jobs are running |
| 🍪 Cookie support | Feed browser cookies to bypass TikTok blocks |
| 🗄 MongoDB backend | User data survives restarts (auto-falls back to JSON) |

---

## Commands

| Command | Description |
|---|---|
| `/start` | Welcome message and instructions |
| `/status` | Show how many downloads are in progress |
| `/stats` | Total users and total downloads |
| `/language` | Switch between English and Khmer |

---

## How to use

### Single link → sent back to chat
1. Send any TikTok link
2. Choose **1080p**, **1440p**, or **🎵 Audio only**
3. The bot downloads and sends it back

### Batch download → choose a save folder
1. Create a `.txt` file with one TikTok link per line
2. Upload the file to the bot
3. Choose quality
4. Choose a save folder (Telegram Desktop / Downloads / Desktop)
5. Files are saved silently — no upload to Telegram chat

---

## Setup

### 1 — Get your Bot Token

1. Open Telegram → search **@BotFather**
2. Send `/newbot` and follow the steps
3. Copy the token (e.g. `123456789:ABCdef...`)

---

### 2 — Configure

```bash
cp .env.example .env
```

Edit `.env` — the only required field is `BOT_TOKEN`:

| Variable | Default | Description |
|---|---|---|
| `BOT_TOKEN` | *(required)* | Your bot token from @BotFather |
| `DOWNLOAD_DIR` | `~/Downloads/Telegram Desktop` | Temp folder for downloads |
| `MAX_WORKERS` | `3` | Parallel download workers |
| `MAX_FILE_SIZE_MB` | `45` | Split threshold in MB |
| `SESSION_TTL` | `300` | Seconds before quality selection expires |
| `FFMPEG_PATH` | `ffmpeg` | Path to ffmpeg binary |
| `FFPROBE_PATH` | `ffprobe` | Path to ffprobe binary |
| `COOKIES_FILE` | *(optional)* | Path to TikTok cookies file |
| `MONGO_URI` | *(optional)* | MongoDB Atlas URI for persistent user data |
| `USERS_FILE` | `/data/users.json` | Fallback JSON path (used if MONGO_URI not set) |

---

### 3 — Run with Docker

```bash
docker compose up -d --build
```

Check logs:
```bash
docker compose logs -f
```

---

### 4 — Run without Docker

```bash
sudo apt install -y ffmpeg
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set BOT_TOKEN
python main.py
```

Keep running after terminal closes:
```bash
nohup python main.py > bot.log 2>&1 &
```

---

## Project structure

```
├── main.py                   ← entry point
├── config/
│   └── settings.py           ← all env vars as a frozen dataclass
├── src/
│   ├── bot.py                ← app wiring + process_job
│   ├── downloader.py         ← yt-dlp video / audio / photo download
│   ├── queue_manager.py      ← FIFO async queue with worker pool
│   └── handlers/
│       ├── commands.py       ← /start, /status, /stats
│       ├── messages.py       ← text links + .txt file handling
│       ├── callbacks.py      ← quality + folder picker callbacks
│       └── language.py       ← /language + language button callbacks
├── helper/
│   ├── link_parser.py        ← TikTok URL extraction + dedup
│   ├── file_utils.py         ← paths and cleanup
│   ├── splitter.py           ← ffmpeg video splitting
│   ├── user_store.py         ← auto-selects MongoDB or JSON backend
│   ├── user_store_mongo.py   ← MongoDB (motor) backend
│   └── _user_store_json.py   ← JSON file backend
├── ui/
│   ├── keyboards.py          ← quality, folder, language keyboards
│   └── templates.py          ← all messages in EN + KH
├── assets/                   ← place cookies.txt here if needed
├── Dockerfile
├── docker-compose.yml
├── render.yaml               ← Render.com Background Worker config
└── .env.example
```

---

## TikTok blocking downloads?

1. Install **"Get cookies.txt LOCALLY"** (Chrome/Firefox extension)
2. Go to [tiktok.com](https://www.tiktok.com) while logged in
3. Export cookies → save as `assets/cookies.txt`
4. Add to `.env`:
   ```env
   COOKIES_FILE=assets/cookies.txt
   ```
5. Restart the bot

---

## Notes

- Single-link downloads are sent directly to your Telegram chat
- Batch downloads are saved to your chosen folder — nothing uploaded to Telegram
- Files sent to chat are deleted from the server immediately after sending
- Quality you pick is the **maximum** — best available is used if TikTok doesn't have it
- MongoDB Atlas free tier works on Render.com (persistent across redeploys); JSON backend needs a Docker volume
