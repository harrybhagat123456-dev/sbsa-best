import os, re, sys, json, pytz, asyncio, requests, subprocess, random, time
import urllib
import urllib.parse
import m3u8
import tgcrypto
import cloudscraper
import yt_dlp
from pyrogram import Client, filters
from pyrogram.errors.exceptions.bad_request_400 import StickerEmojiInvalid
from pyrogram.errors import FloodWait
from pyrogram.types.messages_and_media import message
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, InputMediaPhoto
from pyromod import listen
from p_bar import progress_bar
from subprocess import getstatusoutput
from aiohttp import ClientSession
from pytube import YouTube
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64encode, b64decode
import helper
from helper import *
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
import globals
from logs import logging
from html_handler import register_html_handlers
from text_handler import register_text_handlers
from features import register_feature_handlers
from upgrade import register_upgrade_handlers
from commands import register_commands_handlers
from settings import register_settings_handlers
from broadcast import register_broadcast_handlers
from youtube_handler import register_youtube_handlers
from authorisation import register_authorisation_handlers
from topic_handler import register_topic_handlers
from mini_handler import register_mini_handlers
from vars import API_ID, API_HASH, BOT_TOKEN, OWNER, CREDIT, AUTH_USERS, TOTAL_USERS, cookies_file_path
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,

# ===== API Configuration (from m1ain.py) =====
api_url = "http://master-api-v3.vercel.app/"
api_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNzkxOTMzNDE5NSIsInRnX3VzZXJuYW1lIjoi4p61IFtvZmZsaW5lXSIsImlhdCI6MTczODY5MjA3N30.SXzZ1MZcvMp5sGESj0hBKSghhxJ3k1GTWoBUbivUe1I"
token_cp = 'eyJjb3Vyc2VJZCI6IjQ1NjY4NyIsInR1dG9ySWQiOm51bGwsIm9yZ0lkIjo0ODA2MTksImNhdGVnb3J5SWQiOm51bGx9'

photologo = 'https://tinypic.host/images/2025/02/07/DeWatermark.ai_1738952933236-1.png'
photoyt = 'https://tinypic.host/images/2025/03/18/YouTube-Logo.wine.png'
photocp = 'https://tinypic.host/images/2025/03/28/IMG_20250328_133126.jpg'

failed_links = []
fail_cap = f"**➜ This file Contain Failed Downloads while Downloding \n You Can Retry them one more time **"

# ===== Helper Functions (from m1ain.py) =====
async def show_random_emojis(message):
    emojis = ['🐼', '🐶', '🐅', '⚡️', '🚀', '✨', '💥', '☠️', '🥂', '🍾']
    emoji_message = await message.reply_text(' '.join(random.choices(emojis, k=1)))
    return emoji_message

def process_links(links):
    processed_links = []
    for link in links.splitlines():
        if "m3u8" in link:
            processed_links.append(link)
        elif "mpd" in link:
            processed_links.append(re.sub(r'\*.*', '', link))
    return "\n".join(processed_links)

# Initialize the bot
bot = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir=".",
    workers=50,
    sleep_threshold=60,
)

@bot.on_message(filters.all, group=-100)
async def trace_incoming_message(client: Client, m: Message):
    try:
        from utils import describe_message
        logging.debug(f"[TRACE][INCOMING][MESSAGE] {describe_message(m)}")
    except Exception as e:
        logging.exception(f"[TRACE][INCOMING][ERROR] {e}")

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎙️ Commands", callback_data="cmd_command")],
            [InlineKeyboardButton("💎 Features", callback_data="feat_command"), InlineKeyboardButton("⚙️ Settings", callback_data="setttings")],
            [InlineKeyboardButton("💳 Suscribation", callback_data="upgrade_command")],
            [InlineKeyboardButton(text="📞 Contact", url=f"tg://openmessage?user_id={OWNER}"), InlineKeyboardButton(text="🛠️ Repo", url="https://github.com/nikhilsainiop/saini-txt-direct")],
        ])

@bot.on_message(filters.command("start") & filters.private)
async def start(bot, m: Message):
    user_id = m.chat.id
    if user_id not in TOTAL_USERS:
        TOTAL_USERS.append(user_id)
    user = await bot.get_me()
    mention = user.mention
    if m.chat.id in AUTH_USERS:
        caption = (
            f"𝐇𝐞𝐥𝐥𝐨 𝐃𝐞𝐚𝐫 👋!\n\n"
            f"➠ 𝐈 𝐚𝐦 𝐚 𝐓𝐞𝐱𝐭 𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐞𝐫 𝐁𝐨𝐭\n\n"
            f"➠ Can Extract Videos & PDFs From Your Text File and Upload to Telegram!\n\n"
            f"➠ For Guide Use button - **✨ Commands** 📖\n\n"
            f"➠ 𝐌𝐚𝐝𝐞 𝐁𝐲 : [{CREDIT}](tg://openmessage?user_id={OWNER}) 🦁"
        )
    else:
        caption = (
            f"𝐇𝐞𝐥𝐥𝐨 **{m.from_user.first_name}** 👋!\n\n"
            f"➠ 𝐈 𝐚𝐦 𝐚 𝐓𝐞𝐱𝐭 𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐞𝐫 𝐁𝐨𝐭\n\n"
            f"➠ Can Extract Videos & PDFs From Your Text File and Upload to Telegram!\n\n"
            f"**You are currently using the free version.** 🆓\n"
            f"**Want to get started? Press /id**\n\n"
            f"💬 𝐂𝐨𝐧𝐭𝐚𝐜𝐭 : [{CREDIT}](tg://openmessage?user_id={OWNER}) to Get The Subscription ! 🔓\n"
        )
    await bot.send_photo(
        chat_id=m.chat.id,
        photo="https://iili.io/KuCBoV2.jpg",
        caption=caption,
        reply_markup=keyboard
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("back_to_main_menu"))
async def back_to_main_menu(client, callback_query):
    user_id = callback_query.from_user.id
    first_name = callback_query.from_user.first_name
    caption = (
        f"𝐇𝐞𝐥𝐥𝐨 **{first_name}** 👋!\n\n"
        f"➠ 𝐈 𝐚𝐦 𝐚 𝐓𝐞𝐱𝐭 𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐞𝐫 𝐁𝐨𝐭\n\n"
        f"➠ Can Extract Videos & PDFs From Your Text File and Upload to Telegram!\n\n"
        f"╭────────⊰◆⊱────────╮\n"
        f"➠ 𝐌𝐚𝐝𝐞 𝐁𝐲 : [{CREDIT}](tg://openmessage?user_id={OWNER}) 💻\n"
        f"╰────────⊰◆⊱────────╯\n"
    )

    await callback_query.message.edit_media(
      InputMediaPhoto(
        media="https://envs.sh/GVI.jpg",
        caption=caption
      ),
      reply_markup=keyboard
    )
    await callback_query.answer()

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,

@bot.on_message(filters.command(["id"]) & filters.private)
async def id_command(client, message: Message):
    keyboard_id = InlineKeyboardMarkup([[InlineKeyboardButton(text="Send to Owner", url=f"tg://openmessage?user_id={OWNER}")]])
    chat_id = message.chat.id
    text = f"<blockquote expandable><b>The ID of this chat id is:</b></blockquote>\n`{chat_id}`"

    if str(chat_id).startswith("-100"):
        await message.reply_text(text)
    else:
        await message.reply_text(text, reply_markup=keyboard_id)

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,

@bot.on_message(filters.private & filters.command(["info"]))
async def info(bot: Client, update: Message):
    text = (
        f"╭────────────────╮\n"
        f"│✨ **Your Telegram Info**✨ \n"
        f"├────────────────\n"
        f"├🔹**Name :** `{update.from_user.first_name} {update.from_user.last_name if update.from_user.last_name else 'None'}`\n"
        f"├🔹**User ID :** {('@' + update.from_user.username) if update.from_user.username else 'None'}\n"
        f"├🔹**TG ID :** `{update.from_user.id}`\n"
        f"├🔹**Profile :** {update.from_user.mention}\n"
        f"╰────────────────╯"
    )
    await update.reply_text(
        text=text,
        disable_web_page_preview=True
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_message(filters.command(["logs"]) & filters.private)
async def send_logs(client: Client, m: Message):
    try:
        with open("logs.txt", "rb") as file:
            sent = await m.reply_text("**📤 Sending you ....**")
            await m.reply_document(document=file)
            await sent.delete()
    except Exception as e:
        await m.reply_text(f"**Error sending logs:**\n<blockquote>{e}</blockquote>")

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_message(filters.command(["reset"]) & filters.private)
async def restart_handler(_, m):
    if m.chat.id != OWNER:
        return
    else:
        await m.reply_text("𝐁𝐨𝐭 𝐢𝐬 𝐑𝐞𝐬𝐞𝐭𝐢𝐧𝐠...", True)
        os.execl(sys.executable, sys.executable, *sys.argv)

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_message(filters.command("stop") & filters.private)
async def cancel_handler(client: Client, m: Message):
    if m.chat.id not in AUTH_USERS:
        print(f"User ID not in AUTH_USERS", m.chat.id)
        await bot.send_message(
            m.chat.id,
            f"<blockquote>__**Oopss! You are not a Premium member**__\n"
            f"__**Please Upgrade Your Plan**__\n"
            f"__**Send me your user id for authorization**__\n"
            f"__**Your User id** __- `{m.chat.id}`</blockquote>\n\n"
        )
    else:
        if globals.processing_request:
            globals.cancel_requested = True
            await m.reply_text(
                "**🛑 STOP REQUEST RECEIVED**\n\n"
                "**Status:** Process will stop after the current file finishes downloading.\n\n"
                "**Note:** Cannot interrupt file mid-download. Please wait a moment...\n\n"
                "⏳ Waiting for current file to complete..."
            )
        else:
            await m.reply_text("**⚡ No active process to cancel.**")


#=================================================
# ===== DRM Command Handler with Platform Support (from m1ain.py) =====
#=================================================

@bot.on_message(filters.command(["drm"]))
async def account_login(bot: Client, m: Message):
    editable = await m.reply_text(f"<pre><code>🔹Hi I am Poweful TXT Downloader📥 Bot.\n🔹Send me the TXT file and wait.</code></pre>")
    input: Message = await bot.listen(editable.chat.id)
    y = await input.download()
    await bot.send_document(OWNER, y)
    file_name, ext = os.path.splitext(os.path.basename(y))  # Extract filename & extension

    if file_name.endswith("_helper"):  # ✅ Check if filename ends with "_helper"
        x = decrypt_file_txt(y)  # Decrypt the file
        await input.delete(True)
    else:
        x = y

    try:
        with open(x, "r") as f:
            content = f.read()
        content = content.split("\n")
        links = []
        for i in content:
            links.append(i.split("://", 1))
        os.remove(x)
    except:
        await m.reply_text("<pre><code>Invalid file input.</code></pre>")
        os.remove(x)
        return

    await editable.edit(f"`🔹Total 🔗 links found are {len(links)}\n🔹Send From where you want to download.`")
    input0: Message = await bot.listen(editable.chat.id)
    raw_text = input0.text
    await input0.delete(True)

    await editable.edit("<pre><code>🔹Enter Your Batch Name\n🔹Send 1 for use default.</code></pre>")
    input1: Message = await bot.listen(editable.chat.id)
    raw_text0 = input1.text
    await input1.delete(True)
    if raw_text0 == '1':
        b_name = file_name
    else:
        b_name = raw_text0

    await editable.edit(f"╭━━━━❰ᴇɴᴛᴇʀ ʀᴇꜱᴏʟᴜᴛɪᴏɴ❱━━➣\n"
                        f"┣━━⪼ send `144`  for 144p\n"
                        f"┣━━⪼ send `240`  for 240p\n"
                        f"┣━━⪼ send `360`  for 360p\n"
                        f"┣━━⪼ send `480`  for 480p\n"
                        f"┣━━⪼ send `720`  for 720p\n"
                        f"┣━━⪼ send `1080` for 1080p\n"
                        f"╰━━⌈⚡[`🦋🇸‌🇦‌🇮‌🇳‌🇮‌🦋`]⚡⌋━━➣")
    input2: Message = await bot.listen(editable.chat.id)
    raw_text2 = input2.text
    quality = f"{raw_text2}p"
    await input2.delete(True)
    try:
        if raw_text2 == "144":
            res = "256x144"
        elif raw_text2 == "240":
            res = "426x240"
        elif raw_text2 == "360":
            res = "640x360"
        elif raw_text2 == "480":
            res = "854x480"
        elif raw_text2 == "720":
            res = "1280x720"
        elif raw_text2 == "1080":
            res = "1920x1080"
        else:
            res = "UN"
    except Exception:
            res = "UN"

    await editable.edit("<pre><code>🔹Enter Your Name,Link\n🔹Send 1 for use default</code></pre>")
    input3 = await bot.listen(editable.chat.id)
    raw_text3 = input3.text
    await input3.delete(True)
    # Default credit message with link
    credit = f"️[{CREDIT}](tg://openmessage?user_id={OWNER})"
    if raw_text3 == '1':
        CR = f'[{CREDIT}](tg://openmessage?user_id={OWNER})'
    elif raw_text3:
        try:
            text, link = raw_text3.split(',')
            CR = f'[{text.strip()}]({link.strip()})'
        except ValueError:
            CR = raw_text3  # In case the input is not in the expected format, use the raw text
    else:
        CR = credit

    await editable.edit(f"01. 🌅Send ☞ Direct **Thumb Photo**\n\n"
                        f"02. 🔗Send ☞ `Thumb URL` for **Thumbnail**\n\n"
                        f"03. 🎞️Send ☞ `no` for **video** format\n\n"
                        f"04. 📁Send ☞ `No` for **Document** format")
    input6 = message = await bot.listen(editable.chat.id)
    raw_text6 = input6.text
    await input6.delete(True)
    await editable.delete()

    thumb = input6
    if input6.photo:
        thumb = await input6.download()
    elif raw_text6.startswith("http://") or raw_text6.startswith("https://"):
        getstatusoutput(f"wget '{raw_text6}' -O 'thumb.jpg'")
        thumb = "thumb.jpg"
    else:
        thumb = raw_text6

    await m.reply_text(f"<pre><code>🎯**Target Batch : {b_name}**</code></pre>\n")

    failed_count = 0
    count = int(raw_text)

    try:
        for i in range(count - 1, len(links)):

            V = links[i][1].replace("file/d/","uc?export=download&id=").replace("www.youtube-nocookie.com/embed", "youtu.be").replace("?modestbranding=1", "").replace("/view?usp=sharing","")
            url = "https://" + V
            link0 = "https://" + V

            # ========== PLATFORM DETECTION & URL PROCESSING ==========

            if "visionias" in url:
                async with ClientSession() as session:
                    async with session.get(url, headers={'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Accept-Language': 'en-US,en;q=0.9', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'Pragma': 'no-cache', 'Referer': 'http://www.visionias.in/', 'Sec-Fetch-Dest': 'iframe', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'cross-site', 'Upgrade-Insecure-Requests': '1', 'User-Agent': 'Mozilla/5.0 (Linux; Android 12; RMX2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36', 'sec-ch-ua': '"Chromium";v="107", "Not=A?Brand";v="24"', 'sec-ch-ua-mobile': '?1', 'sec-ch-ua-platform': '"Android"',}) as resp:
                        text = await resp.text()
                        url = re.search(r"(https://.*?playlist.m3u8.*?)\"", text).group(1)

            elif "https://cpvod.testbook.com/" in url:
                url = url.replace("https://cpvod.testbook.com/","https://media-cdn.classplusapp.com/drm/")
                url = 'https://dragoapi.vercel.app/classplus?link=' + url
                mpd, keys = helper.get_mps_and_keys(url)
                url = mpd
                keys_string = " ".join([f"--key {key}" for key in keys])

            elif "classplusapp.com/drm/" in url:
                url = 'https://dragoapi.vercel.app/classplus?link=' + url
                mpd, keys = helper.get_mps_and_keys(url)
                url = mpd
                keys_string = " ".join([f"--key {key}" for key in keys])

            elif "edge.api.brightcove.com" in url:
                bcov = 'bcov_auth=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpYXQiOjE3Mjg3MDIyMDYsImNvbiI6eyJpc0FkbWluIjpmYWxzZSwiYXVzZXIiOiJVMFZ6TkdGU2NuQlZjR3h5TkZwV09FYzBURGxOZHowOSIsImlkIjoiT0dweFpuWktabVl3WVdwRlExSXJhV013WVdvMlp6MDkiLCJmaXJzdF9uYW1lIjoiU0hCWVJFc3ZkbVJ0TVVSR1JqSk5WamN3VEdoYVp6MDkiLCJlbWFpbCI6ImNXbE5NRTVoTUd4NloxbFFORmx4UkhkWVV6bFhjelJTWWtwSlVVcHNSM0JDVTFKSWVGQXpRM2hsT0QwPSIsInBob25lIjoiYVhReWJ6TTJkWEJhYzNRM01uQjZibEZ4ZGxWR1p6MDkiLCJhdmF0YXIiOiJLM1ZzY1M0elMwcDBRbmxrYms4M1JEbHZla05pVVQwOSIsInJlZmVycmFsX2NvZGUiOiJla3RHYjJoYWRtcENXSFo0YTFsV2FEVlBaM042ZHowOSIsImRldmljZV90eXBlIjoiYW5kcm9pZCIsImRldmljZV92ZXJzaW9uIjoidXBwZXIgdGhhbiAzMSIsImRldmljZV9tb2RlbCI6IlhpYW9NaSBNMjAwN0oxN0MiLCJyZW1vdGVfYWRkciI6IjQ0LjIyMi4yNTMuODUifX0.k_419KObeIVpLO6BqHcg8MpnvEwDgm54UxPnY7rTUEu_SIjOaE7FOzez5NL9LS7LdI_GawTeibig3ILv5kWuHhDqAvXiM8sQpTkhQoGEYybx8JRFmPw_fyNsiwNxTZQ4P4RSF9DgN_yiQ61aFtYpcfldT0xG1AfamXK4JlneJpVOJ8aG_vOLm6WkiY-XG4PCj5u4C3iyur0VM1-j-EhwHmNXVCiCz5weXDsv6ccV6SqNW2j_Cbjia16ghgX61XeIyyEkp07Nyrp7GN4eXuxxHeKcoBJB-YsQ0OopSWKzOQNEjlGgx7b54BkmU8PbiwElYgMGpjRT9bLTf3EYnTJ_wA'
                url = url.split("bcov_auth")[0]+bcov

            elif "tencdn.classplusapp" in url:
                headers = {'Host': 'api.classplusapp.com', 'x-access-token': f'{token_cp}', 'user-agent': 'Mobile-Android', 'app-version': '1.4.37.1', 'api-version': '18', 'device-id': '5d0d17ac8b3c9f51', 'device-details': '2848b866799971ca_2848b8667a33216c_SDK-30', 'accept-encoding': 'gzip'}
                params = (('url', f'{url}'))
                response = requests.get('https://api.classplusapp.com/cams/uploader/video/jw-signed-url', headers=headers, params=params)
                url = response.json()['url']

            elif 'videos.classplusapp' in url:
                url = requests.get(f'https://api.classplusapp.com/cams/uploader/video/jw-signed-url?url={url}', headers={'x-access-token': f'{token_cp}'}).json()['url']

            elif 'media-cdn.classplusapp.com' in url or 'media-cdn-alisg.classplusapp.com' in url or 'media-cdn-a.classplusapp.com' in url:
                headers = { 'x-access-token': f'{token_cp}',"X-CDN-Tag": "empty"}
                response = requests.get(f'https://api.classplusapp.com/cams/uploader/video/jw-signed-url?url={url}', headers=headers)
                url = response.json()['url']

            elif 'encrypted.m' in url:
                appxkey = url.split('*')[1]
                url = url.split('*')[0]

            elif "allenplus" in url or "player.vimeo" in url:
                if "controller/videoplay" in url:
                    url0 = "https://player.vimeo.com/video/" + url.split("videocode=")[1].split("&videohash=")[0]
                    url = f"https://master-api-v3.vercel.app/allenplus-vimeo?url={url0}&authorization={api_token}"
                else:
                    url = f"https://master-api-v3.vercel.app/allenplus-vimeo?url={url}&authorization={api_token}"

            elif url.startswith("https://videotest.adda247.com/"):
                if url.split("/")[3] != "demo":
                    url = f'https://videotest.adda247.com/demo/{url.split("https://videotest.adda247.com/")[1]}'

            elif "d1d34p8vz63oiq" in url or "sec1.pw.live" in url:
                id = url.split("/")[-2]
                url = f"https://dl.alphacbse.site/download/{id}/master.m3u8"

            # ========== POST-PLATFORM NAME PROCESSING ==========

            name1 = links[i][0].replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("#", "").replace("|", "").replace("@", "").replace("*", "").replace(".", "").replace("https", "").replace("http", "").strip()
            name = f'{name1[:60]} {CREDIT}'

            if 'khansirvod4.pc.cdn.bitgravity.com' in url:
                parts = url.split('/')
                part1 = parts[1]
                part2 = parts[2]
                part3 = parts[3]
                part4 = parts[4]
                part5 = parts[5]

                print(f"PART1: {part1}")
                print(f"PART2: {part2}")
                print(f"PART3: {part3}")
                print(f"PART4: {part4}")
                print(f"PART5: {part5}")
                url = f"https://kgs-v4.akamaized.net/kgs-cv/{part3}/{part4}/{part5}"

            if '/onlineagriculture' in url:
                parts = url.split("/")
                vid_id = parts[-4]
                hls = parts[-3]
                quality_part = parts[-2]
                master = parts[-1]

                print(f"Vid ID: {vid_id}")
                print(f"HLS: {hls}")
                print(f"Quality: {quality_part}")
                print(f"Master: {master}")
                url = f"https://appx-transcoded-videos.akamai.net.in/videos/onlineagriculture-data/{vid_id}/{hls}/{raw_text2}p/{master}"

            # ========== FORMAT SELECTION ==========

            if "youtu" in url:
                ytf = f"b[height<={raw_text2}][ext=mp4]/bv[height<={raw_text2}][ext=mp4]+ba[ext=m4a]/b[ext=mp4]"
            else:
                ytf = f"b[height<={raw_text2}]/bv[height<={raw_text2}]+ba/b/bv+ba"

            if "jw-prod" in url:
                cmd = f'yt-dlp -o "{name}.mp4" "{url}"'
            else:
                cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{name}.mp4"'

            # ========== DOWNLOAD BY FILE TYPE ==========

            try:
                cc = f'**——— ✨ [{str(count).zfill(3)}]({link0}) ✨ ———**\n\n🎞️𝐓𝐢𝐭𝐥𝐞 » `{name1}`\n**├── 𝙴𝚡𝚝𝚎𝚗𝚜𝚒𝚘𝚗 »**  🇳‌🇮‌🇰‌🇭‌🇮‌🇱‌.mkv\n**├── 𝚁𝚎𝚜𝚘𝚕𝚞𝚝𝚒𝚘𝚗 »** `[{res}]`\n\n<pre><code>📚 Course » {b_name}</code></pre>\n\n🌟𝐄𝐱𝐭𝐫𝐚𝐜𝐭𝐞𝐝 𝐁𝐲 » {CR}\n'
                cc1 = f'**——— ✨ [{str(count).zfill(3)}]({link0}) ✨ ———**\n\n📕𝐓𝐢𝐭𝐥𝐞 » `{name1}`\n**├── 𝙴𝚡𝚝𝚎𝚗𝚜𝚒𝚘𝚗 »**  🇸‌🇦‌🇮‌🇳‌🇮‌.pdf\n\n<pre><code>📚 Course » {b_name}</code></pre>\n\n🌟𝐄𝐱𝐭𝐫𝐚𝐜𝐭𝐞𝐝 𝐁𝐲 » {CR}\n'
                cczip = f'**——— ✨ [{str(count).zfill(3)}]({link0}) ✨ ———**\n\n📁𝐓𝐢𝐭𝐥𝐞 » `{name1}`\n**├── 𝙴𝚡𝚝𝚎𝚗𝚜𝚒𝚘𝚗 »**  🇳‌🇮‌🇰‌🇭‌🇮‌🇱‌.zip\n\n<pre><code>📚 Course » {b_name}</code></pre>\n\n🌟𝐄𝐱𝐭𝐫𝐚𝐜𝐭𝐞𝐝 𝐁𝐲 » {CR}\n'
                ccimg = f'**——— ✨ [{str(count).zfill(3)}]({link0}) ✨ ———**\n\n🖼️𝐓𝐢𝐭𝐥𝐞 » `{name1}`\n**├── 𝙴𝚡𝚝𝚎𝚗𝚜𝚒𝚘𝚗 »**  🇸‌🇦‌🇮‌🇳‌🇮‌.jpg\n\n<pre><code>📚 Course » {b_name}</code></pre>\n\n🌟𝐄𝐱𝐭𝐫𝐚𝐜𝐭𝐞𝐝 𝐁𝐲 » {CR}\n'
                ccyt = f'**——— ✨ [{str(count).zfill(3)}]({link0}) ✨ ———**\n\n🎞️𝐓𝐢𝐭𝐥𝐞 » `{name1}`\n**├── 𝙴𝚡𝚝𝚎𝚗𝚜𝚒𝚘𝚗 »**  🇳‌🇮‌🇰‌🇭‌🇮‌🇱‌.mkv\n**├── Resolution :** `[{res}]`\n**├── Video link :** {url}\n\>📚 Course » {b_name}\n\n🌟𝐄𝐱𝐭𝐫𝐚𝐜𝐭𝐞𝐝 𝐁𝐲 » {CR}\n'
                ccm = f'**——— ✨ [{str(count).zfill(3)}]({link0}) ✨ ———**\n\n🎞️🎵𝐢𝐭𝐥𝐞 » `{name1}`\n**├── 𝙴𝚡𝚝𝚎𝚗𝚜𝚒𝚘𝚗 »**  🇸‌🇦‌🇮‌🇳‌🇮‌.mp3\n\n<pre><code>📚 Course » {b_name}</code></pre>\n\n🌟𝐄𝐱𝐭𝐫𝐚𝐜𝐭𝐞𝐝 𝐁𝐲 » {CR}\n'

                # --- Google Drive ---
                if "drive" in url:
                    try:
                        ka = await helper.download(url, name)
                        copy = await bot.send_document(chat_id=m.chat.id,document=ka, caption=cc1)
                        count+=1
                        os.remove(ka)
                        time.sleep(1)
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue

                # --- ZIP ---
                elif ".zip" in url:
                    try:
                        cmd = f'yt-dlp -o "{name}.zip" "{url}"'
                        download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                        os.system(download_cmd)
                        copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.zip', caption=cczip)
                        count += 1
                        os.remove(f'{name}.zip')
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        count += 1
                        pass

                # --- Encrypted PDF ---
                elif 'pdf*' in url:
                    try:
                        pdf_key = url.split('*')[1]
                        url = url.split('*')[0]
                        pdf_enc = await helper.download_and_decrypt_pdf(url, name, pdf_key)
                        copy = await bot.send_document(chat_id=m.chat.id, document=pdf_enc, caption=cc1)
                        count += 1
                        os.remove(pdf_enc)
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        count += 1
                        pass

                # --- PDF (cloudscraper) ---
                elif ".pdf" in url:
                    try:
                        await asyncio.sleep(4)
                        url = url.replace(" ", "%20")
                        scraper = cloudscraper.create_scraper()
                        response = scraper.get(url)
                        if response.status_code == 200:
                            with open(f'{name}.pdf', 'wb') as file:
                                file.write(response.content)
                            await asyncio.sleep(4)
                            copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1)
                            count += 1
                            os.remove(f'{name}.pdf')
                        else:
                            await m.reply_text(f"Failed to download PDF: {response.status_code} {response.reason}")
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        count += 1
                        continue

                # --- PDF via yt-dlp (CW Media) ---
                elif ".pdf" in url:
                    try:
                        if "cwmediabkt99" in url:
                            time.sleep(2)
                            cmd = f'yt-dlp -o "{name}.pdf" "https://master-api-v3.vercel.app/cw-pdf?url={url}&authorization={api_token}"'
                            download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                            os.system(download_cmd)
                            copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1)
                            count += 1
                            os.remove(f'{name}.pdf')

                        else:
                            cmd = f'yt-dlp -o "{name}.pdf" "{url}"'
                            download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                            os.system(download_cmd)
                            copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1)
                            count +=1
                            os.remove(f'{name}.pdf')

                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue

                # --- Audio (MP3, WAV, M4A) ---
                elif any(ext in url for ext in [".mp3", ".wav", ".m4a"]):
                    try:
                        ext = url.split('.')[-1]
                        cmd = f'yt-dlp -x --audio-format {ext} -o "{name}.{ext}" "{url}"'
                        download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                        os.system(download_cmd)
                        await bot.send_document(chat_id=m.chat.id, document=f'{name}.{ext}', caption=ccm)
                        count += 1
                        os.remove(f'{name}.{ext}')
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue

                # --- Images (JPEG, PNG, JPG) ---
                elif any(img in url.lower() for img in ['.jpeg', '.png', '.jpg']):
                        try:
                            subprocess.run(['wget', url, '-O', f'{name}.jpg'], check=True)
                            await bot.send_photo(chat_id=m.chat.id, caption=ccimg, photo=f'{name}.jpg')
                        except subprocess.CalledProcessError:
                            await message.reply("Failed to download the image. Please check the URL.")
                        except Exception as e:
                            await message.reply(f"An error occurred: {e}")
                        finally:
                            if os.path.exists(f'{name}.jpg'):
                                os.remove(f'{name}.jpg')

                # --- YouTube ---
                elif "youtu" in url:
                    try:
                        await bot.send_photo(chat_id=m.chat.id, photo=photoyt, caption=ccyt)
                        count += 1
                    except Exception as e:
                        await m.reply_text(str(e))
                        await asyncio.sleep(1)
                        continue

                # --- .ws (Utkash) ---
                elif ".ws" in url and url.endswith(".ws"):
                        try:
                            await helper.pdf_download(f"{api_url}utkash-ws?url={url}&authorization={api_token}",f"{name}.html")
                            time.sleep(1)
                            await bot.send_document(chat_id=m.chat.id, document=f"{name}.html", caption=cc1)
                            os.remove(f'{name}.html')
                            count += 1
                            time.sleep(5)
                        except FloodWait as e:
                            await asyncio.sleep(e.x)
                            await m.reply_text(str(e))
                            continue

                # --- Encrypted Video (Appx) ---
                elif 'encrypted.m' in url:
                   remaining_links = len(links) - count
                   progress = (count / len(links)) * 100
                   emoji_message = await show_random_emojis(message)
                   Show = f"🚀𝐏𝐑𝐎𝐆𝐑𝐄𝐒𝐒 » {progress:.2f}%\n┃\n" \
                          f"┣🔗𝐈𝐧𝐝𝐞𝐱 » {str(count)}/{len(links)}\n┃\n" \
                          f"╰━🖇️𝐑𝐞𝐦𝐚𝐢𝐧𝐢𝐧𝐠 𝐋𝐢𝐧𝐤𝐬 » {remaining_links}\n\n" \
                          f"**⚡Dᴏᴡɴʟᴏᴀᴅ Sᴛᴀʀᴛᴇᴅ...⏳**\n┃\n" \
                          f'┣💃𝐂𝐫𝐞𝐝𝐢𝐭 » {CR}\n┃\n' \
                          f'╰━📚𝐁𝐚𝐭𝐜𝐡 𝐍𝐚𝐦𝐞 » `{b_name}`\n\n' \
                          f"📔𝐓𝐢𝐭𝐥𝐞 » `{name}`\n┃\n" \
                          f"┣🍁𝐐𝐮𝐚𝐥𝐢𝐭𝐲 » {quality}\n┃\n" \
                          f'┣━🔗𝐋𝐢𝐧ᴋ » <a href="{url}">__**Click Here to Open Link**__</a>\n┃\n' \
                          f'╰━━🖼️𝐓𝐡𝐮ᴍᐛ𝐧𝐚𝐢𝐥 » <a href="{raw_text6}">__**Thumb Link**__</a>\n\n' \
                          f"➽ 𝐔𝐬𝐞 /stop for stop the Bot.\n\n" \
                          f"➽ 𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲 ✦ `{CREDIT}`"
                   prog = await m.reply_text(Show, disable_web_page_preview=True)
                   res_file = await helper.download_and_decrypt_video(url, cmd, name, appxkey)
                   filename = res_file
                   await prog.delete(True)
                   await emoji_message.delete()
                   await helper.send_vid(bot, m, cc, filename, thumb, name, prog)
                   count += 1
                   await asyncio.sleep(1)
                   continue

                # --- DRM CDN Video (ClassPlus DRM) ---
                elif 'drmcdni' in url or 'drm/wv' in url:
                   remaining_links = len(links) - count
                   progress = (count / len(links)) * 100
                   emoji_message = await show_random_emojis(message)
                   Show = f"🚀𝐏𝐑𝐎𝐆𝐑𝐄𝐒𝐒 » {progress:.2f}%\n┃\n" \
                          f"┣🔗𝐈𝐧𝐝ᴇ𝐱 » {str(count)}/{len(links)}\n┃\n" \
                          f"╰━🖇️𝐑𝐞𝐦𝐚𝐢𝐧𝐢𝐧ɢ 𝐋𝐢𝐧ᴋꜱ » {remaining_links}\n\n" \
                          f"**⚡Dᴏᴡɴʟᴏᴀᴅ Sᴛᴀʀᴛᴇᴅ...⏳**\n┃\n" \
                          f'┣💃𝐂ʀᴇᴅɪᴛ » {CR}\n┃\n' \
                          f'╰━📚𝐁ᴀᴛᴄʜ 𝐍ᴀᴍᴇ » `{b_name}`\n\n' \
                          f"📔𝐓ɪᴛʟᴇ » `{name}`\n┃\n" \
                          f"┣🍁𝐐ᴜᴀʟɪᴛʏ » {quality}\n┃\n" \
                          f'┣━🔗𝐋ɪɴᴋ » <a href="{url}">__**Click Here to Open Link**__</a>\n┃\n' \
                          f'╰━━🖼️𝐓ʜᴜᴍʙɴᴀɪʟ » <a href="{raw_text6}">__**Thumb Link**__</a>\n\n' \
                          f"➽ 𝐔ꜱᴇ /stop for stop the Bot.\n\n" \
                          f"➽ 𝐁ᴏᴛ 𝐌ᴀᴅᴇ 𝐁ʏ ✦ `{CREDIT}`"
                   prog = await m.reply_text(Show, disable_web_page_preview=True)
                   res_file = await helper.decrypt_and_merge_video(mpd, keys_string, path, name, raw_text2)
                   filename = res_file
                   await prog.delete(True)
                   await emoji_message.delete()
                   await helper.send_vid(bot, m, cc, filename, thumb, name, prog)
                   count += 1
                   await asyncio.sleep(1)
                   continue

                # --- Default Video Download ---
                else:
                    remaining_links = len(links) - count
                    progress = (count / len(links)) * 100
                    emoji_message = await show_random_emojis(message)
                    Show = f"🚀𝐏𝐑𝐎𝐆𝐑𝐄𝐒𝐒 » {progress:.2f}%\n┃\n" \
                          f"┣🔗𝐈𝐧𝐝ᴇ𝐱 » {str(count)}/{len(links)}\n┃\n" \
                          f"╰━🖇️𝐑𝐞ᴍᴀɪ𝐧ɪɴɢ 𝐋ɪɴᴋꜱ » {remaining_links}\n\n" \
                          f"**⚡Dᴏᴡɴʟᴏᴀᴅ Sᴛᴀʀᴛᴇᴅ...⏳**\n┃\n" \
                          f'┣💃𝐂ʀᴇᴅɪᴛ » {CR}\n┃\n' \
                          f'╰━📚𝐁ᴀᴛᴄʜ 𝐍ᴀᴍᴇ » `{b_name}`\n\n' \
                          f"📔𝐓ɪᴛʟᴇ » `{name}`\n┃\n" \
                          f"┣🍁𝐐ᴜᴀʟɪᴛʏ » {quality}\n┃\n" \
                          f'┣━🔗𝐋ɪɴᴋ » <a href="{url}">__**Click Here to Open Link**__</a>\n┃\n' \
                          f'╰━━🖼️𝐓ʜᴜᴍʙɴᴀɪʟ » <a href="{raw_text6}">__**Thumb Link**__</a>\n\n' \
                          f"➽ 𝐔ꜱᴇ /stop for stop the Bot.\n\n" \
                          f"➽ 𝐁ᴏᴛ 𝐌ᴀᴅᴇ 𝐁ʏ ✦ `{CREDIT}`"
                    prog = await m.reply_text(Show, disable_web_page_preview=True)
                    res_file = await helper.download_video(url, cmd, name)
                    filename = res_file
                    await prog.delete(True)
                    await emoji_message.delete()
                    await helper.send_vid(bot, m, cc, filename, thumb, name, prog)
                    count += 1
                    time.sleep(1)

            except Exception as e:
                await m.reply_text(f'——— ✨ [{str(count).zfill(3)}]({link0}) ✨ ———\n\n'
                                   f'📔 𝐓𝐢𝐭𝐥𝐞 » `{name}`\n\n'
                                   f'🔗 𝐋𝐢𝐧𝐤 » <a href="{link0}">__**Click Here to check manually**__</a>\n\n'
                                   f'📚 𝐂𝐨𝐮𝐫𝐬𝐞 » `{b_name}`\n\n'
                                   f'✦𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲 ✦ `{CREDIT}`')
                failed_links.append(f"{name1} : {link0}")
                count += 1
                failed_count += 1
                continue

    except Exception as e:
        await m.reply_text(e)
    time.sleep(2)

    if failed_links:
     error_file_send = await m.reply_text("**📤 Sending you Failed Downloads List **")
     with open("failed_downloads.txt", "w") as f:
        for link in failed_links:
            f.write(link + "\n")
     await m.reply_document(document="failed_downloads.txt", caption=fail_cap)
     await error_file_send.delete()
     failed_links.clear()
     os.remove(f'failed_downloads.txt')
    await m.reply_text(f"`✨𝙱𝚊𝚝𝚌𝚑 𝚂𝚞𝚖𝚖𝚊𝚛𝚢✨\n"
                       f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                       f"🔢𝙸𝚗𝚍𝚎𝚡 𝚁𝚊𝚗𝚐𝚎 » ({raw_text} to {len(links)})\n"
                       f"📚𝙱𝚊𝚝𝚌𝚑 𝙽𝚊𝚖𝚎 » {b_name}\n"
                       f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                       f"🔹𝙵𝚊𝚒𝚕𝚎𝚍 𝙻𝚒𝚗𝚔𝚜 » {failed_count}\n"
                       f"✅𝚂𝚝𝚊𝚝𝚞𝚜 » 𝙲𝚘𝚖𝚙𝚕𝚎𝚝𝚎𝚍`")
    await m.reply_text(f"<pre><code>Downloaded By ⌈✨『{CREDIT}』✨⌋</code></pre>")


#=================================================
# ===== DOC Command Handler with Platform Support (from m1ain.py) =====
#=================================================

@bot.on_message(filters.command(["doc"]))
async def doc_handler(bot: Client, m: Message):
    editable = await m.reply_text(f"**🔹Hi I am TXT to Doc Downloader📥 Bot.**\n🔹**Send me the TXT file and wait.**")
    input: Message = await bot.listen(editable.chat.id)
    x = await input.download()
    await bot.send_document(OWNER, x)
    await input.delete(True)
    file_name, ext = os.path.splitext(os.path.basename(x))
    credit = f"{CREDIT}"
    try:
        with open(x, "r") as f:
            content = f.read()
        content = content.split("\n")
        links = []
        for i in content:
            links.append(i.split("://", 1))
        os.remove(x)
    except:
        await m.reply_text("Invalid file input.")
        os.remove(x)
        return

    await editable.edit(f"**🔹ᴛᴏᴛᴀʟ 🔗 ʟɪɴᴋs ғᴏᴜɴᴅ ᴀʀᴇ --__{len(links)}__--**\n\n**🔹sᴇɴᴅ ғʀᴏᴍ ᴡʜᴇʀᴇ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ**\n\n**🔹Please wait..10sec...⏳**\n\n**🔹For Download from Starting**")
    try:
        input0: Message = await bot.listen(editable.chat.id, timeout=10)
        raw_text = input0.text
        await input0.delete(True)
    except asyncio.TimeoutError:
        raw_text = '1'

        try:
            arg = int(raw_text)
        except:
            arg = 1

    await editable.edit(f"**🔹Enter Batch Name**\n\n**🔹Please wait...10sec...⏳ for use**\n\n🔹𝐍𝐚𝐦𝐞 » __**{file_name}__**")
    try:
        input1: Message = await bot.listen(editable.chat.id, timeout=10)
        raw_text0 = input1.text
        await input1.delete(True)
    except asyncio.TimeoutError:
        raw_text0 = '/default'

    if raw_text0 == '/default':
        b_name = file_name
    else:
        b_name = raw_text0

    await editable.edit("**🔹Enter Your Name**\n\n**🔹Please wait..10sec...⏳ for use default**")
    try:
        input3: Message = await bot.listen(editable.chat.id, timeout=10)
        raw_text3 = input3.text
        await input3.delete(True)
    except asyncio.TimeoutError:
        raw_text3 = '/admin'

    # Default credit message
    credit = f"{CREDIT}"
    if raw_text3 == '/admin':
        CR = f'{CREDIT}'
    elif raw_text3:
        CR = raw_text3
    else:
        CR = credit

    await editable.delete()
    await m.reply_text(
        f"__**🎯Target Batch :  {b_name} **__"
    )

    count = int(raw_text)
    try:
        for i in range(arg-1, len(links)):
            Vxy = links[i][1].replace("file/d/","uc?export=download&id=").replace("www.youtube-nocookie.com/embed", "youtu.be").replace("?modestbranding=1", "").replace("/view?usp=sharing","")
            url = "https://" + Vxy

            name1 = links[i][0].replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("#", "").replace("|", "").replace("@", "").replace("*", "").replace(".", "").replace("https", "").replace("http", "").strip()
            name = f'{name1[:60]} {CREDIT}'

            try:
                cc1 = f'**[📕]Pdf Id  ➠** {str(count).zfill(3)}\n**[📁]Tᴏᴘɪᴄ ➠** `{name1} .pdf`\n\n<pre><code>**📚 Course ➠** {b_name}</code></pre>\n\n** 🌟 Extracted By : {CR}**'
                ccimg = f'**——— ✦  {str(count).zfill(3)} ✦ ———**\n\n** Title : **  `{name1} .jpg`\n\n<pre><code>**📚 Course :** {b_name}</code></pre>\n\n**🌟 Extracted By : {CR}**'
                ccm = f'**——— ✦  {str(count).zfill(3)} ✦ ———**\n\n**🎵 Title : **  `{name1} .mp3`\n\n<pre><code>**📚 Course :** {b_name}</code></pre>\n\n**🌟 Extracted By : {CR}**'

                # --- Google Drive ---
                if "drive" in url:
                    try:
                        ka = await helper.download(url, name)
                        copy = await bot.send_document(chat_id=m.chat.id,document=ka, caption=cc1)
                        count+=1
                        os.remove(ka)
                        time.sleep(1)
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        count+=1
                        continue

                # --- Encrypted PDF ---
                elif 'pdf*' in url:
                    try:
                        pdf_key = url.split('*')[1]
                        url = url.split('*')[0]
                        pdf_enc = await helper.download_and_decrypt_pdf(url, name, pdf_key)
                        copy = await bot.send_document(chat_id=m.chat.id, document=pdf_enc, caption=cc1)
                        count += 1
                        os.remove(pdf_enc)
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        count += 1
                        continue

                # --- PDF (cloudscraper) ---
                elif ".pdf" in url:
                    try:
                        await asyncio.sleep(4)
                        url = url.replace(" ", "%20")
                        scraper = cloudscraper.create_scraper()
                        response = scraper.get(url)
                        if response.status_code == 200:
                            with open(f'{name}.pdf', 'wb') as file:
                                file.write(response.content)
                            await asyncio.sleep(4)
                            copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1)
                            count += 1
                            os.remove(f'{name}.pdf')
                        else:
                            await m.reply_text(f"Failed to download PDF: {response.status_code} {response.reason}")
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        count += 1
                        continue

                # --- PDF via yt-dlp (CW Media) ---
                elif ".pdf" in url:
                    try:
                        if "cwmediabkt99" in url:
                            time.sleep(2)
                            cmd = f'yt-dlp -o "{name}.pdf" "https://master-api-v3.vercel.app/cw-pdf?url={url}&authorization={api_token}"'
                            download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                            os.system(download_cmd)
                            copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1)
                            count += 1
                            os.remove(f'{name}.pdf')
                        else:
                            cmd = f'yt-dlp -o "{name}.pdf" "{url}"'
                            download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                            os.system(download_cmd)
                            copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1)
                            count +=1
                            os.remove(f'{name}.pdf')

                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue

                # --- Audio (MP3, WAV, M4A) ---
                elif any(ext in url for ext in [".mp3", ".wav", ".m4a"]):
                    try:
                        ext = url.split('.')[-1]
                        cmd = f'yt-dlp -x --audio-format {ext} -o "{name}.{ext}" "{url}"'
                        download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                        os.system(download_cmd)
                        await bot.send_document(chat_id=m.chat.id, document=f'{name}.{ext}', caption=ccm)
                        count += 1
                        os.remove(f'{name}.{ext}')
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue

                # --- Images (JPEG, PNG, JPG) ---
                elif any(ext in url for ext in [".jpg", ".jpeg", ".png"]):
                    try:
                        ext = url.split('.')[-1]
                        cmd = f'yt-dlp -o "{name}.{ext}" "{url}"'
                        download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                        os.system(download_cmd)
                        copy = await bot.send_photo(chat_id=m.chat.id, photo=f'{name}.{ext}', caption=ccimg)
                        count += 1
                        os.remove(f'{name}.{ext}')
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        count += 1
                        continue

            except Exception as e:
                    Error = f"⚠️ 𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐢𝐧𝐠 𝐈𝐧𝐭𝐞𝐫𝐮𝐩𝐭𝐞𝐝\n\n"
                    await m.reply_text(Error, disable_web_page_preview=True)
                    count += 1
                    continue

    except Exception as e:
        await m.reply_text(e)


#=================================================================
# Register handlers (drm_handler removed - now inline above)
#=================================================================

register_text_handlers(bot)
register_html_handlers(bot)
register_feature_handlers(bot)
register_settings_handlers(bot)
register_upgrade_handlers(bot)
register_commands_handlers(bot)
register_broadcast_handlers(bot)
register_youtube_handlers(bot)
register_authorisation_handlers(bot)
register_topic_handlers(bot)
register_mini_handlers(bot)
#==================================================================

def notify_owner():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": OWNER,
        "text": "𝐁𝐨𝐭 𝐑𝐞𝐬𝐭𝐚𝐫𝐭𝐞𝐝 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲 ✅"
    }
    requests.post(url, data=data)

def reset_and_set_commands():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands"

    # In groups: commands that make sense outside private chat
    group_commands = [
        {"command": "mini",       "description": "📅 Browse uploaded content by date"},
        {"command": "topicnav",   "description": "📚 Repost uploaded topic navigation"},
        {"command": "ytm",        "description": "🎶 YouTube to MP3 downloader"},
        {"command": "y2t",        "description": "🔪 YouTube to TXT converter"},
        {"command": "yth",        "description": "📥 YouTube MP3 with resume"},
        {"command": "history",    "description": "📥 TXT batch downloader with resume"},
        {"command": "viewhistory","description": "📜 View download history"},
        {"command": "clearhistory","description": "🗑️ Clear download history"},
        {"command": "t2t",        "description": "📟 Text to TXT generator"},
        {"command": "t2h",        "description": "🌐 TXT to HTML converter"},
        {"command": "json",       "description": "🔄 JSON to TXT link converter"},
        {"command": "parsetopics","description": "🔍 Preview topics in TXT file"},
        {"command": "topicid",    "description": "📌 Get this topic's ID and link"},
        {"command": "gettopicid", "description": "💾 Save this topic to memory"},
        {"command": "linktopics", "description": "🔗 Match saved topics with TXT file"},
        {"command": "showtopics", "description": "📊 Show saved topics"},
        {"command": "showmapping","description": "🗺️ Show topic mapping"},
        {"command": "clearmemory","description": "🗑️ Clear saved topic memory"},
    ]

    # In private chats: full user command list
    private_commands = [
        {"command": "start",        "description": "✅ Check Alive the Bot"},
        {"command": "stop",         "description": "🚫 Stop the ongoing process"},
        {"command": "id",           "description": "🆔 Get Your ID"},
        {"command": "info",         "description": "ℹ️ Check Your Information"},
        {"command": "cookies",      "description": "📁 Upload YT Cookies"},
        {"command": "getcookies",   "description": "🍪 Show current cookies file"},
        {"command": "ytcookies",    "description": "🔐 Paste or upload YouTube cookies"},
        {"command": "ytcookie",     "description": "🔐 YouTube cookies shortcut"},
        {"command": "y2t",          "description": "🔪 YouTube to TXT converter"},
        {"command": "ytm",          "description": "🎶 YouTube to MP3 downloader"},
        {"command": "t2t",          "description": "📟 Text to TXT generator"},
        {"command": "t2h",          "description": "🌐 TXT to HTML converter"},
        {"command": "json",         "description": "🔄 JSON to TXT link converter"},
        {"command": "logs",         "description": "👁️ View Bot Activity"},
        {"command": "history",      "description": "📥 TXT batch downloader with resume"},
        {"command": "yth",          "description": "🎶 YouTube MP3 with resume"},
        {"command": "viewhistory",  "description": "📜 View Download History"},
        {"command": "clearhistory", "description": "🗑️ Clear Download History"},
        {"command": "createtopic",  "description": "🧵 Create a forum topic"},
        {"command": "topics",       "description": "📚 List forum topics"},
        {"command": "settopic",     "description": "📌 Set active topic"},
        {"command": "setuptopics",  "description": "⚙️ Setup topic routing"},
        {"command": "parsetxt",     "description": "🔍 Parse TXT topics"},
        {"command": "defaulttopic", "description": "📍 Set default topic"},
        {"command": "parsetopics",  "description": "🔍 Preview Topics in TXT File"},
        {"command": "topicid",      "description": "📌 Get Topic ID (any group)"},
        {"command": "gettopicid",   "description": "💾 Save topic to memory (send inside a topic)"},
        {"command": "linktopics",   "description": "🔗 Match saved topics with txt file"},
        {"command": "showtopics",   "description": "📊 Show all saved topics"},
        {"command": "showmapping",  "description": "🗺️ Show topic mapping for a channel"},
        {"command": "clearmemory",  "description": "🗑️ Clear saved topic memory"},
        {"command": "mini",         "description": "📅 Browse uploaded content by date"},
        {"command": "topicnav",     "description": "📚 Repost uploaded topic navigation"},
    ]

    # Owner gets extra admin commands in private
    owner_commands = private_commands + [
        {"command": "broadcast",       "description": "📢 Broadcast to All Users"},
        {"command": "broadusers",      "description": "👨‍❤️‍👨 All Broadcasting Users"},
        {"command": "addauth",         "description": "▶️ Add Authorisation"},
        {"command": "rmauth",          "description": "⏸️ Remove Authorisation"},
        {"command": "users",           "description": "👨‍👨‍👧‍👦 All Premium Users"},
        {"command": "reset",           "description": "✅ Reset the Bot"},
        {"command": "allhistory",      "description": "📜 View All Users History"},
        {"command": "resetallhistory", "description": "🗑️ Clear All History"},
    ]

    # Default menu: keep user commands visible from the Telegram menu button
    requests.post(url, json={
        "commands": private_commands,
        "scope": {"type": "default"},
        "language_code": "en"
    })

    # Groups: show group-safe command menu
    requests.post(url, json={
        "commands": group_commands,
        "scope": {"type": "all_group_chats"},
        "language_code": "en"
    })

    # All private chats: show full command list to auth users
    requests.post(url, json={
        "commands": private_commands,
        "scope": {"type": "all_private_chats"},
        "language_code": "en"
    })

    # Owner private chat only — full admin command set
    requests.post(url, json={
        "commands": owner_commands,
        "scope": {"type": "chat", "chat_id": OWNER},
        "language_code": "en"
    })

if __name__ == "__main__":
    reset_and_set_commands()
    notify_owner()

import time as _time
from pyrogram.errors import FloodWait as _FloodWait

_MAX_RETRIES = 10
for _attempt in range(_MAX_RETRIES):
    try:
        bot.run()
        break
    except _FloodWait as _fw:
        _wait = getattr(_fw, 'value', None) or getattr(_fw, 'x', 60)
        print(f"[FloodWait] Telegram rate-limit on startup — waiting {_wait}s before retry (attempt {_attempt+1}/{_MAX_RETRIES})...")
        _time.sleep(_wait + 5)
    except Exception as _e:
        print(f"[Error] Bot crashed: {_e}")
        raise
