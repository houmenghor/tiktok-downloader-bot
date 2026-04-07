# TikTok Downloader — Telegram Bot

A Telegram bot that downloads TikTok videos at **1080p or 1440p** quality and sends them directly back to you in chat.  
Supports single links, batch downloads via `.txt` file, handles large files automatically, and works for multiple users at the same time.

---

## What it can do

- Paste a single TikTok link → get the video back
- Upload a `.txt` file with hundreds of links → get all videos back one by one
- Choose quality: **1080p** or **1440p**
- Videos over 45 MB are automatically split into parts and sent in order
- Multiple users can use the bot at the same time — all downloads run in a queue
- Check how many jobs are waiting with `/queue`

---

## How to use (as a user)

**Single video:**
1. Open the bot in Telegram
2. Paste any TikTok link and send it
3. Tap **1080p** or **1440p**
4. Wait — the bot will send the video back

**Multiple videos at once:**
1. Create a `.txt` file on your computer
2. Put one TikTok link per line, like this:
   ```
   https://www.tiktok.com/@user/video/123456
   https://vm.tiktok.com/ABCD123/
   https://www.tiktok.com/@user/video/789012
   ```
3. Upload the file to the bot
4. Tap **1080p** or **1440p**
5. The bot will download and send each video one by one

**Commands:**
| Command | What it does |
|---|---|
| `/start` | Show welcome message |
| `/queue` | Show how many videos are currently waiting |

---

## Setup (self-hosted on Ubuntu server)

### 1 — Get your Bot Token

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the steps
3. Copy the token it gives you (looks like `123456789:ABCdef...`)

---

### 2 — Install requirements

```bash
sudo apt update && sudo apt install -y git docker.io docker-compose-plugin
```

---

### 3 — Clone the project

```bash
git clone https://github.com/yourname/tiktok-downloader-telegram.git
cd tiktok-downloader-telegram
```

---

### 4 — Configure

```bash
cp .env.example .env
nano .env
```

The only thing you **must** set is your Bot Token:

```env
BOT_TOKEN=123456789:ABCdef...
```

Everything else works out of the box. Full list of options:

| Variable | Default | Description |
|---|---|---|
| `BOT_TOKEN` | *(required)* | Your Telegram bot token from @BotFather |
| `DOWNLOAD_DIR` | `/tmp/tiktok_downloads` | Where videos are stored temporarily |
| `MAX_WORKERS` | `3` | How many videos download at the same time |
| `MAX_FILE_SIZE_MB` | `45` | Videos larger than this get split into parts |
| `SESSION_TTL` | `300` | Seconds before a quality selection expires |
| `FFMPEG_PATH` | `ffmpeg` | Path to ffmpeg (leave as-is for Docker) |
| `FFPROBE_PATH` | `ffprobe` | Path to ffprobe (leave as-is for Docker) |
| `COOKIES_FILE` | *(optional)* | Path to TikTok cookies file if downloads get blocked |

---

### 5 — Run with Docker

```bash
docker compose up -d --build
```

That's it. The bot is now running.

**Check if it's working:**
```bash
docker compose logs -f
```

You should see:
```
Bot started. Polling...
DownloadQueue started — 3 workers
```

---

## Useful commands

```bash
# Start the bot
docker compose up -d --build

# Stop the bot
docker compose down

# See live logs
docker compose logs -f

# Restart after changing .env
docker compose restart

# Update code and restart
git pull
docker compose up -d --build
```

---

## Run without Docker (manual)

```bash
# Install ffmpeg
sudo apt install -y ffmpeg

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env  # set BOT_TOKEN

# Run
python main.py
```

To keep it running after you close the terminal:
```bash
nohup python main.py > bot.log 2>&1 &
```

---

## Project structure

```
├── main.py               ← start here
├── config/               ← all settings loaded from .env
├── src/
│   ├── bot.py            ← wires everything together
│   ├── downloader.py     ← downloads videos using yt-dlp
│   ├── queue_manager.py  ← handles multiple users fairly
│   └── handlers/         ← responds to Telegram messages
├── helper/
│   ├── link_parser.py    ← finds TikTok links in text
│   ├── file_utils.py     ← file cleanup and paths
│   └── splitter.py       ← splits large videos with ffmpeg
├── ui/
│   ├── keyboards.py      ← quality buttons
│   └── templates.py      ← all bot messages in one place
├── assets/               ← drop cookies.txt here if needed
├── Dockerfile
├── docker-compose.yml
└── .env.example          ← copy this to .env and fill in your token
```

---

## TikTok blocking downloads?

TikTok sometimes blocks yt-dlp. The fix is to give the bot your browser cookies:

1. Install a browser extension like **"Get cookies.txt LOCALLY"** (Chrome/Firefox)
2. Go to [tiktok.com](https://www.tiktok.com) and make sure you're logged in
3. Export cookies → save the file as `assets/cookies.txt`
4. Edit your `.env`:
   ```env
   COOKIES_FILE=assets/cookies.txt
   ```
5. Restart the bot:
   ```bash
   docker compose restart
   ```

---

## Notes

- Videos are **deleted from the server** immediately after being sent to you
- Telegram's file size limit is 50 MB per message — the bot handles this by splitting automatically
- The quality you pick (1080p / 1440p) is the **maximum** — if TikTok doesn't have that quality, the best available is used instead
