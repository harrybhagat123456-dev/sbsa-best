from pyrogram.errors.exceptions.bad_request_400 import StickerEmojiInvalid 
import requests
#from logger import logging
import m3u8
import json
import subprocess
from pyrogram import Client, filters
from pyrogram.types.messages_and_media import message
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import FloodWait
from pyromod import listen
from pyrogram.types import Message    
from p_bar import progress_bar    
from subprocess import getstatusoutput    
from aiohttp import ClientSession    
import helper    
from logger import logging    
import time    
import asyncio    
from pyrogram.types import User, Message    
import sys    
import re    
import os 
import random
import urllib
import urllib.parse
import tgcrypto
import cloudscraper
import yt_dlp
from pytube import YouTube
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64encode, b64decode
from helper import *
from config import API_ID, API_HASH, BOT_TOKEN

OWNER = int(os.environ.get("OWNER", 7385595817))
cookies_file_path= "youtube_cookies.txt"
# watermark_text = ""

photologo = 'https://tinypic.host/images/2025/02/07/DeWatermark.ai_1738952933236-1.png'
photoyt = 'https://tinypic.host/images/2025/03/18/YouTube-Logo.wine.png'
photocp = 'https://tinypic.host/images/2025/03/28/IMG_20250328_133126.jpg'

async def show_random_emojis(message):
    emojis = ['🐼', '🐶', '🐅', '⚡️', '🚀', '✨', '💥', '☠️', '🥂', '🍾']
    emoji_message = await message.reply_text(' '.join(random.choices(emojis, k=1)))
    return emoji_message
  
api_url = "http://master-api-v3.vercel.app/"
api_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNzkxOTMzNDE5NSIsInRnX3VzZXJuYW1lIjoi4p61IFtvZmZsaW5lXSIsImlhdCI6MTczODY5MjA3N30.SXzZ1MZcvMp5sGESj0hBKSghhxJ3k1GTWoBUbivUe1I"
token_cp ='eyJjb3Vyc2VJZCI6IjQ1NjY4NyIsInR1dG9ySWQiOm51bGwsIm9yZ0lkIjo0ODA2MTksImNhdGVnb3J5SWQiOm51bGx9'

failed_links = []  # List to store failed links
fail_cap =f"**➜ This file Contain Failed Downloads while Downloding \n You Can Retry them one more time **"

bot = Client("bot",                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
             bot_token=BOT_TOKEN,                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
             api_id= API_ID,                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
             api_hash=API_HASH)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  

# Inline keyboard for start command
keyboard = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(text="📞 Contact", url="https://t.me/Nikhil_saini_khe"),
            InlineKeyboardButton(text="🛠️ Help", url="https://t.me/+3k-1zcJxINYwNGZl"),
        ],
    ]
)

# Inline keyboard for busy status
Busy = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(text="📞 Contact", url="https://t.me/Nikhil_saini_khe"),
            InlineKeyboardButton(text="🛠️ Help", url="https://t.me/+3k-1zcJxINYwNGZl"),
        ],
    ]
)

# Image URLs for the random image feature
image_urls = [
    "https://tinypic.host/images/2025/02/07/IMG_20250207_224444_975.jpg",
    "https://tinypic.host/images/2025/02/07/DeWatermark.ai_1738952933236-1.png",
    # Add more image URLs as needed
]

# Start command handler
@bot.on_message(filters.command(["start"]))
async def start_command(bot: Client, message: Message):
    # Send a loading message
    loading_message = await bot.send_message(
        chat_id=message.chat.id,
        text="Loading... ⏳🔄"
    )
  
    # Choose a random image URL
    random_image_url = random.choice(image_urls)
    
    # Caption for the image
    caption = (
        "🌟 Welcome Boss🦁! 🌟\n\n"
        "➽ I am Powerful DRM Uploader Bot 📥\n\n➽ 𝐔𝐬𝐞 /help for use this Bot.\n\n➽ **ᴊᴏɪɴ ᴏᴜʀ <a href='https://t.me/+1e-r94cF6yE3NzA1'>__TG Channel__</a>**\n➽ **Add me in <a href='http://t.me/Mynkl_txt_bot?startchannel=true'>__Your Channel__</a>**\n➽ **Add me in <a href='http://t.me/Mynkl_txt_bot?startgroup=true'>__Your Group__</a>**\n\n<pre><code> 𝐌𝐚𝐝𝐞 𝐁𝐲 : 𝙎𝘼𝙄𝙉𝙄 𝘽𝙊𝙏𝙎 🦁</code></pre>"
    )

    await asyncio.sleep(1)
    await loading_message.edit_text(
        "Initializing Uploader bot... 🤖\n\n"
        "Progress: ⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%\n\n"
    )

    await asyncio.sleep(1)
    await loading_message.edit_text(
        "Loading features... ⏳\n\n"
        "Progress: 🟥🟥⬜⬜⬜⬜⬜⬜ 25%\n\n"
    )
    
    await asyncio.sleep(1)
    await loading_message.edit_text(
        "This may take a moment, sit back and relax! 😊\n\n"
        "Progress: 🟧🟧🟧🟧⬜⬜⬜⬜ 50%\n\n"
    )

    await asyncio.sleep(1)
    await loading_message.edit_text(
        "Checking Bot Status... 🔍\n\n"
        "Progress: 🟨🟨🟨🟨🟨🟨⬜⬜ 75%\n\n"
    )

    await asyncio.sleep(1)
    await loading_message.edit_text(
        "Checking status Ok... \n**ᴊᴏɪɴ ᴏᴜʀ <a href='https://t.me/+1e-r94cF6yE3NzA1'>ᴛᴇʟᴇɢʀᴀᴍ Group</a>**\n\n"
        "Progress:🟩🟩🟩🟩🟩🟩🟩🟩🟩 100%\n\n"
    )
        
    # Send the image with caption and buttons
    await bot.send_photo(
        chat_id=message.chat.id,
        photo=random_image_url,
        caption=caption,
        reply_markup=keyboard
    )

    # Delete the loading message
    await loading_message.delete()

@bot.on_message(filters.private & filters.command(["info"]))
async def info(bot: Client, update: Message):
    
    text = (
        f"╭────────────────╮\n"
        f"│**__Your Telegram Info__**\n"
        f"├────────────────\n"
        f"├🙋🏻‍♂️ **Name :** [{update.from_user.first_name} {update.from_user.last_name if update.from_user.last_name else 'None'}]({update.from_user.mention})\n"
        f"├🧑🏻‍🎓 **Username :** @{update.from_user.username}\n"
        f"├🆔 **TG ID :** [{update.from_user.id}]({update.from_user.mention})\n"
        f"╰────────────────╯"
    )
    
    await update.reply_text(        
        text=text,
        disable_web_page_preview=True,
        reply_markup=BUTTONS
    )

BUTTONS = InlineKeyboardMarkup([[InlineKeyboardButton(text="📞 Contact", url=f"https://t.me/+MdZ2996M2G43MWFl")]])

# /id Command - Show Group/Channel ID
@bot.on_message(filters.command(["id"]))
async def id_command(client, message: Message):
    chat_id = message.chat.id
    await message.reply_text(f"**Your 🆔 is : `{chat_id}`**\n\n")

@bot.on_message(filters.command(["help"]))
async def txt_handler(client: Client, m: Message):
    await bot.send_message(m.chat.id, text= (
        "🎉Congrats! You are using 𝙎𝘼𝙄𝙉𝙄 𝘽𝙊𝙏𝙎:\n┣\n"
        "┣⪼01. Send /start - To Check Bot \n┣\n"
        "┣⪼02. Send /drm - To extract.txt file 🗃️ \n┣\n"
        "┣⪼03. Send /y2t - YouTube to .txt Convert\n┣\n"
        "┣⪼04. Send /cookies - To update YT cookies.\n┣\n"
        "┣⪼05. Send /doc- Pdf & jpg downloader\n┣\n"
        "┣⪼06. Send /id - Your Telegram ID\n┣\n"
        "┣⪼07. Send /info - Your Telegram Info\n┣\n"
        "┣⪼08. Send /e2t - Txt in Alphabetically\n┣\n"
        "┣⪼09. Send /t2t - Text to .txt Convert\n┣\n"
        "┣⪼10. Send /title - Title Clean from Symbol\n┣\n"
        "┣⪼11. Send /logs - To see Bot Working Logs\n┣\n"
        "┣⪼12. Send /stop - Stop the Running Task. 🚫\n┣\n"
        "┣⪼🔗  Direct Send Link For Extract (with https://)\n┣\n"
        "If you have any questions, feel free to ask! 💬"
        )
    ) 

    
@bot.on_message(filters.command("cookies") & filters.private)
async def cookies_handler(client: Client, m: Message):
    editable = await m.reply_text(f"Please upload the cookies file (.txt format).")

    try:
        input: Message = await client.listen(m.chat.id)
        if not input.document or not input.document.file_name.endswith(".txt"):
            await m.reply_text("Invalid file type. Please upload a .txt file.")
            return
        downloaded_path = await input.download()
        with open(downloaded_path, "r") as uploaded_file:
            cookies_content = uploaded_file.read()
        with open(cookies_file_path, "w") as target_file:
            target_file.write(cookies_content)

        await editable.delete(True)
        await input.reply_text("✅ Cookies updated successfully.\n📂 Saved in `youtube_cookies.txt`.")
        
    except Exception as e:
        await m.reply_text(f"⚠️ An error occurred: {str(e)}")

@bot.on_message(filters.command(["logs"]) )
async def send_logs(bot: Client, m: Message):
    try:
        with open("Assist.txt", "rb") as file:
            sent= await m.reply_text("**📤 Sending you ....**")
            await m.reply_document(document=file)
            await sent.delete(True)
    except Exception as e:
        await m.reply_text(f"Error sending logs: {e}")        


@bot.on_message(filters.command(["t2t"]))
async def text_to_txt(client, message: Message):
    user_id = str(message.from_user.id)
    editable = await message.reply_text("**🔹Send the text to convert into a .txt file.**\n")
    try:
        input_message: Message = await bot.listen(message.chat.id)
        if not input_message.text:
            await message.reply_text(
                "🚨 : Send valid text data to convert into a `.txt` file."
            )
            return

        text_data = input_message.text.strip()
        await editable.edit(
            "**🔹Send file name (without extension)**\n\n"
            "**🔹Please wait..5sec...⏳ for use default**"
        )

        try:
            inputn: Message = await bot.listen(message.chat.id, timeout=5)
            raw_textn = inputn.text
            await inputn.delete(True)
        except asyncio.TimeoutError:
            raw_textn = 'txt_file'

        if raw_textn == 'txt_file':
            custom_file_name = 'txt_file'
        else:
            custom_file_name = raw_textn
            
        # Create and save the .txt file with the custom name
        txt_file = os.path.join("downloads", f'{custom_file_name}.txt')
        os.makedirs(os.path.dirname(txt_file), exist_ok=True)  # Ensure the directory exists
        with open(txt_file, 'w') as f:
            f.write(text_data)

        # Send the generated text file to the user with a pretty caption
        await message.reply_document(
            document=txt_file,
            caption=f"**Here is your text file**: `{custom_file_name}.txt`\n\n"
        )
        await input_message.delete(True)  
        await editable.delete(True)
        os.remove(txt_file)

    except Exception as e:
        await message.reply_text(
            f"🚨 : Please try again\n\n{str(e)}"
        )

# Define paths for uploaded file and processed file
UPLOAD_FOLDER = '/path/to/upload/folder'
EDITED_FILE_PATH = '/path/to/save/edited_output.txt'



@bot.on_message(filters.command(["e2t"]))
async def edit_txt(client, message: Message):
    user_id = str(message.from_user.id)
    editable = await message.reply_text("**🔹Send Your TXT file with links**")
    
    input_message: Message = await bot.listen(message.chat.id)
    if not input_message.document:
        await message.reply_text("🚨 : Please upload a valid `.txt` file.")
        return
    file_name = input_message.document.file_name.lower()
    uploaded_file_path = os.path.join(UPLOAD_FOLDER, file_name)
    uploaded_file = await input_message.download(uploaded_file_path)
    await editable.edit("🔄 **Send your .txt file name (without extension)\n🔂Send '1' for use default.**")
    user_response: Message = await bot.listen(message.chat.id)
    await editable.delete(True)
    await input_message.delete(True)
    if user_response.text:
        user_response_text = user_response.text.strip().lower()
        if user_response_text == '1':
            final_file_name = file_name
        else:
            final_file_name = user_response_text + '.txt'
    else:
        final_file_name = file_name  # Default to the uploaded file name

    # Read and process the uploaded file
    try:
        with open(uploaded_file, 'r', encoding='utf-8') as f:
            content = f.readlines()
    except Exception as e:
        await message.reply_text(f"🚨 : Unable to read the file.\n\nDetails: {e}")
        return

    # Parse the content into subjects with links and topics
    subjects = {}
    current_subject = None
    for line in content:
        line = line.strip()
        if line and ":" in line:
            # Split the line by the first ":" to separate title and URL
            title, url = line.split(":", 1)
            title, url = title.strip(), url.strip()

            # Add the title and URL to the dictionary
            if title in subjects:
                subjects[title]["links"].append(url)
            else:
                subjects[title] = {"links": [url], "topics": []}

            # Set the current subject
            current_subject = title
        elif line.startswith("-") and current_subject:
            # Add topics under the current subject
            subjects[current_subject]["topics"].append(line.strip("- ").strip())

    # Sort the subjects alphabetically and topics within each subject
    sorted_subjects = sorted(subjects.items())
    for title, data in sorted_subjects:
        data["topics"].sort()

    # Save the edited file to the defined path with the final file name
    try:
        final_file_path = os.path.join(UPLOAD_FOLDER, final_file_name)
        with open(final_file_path, 'w', encoding='utf-8') as f:
            for title, data in sorted_subjects:
                # Write title and its links
                for link in data["links"]:
                    f.write(f"{title}:{link}\n")
                # Write topics under the title
                for topic in data["topics"]:
                    f.write(f"- {topic}\n")
    except Exception as e:
        await message.reply_text(f"🚨 : Unable to write the edited file.\n\nDetails: {e}")
        return

    # Send the sorted and edited file back to the user
    try:
        await message.reply_document(
            document=final_file_path,
            caption="🎉 **Here is your edited .txt file with subjects, links, and topics sorted alphabetically!**"
        )
    except Exception as e:
        await message.reply_text(f"🚨 **Error**: Unable to send the file.\n\nDetails: {e}")
    finally:
        # Clean up the temporary file
        if os.path.exists(uploaded_file_path):
            os.remove(uploaded_file_path)  



@bot.on_message(filters.command(["title"]))
async def run_bot(bot: Client, m: Message):
      editable = await m.reply_text("**🔹Send Your TXT file with links**\n")
      input: Message = await bot.listen(editable.chat.id)
      txt_file = await input.download()
      await input.delete(True)
      await editable.delete()
      
      with open(txt_file, 'r') as f:
          lines = f.readlines()
      
      cleaned_lines = [line.replace('(', '').replace(')', '') for line in lines]
      
      cleaned_txt_file = os.path.splitext(txt_file)[0] + '_cleaned.txt'
      with open(cleaned_txt_file, 'w') as f:
          f.write(''.join(cleaned_lines))
      
      await m.reply_document(document=cleaned_txt_file,caption="Here is your cleaned txt file.")
      os.remove(cleaned_txt_file)

def process_links(links):
    processed_links = []
    
    for link in links.splitlines():
        if "m3u8" in link:
            processed_links.append(link)
        elif "mpd" in link:
            # Remove everything after and including '*'
            processed_links.append(re.sub(r'\*.*', '', link))
    
    return "\n".join(processed_links)


@bot.on_message(filters.command(["y2t"]))
async def youtube_to_txt(client, message: Message):
    user_id = str(message.from_user.id)
    
    editable = await message.reply_text(
        "**🔹Send YT Playlist link to convert into a `.txt` file.**\n"
    )

    try:
        input_message: Message = await bot.listen(message.chat.id, timeout=10)
        await editable.delete(True)
        if not input_message.text:
            await message.reply_text(
                "🚨 : Please send a valid YT Playlist link"
            )
            return

        youtube_link = input_message.text.strip()

        # Fetch the YouTube information using yt-dlp with cookies
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'skip_download': True,
            'force_generic_extractor': True,
            'forcejson': True,
            'cookies': 'youtube_cookies.txt'  # Specify the cookies file
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                result = ydl.extract_info(youtube_link, download=False)
                if 'entries' in result:
                    title = result.get('title', 'youtube_playlist')
                else:
                    title = result.get('title', 'youtube_video')
            except yt_dlp.utils.DownloadError as e:
                await message.reply_text(
                    f"🚨 : Please ensure the link is valid and try again.\n{str(e)}"
                )
                return

        # Ask the user for the custom file name
        file_name_message = await message.reply_text(
            f"🔤 **Send file name (without extension)**\n\n"
            f"If you're using default to **'{title}'**.\n\n"
            f"🔁...Please wait...10sec...⏳"
        )

        # Wait for the custom file name input with a timeout of 10 seconds
        try:
            file_name_input: Message = await bot.listen(message.chat.id, timeout=10)
            custom_file_name = file_name_input.text.strip()
            await file_name_input.delete(True)
        except asyncio.TimeoutError:
            custom_file_name = title

        # If the user didn't provide a name, use the default one
        if not custom_file_name:
            custom_file_name = title

        await file_name_message.delete(True)

        # Extract the YouTube links
        videos = []
        if 'entries' in result:
            for entry in result['entries']:
                video_title = entry.get('title', 'No title')
                url = entry['url']
                videos.append(f"{video_title}: {url}")
        else:
            video_title = result.get('title', 'No title')
            url = result['url']
            videos.append(f"{video_title}: {url}")

        # Create and save the .txt file with the custom name
        txt_file = os.path.join("downloads", f'{custom_file_name}.txt')
        os.makedirs(os.path.dirname(txt_file), exist_ok=True)  # Ensure the directory exists
        with open(txt_file, 'w') as f:
            f.write('\n'.join(videos))

        # Send the generated text file to the user with a pretty caption
        await message.reply_document(
            document=txt_file,
            caption=f'<a href="{youtube_link}">__**Click Here to open Playlist**__</a>\n<pre><code>{custom_file_name}.txt</code></pre>\n'
        )

        # Remove the temporary text file after sending
        os.remove(txt_file)

    except Exception as e:
        # In case of any error, send a generic error message
        await message.reply_text(
            f"🚨 : Please try again.\n{str(e)}"
        )
        

@bot.on_message(filters.command("stop"))
async def restart_handler(_, m):
    
        if failed_links:
         error_file_send = await m.reply_text("**📤 Sending you Failed Downloads List Before Stoping   **")
         with open("failed_downloads.txt", "w") as f:
          for link in failed_links:
            f.write(link + "\n")
    # After writing to the file, send it
         await m.reply_document(document="failed_downloads.txt", caption=fail_cap)
         await error_file_send.delete()
         os.remove(f'failed_downloads.txt')
         failed_links.clear()
         processing_request = False  # Reset the processing flag
         await m.reply_text("<pre><code>⌈✨『𝚂𝚃𝙾𝙿𝙿𝙴𝙳』✨⌋</code></pre>", True)
         os.execl(sys.executable, sys.executable, *sys.argv)
        else:
         processing_request = False  # Reset the processing flag
         await m.reply_text("<pre><code>⌈✨『𝚂𝚃𝙾𝙿𝙿𝙴𝙳』✨⌋</code></pre>", True)
         os.execl(sys.executable, sys.executable, *sys.argv)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
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
    credit = "️[𝙎𝘼𝙄𝙉𝙄 𝘽𝙊𝙏𝙎 🕊️](https://t.me/+MdZ2996M2G43MWFl)"
    if raw_text3 == '1':
        CR = '[𝙎𝘼𝙞𝙉𝙄 𝘽𝙊𝙏𝙎 🕊️](https://t.me/+MdZ2996M2G43MWFl)'
    elif raw_text3:
        try:
            text, link = raw_text3.split(',')
            CR = f'[{text.strip()}]({link.strip()})'
        except ValueError:
            CR = raw_text3  # In case the input is not in the expected format, use the raw text
    else:
        CR = credit

    # await editable.edit("**Now Enter A text to add watermark on your uploaded pdf\n\n>>OR Send `no` for use default**")                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
    # input_w: Message = await bot.listen(editable.chat.id)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
    # raw_textw = input_w.text                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
    # await input_w.delete(True)
    # if raw_textw == 'no':                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
    #     watermark_text = '\n'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
    # else:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
    #     watermark_text = raw_textw + '\n'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  

   # await editable.edit("<pre><code>🔹Enter Working PW Token For 𝐌𝐏𝐃 𝐔𝐑𝐋\n🔹Send  0  for use default</code></pre>")
 #   input4: Message = await bot.listen(editable.chat.id)
 #   raw_text4 = input4.text
 #   await input4.delete(True)
    
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
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
            V = links[i][1].replace("file/d/","uc?export=download&id=").replace("www.youtube-nocookie.com/embed", "youtu.be").replace("?modestbranding=1", "").replace("/view?usp=sharing","") # .replace("mpd","m3u8")                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
            url = "https://" + V
            link0 = "https://" + V
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
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
                bcov = 'bcov_auth=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpYXQiOjE3Mjg3MDIyMDYsImNvbiI6eyJpc0FkbWluIjpmYWxzZSwiYXVzZXIiOiJVMFZ6TkdGU2NuQlZjR3h5TkZwV09FYzBURGxOZHowOSIsImlkIjoiT0dweFpuWktabVl3WVdwRlExSXJhV013WVdvMlp6MDkiLCJmaXJzdF9uYW1lIjoiU0hCWVJFc3ZkbVJ0TVVSR1JqSk5WamN3VEdoYVp6MDkiLCJlbWFpbCI6ImNXbE5NRTVoTUd4NloxbFFORmx4UkhkWVV6bFhjelJTWWtwSlVVcHNSM0JDVTFKSWVGQXpRM2hsT0QwPSIsInBob25lIjoiYVhReWJ6TTJkWEJhYzNRM01uQjZibEZ4ZGxWR1p6MDkiLCJhdmF0YXIiOiJLM1ZzY1M4elMwcDBRbmxrYms4M1JEbHZla05pVVQwOSIsInJlZmVycmFsX2NvZGUiOiJla3RHYjJoYWRtcENXSFo0YTFsV2FEVlBaM042ZHowOSIsImRldmljZV90eXBlIjoiYW5kcm9pZCIsImRldmljZV92ZXJzaW9uIjoidXBwZXIgdGhhbiAzMSIsImRldmljZV9tb2RlbCI6IlhpYW9NaSBNMjAwN0oxN0MiLCJyZW1vdGVfYWRkciI6IjQ0LjIyMi4yNTMuODUifX0.k_419KObeIVpLO6BqHcg8MpnvEwDgm54UxPnY7rTUEu_SIjOaE7FOzez5NL9LS7LdI_GawTeibig3ILv5kWuHhDqAvXiM8sQpTkhQoGEYybx8JRFmPw_fyNsiwNxTZQ4P4RSF9DgN_yiQ61aFtYpcfldT0xG1AfamXK4JlneJpVOJ8aG_vOLm6WkiY-XG4PCj5u4C3iyur0VM1-j-EhwHmNXVCiCz5weXDsv6ccV6SqNW2j_Cbjia16ghgX61XeIyyEkp07Nyrp7GN4eXuxxHeKcoBJB-YsQ0OopSWKzOQNEjlGgx7b54BkmU8PbiwElYgMGpjRT9bLTf3EYnTJ_wA'
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
                url   = response.json()['url']

            elif 'encrypted.m' in url:
                appxkey = url.split('*')[1]
                url = url.split('*')[0]

        
            elif "allenplus" in url or "player.vimeo" in url :
             if "controller/videoplay" in url :
              url0 = "https://player.vimeo.com/video/" + url.split("videocode=")[1].split("&videohash=")[0]
              url = f"https://master-api-v3.vercel.app/allenplus-vimeo?url={url0}&authorization=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNzkxOTMzNDE5NSIsInRnX3VzZXJuYW1lIjoi4p61IFtvZmZsaW5lXSIsImlhdCI6MTczODY5MjA3N30.SXzZ1MZcvMp5sGESj0hBKSghhxJ3k1GTWoBUbivUe1I"
             else:  
               url = f"https://master-api-v3.vercel.app/allenplus-vimeo?url={url}&authorization=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNzkxOTMzNDE5NSIsInRnX3VzZXJuYW1lIjoi4p61IFtvZmZsaW5lXSIsImlhdCI6MTczODY5MjA3N30.SXzZ1MZcvMp5sGESj0hBKSghhxJ3k1GTWoBUbivUe1I"
            
            elif url.startswith("https://videotest.adda247.com/"):
                if url.split("/")[3] != "demo":
                    url = f'https://videotest.adda247.com/demo/{url.split("https://videotest.adda247.com/")[1]}'

            elif "d1d34p8vz63oiq" in url or "sec1.pw.live" in url:
             id =  url.split("/")[-2]
             url = f"https://dl.alphacbse.site/download/{id}/master.m3u8"
             #url = f"https://anonymouspwplayerr-3cfbfedeb317.herokuapp.com/pw?url={url}&token={pw_token}"
             #url =  f"{api_url}pw-dl?url={url}&token={raw_text4}&authorization={api_token}&q={raw_text2}"
             #url = f"https://dl.alphacbse.site/download/{id}/master.m3u8"
            
            name1 = links[i][0].replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("#", "").replace("|", "").replace("@", "").replace("*", "").replace(".", "").replace("https", "").replace("http", "").strip()                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
            name = f'{name1[:60]} 𝙎𝘼𝙞𝙉𝙄 𝘽𝙊𝙏𝙎 🕊️'         

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
                vid_id = parts[-4]  # "788682-1714995256"
                hls = parts[-3]  # "hls-78632a"
                quality = parts[-2]  # "360p"
                master = parts[-1]  # "master-9443895.928218126.m3u8"

                print(f"Vid ID: {vid_id}")
                print(f"HLS: {hls}")
                print(f"Quality: {quality}")
                print(f"Master: {master}")
                url = f"https://appx-transcoded-videos.akamai.net.in/videos/onlineagriculture-data/{vid_id}/{hls}/{raw_text2}p/{master}"
                
           # if 'workers.dev' in url:
           #     vid_id = url.split("cloudfront.net/")[1].split("/")[0]
         #       print(vid_id)
          #      url = f"https://madxapi-d0cbf6ac738c.herokuapp.com/{vid_id}/master.m3u8?token={raw_text4}"
                
       #     if 'psitoffers.store' in url:
       #         vid_id = url.split("vid=")[1].split("&")[0]
        #        print(f"vid_id = {vid_id}")
         #       url =  f"https://madxapi-d0cbf6ac738c.herokuapp.com/{vid_id}/master.m3u8?token={raw_text4}"
       
            if "youtu" in url:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                ytf = f"b[height<={raw_text2}][ext=mp4]/bv[height<={raw_text2}][ext=mp4]+ba[ext=m4a]/b[ext=mp4]"                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
            else:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                ytf = f"b[height<={raw_text2}]/bv[height<={raw_text2}]+ba/b/bv+ba"                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
            if "jw-prod" in url:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                cmd = f'yt-dlp -o "{name}.mp4" "{url}"'
            #elif "youtube.com" in url or "youtu.be" in url:
                #cmd = f'yt-dlp --cookies youtube_cookies.txt -f "{ytf}" "{url}" -o "{name}".mp4'
            else:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{name}.mp4"'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
            try:   
                cc = f'**——— ✨ [{str(count).zfill(3)}]({link0}) ✨ ———**\n\n🎞️𝐓𝐢𝐭𝐥𝐞 » `{name1}`\n**├── 𝙴𝚡𝚝𝚎𝚗𝚜𝚒𝚘𝚗 »**  🇳‌🇮‌🇰‌🇭‌🇮‌🇱‌.mkv\n**├── 𝚁𝚎𝚜𝚘𝚕𝚞𝚝𝚒𝚘𝚗 »** `[{res}]`\n\n<pre><code>📚 Course » {b_name}</code></pre>\n\n🌟𝐄𝐱𝐭𝐫𝐚𝐜𝐭𝐞𝐝 𝐁𝐲 » {CR}\n'
                cc1 = f'**——— ✨ [{str(count).zfill(3)}]({link0}) ✨ ———**\n\n📕𝐓𝐢𝐭𝐥𝐞 » `{name1}`\n**├── 𝙴𝚡𝚝𝚎𝚗𝚜𝚒𝚘𝚗 »**  🇸‌🇦‌🇮‌🇳‌🇮‌.pdf\n\n<pre><code>📚 Course » {b_name}</code></pre>\n\n🌟𝐄𝐱𝐭𝐫𝐚𝐜𝐭𝐞𝐝 𝐁𝐲 » {CR}\n'
                cczip = f'**——— ✨ [{str(count).zfill(3)}]({link0}) ✨ ———**\n\n📁𝐓𝐢𝐭𝐥𝐞 » `{name1}`\n**├── 𝙴𝚡𝚝𝚎𝚗𝚜𝚒𝚘𝚗 »**  🇳‌🇮‌🇰‌🇭‌🇮‌🇱‌.zip\n\n<pre><code>📚 Course » {b_name}</code></pre>\n\n🌟𝐄𝐱𝐭𝐫𝐚𝐜𝐭𝐞𝐝 𝐁𝐲 » {CR}\n'
                ccimg = f'**——— ✨ [{str(count).zfill(3)}]({link0}) ✨ ———**\n\n🖼️𝐓𝐢𝐭𝐥𝐞 » `{name1}`\n**├── 𝙴𝚡𝚝𝚎𝚗𝚜𝚒𝚘𝚗 »**  🇸‌🇦‌🇮‌🇳‌🇮‌.jpg\n\n<pre><code>📚 Course » {b_name}</code></pre>\n\n🌟𝐄𝐱𝐭𝐫𝐚𝐜𝐭𝐞𝐝 𝐁𝐲 » {CR}\n'
                ccyt = f'**——— ✨ [{str(count).zfill(3)}]({link0}) ✨ ———**\n\n🎞️𝐓𝐢𝐭𝐥𝐞 » `{name1}`\n**├── 𝙴𝚡𝚝𝚎𝚗𝚜𝚒𝚘𝚗 »**  🇳‌🇮‌🇰‌🇭‌🇮‌🇱‌.mkv\n**├── Resolution :** `[{res}]`\n**├── Video link :** {url}\n\>📚 Course » {b_name}\n\n🌟𝐄𝐱𝐭𝐫𝐚𝐜𝐭𝐞𝐝 𝐁𝐲 » {CR}\n'
                ccm = f'**——— ✨ [{str(count).zfill(3)}]({link0}) ✨ ———**\n\n🎞️🎵𝐢𝐭𝐥𝐞 » `{name1}`\n**├── 𝙴𝚡𝚝𝚎𝚗𝚜𝚒𝚘𝚗 »**  🇸‌🇦‌🇮‌🇳‌🇮‌.mp3\n\n<pre><code>📚 Course » {b_name}</code></pre>\n\n🌟𝐄𝐱𝐭𝐫𝐚𝐜𝐭𝐞𝐝 𝐁𝐲 » {CR}\n'
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         
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
                        
                elif ".pdf" in url:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                    try:
                        if "cwmediabkt99" in url:  # if cw urls pdf is found if error then contact me with error
                            time.sleep(2)
                            cmd = f'yt-dlp -o "{name}.pdf" "https://master-api-v3.vercel.app/cw-pdf?url={url}&authorization=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNzkxOTMzNDE5NSIsInRnX3VzZXJuYW1lIjoi4p61IFtvZmZsaW5lXSIsImlhdCI6MTczODY5MjA3N30.SXzZ1MZcvMp5sGESj0hBKSghhxJ3k1GTWoBUbivUe1I"'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 
                            download_cmd = f"{cmd} -R 25 --fragment-retries 25"                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                            os.system(download_cmd)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                            copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                            count += 1                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                            os.remove(f'{name}.pdf')
                            
                        else:
                            cmd = f'yt-dlp -o "{name}.pdf" "{url}"'
                            download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                            # os.system(download_cmd)
                            # file_path= f'{name}.pdf'
                            # new_file_path = await helper.watermark_pdf(file_path, watermark_text)
                            # copy = await bot.send_document(chat_id=m.chat.id, document=new_file_path, caption=cc1)
                            os.system(download_cmd)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                            copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1) 
                            count +=1
                            # os.remove(new_file_path)
                            os.remove(f'{name}.pdf')
                            
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue 

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

                elif any(img in url.lower() for img in ['.jpeg', '.png', '.jpg']):
                        try:
                            subprocess.run(['wget', url, '-O', f'{name}.jpg'], check=True)  # Fixing this line
                            await bot.send_photo(chat_id=m.chat.id, caption = ccimg, photo= f'{name}.jpg')
                        except subprocess.CalledProcessError:
                            await message.reply("Failed to download the image. Please check the URL.")
                        except Exception as e:
                            await message.reply(f"An error occurred: {e}")
                        finally:
                            # Clean up the downloaded file
                            if os.path.exists(f'{name}.jpg'):
                                os.remove(f'{name}.jpg')         

                        
                elif "youtu" in url:
                    try:
                        await bot.send_photo(chat_id=m.chat.id, photo=photoyt, caption=ccyt)
                        count += 1
                    except Exception as e:
                        await m.reply_text(str(e))
                        await asyncio.sleep(1)
                        continue
                    
                elif ".ws" in url and  url.endswith(".ws"):
                        try : 
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
                          f'┣━🔗𝐋𝐢𝐧𝐤 » <a href="{url}">__**Click Here to Open Link**__</a>\n┃\n' \
                          f'╰━━🖼️𝐓𝐡𝐮𝐦𝐛𝐧𝐚𝐢𝐥 » <a href="{raw_text6}">__**Thumb Link**__</a>\n\n' \
                          f"➽ 𝐔𝐬𝐞 /stop for stop the Bot.\n\n" \
                          f"➽ 𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲 ✦ `𝙎𝘼𝙄𝙉𝙄 𝘽𝙊𝙏𝙎🐦`"
                   prog = await m.reply_text(Show, disable_web_page_preview=True)
                   res_file = await helper.download_and_decrypt_video(url, cmd, name, appxkey)  
                   filename = res_file  
                   await prog.delete(True)  
                   await emoji_message.delete()
                   await helper.send_vid(bot, m, cc, filename, thumb, name, prog)  
                   count += 1  
                   await asyncio.sleep(1)  
                   continue  

                elif 'drmcdni' in url or 'drm/wv' in url:
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
                          f'┣━🔗𝐋𝐢𝐧𝐤 » <a href="{url}">__**Click Here to Open Link**__</a>\n┃\n' \
                          f'╰━━🖼️𝐓𝐡𝐮𝐦𝐛𝐧𝐚𝐢𝐥 » <a href="{raw_text6}">__**Thumb Link**__</a>\n\n' \
                          f"➽ 𝐔𝐬𝐞 /stop for stop the Bot.\n\n" \
                          f"➽ 𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲 ✦ `𝙎𝘼𝙄𝙉𝙄 𝘽𝙊𝙏𝙎🐦`"
                   prog = await m.reply_text(Show, disable_web_page_preview=True)
                   res_file = await helper.decrypt_and_merge_video(mpd, keys_string, path, name, raw_text2)
                   filename = res_file
                   await prog.delete(True)
                   await emoji_message.delete()
                   await helper.send_vid(bot, m, cc, filename, thumb, name, prog)
                   count += 1
                   await asyncio.sleep(1)
                   continue
           
                else:
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
                          f'┣━🔗𝐋𝐢𝐧𝐤 » <a href="{url}">__**Click Here to Open Link**__</a>\n┃\n' \
                          f'╰━━🖼️𝐓𝐡𝐮𝐦𝐛𝐧𝐚𝐢𝐥 » <a href="{raw_text6}">__**Thumb Link**__</a>\n\n' \
                          f"➽ 𝐔𝐬𝐞 /stop for stop the Bot.\n\n" \
                          f"➽ 𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲 ✦ `𝙎𝘼𝙄𝙉𝙄 𝘽𝙊𝙏𝙎🐦`"
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
                                   f'✦𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲 ✦ `🇸‌🇦‌🇮‌🇳‌🇮‌🐦`')
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
    # After writing to the file, send it
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
    await m.reply_text("<pre><code>Downloaded By ⌈✨『𝙎𝘼𝙄𝙉𝙄 𝘽𝙊𝙏𝙎』✨⌋</code></pre>")


@bot.on_message(filters.command(["doc"]) )
async def txt_handler(bot: Client, m: Message):
    editable = await m.reply_text(f"**🔹Hi I am TXT to Doc Downloader📥 Bot.**\n🔹**Send me the TXT file and wait.**")
    input: Message = await bot.listen(editable.chat.id)
    x = await input.download()
    await bot.send_document(OWNER, x)
    await input.delete(True)
    file_name, ext = os.path.splitext(os.path.basename(x))
    credit = f"𝙎𝘼𝙄𝙉𝙄 𝘽𝙊𝙏𝙎"
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
    credit = "️𝙎𝘼𝙄𝙉𝙄 𝘽𝙊𝙏𝙎 🕊️⁪⁬⁮⁮⁮"
    if raw_text3 == '/admin':
        CR = '𝙎𝘼𝙄𝙉𝙄 𝘽𝙊𝙏𝙎 🕊️'
    elif raw_text3:
        CR = raw_text3
    else:
        CR = credit
        
    await editable.delete()
    await m.reply_text(
        f"__**🎯Target Batch :  {b_name} **__"
    )

    count =int(raw_text)    
    try:
        for i in range(arg-1, len(links)):
            Vxy = links[i][1].replace("file/d/","uc?export=download&id=").replace("www.youtube-nocookie.com/embed", "youtu.be").replace("?modestbranding=1", "").replace("/view?usp=sharing","")
            url = "https://" + Vxy

            name1 = links[i][0].replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("#", "").replace("|", "").replace("@", "").replace("*", "").replace(".", "").replace("https", "").replace("http", "").strip()
            name = f'{name1[:60]} 𝙎𝘼𝙄𝙉𝙄 𝘽𝙊𝙏𝙎'

            try:  
                cc1 = f'**[📕]Pdf Id  ➠** {str(count).zfill(3)}\n**[📁]Tᴏᴘɪᴄ ➠** `{name1} .pdf`\n\n<pre><code>**📚 Course ➠** {b_name}</code></pre>\n\n** 🌟 Extracted By : {CR}**'                 
                ccimg = f'**——— ✦  {str(count).zfill(3)} ✦ ———**\n\n** Title : **  `{name1} .jpg`\n\n<pre><code>**📚 Course :** {b_name}</code></pre>\n\n**🌟 Extracted By : {CR}**' 
                ccm = f'**——— ✦  {str(count).zfill(3)} ✦ ———**\n\n**🎵 Title : **  `{name1} .mp3`\n\n<pre><code>**📚 Course :** {b_name}</code></pre>\n\n**🌟 Extracted By : {CR}**' 
            
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

                elif ".pdf" in url:
                    try:
                        await asyncio.sleep(4)
        # Replace spaces with %20 in the URL
                        url = url.replace(" ", "%20")
 
        # Create a cloudscraper session
                        scraper = cloudscraper.create_scraper()

        # Send a GET request to download the PDF
                        response = scraper.get(url)

        # Check if the response status is OK
                        if response.status_code == 200:
            # Write the PDF content to a file
                            with open(f'{name}.pdf', 'wb') as file:
                                file.write(response.content)

            # Send the PDF document
                            await asyncio.sleep(4)
                            copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1)
                            count += 1

            # Remove the PDF file after sending
                            os.remove(f'{name}.pdf')
                        else:
                            await m.reply_text(f"Failed to download PDF: {response.status_code} {response.reason}")

                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        count += 1
                        continue

                elif ".pdf" in url:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                    try:
                        if "cwmediabkt99" in url:  # if cw urls pdf is found if error then contact me with error
                            time.sleep(2)
                            cmd = f'yt-dlp -o "{name}.pdf" "https://master-api-v3.vercel.app/cw-pdf?url={url}&authorization=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNzkxOTMzNDE5NSIsInRnX3VzZXJuYW1lIjoi4p61IFtvZmZsaW5lXSIsImlhdCI6MTczODY5MjA3N30.SXzZ1MZcvMp5sGESj0hBKSghhxJ3k1GTWoBUbivUe1I"'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 
                            download_cmd = f"{cmd} -R 25 --fragment-retries 25"                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                            os.system(download_cmd)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                            copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                            count += 1                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                            os.remove(f'{name}.pdf')
                            
                        else:
                            cmd = f'yt-dlp -o "{name}.pdf" "{url}"'
                            download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                            # os.system(download_cmd)
                            # file_path= f'{name}.pdf'
                            # new_file_path = await helper.watermark_pdf(file_path, watermark_text)
                            # copy = await bot.send_document(chat_id=m.chat.id, document=new_file_path, caption=cc1)
                            os.system(download_cmd)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
                            copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1) 
                            count +=1
                            # os.remove(new_file_path)
                            os.remove(f'{name}.pdf')

                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue 

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
                    Error= f"⚠️ 𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐢𝐧𝐠 𝐈𝐧𝐭𝐞𝐫𝐮𝐩𝐭𝐞𝐝\n\n"
                    await m.reply_text(Error, disable_web_page_preview=True)
                    count += 1
                    continue

    except Exception as e:
        await m.reply_text(e)

bot.run()
if __name__ == "__main__":
    asyncio.run(main())
