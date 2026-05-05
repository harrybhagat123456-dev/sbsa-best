# YouTube Download Fix — Full Technical Context for Gemini CLI

## PROJECT OVERVIEW

**Repo:** `harrybhagat123456-dev/sbsa-best` on GitHub
**Platform:** Telegram leech bot (Pyrogram 2.3.69) deployed on **Render** (Docker)
**Language:** Python 3.12
**Purpose:** Users send video URLs in Telegram → bot downloads them → uploads to a Telegram channel

### Deployment
- **Render** (free tier) — Docker-based deployment
- Docker image: `python:3.12-slim` + Deno + Node.js 22 + ffmpeg + aria2 + mp4decrypt (Bento4)
- yt-dlp installed via `pip install "yt-dlp[default]"` (includes EJS scripts)
- `bgutil-ytdlp-pot-provider` plugin installed for PO token generation
- The bot runs as: `gunicorn app:app & python3 modules/main.py`

---

## THE PROBLEM

YouTube video downloads **fail** with:
```
ERROR: [youtube] VIDEO_ID: Sign in to confirm you're not a bot. Use --cookies-from-browser or --cookies
```

This error occurs for **login-required/age-restricted** videos. Public videos (like Rick Astley) download fine without any cookies.

### Specific Failing Test Video
- URL: `https://www.youtube.com/watch?v=ngQhPYtCmJY`
- Title: "The Hindu Editorial Analysis | 07 October 2025"
- This video is NOT age-restricted or private — it's a normal editorial analysis
- It works when played in a browser
- It fails from Render's IP even WITH valid cookies
- It ALSO fails from my local machine WITH the same cookies
- It works from my local machine WITHOUT cookies for OTHER public videos

### Key Observation
The cookies file has **valid expiry dates** (all cookies expire between Oct 2026 - May 2028), but YouTube still rejects them server-side. This typically happens when:
1. Cookies were exported from one IP but used from a different IP/region
2. YouTube flagged the session for suspicious activity
3. YouTube requires PO tokens in addition to cookies (new anti-bot measure)

---

## ALL ERRORS ENCOUNTERED (chronological)

### Error 1: "no such option: min-split-size" (Exit Code 2)
```
yt-dlp: error: no such option: min-split-size
```
**Root Cause:** In `modules/saini.py`, `_YTDLP_EXTRA` appended `--downloader-args {_ARIA2C_ARGS}` without quotes around the aria2c args. The shell split `--min-split-size=1M` as a separate yt-dlp argument.
**Fix:** Changed `f'--downloader-args {_ARIA2C_ARGS}'` → `f'--downloader-args "{_ARIA2C_ARGS}"'` ✅ FIXED

### Error 2: "Requested format is not available" (Exit Code 1)
```
ERROR: [youtube] VIDEO_ID: Requested format is not available
```
**Root Cause:** Format selector `bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b` was too strict.
**Fix:** Changed to `bestvideo+bestaudio/best` ✅ FIXED

### Error 3: Invalid po_token format
```
WARNING: Invalid po_token configuration format. Expected "CLIENT.CONTEXT+PO_TOKEN", got "web"
```
**Root Cause:** Previously had `--extractor-args youtube:po_token=web` in the yt-dlp command. This is invalid syntax.
**Fix:** Removed all `--extractor-args` from yt-dlp commands, letting bgutil plugin handle PO tokens automatically. ✅ FIXED

### Error 4: No JavaScript Runtime
```
WARNING: No supported JavaScript runtime could be found
```
**Root Cause:** Deno was installed in Dockerfile but `ENV PATH` wasn't set properly, so yt-dlp couldn't find it.
**Fix:** Added `ENV PATH="/usr/local/bin:$PATH"` + `deno --version` verification step in Dockerfile. Also added Node.js 22 as fallback. ✅ FIXED

### Error 5 (CURRENT): "Sign in to confirm you're not a bot" (Exit Code 1)
```
WARNING: [youtube] No title found in player responses; falling back to title from initial data.
ERROR: [youtube] VIDEO_ID: Sign in to confirm you're not a bot.
```
**Status:** ❌ UNRESOLVED — This is the main problem we need to solve.

---

## ALL FIXES ATTEMPTED

### 1. Added `--cookies` flag to yt-dlp command
- Added `--cookies "/app/modules/youtube_cookies.txt"` to the yt-dlp command in drm_handler.py
- Cookies are a Netscape-format file exported from Firefox
- Result: Still blocked ❌

### 2. Added `--extractor-args youtube:player_client=tv_simply,ios,android_vr`
- Tried different YouTube player clients as fallback
- Some clients (tv_simply) are less aggressive about bot detection
- Result: All clients blocked ❌

### 3. Added `--extractor-args youtube:po_token=web`
- Tried to pass a PO token directly
- Invalid format — yt-dlp expects `CLIENT.CONTEXT+PO_TOKEN` not just `web`
- Result: Caused a new error, removed ❌

### 4. Removed ALL `--extractor-args`, let bgutil plugin handle it
- Installed `bgutil-ytdlp-pot-provider` plugin
- This plugin should automatically generate PO tokens via external server
- Result: Plugin's script-node and script-deno providers are **unavailable** (server build files not found). Only `bgutil:http` provider is available, but it needs a running server at `http://127.0.0.1:4416`. ❌

### 5. Changed format selector
- From strict: `bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b`
- To flexible: `bestvideo+bestaudio/best`
- Result: Fixed format errors but not the auth issue. Cookies still rejected. ✅ (for format issue)

### 6. Fixed aria2c downloader-args quoting
- Added double quotes around aria2c args in `--downloader-args`
- Result: Fixed the shell splitting issue ✅

### 7. Installed Deno + Node.js in Dockerfile
- Added `ENV PATH="/usr/local/bin:$PATH"` after Deno install
- Added Node.js 22.x as fallback JS runtime
- Added build verification steps (`deno --version`, `node --version`)
- Result: JS runtime now found by yt-dlp, but download still blocked because cookies are rejected ✅ (for JS runtime)

### 8. Replaced shell-based yt-dlp with Python API
- Created new `download_youtube_video()` function in `saini.py`
- Uses `yt_dlp.YoutubeDL` Python API instead of subprocess shell commands
- Multi-strategy fallback: 5 client strategies × multiple format selectors
- Routes YouTube URLs through this new function in `drm_handler.py`
- Result: Public videos work (tested at 49 MB/s). Login-required videos still fail because cookies are rejected. ✅ (for public videos) ❌ (for login-required)

### 9. Tested ALL player clients individually via Python API
Tested `web`, `ios`, `tv_simply`, `mweb`, `mediaconnect`, `android`, `android_vr` — ALL return `LOGIN_REQUIRED` for the target video.
Result: ❌

### 10. Tested target video WITHOUT cookies
Still returns "Sign in to confirm you're not a bot" — this specific video requires authentication regardless.
Result: ❌

### 11. Tested a DIFFERENT public video WITHOUT cookies
`https://www.youtube.com/watch?v=dQw4w9WgXcQ` — works perfectly, returns 30+ formats, downloads at 49 MB/s.
Result: ✅

---

## CURRENT ARCHITECTURE

### File Structure (relevant files)
```
sbsa-best/
├── Dockerfile                          # Docker build config
├── modules/
│   ├── main.py                         # Bot entry point
│   ├── vars.py                         # Env vars, cookies_file_path
│   ├── saini.py                        # Core download functions
│   │   ├── download_video()            # Generic yt-dlp via subprocess + aria2c (non-YouTube)
│   │   ├── download_youtube_video()    # NEW: YouTube-specific, Python API, multi-strategy
│   │   ├── _resolve_cookies_path()     # Finds cookies file
│   │   ├── _yt_dlp_extract()          # Thread-based extraction
│   │   ├── _yt_dlp_download()         # Thread-based download
│   │   ├── _find_downloaded_media()    # Locates downloaded file
│   │   └── _YTDLP_EXTRA / _ARIA2C_ARGS # Shared download args
│   ├── drm_handler.py                  # Main URL handler (JW, Brightcove, YouTube, etc.)
│   │   ├── Line ~1652: yt-dlp command for YouTube (OLD, dead code now)
│   │   └── Line ~2082: Routes YouTube URLs to download_youtube_video() (NEW)
│   ├── youtube_handler.py              # /ytm, /y2t, /ytcookies, /getcookies commands
│   │   ├── /ytm: yt-dlp subprocess for audio download
│   │   ├── /y2t: yt-dlp subprocess for audio download
│   │   └── /ytcookies: Upload/update cookies
│   └── youtube_cookies.txt             # Netscape-format YouTube cookies
```

### Download Flow for YouTube URLs
```
User sends YouTube URL in Telegram
    ↓
drm_handler.py: URL detected as YouTube
    ↓
drm_handler.py line 2081: if "youtube.com" in url or "youtu.be" in url:
    ↓
helper.download_youtube_video(url, name, quality=raw_text2)  [saini.py]
    ↓
Strategy loop (5 clients × 4 formats = up to 20 attempts):
    1. web + cookies → extract_info → if formats found → download
    2. ios + cookies → extract_info → if formats found → download
    3. tv_simply + cookies → extract_info → if formats found → download
    4. web (no cookies) → extract_info → if formats found → download
    5. tv_simply (no cookies) → extract_info → if formats found → download
    ↓
Returns: path to .mp4 file OR None (with last_download_error set)
```

### Download Flow for Non-YouTube URLs
```
User sends non-YouTube URL
    ↓
drm_handler.py: URL is generic
    ↓
helper.download_video(url, cmd, name)  [saini.py]
    ↓
Shell command: yt-dlp + _YTDLP_EXTRA (includes aria2c args)
    ↓
Returns: path to file OR None
```

---

## CURRENT DOCKERFILE
```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl unzip ffmpeg aria2 gcc g++ make cmake wget git
RUN curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh
ENV PATH="/usr/local/bin:$PATH"
RUN deno --version
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && apt-get install -y nodejs
RUN node --version
# ... Bento4 build ...
WORKDIR /app
COPY . .
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel \
    && pip3 install --no-cache-dir --upgrade -r sainibots.txt \
    && pip3 install --no-cache-dir --upgrade "yt-dlp[default]" \
    && pip3 install --no-cache-dir --upgrade bgutil-ytdlp-pot-provider
RUN yt-dlp --version && yt-dlp --list-interfaces 2>&1 | head -5
EXPOSE 8000
CMD ["sh", "-c", "rm -f bot.session bot.session-journal && gunicorn --bind 0.0.0.0:${PORT:-8000} app:app & python3 modules/main.py"]
```

---

## COOKIES FILE ANALYSIS
```
File: modules/youtube_cookies.txt
Format: Netscape HTTP Cookie File
Size: ~1921 bytes (19 cookies)

All cookies VALID by date (none expired):
  __Secure-3PAPISID    ✅ expires 2026-11-01
  __Secure-3PSID       ✅ expires 2026-11-01
  __Secure-1PSIDTS     ✅ expires 2026-11-01
  __Secure-3PSIDTS     ✅ expires 2026-11-01
  __Secure-3PSIDCC     ✅ expires 2027-05-05
  VISITOR_INFO1_LIVE   ✅ expires 2026-11-01
  __Secure-YNID        ✅ expires 2026-11-01
  __Secure-ROLLOUT_TOKEN ✅ expires 2026-11-01
  __Secure-YT_TVFAS    ✅ expires 2028-05-04
  __Secure-YT_DERP     ✅ expires 2027-05-20
  GPS                  ✅ expires 2026-05-05
  SOCS                 ✅ expires (session)

Despite valid dates, YouTube rejects these cookies. Likely causes:
- Exported from a different IP/region than Render's US IP
- YouTube invalidated the session server-side
- YouTube now requires PO tokens IN ADDITION to cookies
```

---

## YT-DLP DEBUG OUTPUT (verbose)

### Key debug lines from testing:
```
[debug] JS runtimes: deno-2.7.14
[debug] Plugin directories: /home/z/.venv/lib/python3.12/site-packages/yt_dlp_plugins
[debug] Loaded 1864 extractors
[debug] [youtube] [pot:bgutil:script-node] Script path doesn't exist: /home/z/bgutil-ytdlp-pot-provider/server/build/generate_once.js
[debug] [youtube] [pot:bgutil:script-deno] Script path doesn't exist: /home/z/bgutil-ytdlp-pot-provider/server/src/generate_once.ts
[debug] [youtube] [pot] PO Token Providers: bgutil:http-1.3.1 (external), bgutil:script-node-1.3.1 (external, unavailable), bgutil:script-deno-1.3.1 (external, unavailable)
[debug] [youtube] [pot] PO Token Cache Providers: memory
[debug] [youtube] [pot] PO Token Cache Spec Providers: webpo
[debug] [youtube] [jsc] JS Challenge Providers: deno
[debug] [youtube] Detected experiment to bind GVS PO Token to video ID for web client
[debug] [youtube] VIDEO_ID: web player response playability status: LOGIN_REQUIRED
[debug] [youtube] VIDEO_ID: android_vr player response playability status: LOGIN_REQUIRED
[debug] [youtube] VIDEO_ID: web_safari player response playability status: LOGIN_REQUIRED
ERROR: [youtube] VIDEO_ID: Sign in to confirm you're not a bot.
```

### Critical findings from debug:
1. **bgutil:script-node and bgutil:script-deno are UNAVAILABLE** — server build files not installed
2. **bgutil:http is available** but it tries to connect to `http://127.0.0.1:4416` which isn't running
3. **YouTube detected "experiment to bind GVS PO Token to video ID for web client"** — this is a new anti-bot measure where PO tokens are tied to specific video IDs
4. **ALL player clients return LOGIN_REQUIRED** — web, android_vr, web_safari, ios, tv_simply
5. The JS challenge provider (Deno) works fine for the EJS n-challenge, but the login/auth layer is separate

---

## WHAT WORKS vs WHAT DOESN'T

### ✅ WORKS
- Public YouTube videos (tested: `dQw4w9WgXcQ`) — downloads at 48 MB/s without cookies
- Non-YouTube URLs (Brightcove, DASH, direct links) — work via aria2c + subprocess
- Dockerfile builds successfully with Deno + Node.js
- yt-dlp correctly detects Deno as JS runtime
- Cookie file parsing and upload via `/ytcookies` command
- Multiple format selection strategies
- The `download_youtube_video()` multi-strategy function logic is correct

### ❌ DOESN'T WORK
- Login-required or bot-flagged YouTube videos (tested: `ngQhPYtCmJY`)
- bgutil plugin's script-based PO token generation (server files not found)
- bgutil plugin's http-based PO token generation (server not running at port 4416)
- Cookies exported from user's PC are rejected by YouTube from Render's IP
- The specific video `ngQhPYtCmJY` fails from ALL tested IPs with ALL strategies

---

## POTENTIAL SOLUTIONS TO TRY

### Solution A: Fix bgutil PO Token Generation (RECOMMENDED)
The bgutil plugin has 3 providers:
1. `bgutil:http` — connects to external HTTP server. Needs `bgutil-ytdlp-pot-provider` server running at `http://127.0.0.1:4416`.
2. `bgutil:script-node` — runs Node.js script locally. Needs server build at `.../bgutil-ytdlp-pot-provider/server/build/generate_once.js`
3. `bgutil:script-deno` — runs Deno script locally. Needs server source at `.../bgutil-ytdlp-pot-provider/server/src/generate_once.ts`

**To fix script-node provider:**
1. Clone `https://github.com/Brainy09/bgutil-ytdlp-pot-provider` in the Docker build
2. Build the server: `cd server && npm install && npm run build`
3. Set env var or yt-dlp option to point to the build directory

**To fix http provider:**
1. Start the bgutil server as a background process in the Docker container
2. Or use the public bgutil server if available (check their docs)

### Solution B: Use `--po-token` with Manually Obtained Token
1. Obtain a valid PO token from the browser (using browser dev tools network tab, or tools like `po-token-generator`)
2. Pass it via yt-dlp: `--extractor-args "youtube:po_token=web+PO_TOKEN_HERE"`
3. The format is: `CLIENT.CONTEXT+PO_TOKEN` (e.g., `web+gASAAAA...`)
4. Problem: PO tokens are short-lived and video-specific

### Solution C: Use a Proxy (same region as cookie export)
1. Use a residential/HTTP proxy in the same region as where the cookies were exported
2. Pass via yt-dlp: `--proxy "http://user:pass@proxy:port"`
3. This makes YouTube think the request comes from the same IP as the browser session
4. Cost: proxy services cost money

### Solution D: Fresh Cookies from Render's IP
1. Use a headless browser (Playwright/Puppeteer) on Render to:
   - Open YouTube
   - Complete the login flow (OAuth or username/password)
   - Export cookies automatically
2. This gives cookies that are native to Render's IP
3. Problem: Render free tier may not have enough memory for a headless browser
4. Alternative: Run the headless browser login locally, get cookies, then use from Render (but this may have the same IP mismatch issue)

### Solution E: Use `--extractor-args youtube:player_client=tv` with OAuth
1. The `tv` client (Smart TV) uses a different auth flow that may be less aggressive
2. Generate OAuth credentials for YouTube TV app
3. Pass them via yt-dlp's `--extractor-args`

### Solution F: Use yt-dlp Nightly/Edge Build
1. The yt-dlp nightly builds sometimes have newer YouTube extraction fixes
2. Install via: `pip install --pre yt-dlp`
3. Or from GitHub: `pip install git+https://github.com/yt-dlp/yt-dlp@master`

### Solution G: Use an Alternative YouTube Library
1. `pytube` — simpler but often broken
2. `youtube-transcript-api` — for transcripts only
3. Custom implementation using YouTube's innerTube API directly (what yt-dlp does internally)
4. Use `Gallery-dl` which has its own YouTube extractor

### Solution H: Browser Automation Fallback
1. When yt-dlp fails, fall back to Playwright/Selenium:
   - Open video URL in headless browser
   - Wait for video to load
   - Intercept network requests to find the actual video stream URLs
   - Download the stream URLs directly
2. More reliable but slower and uses more memory

---

## FILES TO MODIFY

| File | What to Change |
|------|---------------|
| `modules/saini.py` | The `download_youtube_video()` function — add PO token support, proxy support, or browser fallback |
| `Dockerfile` | Add bgutil server build, or add Playwright for browser automation |
| `modules/youtube_handler.py` | The `/ytm` and `/y2t` handlers still use old subprocess yt-dlp — should also use Python API |
| `modules/drm_handler.py` | Line ~1652 has dead code (old YouTube command) — can be cleaned up |

---

## ENVIRONMENT NOTES

- Render free tier: limited RAM (~512MB), limited build time
- Container must be stateless (ephemeral filesystem) — cookies file gets rebuilt from committed file on each deploy
- PORT env var is set by Render (default 10000)
- The cookies file is committed to the git repo at `modules/youtube_cookies.txt`

---

## IMPORTANT NOTES FOR GEMINI

1. **Do NOT suggest `--cookies-from-browser`** — this only works when a real browser is running on the same machine with the user logged in. There is no browser on Render.

2. **Do NOT suggest using `--po_token=web`** — this is invalid syntax. The correct format is `CLIENT.CONTEXT+ACTUAL_PO_TOKEN_BASE64`.

3. **The cookies file has VALID dates but YouTube REJECTS it server-side.** The problem is NOT expired cookies. It's IP mismatch or YouTube's new bot detection.

4. **The `download_youtube_video()` function in saini.py is the correct place to add any new download logic.** Do NOT modify the shell-based `download_video()` for YouTube — it's only used for non-YouTube URLs now.

5. **Public videos work perfectly.** Only login-required/bot-flagged videos fail. Any solution should not break the working public video path.

6. **The bot runs in an async event loop (Pyrogram).** Any new code must be async-compatible. Use `asyncio.get_event_loop().run_in_executor()` for blocking operations.

7. **Auto-push requirement:** After making any changes, always `git add && git commit && git push origin main` automatically. No manual steps.

8. **Language:** The user communicates in English. Code comments can be in English.
