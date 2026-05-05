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

# ── Proxy support for YouTube bot detection bypass ────────────────────────
# Set PROXY_URL env var to use a proxy (e.g., socks5://user:pass@host:port)
# Required for Heroku/cloud servers since YouTube blocks datacenter IPs.
_YT_PROXY = os.environ.get('PROXY_URL', '').strip() or None
if _YT_PROXY:
    print(f"[YT_DL] Proxy enabled: {_YT_PROXY}")
else:
    print("[YT_DL] No proxy configured (set PROXY_URL env var for YouTube downloads on cloud servers)")

# ── YouTube player_client strategies for bot detection bypass ────────────
# YouTube now requires PO Token for most clients. Order matters: try least-restrictive first.
# mweb: only needs PO Token for GVS (auto-handled by bgutil-ytdlp-pot-provider plugin)
# tv_simply: no PO Token needed (limited formats, no account cookies)
# web_embedded: no PO Token (only embeddable videos)
# default: fallback
_YT_PLAYER_CLIENTS = ['mweb', 'tv_simply', 'web_embedded', 'default']

# ── Download speed constants ──────────────────────────────────────────────────
# Shared aria2c args used in every yt-dlp download command
_ARIA2C_ARGS = (
    'aria2c:'
    '-x 16 '                       # 16 connections per server (max)
    '-s 16 '                       # 16 splits per file (max)
    '-j 16 '                       # 16 parallel fragment downloads (max)
    '--min-split-size=1M '         # minimum valid value for aria2c
    '--disk-cache=256M '           # large cache for maximum throughput
    '--file-allocation=none '
    '--enable-http-pipelining=true '
    '--http-accept-gzip=true '
    '--max-tries=0 '
    '--retry-wait=1'               # retry faster
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
    '--remote-components ejs:github '
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


async def download_video(url, cmd, name):
    _cookies = _resolve_cookies_path()
    if _cookies and ("youtube.com" in url or "youtu.be" in url):
        if "--cookies" not in cmd:
            cmd = cmd.replace("yt-dlp ", f'yt-dlp --cookies "{_cookies}" ', 1)
    download_cmd = f'{cmd} {_YTDLP_EXTRA}'
    global failed_counter, last_download_error
    last_download_error = ""
    print(f"[DOWNLOAD] Starting: {download_cmd}")
    logging.info(download_cmd)
    _proc = await asyncio.create_subprocess_shell(
        download_cmd,
        stdout=None,   # stream directly to Render/console
        stderr=None,   # stream directly to Render/console
    )
    await _proc.wait()
    k = _proc
    if k.returncode != 0:
        last_download_error = f"yt-dlp exited with code {k.returncode}"
        print(f"[DOWNLOAD] Failed with code {k.returncode} for: {name}")
    else:
        print(f"[DOWNLOAD] Done: {name}")
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


# ═══════════════════════════════════════════════════════════════════════════════
# Custom YouTube Downloader (yt_dlp Python API, no subprocess)
# Proper cookie handling, real error messages, multiple format fallbacks
# ═══════════════════════════════════════════════════════════════════════════════

def _resolve_cookies_path():
    """Find the YouTube cookies file by checking common locations."""
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _candidates = [
        os.path.join(_script_dir, "youtube_cookies.txt"),
        os.path.join(_script_dir, "downloads", "www.youtube.com_cookies.txt"),
        os.path.join(os.getcwd(), "youtube_cookies.txt"),
        os.path.join(os.getcwd(), "modules", "youtube_cookies.txt"),
    ]
    # Also try env var
    _env_cookie = os.environ.get("cookies_file_path", "")
    if _env_cookie:
        _candidates.insert(0, _env_cookie)
        _candidates.insert(0, os.path.abspath(_env_cookie))

    for c in _candidates:
        if os.path.isfile(c):
            print(f"[YT_COOKIES] Found cookies at: {c}")
            return os.path.abspath(c)

    print("[YT_COOKIES] WARNING: No cookies file found in any known location")
    return None


def _yt_dlp_extract(ydl_opts, url):
    """Run yt_dlp.extract_info in a blocking call (for thread executor)."""
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info


def _yt_dlp_extract_info_only(ydl_opts, url):
    """Extract video info WITHOUT downloading — used to find available formats."""
    opts = dict(ydl_opts)
    opts['format'] = None  # Don't select any format yet
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info


def _pick_best_format_id(info):
    """
    Pick the best available format_id from extracted info.
    Priority: highest resolution combined video+audio, then pre-merged, then best video only.
    Returns format_id string or None.
    """
    formats = info.get('formats', [])
    if not formats:
        return None

    # Separate video-only, audio-only, and combined formats
    video_only = []
    audio_only = []
    combined = []

    for f in formats:
        vcodec = f.get('vcodec', 'none')
        acodec = f.get('acodec', 'none')
        height = f.get('height', 0)
        fid = f.get('format_id', '')

        # Skip formats that are clearly not downloadable
        if f.get('protocol', '') in ['mhtml', '']:
            continue

        if vcodec != 'none' and acodec != 'none':
            combined.append(f)
        elif vcodec != 'none':
            video_only.append(f)
        elif acodec != 'none':
            audio_only.append(f)

    # Strategy 1: Best combined (video+audio in one file — no merge needed)
    if combined:
        best = max(combined, key=lambda f: (f.get('height', 0), f.get('filesize', 0) or f.get('filesize_approx', 0)))
        print(f"[YT_DL] Selected combined format: {best.get('format_id')} ({best.get('height')}p {best.get('ext')})")
        return best.get('format_id')

    # Strategy 2: Best video + best audio (yt-dlp format string)
    if video_only and audio_only:
        best_video = max(video_only, key=lambda f: (f.get('height', 0), f.get('filesize', 0) or f.get('filesize_approx', 0)))
        best_audio = max(audio_only, key=lambda f: (f.get('abr', 0) or 0, f.get('filesize', 0) or f.get('filesize_approx', 0)))
        print(f"[YT_DL] Selected video+audio: {best_video.get('format_id')} ({best_video.get('height')}p) + {best_audio.get('format_id')} ({best_audio.get('abr')}kbps)")
        return f"{best_video.get('format_id')}+{best_audio.get('format_id')}"

    # Strategy 3: Just best video (audio-only video like music)
    if video_only:
        best = max(video_only, key=lambda f: (f.get('height', 0), f.get('filesize', 0) or f.get('filesize_approx', 0)))
        return best.get('format_id')

    # Strategy 4: Just audio
    if audio_only:
        best = max(audio_only, key=lambda f: (f.get('abr', 0) or 0))
        return best.get('format_id')

    return None


async def download_youtube_video(url, output_name, quality=None, cookies_path=None):
    """
    Custom YouTube downloader using yt_dlp Python API directly.
    No subprocess — proper cookie handling, real error messages, multiple fallbacks.

    Always downloads the BEST available quality (ignores user quality setting).
    First extracts available formats, picks the best, then downloads.

    Args:
        url:          YouTube URL
        output_name:  Output filename prefix (without extension)
        quality:      Ignored — always downloads best available (kept for API compat)
        cookies_path: Optional explicit cookies file path

    Returns:
        Path to downloaded file (str), or raises Exception with real error message.
    """
    global last_download_error
    last_download_error = ""

    # ── Resolve cookies ────────────────────────────────────────────────────
    if not cookies_path or not os.path.isfile(cookies_path):
        cookies_path = _resolve_cookies_path()

    # ── YouTube always uses BEST available quality ─────────────────────────
    print(f"[YT_DL] Quality param '{quality}' ignored — downloading best available")
    print(f"[YT_DL] URL: {url}")

    # ── Build base yt-dlp options (shared across all attempts) ─────────────
    def _build_opts(fmt, dl_opts=None):
        opts = {
            'format': fmt,
            'outtmpl': f'{output_name}.%(ext)s',
            'quiet': False,
            'no_warnings': False,
            'retries': 10,
            'fragment_retries': 10,
            'concurrent_fragment_downloads': 8,
            'socket_timeout': 30,
            'http_chunk_size': 10485760,
            'noprogress': False,
            'no_part': True,
            'merge_output_format': 'mp4',
            'progress_hooks': [],
            # ── Bot detection bypass: use mweb/tv_simply player_client ──
            'extractor_args': {
                'youtube': {
                    'player_client': _YT_PLAYER_CLIENTS,
                }
            },
            'verbose': True,
        }
        if dl_opts:
            opts.update(dl_opts)
        if cookies_path and os.path.isfile(cookies_path):
            opts['cookiefile'] = os.path.abspath(cookies_path)
        # ── Proxy for bypassing YouTube bot detection on cloud servers ──
        if _YT_PROXY:
            opts['proxy'] = _YT_PROXY
        return opts

    loop = asyncio.get_event_loop()

    # ── STEP 1: Extract info to find available formats ────────────────────
    print(f"[YT_DL] Step 1: Extracting video info to find available formats...")
    try:
        base_opts = _build_opts(None)  # No format yet
        info = await loop.run_in_executor(None, _yt_dlp_extract_info_only, base_opts, url)
    except yt_dlp.utils.ExtractorError as e:
        last_download_error = f"Cannot extract video info: {e}"
        raise Exception(f"YouTube download failed: {e}")
    except Exception as e:
        last_download_error = f"Cannot extract video info: {type(e).__name__}: {e}"
        raise Exception(f"YouTube download failed: {e}")

    if not info:
        raise Exception("YouTube download failed: Could not extract video info (empty response)")

    # ── STEP 2: Pick the best available format ─────────────────────────────
    print(f"[YT_DL] Step 2: Picking best available format from {len(info.get('formats', []))} formats...")
    chosen_fmt = _pick_best_format_id(info)

    # Fallback: if our picker fails, let yt-dlp decide with "best"
    if not chosen_fmt:
        print(f"[YT_DL] Format picker returned None, using yt-dlp 'best' selector")
        chosen_fmt = "best"

    print(f"[YT_DL] Selected format: {chosen_fmt}")

    # ── STEP 3: Download with chosen format ────────────────────────────────
    aria2c_args = '-x 16 -s 16 -j 16 --min-split-size=1M --disk-cache=256M --file-allocation=none --max-tries=10 --retry-wait=2'
    download_attempts = [
        {"external_downloader": "aria2c", "downloader_args": {"aria2c": aria2c_args}, "label": "aria2c"},
        {},  # Native yt-dlp downloader
    ]

    last_err = ""
    for attempt in download_attempts:
        dl_label = attempt.get("label", "native")
        dl_opts = {k: v for k, v in attempt.items() if k != "label"}
        try:
            ydl_opts = _build_opts(chosen_fmt, dl_opts)
            print(f"[YT_DL] Step 3: Downloading with format='{chosen_fmt}' dl='{dl_label}'")
            info = await loop.run_in_executor(None, _yt_dlp_extract, ydl_opts, url)

            # Find the downloaded file
            dl_file = None
            if info and 'requested_downloads' in info:
                for dl_entry in info['requested_downloads']:
                    _fpath = dl_entry.get('filepath') or dl_entry.get('filename')
                    if _fpath and os.path.isfile(_fpath) and os.path.getsize(_fpath) > 0:
                        dl_file = _fpath
                        break
            if not dl_file:
                dl_file = _find_downloaded_media(output_name)
            if dl_file and os.path.isfile(dl_file) and os.path.getsize(dl_file) > 0:
                size = os.path.getsize(dl_file)
                print(f"[YT_DL] SUCCESS: {dl_file} ({size} bytes)")
                return dl_file

            last_err = "Download completed but output file not found on disk"

        except yt_dlp.utils.DownloadError as e:
            last_err = str(e)
            _err_lower = last_err.lower()
            if 'aria2' in _err_lower or 'external downloader' in _err_lower:
                print(f"[YT_DL] aria2c error, trying native: {last_err[:200]}")
                continue
            print(f"[YT_DL] DownloadError: {last_err[:200]}")
            continue

        except yt_dlp.utils.ExtractorError as e:
            last_err = f"Extractor error: {str(e)}"
            print(f"[YT_DL] ExtractorError: {last_err[:200]}")
            break

        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)}"
            print(f"[YT_DL] Error: {last_err[:200]}")
            continue

    # All attempts failed
    last_download_error = f"yt-dlp failed: {last_err}"
    print(f"[YT_DL] ALL ATTEMPTS FAILED: {last_download_error}")

    # ── Provide helpful error message ────────────────────────────────────
    _hint = ""
    if 'not a bot' in last_err.lower() or 'sign in' in last_err.lower():
        if not _YT_PROXY:
            _hint = (
                "\n\n💡 TIP: YouTube is blocking this server's IP. "
                "Set PROXY_URL env var (e.g., socks5://user:pass@host:port) "
                "in Heroku Config Vars to use a residential proxy."
            )
        elif not (cookies_path and os.path.isfile(cookies_path)):
            _hint = (
                "\n\n💡 TIP: YouTube requires login cookies. "
                "Use /cookies command to upload cookies file."
            )
        else:
            _hint = (
                "\n\n💡 TIP: Cookies may be expired or from a different IP. "
                "Re-export cookies from your browser and upload with /cookies. "
                "Also try refreshing your proxy subscription."
            )
    raise Exception(f"YouTube download failed: {last_err}{_hint}")
