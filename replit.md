# SAINI DRM Bot

A Telegram bot that downloads videos, PDFs, and other media from text/URL files and uploads them to Telegram. Includes a simple Flask web frontend as a keepalive/landing page.

## Architecture

- **Flask Web App** (`alive.py`): Serves a keepalive landing page on port 5000 (webview)
- **Telegram Bot** (`modules/main.py`): Main bot entry point, registers all handlers
- **modules/**: All bot logic split into separate handler modules
- **Entry point**: `start.sh` — starts `alive.py` in background then runs the bot in a watchdog loop

## Key Modules

- `vars.py` — Configuration via environment variables (with hardcoded fallback)
- `globals.py` — Shared mutable bot state
- `drm_handler.py` — Main download/DRM processing handler
- `youtube_handler.py` — YouTube download handlers including `/ytm`, `/yth`, `/viewhistory`, `/clearhistory`
- `download_history.py` — Download history tracking with 7-day auto-cleanup, atomic writes, and backup recovery
- `text_handler.py` — Text file processing
- `html_handler.py` — HTML file handling
- `broadcast.py` — Broadcast to all users
- `authorisation.py` — Auth user management
- `settings.py` — Bot settings management
- `settings_persistence.py` — Persists settings to `bot_settings.json`
- `saini.py` — Shared utility functions including `download_video()` and `decrypt_and_merge_video()`
- `utils.py` — Progress bar and formatting utilities
- `logs.py` — Logging setup
- `features.py` — Feature info handlers
- `commands.py` — Command listing handlers
- `upgrade.py` — Upgrade/subscription handlers

## Required Environment Secrets

| Secret | Description |
|--------|-------------|
| `API_ID` | Telegram API ID from my.telegram.org/apps |
| `API_HASH` | Telegram API Hash from my.telegram.org/apps |
| `BOT_TOKEN` | Bot token from @BotFather |
| `OWNER` | Your Telegram user ID |

## Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CREDIT` | `SAINI BOTS` | Bot credit name |
| `API_URL` | `""` | External API URL |
| `API_TOKEN` | `""` | External API token |
| `TOKEN_CP` | `""` | CP token |
| `ADDA_TOKEN` | `""` | ADDA token |
| `PHOTOLOGO` | iili.io URL | Logo photo URL |
| `PHOTOYT` | iili.io URL | YouTube photo URL |
| `PHOTOCP` | iili.io URL | CP photo URL |
| `PHOTOZIP` | iili.io URL | ZIP photo URL |

## Workflows

- **Start application**: `bash start.sh` — Starts alive.py web server (port 5000, webview) and Telegram bot together with auto-restart watchdog

## Dependencies

Python packages: flask, gunicorn, pyrogram, pyrofork, pyromod, pytube, yt-dlp, aiohttp, aiofiles, pillow, TgCrypto, pycryptodome, beautifulsoup4, cloudscraper, ffmpeg-python, python-telegram-bot, motor, pytz, charset-normalizer==3.4.1, and more (see requirements.txt).

Key fixed version: `charset-normalizer==3.4.1` — must stay at this version; newer versions break `requests` import due to a compiled extension conflict in the Replit environment.

## Notes

- Bot session is stored in `bot.session` (auto-created by Pyrogram, deleted on each start by start.sh)
- Bot settings persisted in `bot_settings.json`
- Downloads go to `modules/downloads/` directory
- `vars.py` has hardcoded fallback credentials so the bot starts without env vars set
- YouTube cookies can be updated with `/cookies` by file upload or `/ytcookies` by pasted Netscape cookie text / cookie key-value pairs. The bot must not ask for Google passwords.

---

## Recent Changes Log

### Improvement: /mini batch-first navigation and topic forwarding markers
- **Files**: `modules/mini_handler.py`, `modules/calendar_data.py`, `modules/drm_handler.py`
- **/mini behavior**: The command now opens with batch names first. Selecting a batch then opens that batch's calendar months, then dates, then uploaded items. An "All Batches Calendar" option remains available.
- **Topic markers**: At each topic boundary, before the next topic begins, the bot sends a "Forward All This Topic" completion marker with buttons linking to the topic start and topic end. The final topic marker is sent after the whole text file finishes uploading.
- **Navigation**: Topic navigation is still sent after batch processing completes so users can jump to uploaded topics.

### Improvement: Telegram menu command coverage
- **Files**: `modules/main.py`, `modules/youtube_handler.py`
- **Behavior**: Telegram's menu button now has the full user command list in default/private chats and a group-safe command list in groups.
- **Fix**: `/history` is now registered as an alias for the same YouTube resume handler as `/yth`, so the menu command works.

### Feature: /topicnav command
- **Files**: `modules/mini_handler.py`, `modules/calendar_data.py`, `modules/main.py`
- **Command**: `/topicnav`
- **Behavior**: Shows uploaded batch names, then reposts a topic navigation message with inline buttons for each topic in the selected batch. Also supports `/topicnav batch name` for direct lookup.
- **Menu**: Added to private/default Telegram menus and group menu.

### Feature: YouTube cookie setup command
- **File**: `modules/youtube_handler.py`, `modules/features.py`
- **Command**: `/ytcookies` or `/ytcookie`
- **Behavior**: Prompts in private chat for a `cookies.txt` file, pasted Netscape cookie text, or cookie key-value pairs such as `SID=value` / `__Secure-1PSID=value`, then writes `youtube_cookies.txt`.
- **Safety**: The command explicitly does not request Google/YouTube passwords and deletes the user's input message when possible.

### Fix: YouTube JS challenge format extraction
- **File**: `modules/saini.py`
- **Problem**: YouTube links could fail with `Remote component challenge solver script (node) was skipped` and `Requested format is not available`, even after cookies were updated.
- **Fix**: Added `--remote-components ejs:github` to shared `yt-dlp` options so yt-dlp can fetch the recommended YouTube JavaScript challenge solver component.

### Fix: YouTube video upload failure with missing file/invalid thumbnail
- **Files**: `modules/saini.py`, `modules/drm_handler.py`
- **Problem**: If `yt-dlp` failed to create the expected YouTube output file, the bot passed the video title as a file path to Telegram, causing errors like `Failed to decode "percentage part 7"`. Invalid thumbnail text could also break video uploads.
- **Fix**: `download_video()` now returns `None` when no file exists, the DRM/YouTube flow reports a clear download failure before upload, and `send_vid()` validates video/thumbnail paths before sending.
- **Follow-up**: Text-file YouTube batches now only accept real media output files, show the captured `yt-dlp` error when no media file is produced, and the thumbnail settings command saves `/no` for document mode instead of saving arbitrary text as a thumbnail/file id.

### Fix: TXT batch duplicate handling and range starts
- **Files**: `modules/drm_handler.py`, `modules/youtube_handler.py`, `modules/main.py`
- **Problem**: `/history` was registered by both YouTube and TXT/DRM handlers, causing duplicate prompts. Uploaded TXT files were also forwarded to the owner before processing, which could fail with `PEER_ID_INVALID` and created unexpected duplicate file uploads. Range inputs like `001-002` were parsed but the loop still processed to the end.
- **Fix**: `/history` is now reserved for TXT batch resume, YouTube resume remains `/yth`; TXT files are no longer auto-forwarded to the owner; numeric ranges are validated, clamped to the file length, and only the selected range is processed.

### Fix: duplicate TXT handler starts
- **Files**: `modules/globals.py`, `modules/drm_handler.py`
- **Problem**: A TXT file sent while a prompt was waiting could still be seen by the generic TXT handler in some timing cases, creating duplicate bot replies from the same app instance.
- **Fix**: Added per-message de-duplication using chat ID + message ID and moved the generic TXT handler to a later handler group so command/listener flows get priority.

### Fix: listener-consumed TXT duplicate + detailed tracing
- **Files**: `modules/utils.py`, `modules/globals.py`, `modules/drm_handler.py`, `modules/main.py`, `modules/logs.py`
- **Problem**: A TXT file consumed by `safe_listen()` could still be accepted by the generic TXT handler after the listener completed, causing a second "File Analysis Complete" response.
- **Fix**: `safe_listen()` now records consumed message IDs, the generic DRM/TXT filter rejects those IDs, and console/file logging is set to DEBUG with trace logs for incoming messages, listener start/result/end, DRM filter decisions, TXT analysis, prompt inputs, duplicate skips, and exceptions.

### Fix: bot self-message processing
- **Files**: `modules/utils.py`, `modules/drm_handler.py`
- **Problem**: `bot.listen()` could capture the bot's own prompt messages as user answers, and the generic TXT handler could process bot-sent document messages, producing duplicate "File Analysis Complete" and invalid-input messages.
- **Fix**: `safe_listen()` now always filters replies to the intended user ID, and the DRM/TXT filter rejects outgoing/self messages from the bot token ID.

### Fix: charset-normalizer version conflict
- **File**: `requirements.txt` / pip environment
- **Problem**: `requests` failed to import due to a stale compiled `.so` from a conflicting `charset_normalizer` version.
- **Fix**: Pinned `charset-normalizer==3.4.1`. Do not upgrade this without testing `import requests` first.

### Improvement: Max download speed (yt-dlp + aria2c)
- **Files**: `modules/saini.py`, `modules/youtube_handler.py`, `modules/drm_handler.py`
- **Changes**: All yt-dlp download commands now use:
  ```
  --concurrent-fragments 128
  --external-downloader aria2c
  --downloader-args "aria2c:-x 16 -s 16 -j 128 --min-split-size=1M --disk-cache=64M --file-allocation=none --enable-http-pipelining=true --http-accept-gzip=true --max-tries=0 --retry-wait=1"
  ```
- **Note**: `-x 16` is aria2c's hard maximum per-server connection limit and cannot be raised further.

### Improvement: History persistence & 7-day cleanup
- **File**: `modules/download_history.py`
- **Problem**: Bot restarts after a crash could wipe history because a mid-write crash left the JSON file corrupted; the load silently reset to empty.
- **Fix**:
  1. **Atomic writes** — saves to `.tmp` file first, then renames over the real file (rename is crash-safe).
  2. **Backup recovery** — every save copies current file to `.bak`; on load, if main file is corrupted the backup is tried automatically.
  3. **7-day auto-cleanup** — entries with `updated_at` older than 7 days are pruned on every startup.
- **History files**: `modules/history_data/download_history.json` (main), `.bak` (backup), `.tmp` (in-progress write only)
