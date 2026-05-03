import os
import re
import sys
import json
import time
import shutil
from vars import CREDIT, OWNER, AUTH_USERS
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, PeerIdInvalid, UserIsBlocked, InputUserDeactivated
from pyrogram.errors.exceptions.bad_request_400 import StickerEmojiInvalid
from pyrogram.types.messages_and_media import message
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Message

DOWNLOAD_FOLDERS = [
    os.path.join(os.path.dirname(__file__), "..", "downloads"),
    os.path.join(os.path.dirname(__file__), "downloads"),
]
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,

# commands button
def register_commands_handlers(bot):
    # .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
    @bot.on_callback_query(filters.regex("cmd_command"))
    async def cmd(client, callback_query):
        user_id = callback_query.from_user.id
        first_name = callback_query.from_user.first_name
        caption = (
            f"🌟  **Welcome** [{first_name}](tg://user?id={user_id})! 🌟\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            f"**🔘 Tap a button for Commands**\n"
            f"<blockquote><b>🕵 Users | 👑 Owner</b></blockquote>\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            f"🚀 Let’s start powerful features!"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🕵 Users", callback_data="user_command"), InlineKeyboardButton("👑 Owner", callback_data="owner_command")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main_menu")]
        ])
        await callback_query.message.edit_media(
        InputMediaPhoto(
          media="https://tinypic.host/images/2025/07/14/file_00000000fc2461fbbdd6bc500cecbff8_conversation_id6874702c-9760-800e-b0bf-8e0bcf8a3833message_id964012ce-7ef5-4ad4-88e0-1c41ed240c03-1-1.jpg",
          caption=caption
        ),
        reply_markup=keyboard
        )
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
    @bot.on_callback_query(filters.regex("user_command"))
    async def help_button(client, callback_query):
      user_id = callback_query.from_user.id
      first_name = callback_query.from_user.first_name
      keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Commands", callback_data="cmd_command")]])
      caption = (
            f"💥 𝐁𝐎𝐓𝐒 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n" 
            f"📌 𝗠𝗮𝗶𝗻 𝗙𝗲𝗮𝘁𝘂𝗿𝗲𝘀:\n"  
            f"➥ /start – Bot Status Check\n"
            f"➥ /y2t – YouTube → .txt Converter\n"  
            f"➥ /ytm – YouTube → .mp3 downloader\n"  
            f"➥ /t2t – Text → .txt Generator\n"
            f"➥ /t2h – .txt → .html Converter\n" 
            f"➥ /stop – Cancel Running Task\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰ \n\n" 
            f"⚙️ 𝗧𝗼𝗼𝗹𝘀 & 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀:\n" 
            f"➥ /cookies – Update YT Cookies\n" 
            f"➥ /id – Get Chat/User ID\n"  
            f"➥ /info – User Details\n"  
            f"➥ /logs – View Bot Activity\n"
            f"➥ /storage – Check Storage Usage\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
            f"💡 𝗡𝗼𝘁𝗲:\n"  
            f"• Send any link for auto-extraction\n"
            f"• Send direct .txt file for auto-extraction\n"
            f"• Supports batch processing\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
            f"╭────────⊰◆⊱────────╮\n"   
            f" ➠ 𝐌𝐚𝐝𝐞 𝐁𝐲 : {CREDIT} 💻\n"
            f"╰────────⊰◆⊱────────╯\n"
      )
    
      await callback_query.message.edit_media(
        InputMediaPhoto(
          media="https://tinypic.host/images/2025/07/14/file_00000000fc2461fbbdd6bc500cecbff8_conversation_id6874702c-9760-800e-b0bf-8e0bcf8a3833message_id964012ce-7ef5-4ad4-88e0-1c41ed240c03-1-1.jpg",
          caption=caption
        ),
        reply_markup=keyboard
        )
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
    @bot.on_callback_query(filters.regex("owner_command"))
    async def help_button(client, callback_query):
      user_id = callback_query.from_user.id
      first_name = callback_query.from_user.first_name
      keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Commands", callback_data="cmd_command")]])
      caption = (
            f"👤 𝐁𝐨𝐭 𝐎𝐰𝐧𝐞𝐫 𝐂𝐨𝐦𝐦𝐚𝐧𝐝𝐬\n\n" 
            f"➥ /addauth xxxx – Add User ID\n" 
            f"➥ /rmauth xxxx – Remove User ID\n"  
            f"➥ /users – Total User List\n"  
            f"➥ /broadcast – For Broadcasting\n"  
            f"➥ /broadusers – All Broadcasting Users\n"  
            f"➥ /reset – Reset Bot\n"
            f"➥ /cleanup – Clear Downloads Now\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"  
            f"╭────────⊰◆⊱────────╮\n"   
            f" ➠ 𝐌𝐚𝐝𝐞 𝐁𝐲 : {CREDIT} 💻\n"
            f"╰────────⊰◆⊱────────╯\n"
      )
    
      await callback_query.message.edit_media(
        InputMediaPhoto(
          media="https://tinypic.host/images/2025/07/14/file_00000000fc2461fbbdd6bc500cecbff8_conversation_id6874702c-9760-800e-b0bf-8e0bcf8a3833message_id964012ce-7ef5-4ad4-88e0-1c41ed240c03-1-1.jpg",
          caption=caption
        ),
        reply_markup=keyboard
      )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
    @bot.on_message(filters.command("storage") & filters.private)
    async def storage_cmd(client, message: Message):
        user_id = message.from_user.id

        disk = shutil.disk_usage("/")
        total_gb  = disk.total / (1024 ** 3)
        used_gb   = disk.used  / (1024 ** 3)
        free_gb   = disk.free  / (1024 ** 3)
        used_pct  = (disk.used / disk.total) * 100

        bar_filled = int(used_pct / 5)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)

        folder_lines = ""
        for folder in DOWNLOAD_FOLDERS:
            if os.path.isdir(folder):
                count = sum(1 for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)))
                size_bytes = sum(
                    os.path.getsize(os.path.join(folder, f))
                    for f in os.listdir(folder)
                    if os.path.isfile(os.path.join(folder, f))
                )
                size_mb = size_bytes / (1024 ** 2)
                label = os.path.basename(os.path.abspath(folder))
                parent = os.path.basename(os.path.abspath(os.path.join(folder, "..")))
                display = f"{parent}/downloads" if parent != "." else "downloads"
                folder_lines += f"➥ `{display}` → {count} file(s), {size_mb:.2f} MB\n"
            else:
                label = os.path.basename(folder)
                folder_lines += f"➥ `{label}` → folder not found\n"

        text = (
            f"💾 **Storage Usage**\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
            f"📊 **Disk:**\n"
            f"`[{bar}]` {used_pct:.1f}%\n"
            f"➥ Total : **{total_gb:.2f} GB**\n"
            f"➥ Used  : **{used_gb:.2f} GB**\n"
            f"➥ Free  : **{free_gb:.2f} GB**\n\n"
            f"📁 **Download Folders:**\n"
            f"{folder_lines}\n"
            f"🗑️ Auto-cleanup runs every **5 days**\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰"
        )

        await message.reply_text(text)

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
    @bot.on_message(filters.command("cleanup") & filters.private)
    async def cleanup_cmd(client, message: Message):
        user_id = message.from_user.id
        if user_id not in AUTH_USERS and user_id != OWNER:
            await message.reply_text("❌ You are not authorized to use this command.")
            return

        msg = await message.reply_text("🗑️ Cleaning downloads... please wait.")

        total_deleted = 0
        total_freed = 0
        report_lines = ""

        for folder in DOWNLOAD_FOLDERS:
            if not os.path.isdir(folder):
                continue
            deleted = 0
            freed = 0
            failed = 0
            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)
                if not os.path.isfile(filepath):
                    continue
                try:
                    size = os.path.getsize(filepath)
                    os.remove(filepath)
                    deleted += 1
                    freed += size
                except Exception:
                    failed += 1
            parent = os.path.basename(os.path.abspath(os.path.join(folder, "..")))
            display = f"{parent}/downloads"
            freed_mb = freed / (1024 ** 2)
            report_lines += f"➥ `{display}` → {deleted} deleted, {freed_mb:.2f} MB freed"
            if failed:
                report_lines += f" ({failed} failed)"
            report_lines += "\n"
            total_deleted += deleted
            total_freed += freed

        total_freed_mb = total_freed / (1024 ** 2)
        text = (
            f"✅ **Cleanup Done!**\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
            f"{report_lines}\n"
            f"📦 Total: **{total_deleted} file(s)** removed\n"
            f"💨 Space freed: **{total_freed_mb:.2f} MB**\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰"
        )
        await msg.edit_text(text)


    @bot.on_message(filters.command("help") & filters.private)
    async def help_command(client, message: Message):
        is_owner = message.from_user and message.from_user.id == OWNER

        user_section = (
            "<b>📥 Downloads</b>\n"
            "➥ /stop – Stop ongoing process\n"
            "➥ /history – Resume batch download from TXT\n"
            "➥ /viewhistory – View download history\n"
            "➥ /clearhistory – Clear download history\n\n"

            "<b>🎬 YouTube</b>\n"
            "➥ /ytm – YouTube → MP3 downloader\n"
            "➥ /y2t – YouTube → TXT converter\n"
            "➥ /yth – YouTube MP3 with resume\n\n"

            "<b>🔧 Tools</b>\n"
            "➥ /t2t – Text → TXT generator\n"
            "➥ /t2h – TXT → HTML converter\n"
            "➥ /json – JSON → TXT link converter\n"
            "➥ /cookies – Upload YouTube cookies\n"
            "➥ /getcookies – Show current cookies\n"
            "➥ /ytcookies – Paste/upload YT cookies\n\n"

            "<b>📁 Info & Storage</b>\n"
            "➥ /id – Get chat/user ID\n"
            "➥ /info – Your Telegram info\n"
            "➥ /logs – View bot activity log\n"
            "➥ /storage – Disk usage\n"
            "➥ /cleanup – Delete downloaded files\n"
            "➥ /mini – Browse uploads by date\n\n"

            "<b>🧵 Forum Topics</b>\n"
            "➥ /maketopics – Bulk-create topics from TXT\n"
            "<s>➥ /createtopic – Create a forum topic</s>\n"
            "<s>➥ /topics – List topics in a group</s>\n"
            "<s>➥ /settopic – Set active topic</s>\n"
            "<s>➥ /defaulttopic – Set default fallback topic</s>\n"
            "<s>➥ /topicid – Get topic ID (run inside a topic)</s>\n"
            "<s>➥ /gettopicid [GROUP_ID] – Save topic(s) to memory</s>\n"
            "<s>➥ /linktopics – Match saved topics with TXT</s>\n"
            "<s>➥ /showtopics – Show saved topics</s>\n"
            "<s>➥ /showmapping – Show topic→TXT mapping</s>\n"
            "<s>➥ /parsetopics – Preview topics in TXT file</s>\n"
            "<s>➥ /clearmemory – Clear saved topic memory</s>\n"
            "<s>➥ /cleartopicmap [GROUP_ID] – Wipe topic mapping</s>\n"
            "<s>➥ /fixmapping [GROUP_ID] – Fix subtopic IDs</s>\n\n"

            "<b>🎭 Render Accounts</b>\n"
            "➥ /addaccount – Add Render account slot\n"
            "➥ /listaccounts – List registered accounts\n"
            "➥ /removeaccount – Remove account slot\n"
            "➥ /switchslot – Switch active account\n"
        )

        owner_section = (
            "\n<b>👑 Owner Only</b>\n"
            "➥ /broadcast – Broadcast to all users\n"
            "➥ /broadusers – Show broadcast users\n"
            "➥ /addauth USER_ID – Authorize a user\n"
            "➥ /rmauth USER_ID – Remove authorization\n"
            "➥ /users – List premium users\n"
            "➥ /allhistory – View all users' history\n"
            "➥ /resetallhistory – Clear all history\n"
            "➥ /reset – Restart the bot\n"
        )

        text = (
            "<b>🤖 SAINI DRM Bot — All Commands</b>\n"
            "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
            + user_section
            + (owner_section if is_owner else "")
            + "\n▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            f"➠ Made by <a href='tg://openmessage?user_id={OWNER}'>{CREDIT}</a>"
        )

        MAX = 3800
        chunks = [text[i:i+MAX] for i in range(0, len(text), MAX)]
        await message.reply_text(chunks[0], parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)
        for c in chunks[1:]:
            await message.reply_text(c, parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)


