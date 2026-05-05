import os
import re
import time
import mmap
import datetime
import xml.etree.ElementTree as ET
import aiohttp
import aiofiles
import asyncio
import logging
import requests
import tgcrypto
import subprocess
import concurrent.futures
from math import ceil
from urllib.parse import urljoin
from utils import progress_bar
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from io import BytesIO
from pathlib import Path
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode
import yt_dlp

last_download_error = ""

# ── YouTube downloads use simple yt-dlp command via download_video() (no cookies) ──


# ── Download speed constants ──────────────────────────────────────────────────
# Shared aria2c args used in every yt-dlp download command
_ARIA2C_ARGS = (
    'aria2c:-x 16 '                 # 16 connections per server (max)
    '-s 16 '                       # 16 splits per file (max)
    '-j 16 '                       # 16 parallel fragment downloads (max)
    '--min-split-size=1M '         # minimum valid value for aria2c
    '--disk-cache=256M '           # large cache for maximum throughput
    '--file-allocation=none '
    '--enable-http-pipelining=true '
    '--http-accept-gzip=true '
    '--max-tries=0 '
    '--retry-wait=1'
)
_YTDLP_EXTRA = (
    '-R 0 '                        # infinite retries
    '--fragment-retries 0 '        # infinite fragment retries
    '--concurrent-fragments 16 '   # 16 concurrent fragments (max)
    '--socket-timeout 15 '         # faster timeout → quicker retry
    '--buffer-size 16K '           # larger read buffer
    '--http-chunk-size 10M '       # larger chunk per request
    '--throttled-rate 100K '       # auto-retry if speed drops below 100KB/s
    '--progress '                  # always show progress
    '--newline '                   # one line per progress update (console-friendly)
    '--no-part '
    '--external-downloader aria2c '
    f'--downloader-args "{_ARIA2C_ARGS}"'
)


def sanitize_filename(filename):
    """Clean filename for safe file operations"""
    # Remove or replace problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)  # Remove invalid chars
    filename = re.sub(r'[()[\]]', '', filename)       # Remove brackets
    filename = re.sub(r'\s+', ' ', filename)          # Replace multiple spaces with single space
    filename = filename.strip()                       # Remove leading/trailing spaces
    return filename[:200]  # Limit length to prevent long filename issues

def _find_downloaded_media(name):
    media_extensions = (".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi", ".ts")
    direct_candidates = [
        name,
        f"{name}.webm",
        f"{name}.mkv",
        f"{name}.mp4",
        f"{name}.mp4.webm",
    ]
    for candidate in direct_candidates:
        if os.path.isfile(candidate) and os.path.getsize(candidate) > 0:
            ext = os.path.splitext(candidate)[1].lower()
            if ext in media_extensions or candidate == name:
                return candidate

    folder = os.path.dirname(name) or "."
    prefix = os.path.basename(name)
    if not os.path.isdir(folder):
        return None

    matches = []
    for entry in os.listdir(folder):
        if not entry.startswith(prefix):
            continue
        path = os.path.join(folder, entry)
        ext = os.path.splitext(entry)[1].lower()
        if os.path.isfile(path) and ext in media_extensions and os.path.getsize(path) > 0:
            matches.append(path)
    if not matches:
        return None
    return max(matches, key=lambda p: os.path.getsize(p))

def duration(filename):
    """Get video duration with proper filename handling"""
    try:
        # Use subprocess list argument (no shell) to avoid escaping issues
        result = subprocess.run([
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            filename
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            print(f"ffprobe error for {filename}: {result.stderr}")
            return 60  # Return default duration of 60 seconds
        
        duration_str = result.stdout.strip()
        if duration_str and duration_str != 'N/A':
            return float(duration_str)
        else:
            return 60  # Default duration if unavailable
            
    except (ValueError, subprocess.SubprocessError) as e:
        print(f"Duration extraction error for {filename}: {e}")
        return 60  # Return default duration on error
 
def exec(cmd):
        process = subprocess.run(cmd, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        output = process.stdout.decode()
        print(output)
        return output
        #err = process.stdout.decode()

def pull_run(work, cmds):
    with concurrent.futures.ThreadPoolExecutor(max_workers=work) as executor:
        print("Waiting for tasks to complete")
        fut = executor.map(exec,cmds)
        
async def aio(url,name):
    k = f'{name}.pdf'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(k, mode='wb')
                await f.write(await resp.read())
                await f.close()
    return k


async def download(url,name):
    ka = f'{name}.pdf'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(ka, mode='wb')
                await f.write(await resp.read())
                await f.close()
    return ka


def parse_vid_info(info):
    info = info.strip()
    info = info.split("\n")
    new_info = []
    temp = []
    for i in info:
        i = str(i)
        if "[" not in i and '---' not in i:
            while "  " in i:
                i = i.replace("  ", " ")
            i.strip()
            i = i.split("|")[0].split(" ",2)
            try:
                if "RESOLUTION" not in i[2] and i[2] not in temp and "audio" not in i[2]:
                    temp.append(i[2])
                    new_info.append((i[0], i[2]))
            except:
                pass
    return new_info

def vid_info(info):
    info = info.strip()
    info = info.split("\n")
    new_info = dict()
    temp = []
    for i in info:
        i = str(i)
        if "[" not in i and '---' not in i:
            while "  " in i:
                i = i.replace("  ", " ")
            i.strip()
            i = i.split("|")[0].split(" ",3)
            try:
                if "RESOLUTION" not in i[2] and i[2] not in temp and "audio" not in i[2]:
                    temp.append(i[2])
                    
                    # temp.update(f'{i[2]}')
                    # new_info.append((i[2], i[0]))
                    #  mp4,mkv etc ==== f"({i[1]})" 
                    
                    new_info.update({f'{i[2]}':f'{i[0]}'})

            except:
                pass
    return new_info


async def decrypt_and_merge_video(mpd_url, keys_string, output_path, output_name, quality="720"):
    try:
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        cmd1 = f'yt-dlp -f "bv[height<={quality}]+ba/b" -o "{output_path}/file.%(ext)s" --allow-unplayable-format --no-check-certificate {_YTDLP_EXTRA} "{mpd_url}"'
        print(f"Running command: {cmd1}")
        _p1 = await asyncio.create_subprocess_shell(cmd1, stdout=None, stderr=None)
        await _p1.wait()

        avDir = list(output_path.iterdir())
        print(f"Downloaded files: {avDir}")
        print("Decrypting")

        video_decrypted = False
        audio_decrypted = False

        for data in avDir:
            if data.suffix == ".mp4" and not video_decrypted:
                cmd2 = f'mp4decrypt {keys_string} --show-progress "{data}" "{output_path}/video.mp4"'
                print(f"Running command: {cmd2}")
                _p2 = await asyncio.create_subprocess_shell(cmd2, stdout=None, stderr=None)
                await _p2.wait()
                if (output_path / "video.mp4").exists():
                    video_decrypted = True
                data.unlink()
            elif data.suffix == ".m4a" and not audio_decrypted:
                cmd3 = f'mp4decrypt {keys_string} --show-progress "{data}" "{output_path}/audio.m4a"'
                print(f"Running command: {cmd3}")
                _p3 = await asyncio.create_subprocess_shell(cmd3, stdout=None, stderr=None)
                await _p3.wait()
                if (output_path / "audio.m4a").exists():
                    audio_decrypted = True
                data.unlink()

        if not video_decrypted or not audio_decrypted:
            raise FileNotFoundError("Decryption failed: video or audio file not found.")

        cmd4 = f'ffmpeg -i "{output_path}/video.mp4" -i "{output_path}/audio.m4a" -c copy "{output_path}/{output_name}.mp4"'
        print(f"Running command: {cmd4}")
        _p4 = await asyncio.create_subprocess_shell(cmd4, stdout=None, stderr=None)
        await _p4.wait()
        if (output_path / "video.mp4").exists():
            (output_path / "video.mp4").unlink()
        if (output_path / "audio.m4a").exists():
            (output_path / "audio.m4a").unlink()
        
        filename = output_path / f"{output_name}.mp4"

        if not filename.exists():
            raise FileNotFoundError("Merged video file not found.")

        cmd5 = f'ffmpeg -i "{filename}" 2>&1 | grep "Duration"'
        duration_info = os.popen(cmd5).read()
        print(f"Duration info: {duration_info}")

        return str(filename)

    except Exception as e:
        print(f"Error during decryption and merging: {str(e)}")
        raise

async def run(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    print(f'[{cmd!r} exited with {proc.returncode}]')
    if proc.returncode == 1:
        return False
    if stdout:
        return f'[stdout]\n{stdout.decode()}'
    if stderr:
        return f'[stderr]\n{stderr.decode()}'

    

def old_download(url, file_name, chunk_size = 1024 * 10):
    if os.path.exists(file_name):
        os.remove(file_name)
    r = requests.get(url, allow_redirects=True, stream=True)
    with open(file_name, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=chunk_size):
            if chunk:
                fd.write(chunk)
    return file_name


def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size < 1024.0 or unit == 'PB':
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"


def time_name():
    date = datetime.date.today()
    now = datetime.datetime.now()
    current_time = now.strftime("%H%M%S")
    return f"{date} {current_time}.mp4"


# ═══════════════════════════════════════════════════════════════════════════════
# Auto-fetch free proxy from ProxyScrape API
# ═══════════════════════════════════════════════════════════════════════════════

_cached_proxy = ""
_cached_proxy_time = 0
_PROXY_CACHE_SECONDS = 1800  # Cache proxy for 30 minutes

def _auto_fetch_proxy():
    """
    Fetch a working free HTTP proxy from ProxyScrape API.
    Tests each proxy against YouTube and returns the first one that works.
    Returns empty string if no working proxy found.
    """
    import concurrent.futures
    global _cached_proxy, _cached_proxy_time

    # Return cached proxy if still fresh
    now = time.time()
    if _cached_proxy and (now - _cached_proxy_time) < _PROXY_CACHE_SECONDS:
        logging.info(f"[YT-PROXY] Using cached proxy (age: {int(now - _cached_proxy_time)}s)")
        return _cached_proxy

    logging.info("[YT-PROXY] No proxy configured, fetching free proxy from ProxyScrape...")

    try:
        # Fetch proxy list from ProxyScrape API
        resp = requests.get(
            "https://api.proxyscrape.com/v4/free-proxy-list/get",
            params={
                "request": "display_proxies",
                "proxy_format": "protocolipport",
                "format": "text",
                "timeout": "5000",
            },
            timeout=10
        )
        if resp.status_code != 200:
            logging.warning(f"[YT-PROXY] ProxyScrape API returned {resp.status_code}")
            return _cached_proxy  # Return stale cache if available

        proxy_lines = resp.text.strip().split("\n")
        # Only try HTTP/HTTPS proxies (faster, more compatible with yt-dlp)
        http_proxies = [p.strip() for p in proxy_lines if p.strip().startswith("http")]

        if not http_proxies:
            logging.warning("[YT-PROXY] No HTTP proxies found in list")
            return _cached_proxy

        logging.info(f"[YT-PROXY] Found {len(http_proxies)} HTTP proxies, testing...")

        # Test proxies in parallel against YouTube
        test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # Short video, fast test

        def _test_single(proxy_url):
            try:
                r = requests.get(
                    test_url,
                    proxies={"http": proxy_url, "https": proxy_url},
                    timeout=10,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                if r.status_code == 200 and "YouTube" in r.text:
                    return proxy_url
            except Exception:
                pass
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(_test_single, p): p for p in http_proxies[:20]}
            for future in concurrent.futures.as_completed(futures, timeout=30):
                result = future.result()
                if result:
                    _cached_proxy = result
                    _cached_proxy_time = now
                    logging.info(f"[YT-PROXY] Found working proxy: {result}")
                    return result

        logging.warning("[YT-PROXY] No working proxy found from ProxyScrape")
        return _cached_proxy  # Return stale cache if available

    except Exception as e:
        logging.error(f"[YT-PROXY] Error fetching proxies: {str(e)[:100]}")
        return _cached_proxy


# ═══════════════════════════════════════════════════════════════════════════════
# Robust YouTube Downloader — uses yt_dlp Python API with multi-strategy fallback
# Handles: cookies, multiple player clients, quality selection, aria2c fallback
# ═══════════════════════════════════════════════════════════════════════════════

def _resolve_cookies_path():
    """Find cookies file from known locations."""
    candidates = [
        os.path.join(os.path.dirname(__file__), "youtube_cookies.txt"),
        os.path.join(os.path.dirname(__file__), "..", "youtube_cookies.txt"),
        "youtube_cookies.txt",
        "/app/modules/youtube_cookies.txt",
    ]
    for p in candidates:
        abs_p = os.path.abspath(p)
        if os.path.isfile(abs_p) and os.path.getsize(abs_p) > 0:
            logging.info(f"[YT] Found cookies: {abs_p}")
            return abs_p
    logging.warning("[YT] No cookies file found")
    return None


def _yt_dlp_extract(ydl_opts):
    """Extract info using yt_dlp in a thread (avoids blocking event loop)."""
    import concurrent.futures
    def _do_extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(ydl_opts.get('_url'), download=False)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_do_extract).result()


def _yt_dlp_download(ydl_opts):
    """Download using yt_dlp in a thread (avoids blocking event loop)."""
    import concurrent.futures
    def _do_download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.download([ydl_opts.get('_url')])
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_do_download).result()


async def download_youtube_video(url, name, quality="720"):
    """
    Robust YouTube downloader with multi-strategy fallback.

    Strategies tried in order:
    1. Cookies + web client (best for login-required videos)
    2. Cookies + ios client (fallback for age-restricted)
    3. Cookies + tv_simply client (fallback)
    4. No cookies + web client (works for public videos)
    5. No cookies + tv_simply client

    Each strategy tries multiple format selectors.

    Returns: path to downloaded file or None on failure.
    """
    global last_download_error
    last_download_error = ""

    # Load proxy from vars (set via env var YT_PROXY_URL or /setproxy command)
    # If no proxy set, auto-fetch a fresh free proxy from proxyscrape
    try:
        from vars import yt_proxy_url as _proxy_url
        proxy = _proxy_url.strip() if _proxy_url else ""
    except ImportError:
        proxy = ""

    if not proxy:
        proxy = _auto_fetch_proxy()

    if proxy:
        logging.info(f"[YT] Using proxy: {proxy[:60]}")

    cookies_path = _resolve_cookies_path()
    base_name = name if name else "youtube_video"
    safe_name = re.sub(r'[<>:"/\\|?*]', '', base_name)[:200]

    # Define quality-based format selectors
    if quality == "best" or not quality:
        format_strategies = [
            "bestvideo+bestaudio/best",
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "best",
        ]
    else:
        q = int(quality)
        format_strategies = [
            f"bestvideo[height<={q}]+bestaudio/best[height<={q}]",
            f"best[height<={q}]/bestvideo+bestaudio/best",
            "bestvideo+bestaudio/best",
            "best",
        ]

    # Define client strategies: (player_client, use_cookies, label)
    client_strategies = [
        ("web", True, "web+cookies"),
        ("ios", True, "ios+cookies"),
        ("tv_simply", True, "tv+cookies"),
        ("web", False, "web (no cookies)"),
        ("tv_simply", False, "tv (no cookies)"),
    ]

    for client, use_cookies, label in client_strategies:
        # Skip cookie strategies if no cookies file
        if use_cookies and not cookies_path:
            logging.info(f"[YT] Skipping {label} — no cookies file")
            continue

        for fmt in format_strategies:
            ydl_opts = {
                '_url': url,
                'format': fmt,
                'outtmpl': f'{safe_name}.%(ext)s',
                'merge_output_format': 'mp4',
                'quiet': True,
                'no_warnings': False,
                'skip_download': True,  # Extract only first
                'extractor_args': {'youtube': {'player_client': [client]}},
            }

            # Add proxy if configured (bypasses cloud IP bot detection)
            if proxy:
                ydl_opts['proxy'] = proxy

            if use_cookies and cookies_path:
                ydl_opts['cookiefile'] = cookies_path

            # Try extract
            try:
                logging.info(f"[YT] Trying {label} | format: {fmt}")
                info = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: _yt_dlp_extract(ydl_opts)
                )

                if not info or 'formats' not in info or len(info.get('formats', [])) == 0:
                    logging.warning(f"[YT] {label}: No formats found")
                    continue

                # Got formats! Now download
                title = info.get('title', safe_name)[:80]
                n_formats = len(info['formats'])
                logging.info(f"[YT] {label}: Found {n_formats} formats — '{title}'")

                # Switch to download mode
                ydl_opts['skip_download'] = False
                ydl_opts['noprogress'] = False
                ydl_opts['progress_hooks'] = [_make_progress_hook()]

                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: _yt_dlp_download(ydl_opts)
                )

                # Find downloaded file
                result = _find_downloaded_media(safe_name)
                if result:
                    logging.info(f"[YT] Download OK: {result}")
                    return result
                else:
                    last_download_error = f"{label}: Download seemed OK but file not found"
                    logging.error(f"[YT] File not found after download for: {safe_name}")

            except yt_dlp.utils.DownloadError as e:
                err_str = str(e)
                # If "Sign in to confirm" — cookies are dead, skip remaining cookie strategies
                if "Sign in to confirm" in err_str:
                    logging.warning(f"[YT] {label}: Login required — cookies may be expired")
                    if use_cookies:
                        last_download_error = f"YouTube requires sign-in. Your cookies may be expired. Please use /ytcookies to upload fresh cookies exported from your browser (while logged into YouTube)."
                        break  # Skip remaining formats for this client, try next client
                    continue
                elif "not available" in err_str:
                    logging.warning(f"[YT] {label}: Format not available — trying next format")
                    continue
                else:
                    last_download_error = f"[{label}] {err_str[:300]}"
                    logging.error(f"[YT] {label} failed: {err_str[:200]}")
                    continue

            except Exception as e:
                last_download_error = f"[{label}] {str(e)[:300]}"
                logging.error(f"[YT] {label} error: {str(e)[:200]}")
                continue

    # All strategies failed
    if not last_download_error:
        last_download_error = "All download strategies failed. The video may be private, age-restricted, or cookies are expired."
    logging.error(f"[YT] ALL strategies failed for {url}: {last_download_error}")
    return None


def _make_progress_hook():
    """Return a progress hook for yt-dlp."""
    def hook(d):
        if d['status'] == 'downloading':
            _total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            _downloaded = d.get('downloaded_bytes', 0)
            if _total > 0:
                pct = (_downloaded / _total) * 100
                speed = d.get('speed', 0)
                speed_str = f"{speed/1024/1024:.1f}MB/s" if speed else "?"
                logging.info(f"[YT] Progress: {pct:.1f}% ({speed_str})")
        elif d['status'] == 'finished':
            logging.info(f"[YT] Download finished: {d.get('filename', '?')}")
        elif d['status'] == 'error':
            logging.error(f"[YT] Download error: {d.get('error', '?')}")
    return hook


async def download_video(url, cmd, name):
    download_cmd = f'{cmd} {_YTDLP_EXTRA}'
    global failed_counter, last_download_error
    last_download_error = ""
    logging.info(f"[DOWNLOAD] Starting: {download_cmd}")
    _proc = await asyncio.create_subprocess_shell(
        download_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await _proc.communicate()
    k = _proc
    stdout_text = stdout.decode('utf-8', errors='replace')[-1000:] if stdout else ''
    stderr_text = stderr.decode('utf-8', errors='replace')[-1000:] if stderr else ''
    logging.info(f"[DOWNLOAD] Exit code: {k.returncode} for: {name}")
    if stdout_text:
        logging.info(f"[DOWNLOAD] stdout: {stdout_text}")
    if stderr_text:
        logging.error(f"[DOWNLOAD] stderr: {stderr_text}")
    if k.returncode != 0:
        last_download_error = f"yt-dlp exited with code {k.returncode}"
        if stderr_text:
            last_download_error += f"\n{stderr_text}"
    else:
        logging.info(f"[DOWNLOAD] Done: {name}")
    if "visionias" in cmd and k.returncode != 0 and failed_counter <= 10:
        failed_counter += 1
        await asyncio.sleep(5)
        return await download_video(url, cmd, name)
    failed_counter = 0
    return _find_downloaded_media(name)


async def send_doc(bot: Client, m: Message, cc, ka, cc1, prog, count, name, channel_id):
    try:
        reply = await bot.send_message(channel_id, f"Downloading pdf:\n<pre><code>{name}</code></pre>")
    except FloodWait as e:
        await asyncio.sleep(e.value)
        reply = await bot.send_message(channel_id, f"Downloading pdf:\n<pre><code>{name}</code></pre>")
    start_time = time.time()
    try:
        await bot.send_document(ka, caption=cc1)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await bot.send_document(ka, caption=cc1)
    count += 1
    await reply.delete(True)
    os.remove(ka) 


def decrypt_file(file_path, key):  
    if not os.path.exists(file_path): 
        return False  

    with open(file_path, "r+b") as f:  
        num_bytes = min(28, os.path.getsize(file_path))  
        with mmap.mmap(f.fileno(), length=num_bytes, access=mmap.ACCESS_WRITE) as mmapped_file:  
            for i in range(num_bytes):  
                mmapped_file[i] ^= ord(key[i]) if i < len(key) else i 
    return True  

async def download_and_decrypt_video(url, cmd, name, key):  
    video_path = await download_video(url, cmd, name)  
    
    if video_path:  
        decrypted = decrypt_file(video_path, key)  
        if decrypted:  
            print(f"File {video_path} decrypted successfully.")  
            return video_path  
        else:  
            print(f"Failed to decrypt {video_path}.")  
            return None  

async def send_vid(bot: Client, m: Message, cc, filename, vidwatermark, thumb, name, prog, channel_id, topic_id=None):
    if not filename or not os.path.isfile(filename):
        raise FileNotFoundError(f"Downloaded video file not found: {filename or name}")
    _tp = await asyncio.create_subprocess_shell(
        f'ffmpeg -y -ss 00:00:10 -i "{filename}" -vframes 1 -vf scale=320:-1 -q:v 5 "{filename}.jpg"',
        stdout=None,
        stderr=None,
    )
    await _tp.wait()
    await prog.delete (True)
    _thread_kwargs = {"message_thread_id": topic_id} if topic_id else {}
    try:
        reply1 = await bot.send_message(channel_id, f"**📩 Uploading Video 📩:-**\n<blockquote>**{name}**</blockquote>", **_thread_kwargs)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        reply1 = await bot.send_message(channel_id, f"**📩 Uploading Video 📩:-**\n<blockquote>**{name}**</blockquote>", **_thread_kwargs)
    
    try:
        reply = await m.reply_text(f"**Generate Thumbnail:**\n<blockquote>**{name}**</blockquote>")
    except FloodWait as e:
        await asyncio.sleep(e.value)
        reply = await m.reply_text(f"**Generate Thumbnail:**\n<blockquote>**{name}**</blockquote>")
    try:
        if thumb == "/d":
            thumbnail = f"{filename}.jpg"
        elif thumb == "/no":
            thumbnail = None
        else:
            thumbnail = thumb if os.path.isfile(str(thumb)) else None
        
        if vidwatermark == "/d":
            w_filename = f"{filename}"
        else:
            w_filename = f"w_{filename}"
            font_path = "vidwater.ttf"
            _wp = await asyncio.create_subprocess_shell(
                f'ffmpeg -i "{filename}" -vf "drawtext=fontfile={font_path}:text=\'{vidwatermark}\':fontcolor=white@0.3:fontsize=h/6:x=(w-text_w)/2:y=(h-text_h)/2" -codec:a copy "{w_filename}"',
                stdout=None,
                stderr=None,
            )
            await _wp.wait()
            
    except Exception as e:
        await m.reply_text(str(e))

    dur = int(duration(w_filename))
    start_time = time.time()

    sent_msg = None
    try:
        if thumb == "/no":
            raise ValueError("document upload requested")
        sent_msg = await bot.send_video(channel_id, w_filename, caption=cc, supports_streaming=True, height=720, width=1280, thumb=thumbnail, duration=dur, progress=progress_bar, progress_args=(reply, start_time), **_thread_kwargs)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        sent_msg = await bot.send_video(channel_id, w_filename, caption=cc, supports_streaming=True, height=720, width=1280, thumb=thumbnail, duration=dur, progress=progress_bar, progress_args=(reply, start_time), **_thread_kwargs)
    except Exception:
        try:
            sent_msg = await bot.send_document(channel_id, w_filename, caption=cc, progress=progress_bar, progress_args=(reply, start_time), **_thread_kwargs)
        except FloodWait as e:
            await asyncio.sleep(e.value)
            sent_msg = await bot.send_document(channel_id, w_filename, caption=cc, progress=progress_bar, progress_args=(reply, start_time), **_thread_kwargs)
    if os.path.exists(w_filename):
        os.remove(w_filename)
    await reply.delete(True)
    await reply1.delete(True)
    if os.path.exists(f"{filename}.jpg"):
        os.remove(f"{filename}.jpg")
    return sent_msg


# ═══════════════════════════════════════════════════════════════════════════════
# CareerWill DRM DASH Downloader (custom, no yt-dlp)
# Downloads segments directly with requests → mp4decrypt → ffmpeg merge
# ═══════════════════════════════════════════════════════════════════════════════

def _parse_iso8601_duration(duration_str):
    """Parse ISO 8601 duration like PT93M19.200S or PT1H30M0S → seconds."""
    total = 0.0
    m = re.match(r'PT(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?', duration_str)
    if m:
        total = float(m.group(1) or 0) * 3600 + float(m.group(2) or 0) * 60 + float(m.group(3) or 0)
    return total


def _parse_dash_mpd(mpd_url, quality="720"):
    """
    Parse DASH MPD manifest and return selected video+audio representations.
    Returns dict with 'video' and 'audio' representation info, or raises on error.
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
    })

    resp = session.get(mpd_url, timeout=30)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)

    # ── Namespace handling ──────────────────────────────────────────────────
    _ns = ''
    if root.tag.startswith('{'):
        _ns = root.tag.split('}')[0] + '}'

    def _find(parent, tag):
        return parent.find(f'{_ns}{tag}')

    def _findall(parent, tag):
        return parent.findall(f'{_ns}{tag}')

    def _resolve(base, url):
        if url.startswith('http'):
            return url
        return urljoin(base, url)

    # ── Base URL resolution ─────────────────────────────────────────────────
    mpd_base = mpd_url.rsplit('/', 1)[0] + '/'
    bu = _find(root, 'BaseURL')
    if bu is not None and bu.text:
        mpd_base = _resolve(mpd_base, bu.text.strip())
        if not mpd_base.endswith('/'):
            mpd_base += '/'

    # ── Media duration (for fallback segment count) ─────────────────────────
    media_dur_str = root.get('mediaPresentationDuration', '')
    media_duration = _parse_iso8601_duration(media_dur_str) if media_dur_str else 0

    # ── Parse representations ───────────────────────────────────────────────
    video_reps = []
    audio_reps = []

    for period in _findall(root, 'Period'):
        if not media_duration:
            pd = period.get('duration', '')
            if pd:
                media_duration = _parse_iso8601_duration(pd)

        p_base = mpd_base
        pb = _find(period, 'BaseURL')
        if pb is not None and pb.text:
            p_base = _resolve(mpd_base, pb.text.strip())
            if not p_base.endswith('/'):
                p_base += '/'

        for aset in _findall(period, 'AdaptationSet'):
            ct = (aset.get('contentType', '') + aset.get('mimeType', '')).lower()
            is_video = 'video' in ct
            is_audio = 'audio' in ct

            a_base = p_base
            ab = _find(aset, 'BaseURL')
            if ab is not None and ab.text:
                a_base = _resolve(p_base, ab.text.strip())
                if not a_base.endswith('/'):
                    a_base += '/'

            # SegmentTemplate at AdaptationSet level (shared by all Representations)
            as_tmpl = _find(aset, 'SegmentTemplate')

            for rep in _findall(aset, 'Representation'):
                rep_info = {
                    'id': rep.get('id', ''),
                    'bandwidth': int(rep.get('bandwidth', '0')),
                    'width': int(rep.get('width', '0')),
                    'height': int(rep.get('height', '0')),
                    'base_url': a_base,
                    'init_url': None,
                    'segment_urls': [],
                }

                rb = _find(rep, 'BaseURL')
                if rb is not None and rb.text:
                    rep_info['base_url'] = _resolve(a_base, rb.text.strip())
                    if not rep_info['base_url'].endswith('/'):
                        rep_info['base_url'] += '/'

                tmpl = _find(rep, 'SegmentTemplate') or as_tmpl

                if tmpl is not None:
                    media_t = tmpl.get('media', '')
                    init_t = tmpl.get('initialization', '')
                    start_n = int(tmpl.get('startNumber', '1'))
                    timescale = int(tmpl.get('timescale', '1'))
                    seg_dur = int(tmpl.get('duration', '0'))

                    def _fill(template, number=None, bw=None):
                        t = template
                        if number is not None:
                            t = t.replace('$Number$', str(number))
                            t = re.sub(r'\$Number%\d+d\$', str(number), t)
                        if bw is not None:
                            t = t.replace('$Bandwidth$', str(bw))
                        return _resolve(rep_info['base_url'], t)

                    if init_t:
                        rep_info['init_url'] = _fill(init_t, bw=rep_info['bandwidth'])

                    timeline = _find(tmpl, 'SegmentTimeline')
                    if timeline is not None:
                        seg_num = start_n
                        for s in _findall(timeline, 'S'):
                            d = int(s.get('d', '0'))
                            r = int(s.get('r', '0'))
                            rep_info['segment_urls'].append(
                                _fill(media_t, number=seg_num, bw=rep_info['bandwidth'])
                            )
                            seg_num += 1
                            for _ in range(r):
                                rep_info['segment_urls'].append(
                                    _fill(media_t, number=seg_num, bw=rep_info['bandwidth'])
                                )
                                seg_num += 1
                    elif seg_dur > 0 and media_duration > 0:
                        num_segs = int(media_duration * timescale / seg_dur)
                        for n in range(start_n, start_n + num_segs):
                            rep_info['segment_urls'].append(
                                _fill(media_t, number=n, bw=rep_info['bandwidth'])
                            )
                else:
                    slist = _find(rep, 'SegmentList')
                    if slist is not None:
                        init_el = _find(slist, 'Initialization')
                        if init_el is not None:
                            rep_info['init_url'] = _resolve(
                                rep_info['base_url'], init_el.get('sourceURL', '')
                            )
                        for su in _findall(slist, 'SegmentURL'):
                            mu = su.get('media', '')
                            if mu:
                                rep_info['segment_urls'].append(
                                    _resolve(rep_info['base_url'], mu)
                                )

                if is_video:
                    video_reps.append(rep_info)
                elif is_audio:
                    audio_reps.append(rep_info)

    # ── Quality selection ───────────────────────────────────────────────────
    max_h = int(quality)
    sel_video = None
    for v in sorted(video_reps, key=lambda x: x['height'], reverse=True):
        if v['height'] <= max_h:
            sel_video = v
            break
    if sel_video is None and video_reps:
        sel_video = min(video_reps, key=lambda x: abs(x['height'] - max_h))

    sel_audio = audio_reps[0] if audio_reps else None

    print(f"[CW_DASH] Parsed: {len(video_reps)} video, {len(audio_reps)} audio reps")
    for v in video_reps:
        print(f"[CW_DASH]   Video {v['width']}x{v['height']} bw={v['bandwidth']} segs={len(v['segment_urls'])}")
    for a in audio_reps:
        print(f"[CW_DASH]   Audio bw={a['bandwidth']} segs={len(a['segment_urls'])}")
    if sel_video:
        print(f"[CW_DASH] Selected video: {sel_video['width']}x{sel_video['height']} ({len(sel_video['segment_urls'])} segments)")

    if not sel_video:
        raise Exception("No video representation found in MPD manifest")

    return {'video': sel_video, 'audio': sel_audio, 'session': session}


async def _download_dash_segments(rep_info, label, session, output_dir):
    """Download init + all media segments, concatenate into one fragmented MP4."""
    out_file = output_dir / f"{label}.fragmented.mp4"

    if rep_info['init_url']:
        print(f"[CW_DASH] Downloading {label} init segment...")
        resp = session.get(rep_info['init_url'], timeout=120)
        if resp.status_code != 200:
            raise Exception(f"Failed to download {label} init segment: HTTP {resp.status_code}")
        with open(out_file, 'wb') as f:
            f.write(resp.content)

    total = len(rep_info['segment_urls'])
    for idx, seg_url in enumerate(rep_info['segment_urls']):
        if idx % 100 == 0:
            print(f"[CW_DASH] {label} segment {idx+1}/{total}...")
        try:
            resp = session.get(seg_url, timeout=120)
            if resp.status_code != 200:
                raise Exception(f"{label} segment {idx+1} failed: HTTP {resp.status_code}")
            with open(out_file, 'ab') as f:
                f.write(resp.content)
        except Exception as e:
            # Retry once
            print(f"[CW_DASH] Retrying {label} segment {idx+1}: {e}")
            await asyncio.sleep(2)
            resp = session.get(seg_url, timeout=120)
            if resp.status_code != 200:
                raise Exception(f"{label} segment {idx+1} failed after retry: HTTP {resp.status_code}")
            with open(out_file, 'ab') as f:
                f.write(resp.content)

    size = os.path.getsize(out_file)
    print(f"[CW_DASH] {label} done: {size} bytes ({total} segments)")
    return str(out_file)


async def download_careerwill_drm(mpd_url, kid, key, output_path, output_name, quality="720"):
    """
    CareerWill DRM DASH downloader — no yt-dlp.
    Parses MPD → downloads segments with requests → mp4decrypt → ffmpeg merge.

    Args:
        mpd_url:   DASH MPD manifest URL (without the *kid:key suffix)
        kid:       Key ID hex string
        key:       Decryption key hex string
        output_path: Directory for temp files
        output_name: Output filename without extension
        quality:   Max height (e.g. "720")
    Returns:
        Path to final .mp4 file
    """
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. Parse MPD
    print(f"[CW_DRM] Parsing MPD: {mpd_url}")
    # Ensure quality is a valid number string
    try:
        _q = int(quality)
    except (ValueError, TypeError):
        _q = 720
        print(f"[CW_DRM] Invalid quality '{quality}', defaulting to 720")
    parsed = _parse_dash_mpd(mpd_url, str(_q))
    video_rep = parsed['video']
    audio_rep = parsed['audio']
    session = parsed['session']

    # 2. Download segments
    print("[CW_DRM] Downloading video segments...")
    video_frag = await _download_dash_segments(video_rep, "video", session, output_path)

    audio_frag = None
    if audio_rep:
        print("[CW_DRM] Downloading audio segments...")
        audio_frag = await _download_dash_segments(audio_rep, "audio", session, output_path)

    session.close()

    # 3. Decrypt with mp4decrypt
    print("[CW_DRM] Decrypting with ClearKey...")
    kid_key_arg = f"--key {kid}:{key}"

    video_dec = f"{output_path}/video_decrypted.mp4"
    p = await asyncio.create_subprocess_shell(
        f'mp4decrypt {kid_key_arg} --show-progress "{video_frag}" "{video_dec}"',
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await p.communicate()
    if p.returncode != 0 or not os.path.exists(video_dec):
        print(f"[CW_DRM] mp4decrypt video error: {stderr.decode()}")
        raise Exception(f"mp4decrypt video decryption failed")

    audio_dec = None
    if audio_frag:
        audio_dec = f"{output_path}/audio_decrypted.m4a"
        p = await asyncio.create_subprocess_shell(
            f'mp4decrypt {kid_key_arg} --show-progress "{audio_frag}" "{audio_dec}"',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await p.communicate()
        if p.returncode != 0 or not os.path.exists(audio_dec):
            print(f"[CW_DRM] mp4decrypt audio error: {stderr.decode()}")
            raise Exception(f"mp4decrypt audio decryption failed")

    # 4. Merge with ffmpeg
    print("[CW_DRM] Merging with ffmpeg...")
    output_file = str(output_path / f"{output_name}.mp4")

    if audio_dec:
        cmd = f'ffmpeg -y -i "{video_dec}" -i "{audio_dec}" -c copy "{output_file}"'
    else:
        cmd = f'ffmpeg -y -i "{video_dec}" -c copy "{output_file}"'

    p = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await p.communicate()
    if p.returncode != 0 or not os.path.exists(output_file):
        print(f"[CW_DRM] ffmpeg error: {stderr.decode()[-500:]}")
        raise Exception("ffmpeg merge failed")

    # 5. Cleanup temp files
    for f in [video_frag, video_dec, audio_frag, audio_dec]:
        if f and os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

    print(f"[CW_DRM] Done! {output_file} ({os.path.getsize(output_file)} bytes)")
    return output_file

