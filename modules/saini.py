import os
import re
import time
import mmap
import datetime
import aiohttp
import aiofiles
import asyncio
import logging
import requests
import tgcrypto
import subprocess
import concurrent.futures
from math import ceil
from utils import progress_bar
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from io import BytesIO
from pathlib import Path  
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode

last_download_error = ""

# ── Download speed constants ──────────────────────────────────────────────────
# Shared aria2c args used in every yt-dlp download command
_ARIA2C_ARGS = (
    'aria2c:'
    '-x 4 '                        # 4 connections per server (free-tier safe)
    '-s 4 '                        # 4 splits per file
    '-j 4 '                        # 4 parallel fragment downloads
    '--min-split-size=1M '         # less fragmentation → lower CPU load
    '--disk-cache=64M '            # low RAM usage for free tier
    '--file-allocation=none '
    '--enable-http-pipelining=true '
    '--http-accept-gzip=true '
    '--max-tries=0 '
    '--retry-wait=2 '
    '--piece-length=1M'
)
_YTDLP_EXTRA = (
    '-R 10 '
    '--fragment-retries 10 '
    '--concurrent-fragments 4 '    # 4 concurrent — free-tier safe
    '--socket-timeout 30 '
    '--no-part '
    '--js-runtimes node '
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
        _p1 = await asyncio.create_subprocess_shell(cmd1, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
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
                _p2 = await asyncio.create_subprocess_shell(cmd2, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                await _p2.wait()
                if (output_path / "video.mp4").exists():
                    video_decrypted = True
                data.unlink()
            elif data.suffix == ".m4a" and not audio_decrypted:
                cmd3 = f'mp4decrypt {keys_string} --show-progress "{data}" "{output_path}/audio.m4a"'
                print(f"Running command: {cmd3}")
                _p3 = await asyncio.create_subprocess_shell(cmd3, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                await _p3.wait()
                if (output_path / "audio.m4a").exists():
                    audio_decrypted = True
                data.unlink()

        if not video_decrypted or not audio_decrypted:
            raise FileNotFoundError("Decryption failed: video or audio file not found.")

        cmd4 = f'ffmpeg -i "{output_path}/video.mp4" -i "{output_path}/audio.m4a" -c copy "{output_path}/{output_name}.mp4"'
        print(f"Running command: {cmd4}")
        _p4 = await asyncio.create_subprocess_shell(cmd4, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
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
    download_cmd = f'{cmd} {_YTDLP_EXTRA}'
    global failed_counter, last_download_error
    last_download_error = ""
    print(download_cmd)
    logging.info(download_cmd)
    _proc = await asyncio.create_subprocess_shell(
        download_cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await _proc.communicate()
    if stderr:
        last_download_error = stderr.decode(errors="ignore").strip()[-800:]
    k = _proc
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
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
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
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
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
