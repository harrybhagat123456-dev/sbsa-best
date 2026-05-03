import os, re, sys, json, pytz, asyncio, requests, subprocess, random
from pyrogram import Client, filters
from pyrogram.errors.exceptions.bad_request_400 import StickerEmojiInvalid
from pyrogram.types.messages_and_media import message
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, InputMediaPhoto
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
import globals
from render_manager import register_render_manager_handlers
from logs import logging
from html_handler import register_html_handlers
from drm_handler import register_drm_handlers
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
from auto_topic_creator import register_auto_topic_handlers
from vars import API_ID, API_HASH, BOT_TOKEN, OWNER, CREDIT, AUTH_USERS, TOTAL_USERS, cookies_file_path
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,

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
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text="Send to Owner", url=f"tg://openmessage?user_id={OWNER}")]])
    chat_id = message.chat.id
    text = f"<blockquote expandable><b>The ID of this chat id is:</b></blockquote>\n`{chat_id}`"
    
    if str(chat_id).startswith("-100"):
        await message.reply_text(text)
    else:
        await message.reply_text(text, reply_markup=keyboard)

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
async def send_logs(client: Client, m: Message):  # Correct parameter name
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
register_drm_handlers(bot)
register_topic_handlers(bot)
register_mini_handlers(bot)
register_render_manager_handlers(bot)
register_auto_topic_handlers(bot)
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
        {"command": "start",          "description": "✅ Check Alive the Bot"},
        {"command": "help",           "description": "📖 Full command reference"},
        {"command": "stop",           "description": "🚫 Stop the ongoing process"},
        {"command": "id",             "description": "🆔 Get Your ID"},
        {"command": "info",           "description": "ℹ️ Check Your Information"},
        {"command": "cookies",        "description": "📁 Upload YT Cookies"},
        {"command": "getcookies",     "description": "🍪 Show current cookies file"},
        {"command": "ytcookies",      "description": "🔐 Paste or upload YouTube cookies"},
        {"command": "ytcookie",       "description": "🔐 YouTube cookies shortcut"},
        {"command": "y2t",            "description": "🔪 YouTube to TXT converter"},
        {"command": "ytm",            "description": "🎶 YouTube to MP3 downloader"},
        {"command": "t2t",            "description": "📟 Text to TXT generator"},
        {"command": "t2h",            "description": "🌐 TXT to HTML converter"},
        {"command": "json",           "description": "🔄 JSON to TXT link converter"},
        {"command": "logs",           "description": "👁️ View Bot Activity"},
        {"command": "storage",        "description": "💾 Check disk & downloads storage"},
        {"command": "cleanup",        "description": "🗑️ Delete downloaded files now"},
        {"command": "history",        "description": "📥 TXT batch downloader with resume"},
        {"command": "yth",            "description": "🎶 YouTube MP3 with resume"},
        {"command": "viewhistory",    "description": "📜 View Download History"},
        {"command": "clearhistory",   "description": "🗑️ Clear Download History"},
        {"command": "mini",           "description": "📅 Browse uploaded content by date"},
        {"command": "topicnav",       "description": "📚 Repost uploaded topic navigation"},
        {"command": "createtopic",    "description": "🧵 Create a forum topic"},
        {"command": "maketopics",     "description": "🧵 Bulk-create forum topics from TXT file"},
        {"command": "topics",         "description": "📚 List forum topics"},
        {"command": "settopic",       "description": "📌 Set active topic"},
        {"command": "setuptopics",    "description": "⚙️ Setup topic routing"},
        {"command": "parsetxt",       "description": "🔍 Parse TXT topics"},
        {"command": "defaulttopic",   "description": "📍 Set default topic"},
        {"command": "parsetopics",    "description": "🔍 Preview Topics in TXT File"},
        {"command": "topicid",        "description": "📌 Get Topic ID (any group)"},
        {"command": "gettopicid",     "description": "💾 Save topic(s) to memory"},
        {"command": "linktopics",     "description": "🔗 Match saved topics with txt file"},
        {"command": "showtopics",     "description": "📊 Show all saved topics"},
        {"command": "showmapping",    "description": "🗺️ Show topic mapping for a channel"},
        {"command": "clearmemory",    "description": "🗑️ Clear saved topic memory"},
        {"command": "cleartopicmap",  "description": "🗑️ Wipe txt→topic mapping for a group"},
        {"command": "fixmapping",     "description": "🔧 Fix subtopic IDs to parent"},
        {"command": "addaccount",     "description": "➕ Add a new Render account slot"},
        {"command": "listaccounts",   "description": "📋 List all registered Render accounts"},
        {"command": "removeaccount",  "description": "🗑️ Remove a Render account slot"},
        {"command": "switchslot",     "description": "🔄 Switch active Render account slot"},
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
