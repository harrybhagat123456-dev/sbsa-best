import os
import re
import sys
import m3u8
import json
import time
import pytz
import asyncio
import requests
import subprocess
import urllib
import urllib.parse
import yt_dlp
import tgcrypto
import cloudscraper
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64encode, b64decode
from logs import logging
from bs4 import BeautifulSoup
import saini as helper
import html_handler
import globals
from authorisation import add_auth_user, list_auth_users, remove_auth_user
from broadcast import broadcast_handler, broadusers_handler
from text_handler import text_to_txt
from youtube_handler import ytm_handler, y2t_handler, getcookies_handler, cookies_handler

try:
    from download_history import (
        check_and_get_resume_info,
        update_download_progress,
        mark_download_completed,
        mark_download_paused,
        get_history,
    )
    _HISTORY_ENABLED = True
    print("[DRM Handler] History module loaded")
except ImportError as e:
    _HISTORY_ENABLED = False
    print(f"[DRM Handler] History module not available: {e}")
from utils import progress_bar, safe_listen as _base_safe_listen, describe_message
from vars import API_ID, API_HASH, BOT_TOKEN, OWNER, CREDIT, AUTH_USERS, TOTAL_USERS
from vars import api_url, api_token, token_cp, adda_token, photologo, photoyt, photocp, photozip
from aiohttp import ClientSession
from subprocess import getstatusoutput
from pytube import YouTube
from aiohttp import web
import random
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InputMediaPhoto
from pyrogram.errors import FloodWait, PeerIdInvalid, UserIsBlocked, InputUserDeactivated
from pyrogram.errors.exceptions.bad_request_400 import StickerEmojiInvalid
from pyrogram.types.messages_and_media import message
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import aiohttp
import aiofiles
import zipfile
import shutil
import ffmpeg

try:
    BOT_ID = int(str(BOT_TOKEN).split(":", 1)[0])
except Exception:
    BOT_ID = None

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,

def parse_number_or_range(raw_text):
    """Parse '5', '001-002', '1-10' etc. Returns (start, end) tuple or None on failure.
    A single number N means 'start from N to end of file' (end = very large sentinel)."""
    raw_text = str(raw_text).strip()
    if '-' in raw_text and not raw_text.startswith('-'):
        parts = raw_text.split('-')
        if len(parts) == 2:
            try:
                start = int(parts[0].strip())
                end = int(parts[1].strip())
                if start < 1 or end < start:
                    return None
                return (start, end)
            except ValueError:
                pass
    try:
        n = int(raw_text)
        if n < 1:
            return None
        return (n, 10**9)
    except ValueError:
        return None


def _download_message_key(message):
    chat_id = getattr(getattr(message, "chat", None), "id", None)
    message_id = getattr(message, "id", None)
    return f"{chat_id}:{message_id}" if chat_id is not None and message_id is not None else None


def _claim_download_message(message):
    now = time.time()
    stale_before = now - 3600
    for key, seen_at in list(globals.processed_download_messages.items()):
        if seen_at < stale_before:
            globals.processed_download_messages.pop(key, None)
    for key, seen_at in list(globals.listener_consumed_messages.items()):
        if seen_at < stale_before:
            globals.listener_consumed_messages.pop(key, None)
    key = _download_message_key(message)
    if not key:
        logging.debug(f"[TRACE][DRM][CLAIM_NO_KEY] {describe_message(message)}")
        return True
    if key in globals.processed_download_messages:
        logging.warning(f"[TRACE][DRM][DUPLICATE_SKIP] key={key} {describe_message(message)}")
        return False
    globals.processed_download_messages[key] = now
    logging.debug(f"[TRACE][DRM][CLAIM_OK] key={key} {describe_message(message)}")
    return True


# ============================================================
# FORWARD ALL — stores topic message ranges for callback buttons
# Supports: Forward to Saved Messages, Forward to Custom Chat,
#           Copy Message Links (for manual sharing anywhere)
# ============================================================
_fwd_range_store = {}     # key -> {channel_id, message_ids, topic_name}
_fwd_pending_chat = {}    # user_id -> fwd_key (waiting for chat input)
_FWD_MAX_STORE = 200      # keep at most N entries (auto-cleanup)

def _store_fwd_range(channel_id, message_ids, topic_name):
    """Store a forward range and return a short callback key."""
    global _fwd_range_store
    # Cleanup old entries if store is too large
    if len(_fwd_range_store) > _FWD_MAX_STORE:
        _oldest = list(_fwd_range_store.keys())[:len(_fwd_range_store) // 2]
        for k in _oldest:
            _fwd_range_store.pop(k, None)
    key = f"fwd_{abs(hash(f'{channel_id}:{topic_name}:{message_ids[0] if message_ids else 0}')) % 999999}"
    _fwd_range_store[key] = {
        "channel_id": channel_id,
        "message_ids": list(message_ids),
        "topic_name": topic_name,
    }
    return key


async def _do_forward_messages(client, user_id, from_chat, msg_ids, callback_msg=None):
    """Core forwarding logic — copies messages without sender name (no forward header)."""
    forwarded = 0
    failed = 0
    for mid in msg_ids:
        try:
            await client.copy_messages(user_id, from_chat, mid)
            forwarded += 1
            await asyncio.sleep(0.3)
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            try:
                await client.copy_messages(user_id, from_chat, mid)
                forwarded += 1
            except Exception:
                failed += 1
        except Exception as e:
            print(f"[FwdAll] Failed to copy msg {mid}: {e}")
            failed += 1
    return forwarded, failed


async def _fwd_all_callback_handler(client, callback):
    """
    Handle 'Forward All' inline button clicks.
    Shows a menu in user's PM with forwarding options:
      1. Forward to Saved Messages (instant)
      2. Forward to Custom Chat (user picks destination)
      3. Copy Message Links (share anywhere via Telegram)
    """
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton as IKB
    key = callback.data
    data = _fwd_range_store.get(key)
    if not data:
        await callback.answer("Error: Forward data expired or not found.", show_alert=True)
        return

    user_id = callback.from_user.id
    msg_ids = data["message_ids"]
    from_chat = data["channel_id"]
    topic_name = data["topic_name"]

    if not msg_ids:
        await callback.answer("No messages to forward.", show_alert=True)
        return

    await callback.answer()

    # Build the forward options menu and send to user's PM
    try:
        _opts_text = (
            f"📋 <b>Copy Options — {topic_name}</b>\n\n"
            f"<blockquote>Total messages: <b>{len(msg_ids)}</b></blockquote>\n\n"
            f"Choose a destination below:\n"
            f"• <b>Saved Messages</b> — instant copy to your Saved Messages\n"
            f"• <b>Custom Chat</b> — copy to any chat (send chat ID or @username)\n"
            f"• <b>Copy Links</b> — get all message links to share anywhere"
        )
        _buttons = InlineKeyboardMarkup([
            [IKB("📥 Copy to Saved Messages", callback_data=f"fwd_saved|{key}")],
            [IKB("🔄 Copy to Custom Chat", callback_data=f"fwd_custom|{key}")],
            [IKB("📋 Copy Message Links", callback_data=f"fwd_links|{key}")],
        ])
        await client.send_message(user_id, _opts_text, reply_markup=_buttons, disable_web_page_preview=True)
    except Exception as e:
        print(f"[FwdAll] Failed to send options to user: {e}")
        # Fallback: forward directly to Saved Messages
        await callback.answer("Sending to your Saved Messages...", show_alert=True)
        await _do_forward_messages(client, user_id, from_chat, msg_ids)
        try:
            from pyrogram.types import InlineKeyboardMarkup
            _btn = InlineKeyboardMarkup([[IKB("✅ Done", callback_data="fwd_done")]])
            await callback.message.edit_reply_markup(reply_markup=_btn)
        except Exception:
            pass


async def _fwd_action_callback_handler(client, callback):
    """
    Handle forward action sub-buttons:
      fwd_saved|<key>  — forward all to Saved Messages
      fwd_custom|<key> — prompt user to send chat ID/username
      fwd_links|<key>  — copy all message permalinks
    """
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton as IKB
    parts = callback.data.split("|", 1)
    if len(parts) != 2:
        await callback.answer("Invalid callback.", show_alert=True)
        return
    action, key = parts
    data = _fwd_range_store.get(key)
    if not data:
        await callback.answer("Forward data expired. Re-upload the batch.", show_alert=True)
        return

    user_id = callback.from_user.id
    msg_ids = data["message_ids"]
    from_chat = data["channel_id"]
    topic_name = data["topic_name"]

    if action == "fwd_saved":
        # ── Forward all messages to user's Saved Messages ──
        await callback.answer(f"Forwarding {len(msg_ids)} messages to Saved Messages...", show_alert=False)
        # Update button to show "Forwarding..."
        try:
            _loading_btn = InlineKeyboardMarkup([
                [IKB(f"⏳ Forwarding {len(msg_ids)} messages...", callback_data="fwd_busy")],
            ])
            await callback.message.edit_reply_markup(reply_markup=_loading_btn)
        except Exception:
            pass

        forwarded, failed = await _do_forward_messages(client, user_id, from_chat, msg_ids)
        _result = f"✅ Copied {forwarded} messages to Saved Messages"
        if failed:
            _result += f"\n❌ {failed} failed"
        try:
            _done_btn = InlineKeyboardMarkup([[IKB("✅ Done", callback_data="fwd_done")]])
            await callback.message.edit_text(_result, reply_markup=_done_btn, disable_web_page_preview=True)
        except Exception:
            pass

    elif action == "fwd_custom":
        # ── Ask user to provide chat destination ──
        await callback.answer()
        global _fwd_pending_chat
        _fwd_pending_chat[user_id] = key
        try:
            _prompt_text = (
                f"🔄 <b>Copy to Custom Chat</b>\n\n"
                f"Topic: <b>{topic_name}</b> ({len(msg_ids)} messages)\n\n"
                f"Send the <b>chat ID</b> or <b>@username</b> of the chat/group/channel where you want to copy all messages.\n\n"
                f"<i>Examples:</i>\n"
                f"• <code>@my_channel</code>\n"
                f"• <code>-1001234567890</code>\n"
                f"• Forward any message from the target chat to me\n\n"
                f"Send /cancel to cancel."
            )
            await client.send_message(user_id, _prompt_text, disable_web_page_preview=True)
        except Exception as e:
            print(f"[FwdAll] Failed to send custom chat prompt: {e}")

    elif action == "fwd_links":
        # ── Generate all message permalinks ──
        await callback.answer("Generating message links...", show_alert=False)
        try:
            _chat_info = await client.get_chat(from_chat)
            _username = getattr(_chat_info, 'username', None)
            _chat_short = str(from_chat)
            if _chat_short.startswith("-100"):
                _chat_short = _chat_short[4:]
            else:
                _chat_short = _chat_short.lstrip("-")

            _links = []
            for mid in msg_ids:
                if _username:
                    _links.append(f"https://t.me/{_username}/{mid}")
                else:
                    _links.append(f"https://t.me/c/{_chat_short}/{mid}")

            _links_text = "\n".join(_links)
            _header = f"📋 <b>Message Links — {topic_name}</b>\n({len(msg_ids)} messages)\n\n"

            # Send in chunks if too long (Telegram message limit ~4096 chars)
            _chunk_size = 50
            for i in range(0, len(_links), _chunk_size):
                _chunk = _links[i:i + _chunk_size]
                _chunk_text = _header if i == 0 else ""
                _chunk_text += "\n".join(_chunk)
                await client.send_message(user_id, _chunk_text, disable_web_page_preview=True)
                await asyncio.sleep(0.3)

            # Update the options message
            _done_btn = InlineKeyboardMarkup([[IKB("✅ Links Sent", callback_data="fwd_done")]])
            await callback.message.edit_reply_markup(reply_markup=_done_btn)
        except Exception as e:
            print(f"[FwdAll] Failed to generate links: {e}")
            await callback.answer(f"Error: {e}", show_alert=True)


async def _fwd_chat_input_handler(client, message):
    """
    Handle user's reply with chat ID/username for custom forward destination.
    Also handles forwarded messages (user forwards a msg from target chat to bot).
    """
    global _fwd_pending_chat, _fwd_range_store
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton as IKB

    user_id = message.from_user.id
    fwd_key = _fwd_pending_chat.pop(user_id, None)
    if not fwd_key:
        return  # Not expecting chat input from this user

    data = _fwd_range_store.get(fwd_key)
    if not data:
        await message.reply_text("❌ Forward data expired. Please try again from the batch channel.")
        return

    # ── Determine target chat from user's message ──
    target_chat = None
    target_label = ""

    # Case 1: User forwarded a message from the target chat
    if message.forward_from_chat:
        target_chat = message.forward_from_chat.id
        target_label = f"@{message.forward_from_chat.username}" if message.forward_from_chat.username else str(target_chat)
    elif message.forward_from:
        # Forwarded from a user — use their user ID
        target_chat = message.forward_from.id
        target_label = str(target_chat)
    # Case 2: User sent a chat ID or @username
    elif message.text:
        _text = message.text.strip()
        if _text.startswith("@"):
            target_chat = _text  # Pyrogram accepts @username directly
            target_label = _text
        elif _text.lstrip("-").isdigit():
            target_chat = int(_text)
            target_label = _text
        else:
            await message.reply_text("❌ Invalid input. Please send a valid chat ID (e.g., -1001234567890) or @username.\nSend /cancel to cancel.")
            _fwd_pending_chat[user_id] = fwd_key  # Restore pending state
            return

    if not target_chat:
        await message.reply_text("❌ Could not determine target chat. Please forward a message from the target chat or send its ID/@username.\nSend /cancel to cancel.")
        _fwd_pending_chat[user_id] = fwd_key  # Restore pending state
        return

    # ── Forward all messages to the target chat ──
    msg_ids = data["message_ids"]
    from_chat = data["channel_id"]
    topic_name = data["topic_name"]

    _status = await message.reply_text(f"⏳ Copying {len(msg_ids)} messages to {target_label}...")

    forwarded, failed = await _do_forward_messages(client, target_chat, from_chat, msg_ids)

    _result = f"✅ Copied {forwarded} messages to {target_label}"
    if failed:
        _result += f"\n❌ {failed} failed"
    try:
        await _status.edit_text(_result)
    except Exception:
        await message.reply_text(_result)


# ============================================================
# FLOOD CONTROL CONFIGURATION
# ============================================================
UPLOAD_DELAY = 0          # no artificial delay — let Telegram flood control handle it
FLOOD_EXTRA_DELAY = 0     # wait exact flood time only, no extra buffer
MAX_FLOOD_RETRIES = 5

# ── Rainbow graffiti-style topic header ──────────────────────────────────────
_RAINBOW = ['🔴', '🟠', '🟡', '🟢', '🔵', '🟣']

def _rainbow_topic_text(text):
    """
    Convert each letter into a coloured bold-italic Unicode glyph paired with
    a cycling rainbow-dot emoji, e.g. NOTICES →  🔴𝙉 🟠𝙊 🟡𝙏 🟢𝙄 🔵𝘾 🟣𝙀 🔴𝙎
    Uses Mathematical Sans-Serif Bold Italic (U+1D63C…) which renders in
    Telegram as large stylised letters similar to graffiti emoji packs.
    """
    parts = []
    ci = 0
    for ch in text.upper():
        if 'A' <= ch <= 'Z':
            fancy = chr(0x1D63C + ord(ch) - ord('A'))
            parts.append(f"{_RAINBOW[ci % len(_RAINBOW)]}{fancy}")
            ci += 1
        elif ch == ' ':
            parts.append('  ')
        else:
            parts.append(ch)
    return ' '.join(parts)


async def safe_listen(bot, chat_id, user_id, timeout=60, filters=None):
    """
    Wrapper for bot.listen() that tracks active conversations.
    Returns None on any timeout or cancellation.
    If the user sends a /command, it is treated as cancellation (returns None).
    Delegates to the shared safe_listen in utils.py with cancel_on_command=True.
    """
    return await _base_safe_listen(bot, chat_id, user_id, timeout, filters, cancel_on_command=True)


# ============================================================
# FLOOD-SAFE UPLOAD FUNCTIONS
# ============================================================

async def safe_send_document(bot, chat_id, document, caption=None, message_thread_id=None, max_retries=MAX_FLOOD_RETRIES):
    """
    Send document with automatic flood handling and retry logic.
    """
    for attempt in range(max_retries):
        try:
            kwargs = dict(chat_id=chat_id, document=document, caption=caption)
            if message_thread_id:
                kwargs["message_thread_id"] = message_thread_id
            result = await bot.send_document(**kwargs)
            # Add delay after successful upload to prevent flood
            await asyncio.sleep(UPLOAD_DELAY)
            return result, True
            
        except FloodWait as e:
            wait_time = e.value  # Telegram tells us how long to wait
            print(f"FloodWait: Need to wait {wait_time} seconds (attempt {attempt + 1}/{max_retries})")
            
            if attempt < max_retries - 1:
                # Wait the required time + extra buffer
                total_wait = wait_time + FLOOD_EXTRA_DELAY
                await asyncio.sleep(total_wait)
            else:
                return None, False
                
        except Exception as e:
            print(f"Error sending document: {e}")
            return None, False
    
    return None, False


async def safe_send_video(bot, chat_id, video, caption=None, thumb=None, message_thread_id=None, max_retries=MAX_FLOOD_RETRIES):
    """
    Send video with automatic flood handling and retry logic.
    """
    for attempt in range(max_retries):
        try:
            kwargs = dict(chat_id=chat_id, video=video, caption=caption, thumb=thumb)
            if message_thread_id:
                kwargs["message_thread_id"] = message_thread_id
            result = await bot.send_video(**kwargs)
            # Add delay after successful upload to prevent flood
            await asyncio.sleep(UPLOAD_DELAY)
            return result, True
            
        except FloodWait as e:
            wait_time = e.value
            print(f"FloodWait: Need to wait {wait_time} seconds (attempt {attempt + 1}/{max_retries})")
            
            if attempt < max_retries - 1:
                total_wait = wait_time + FLOOD_EXTRA_DELAY
                await asyncio.sleep(total_wait)
            else:
                return None, False
                
        except Exception as e:
            print(f"Error sending video: {e}")
            return None, False
    
    return None, False


async def safe_send_photo(bot, chat_id, photo, caption=None, message_thread_id=None, max_retries=MAX_FLOOD_RETRIES):
    """
    Send photo with automatic flood handling and retry logic.
    """
    for attempt in range(max_retries):
        try:
            kwargs = dict(chat_id=chat_id, photo=photo, caption=caption)
            if message_thread_id:
                kwargs["message_thread_id"] = message_thread_id
            result = await bot.send_photo(**kwargs)
            await asyncio.sleep(UPLOAD_DELAY)
            return result, True
            
        except FloodWait as e:
            wait_time = e.value
            print(f"FloodWait: Need to wait {wait_time} seconds (attempt {attempt + 1}/{max_retries})")
            
            if attempt < max_retries - 1:
                total_wait = wait_time + FLOOD_EXTRA_DELAY
                await asyncio.sleep(total_wait)
            else:
                return None, False
                
        except Exception as e:
            print(f"Error sending photo: {e}")
            return None, False
    
    return None, False


async def safe_send_message(bot, chat_id, text, max_retries=MAX_FLOOD_RETRIES, **kwargs):
    """
    Send message with automatic flood handling and retry logic.
    """
    for attempt in range(max_retries):
        try:
            result = await bot.send_message(
                chat_id=chat_id,
                text=text,
                **kwargs
            )
            # Small delay for messages too
            await asyncio.sleep(1)
            return result, True
            
        except FloodWait as e:
            wait_time = e.value
            print(f"FloodWait: Need to wait {wait_time} seconds (attempt {attempt + 1}/{max_retries})")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(wait_time + 2)
            else:
                return None, False
                
        except Exception as e:
            print(f"Error sending message: {e}")
            return None, False
    
    return None, False


async def drm_handler(bot: Client, m: Message):
    """
    Public entry point. Acquires an exclusive per-user lock so that concurrent
    messages from the same user cannot trigger a duplicate handler while this one
    is still running (including the gap before the first safe_listen call).
    """
    logging.info(f"[TRACE][DRM][ENTER] {describe_message(m)} active={dict(globals.active_conversations)}")
    if not _claim_download_message(m):
        return
    user_id = m.from_user.id
    globals.active_conversations[user_id] = globals.active_conversations.get(user_id, 0) + 1
    try:
        await _drm_handler_impl(bot, m)
        logging.info(f"[TRACE][DRM][COMPLETE] {describe_message(m)}")
    except Exception as e:
        logging.exception(f"[TRACE][DRM][ERROR] {describe_message(m)} error={e}")
        raise
    finally:
        _count = globals.active_conversations.get(user_id, 0) - 1
        if _count <= 0:
            globals.active_conversations.pop(user_id, None)
        else:
            globals.active_conversations[user_id] = _count
        logging.debug(f"[TRACE][DRM][EXIT] {describe_message(m)} active={dict(globals.active_conversations)}")


async def _drm_handler_impl(bot: Client, m: Message):
    globals.processing_request = True
    globals.cancel_requested = False
    caption = globals.caption
    endfilename = globals.endfilename
    thumb = globals.thumb
    CR = globals.CR
    cwtoken = globals.cwtoken
    cptoken = globals.cptoken
    pwtoken = globals.pwtoken
    vidwatermark = globals.vidwatermark
    raw_text2 = globals.raw_text2
    quality = globals.quality
    res = globals.res
    topic = globals.topic

    user_id = m.from_user.id
    _hist_file_hash  = None   # set when coming from /history command
    _hist_channel_id = None   # saved channel from previous run
    _hist_topic_map  = {}     # saved topic map from previous run

    if m.document and m.document.file_name.endswith('.txt'):
        logging.info(f"[TRACE][DRM][TXT_DOWNLOAD_START] {describe_message(m)}")
        x = await m.download()
        await m.delete(True)
        file_name, ext = os.path.splitext(os.path.basename(x))
        path = f"./downloads/{m.chat.id}"
        with open(x, "r") as f:
            content = f.read()
        lines = content.split("\n")

        # ── GLOBAL HISTORY AUTO-SCAN (runs on every .txt upload) ─────────────
        # Only runs when /history command hasn't already set an override
        if _HISTORY_ENABLED and not globals.history_override:
            try:
                _raw_links = []
                for _rl in lines:
                    _l = _rl.strip()
                    if _l.startswith("//"):
                        _l = "https:" + _l
                    elif "://" not in _l and ": //" in _l:
                        _l = _l.replace(": //", ": https://", 1)
                    if "://" in _l:
                        _raw_links.append("https://" + _l.split("://", 1)[1].strip())

                if _raw_links:
                    _fhash, _ridx, _ = await check_and_get_resume_info(
                        file_path=x,
                        file_name=file_name,
                        user_id=user_id,
                        links=_raw_links,
                    )
                    _summary = get_history().get_progress_summary(_fhash)
                    _is_res = (
                        _summary.get("can_resume") and
                        _summary.get("status") == "in_progress" and
                        _ridx > 0
                    )
                    if _is_res:
                        _saved_meta = (get_history().get_entry(_fhash) or {}).get("metadata", {})
                        _prog = _summary.get("progress_percent", 0)
                        _done = _summary.get("completed", 0)
                        _tot  = _summary.get("total_links", len(_raw_links))
                        globals.history_override = {
                            "file_hash":        _fhash,
                            "is_resumable":     True,
                            "resume_index":     _ridx,
                            "b_name":           _saved_meta.get("batch_name", ""),
                            "channel_id":       _saved_meta.get("channel_id"),
                            "topic_map":        _saved_meta.get("topic_map", {}),
                            "progress_percent": _prog,
                            "completed":        _done,
                            "total_links":      _tot,
                        }
                        logging.info(f"[TRACE][DRM][GLOBAL_HISTORY_RESUME] hash={_fhash} from={_ridx + 1}")
                    else:
                        # New file — register it so progress is tracked going forward
                        globals.history_override = {
                            "file_hash":    _fhash,
                            "is_resumable": False,
                            "resume_index": 0,
                            "b_name":       "",
                            "channel_id":   None,
                            "topic_map":    {},
                        }
                        logging.info(f"[TRACE][DRM][GLOBAL_HISTORY_NEW] hash={_fhash} links={len(_raw_links)}")
            except Exception as _he:
                logging.warning(f"[DRM] Global history auto-scan failed: {_he}")
        # ─────────────────────────────────────────────────────────────────────

        os.remove(x)
        logging.info(f"[TRACE][DRM][TXT_DOWNLOADED] file_name={file_name!r} ext={ext!r} line_count={len(lines)} path={path!r}")
    elif m.text and "://" in m.text:
        logging.info(f"[TRACE][DRM][TEXT_URL_INPUT] {describe_message(m)}")
        lines = [m.text]
    else:
        logging.info(f"[TRACE][DRM][IGNORED_INPUT] {describe_message(m)}")
        return

    if m.document:
        if m.chat.id not in AUTH_USERS:
            print(f"User ID not in AUTH_USERS", m.chat.id)
            await bot.send_message(m.chat.id, f"<blockquote>__**Oopss! You are not a Premium member\nPLEASE /upgrade YOUR PLAN\nSend me your user id for authorization\nYour User id**__ - `{m.chat.id}`</blockquote>\n")
            return

    pdf_count = 0
    img_count = 0
    v2_count = 0
    mpd_count = 0
    m3u8_count = 0
    yt_count = 0
    drm_count = 0
    zip_count = 0
    other_count = 0
    
    links = []
    link_chapters = []   # heading that applies to each link (same index as links)
    link_topic_ids = []  # topic_id (int or None) parsed from [id] prefix on chapter lines
    _current_chapter = ""
    _current_topic_id = None
    for i in lines:
        _line = i.strip()
        # Normalize protocol-relative URLs (// or : //) → https://
        if _line.startswith("//"):
            _line = "https:" + _line
        elif "://" not in _line and ": //" in _line:
            _line = _line.replace(": //", ": https://", 1)
        if "://" in _line:
            # Check for inline [TopicName] prefix on content lines: "[Arithmetic] Title: url"
            _inline_topic = re.match(r'^\[([^\]]+)\]\s*(.*)', _line)
            if _inline_topic:
                _prefix = _inline_topic.group(1).strip()
                _rest   = _inline_topic.group(2).strip()
                if _prefix.lstrip('-').isdigit():
                    # Numeric ID prefix → treat as [topic_id] routing
                    _current_topic_id = int(_prefix)
                    _line = _rest
                else:
                    # Named topic → use as chapter, topic_id resolved later
                    _current_chapter  = _prefix
                    _current_topic_id = None
                    _line = _rest
            url = _line.split("://", 1)[1]
            links.append(_line.split("://", 1))
            # Auto-detect (Category) prefix in link name and use as chapter
            _name_auto = links[-1][0]
            _cat_auto = re.match(r'^\(([^)]+)\)\s*', _name_auto)
            link_chapters.append(_cat_auto.group(1).strip() if _cat_auto else _current_chapter)
            link_topic_ids.append(_current_topic_id)
            if ".pdf" in url:
                pdf_count += 1
            elif url.endswith((".png", ".jpeg", ".jpg")):
                img_count += 1
            elif "v2" in url:
                v2_count += 1
            elif "mpd" in url:
                mpd_count += 1
            elif "m3u8" in url:
                m3u8_count += 1
            elif "drm" in url:
                drm_count += 1
            elif "youtu" in url:
                yt_count += 1
            elif "zip" in url:
                zip_count += 1
            else:
                other_count += 1
        elif ": //" in _line:
            _parts = _line.split(": //", 1)
            url = _parts[1]
            links.append([_parts[0].strip(), url])
            # Auto-detect (Category) prefix in link name and use as chapter
            _name_auto2 = links[-1][0]
            _cat_auto2 = re.match(r'^\(([^)]+)\)\s*', _name_auto2)
            link_chapters.append(_cat_auto2.group(1).strip() if _cat_auto2 else _current_chapter)
            link_topic_ids.append(_current_topic_id)
            if ".pdf" in url:
                pdf_count += 1
            elif url.endswith((".png", ".jpeg", ".jpg")):
                img_count += 1
            elif "v2" in url:
                v2_count += 1
            elif "mpd" in url:
                mpd_count += 1
            elif "m3u8" in url:
                m3u8_count += 1
            elif "drm" in url:
                drm_count += 1
            elif "youtu" in url:
                yt_count += 1
            elif "zip" in url:
                zip_count += 1
            else:
                other_count += 1
        else:
            stripped = i.strip()
            if stripped and not stripped.startswith('#'):
                # Parse optional [topic_id] prefix: "[12345] Topic Name"
                _tid_match = re.match(r'^\[(\d+)\]\s*(.*)', stripped)
                if _tid_match:
                    _current_topic_id = int(_tid_match.group(1))
                    _current_chapter = _tid_match.group(2).strip()
                else:
                    _current_topic_id = None
                    _current_chapter = stripped
                    
    if not links:
        logging.warning(f"[TRACE][DRM][NO_LINKS] line_count={len(lines)} {describe_message(m)}")
        await m.reply_text("<b>🔹Invalid Input.</b>")
        return

    # ── Build topic summary (ordered, preserving appearance order) ────────────
    _topic_summary = []          # list of [topic_name, link_count]
    _ts_seen = {}                # topic_name → index in _topic_summary
    for _chap in link_chapters:
        _label = _chap if _chap else "📂 General"
        if _label not in _ts_seen:
            _ts_seen[_label] = len(_topic_summary)
            _topic_summary.append([_label, 0])
        _topic_summary[_ts_seen[_label]][1] += 1

    if m.document:
        # ── Read history override (set by /history command handler) ──────────
        _h = globals.history_override.copy()
        globals.history_override = {}
        _hist_file_hash  = _h.get("file_hash")
        _is_hist_resume  = _h.get("is_resumable", False)
        _hist_resume_idx = _h.get("resume_index", 0)
        _hist_b_name     = _h.get("b_name", "")
        _hist_channel_id = _h.get("channel_id")      # saved from previous run
        _hist_topic_map  = _h.get("topic_map", {})   # topic_name → topic_id

        # ── UNIFIED ANALYSIS (always shown — with resume info if detected) ─
        _ts_lines = []
        for _idx2, (_ts_name, _ts_cnt) in enumerate(_topic_summary, 1):
            _ts_lines.append(f"  {_idx2}. 📌 {_ts_name} — {_ts_cnt} link{'s' if _ts_cnt != 1 else ''}")
        _ts_block = "\n".join(_ts_lines) if _ts_lines else "  (no topics detected)"

        _link_counts = (
            f"<blockquote>•PDF : {pdf_count}      •V2 : {v2_count}\n"
            f"•Img : {img_count}      •YT : {yt_count}\n"
            f"•zip : {zip_count}       •m3u8 : {m3u8_count}\n"
            f"•drm : {drm_count}      •Other : {other_count}\n"
            f"•mpd : {mpd_count}</blockquote>"
        )

        if _is_hist_resume:
            _r_prog  = _h.get("progress_percent", 0)
            _r_done  = _h.get("completed", 0)
            _r_tot   = _h.get("total_links", len(links))
            _r_bname = _hist_b_name or file_name.replace('_', ' ')
            _r_ch    = f"<code>{_hist_channel_id}</code> ✅ saved" if _hist_channel_id else "⚠️ not saved — will ask"
            _r_topics = (
                f"✅ {len(_hist_topic_map)} topic(s) — auto-routed to saved positions"
                if _hist_topic_map else
                "🔍 no saved map — will resolve now"
            )
            _analysis_text = (
                f"<b>📋 File Analysis + ♻️ Resume Detected</b>\n\n"
                f"<b>🗂 Topics in this file:</b>\n"
                f"<blockquote>{_ts_block}</blockquote>\n\n"
                f"<b>📊 Link Type Breakdown:</b>\n"
                f"{_link_counts}\n"
                f"<b>Total 🔗 Links : {len(links)}</b>\n\n"
                f"<b>♻️ Previous run found:</b>\n"
                f"<blockquote>"
                f"📊 Progress : {_r_prog}% ({_r_done}/{_r_tot} done)\n"
                f"⏩ Resume from : link #{_hist_resume_idx + 1}\n"
                f"📚 Batch : <code>{_r_bname}</code>\n"
                f"📢 Channel : {_r_ch}\n"
                f"🗺️ Topics : {_r_topics}"
                f"</blockquote>"
            )
        else:
            _analysis_text = (
                f"<b>📋 File Analysis Complete!</b>\n\n"
                f"<b>🗂 Topics that will be Pinned:</b>\n"
                f"<blockquote>{_ts_block}</blockquote>\n\n"
                f"<b>📊 Link Type Breakdown:</b>\n"
                f"{_link_counts}\n"
                f"<b>Total 🔗 Links : {len(links)}</b>"
            )

        await m.reply_text(_analysis_text, parse_mode=enums.ParseMode.HTML)
        logging.info(
            f"[TRACE][DRM][ANALYSIS_SENT] msg_key={_download_message_key(m)} links={len(links)} "
            f"topics={len(_topic_summary)} resume={_is_hist_resume} "
            f"pdf={pdf_count} img={img_count} yt={yt_count} "
            f"m3u8={m3u8_count} drm={drm_count} mpd={mpd_count} zip={zip_count} other={other_count}"
        )
        await asyncio.sleep(1)

        if _is_hist_resume:
            # ── RESUME: all params pre-filled from history ────────────
            raw_text = str(_hist_resume_idx + 1)
            b_name   = _hist_b_name or file_name.replace('_', ' ')

            if _hist_channel_id:
                channel_id = _hist_channel_id
                raw_text7  = str(_hist_channel_id)
            else:
                editable = await m.reply_text(
                    f"<b>▶️ One last thing — Channel ID needed to resume</b>\n\n"
                    f"<blockquote><i>🔹 Make me an admin to upload.\n"
                    f"🔸 Send /id in your channel to get the Channel ID.\n"
                    f"Example: Channel ID = -100XXXXXXXXXXX\n\n"
                    f"Send /d to upload to this chat instead.</i></blockquote>",
                    parse_mode=enums.ParseMode.HTML,
                )
                try:
                    input7: Message = await safe_listen(bot, editable.chat.id, user_id, timeout=30)
                    if input7 is None:
                        raw_text7 = '/d'
                    else:
                        raw_text7 = input7.text
                        await input7.delete(True)
                except asyncio.TimeoutError:
                    raw_text7 = '/d'
                if "/d" in raw_text7:
                    channel_id = m.chat.id
                else:
                    channel_id = raw_text7
                await editable.delete()

        else:
            # ── NORMAL FLOW: ask start → batch name → channel ─────────
            editable = await m.reply_text(f"<b>Send start number to download from that point to end\nOr send a range like <code>1-10</code> to limit\n(1 – {len(links)})</b>", parse_mode=enums.ParseMode.HTML)
            try:
                input0: Message = await safe_listen(bot, editable.chat.id, user_id, timeout=20)
                if input0 is None:
                    raw_text = '1'
                else:
                    raw_text = input0.text
                    await input0.delete(True)
            except asyncio.TimeoutError:
                raw_text = '1'
            logging.info(f"[TRACE][DRM][START_INDEX_INPUT] raw_text={raw_text!r} msg_key={_download_message_key(m)}")

            _parsed_start = parse_number_or_range(raw_text)
            if _parsed_start is None:
                try:
                    await editable.edit(f"**⚠️ Invalid input. Send a number (e.g. `5`) or range (e.g. `1-10`).**")
                except Exception:
                    await m.reply_text(f"**⚠️ Invalid input. Send a number (e.g. `5`) or range (e.g. `1-10`).**")
                globals.processing_request = False
                return
            if _parsed_start[0] > len(links):
                try:
                    await editable.edit(f"**🔹Enter number in range of Index (01-{len(links)})**")
                except Exception:
                    await m.reply_text(f"**🔹Enter number in range of Index (01-{len(links)})**")
                globals.processing_request = False
                await m.reply_text("**🔹Exiting Task......  **")
                return
            if _parsed_start[1] > len(links):
                _parsed_start = (_parsed_start[0], len(links))

            try:
                await editable.edit(f"**Enter Batch Name or send /d**")
            except Exception:
                editable = await m.reply_text(f"**Enter Batch Name or send /d**")
            try:
                input1: Message = await safe_listen(bot, editable.chat.id, user_id, timeout=20)
                if input1 is None:
                    raw_text0 = '/d'
                else:
                    raw_text0 = input1.text
                    await input1.delete(True)
            except asyncio.TimeoutError:
                raw_text0 = '/d'
            logging.info(f"[TRACE][DRM][BATCH_NAME_INPUT] raw_text0={raw_text0!r} msg_key={_download_message_key(m)}")

            if raw_text0 == '/d':
                b_name = file_name.replace('_', ' ')
            else:
                b_name = raw_text0

            # Save batch name to history for future resume
            if _hist_file_hash and _HISTORY_ENABLED:
                try:
                    _he = get_history().get_entry(_hist_file_hash)
                    if _he:
                        _he["metadata"]["batch_name"] = b_name
                        get_history()._save_history()
                except Exception:
                    pass

            try:
                await editable.edit("__**⚠️Provide the Channel ID or send /d__\n\n<blockquote><i>🔹 Make me an admin to upload.\n🔸Send /id in your channel to get the Channel ID.\n\nExample: Channel ID = -100XXXXXXXXXXX</i></blockquote>\n**")
            except Exception:
                editable = await m.reply_text("__**⚠️Provide the Channel ID or send /d__\n\n<blockquote><i>🔹 Make me an admin to upload.\n🔸Send /id in your channel to get the Channel ID.\n\nExample: Channel ID = -100XXXXXXXXXXX</i></blockquote>\n**")
            try:
                input7: Message = await safe_listen(bot, editable.chat.id, user_id, timeout=20)
                if input7 is None:
                    raw_text7 = '/d'
                else:
                    raw_text7 = input7.text
                    await input7.delete(True)
            except asyncio.TimeoutError:
                raw_text7 = '/d'
            logging.info(f"[TRACE][DRM][CHANNEL_INPUT] raw_text7={raw_text7!r} msg_key={_download_message_key(m)}")

            if "/d" in raw_text7:
                channel_id = m.chat.id
            else:
                channel_id = raw_text7
            await editable.delete()

    elif m.text:
        if any(ext in links[i][1] for ext in [".pdf", ".jpeg", ".jpg", ".png"] for i in range(len(links))):
            raw_text = '1'
            raw_text7 = '/d'
            channel_id = m.chat.id
            b_name = '**Link Input**'
            await m.delete()
        else:
            editable = await m.reply_text(f"╭━━━━❰ᴇɴᴛᴇʀ ʀᴇꜱᴏʟᴜᴛɪᴏɴ❱━━➣ \n┣━━⪼ send `144`  for 144p\n┣━━⪼ send `240`  for 240p\n┣━━⪼ send `360`  for 360p\n┣━━⪼ send `480`  for 480p\n┣━━⪼ send `720`  for 720p\n┣━━⪼ send `1080` for 1080p\n╰━━⌈⚡[🦋`{CREDIT}`🦋]⚡⌋━━➣ ")
            input2: Message = await safe_listen(bot, editable.chat.id, user_id, timeout=60, filters=filters.text & filters.user(m.from_user.id))
            if input2 is None:
                raw_text2 = '480'
            else:
                raw_text2 = input2.text
                await input2.delete(True)
            quality = f"{raw_text2}p"
            await m.delete()
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
            raw_text = '1'
            raw_text7 = '/d'
            channel_id = m.chat.id
            b_name = '**Link Input**'
            await editable.delete()
        
    # ── Validate & resolve channel ID before any uploads ─────────────────────
    if m.document and "/d" not in str(raw_text7):
        try:
            # Convert numeric string IDs to int so Pyrogram can resolve the peer
            _cid_str = str(channel_id).strip()
            if _cid_str.lstrip('-').isdigit():
                channel_id = int(_cid_str)
            _ch = await bot.get_chat(channel_id)
            # Persist the resolved id (avoids string vs int issues later)
            channel_id = _ch.id
            # Save channel_id to history so future resumes skip this prompt
            if _hist_file_hash and _HISTORY_ENABLED:
                try:
                    _he = get_history().get_entry(_hist_file_hash)
                    if _he:
                        _he["metadata"]["channel_id"] = channel_id
                        get_history()._save_history()
                except Exception:
                    pass
        except PeerIdInvalid:
            await m.reply_text(
                "<blockquote><b>❌ Invalid Channel ID or Bot Not Added!</b>\n\n"
                "• Make sure the bot is an <b>admin</b> in the channel.\n"
                "• Then send <code>/id</code> in the channel to get the correct ID.\n"
                "• Correct format: <code>-100XXXXXXXXXXX</code>\n\n"
                "You do <b>NOT</b> need to remove and re-add the bot — "
                "just make it an admin and try again.</blockquote>"
            )
            globals.processing_request = False
            return
        except Exception as e:
            await m.reply_text(
                f"<blockquote><b>❌ Channel Error:</b> <code>{e}</code>\n\n"
                f"Make sure the bot is an admin in the channel and the ID is correct.</blockquote>"
            )
            globals.processing_request = False
            return

    # ── Topic ID resolution for named topics ──────────────────────────────────
    # Priority: 1) history (previous run)  2) /linktopics mapping  3) interactive asking
    _named_topic_id_map = {}  # topic_name → telegram topic_id (int)

    def _resolve_from_map(name: str, src: dict):
        """Exact match, then parent fallback: 'English/Grammar' → 'English'."""
        if name in src:
            return src[name]
        _p = name.split('/')[0].strip()
        if _p != name and _p in src:
            return src[_p]
        return None

    # Pre-populate from history so resume goes straight to upload
    if _hist_topic_map:
        _named_topic_id_map.update(_hist_topic_map)
        # Also add parent-resolved entries for any chapter not explicitly in history
        for _chap in set(link_chapters):
            if _chap and _chap not in _named_topic_id_map:
                _v = _resolve_from_map(_chap, _hist_topic_map)
                if _v is not None:
                    _named_topic_id_map[_chap] = _v

    if m.document:
        _unnamed_topics = []
        _seen_unnamed = set()
        for _i, (_chap, _tid) in enumerate(zip(link_chapters, link_topic_ids)):
            if _chap and _tid is None and _chap not in _seen_unnamed:
                _seen_unnamed.add(_chap)
                _unnamed_topics.append(_chap)

        if _unnamed_topics:
            # Try saved mapping first (from /linktopics or auto_topic_creator)
            try:
                from modules.topic_handler import get_txt_topic_mapping
            except ImportError:
                try:
                    from topic_handler import get_txt_topic_mapping
                except ImportError:
                    get_txt_topic_mapping = None

            _saved_map = {}
            if get_txt_topic_mapping and channel_id:
                try:
                    _saved_map = get_txt_topic_mapping(channel_id)
                except Exception:
                    _saved_map = {}

            # Apply saved mapping — exact match first, then parent fallback
            # e.g. "English/Grammar Study Material" → falls back to "English" topic
            _still_unresolved = []
            for _topic_name in _unnamed_topics:
                _tid_found = _resolve_from_map(_topic_name, _saved_map)
                if _tid_found is not None:
                    _named_topic_id_map[_topic_name] = _tid_found
                elif _topic_name not in _named_topic_id_map:
                    _still_unresolved.append(_topic_name)

            if _saved_map and not _still_unresolved:
                # All resolved from saved mapping — no need to ask
                _n = len(_named_topic_id_map)
                await m.reply_text(
                    f"<b>✅ Topic mapping loaded from memory ({_n} topic{'s' if _n!=1 else ''}).</b>\n"
                    f"<i>Videos will be routed automatically.</i>",
                    parse_mode=enums.ParseMode.HTML
                )
            elif _still_unresolved:
                # Ask only for topics not in saved mapping
                if _saved_map:
                    await m.reply_text(
                        f"<b>ℹ️ {len(_named_topic_id_map)} topic(s) loaded from memory. "
                        f"Need IDs for {len(_still_unresolved)} more.</b>",
                        parse_mode=enums.ParseMode.HTML
                    )
                _total = len(_still_unresolved)
                _tid_prompt = await m.reply_text(
                    f"<b>📌 Topic ID Setup ({_total} topic{'s' if _total > 1 else ''} need IDs)</b>\n\n"
                    f"For each topic, send its <b>Telegram Forum Topic ID</b>.\n"
                    f"Send <code>/d</code> to skip this topic.\n"
                    f"Send <code>/d</code> when asked for the first topic to skip <b>all</b> topic ID steps.\n\n"
                    f"<i>Tip: Run <code>/linktopics</code> once to auto-configure all topics.</i>",
                    parse_mode=enums.ParseMode.HTML
                )
                await asyncio.sleep(0.5)

                _skip_all_topics = False
                for _idx, _topic_name in enumerate(_still_unresolved, 1):
                    if _skip_all_topics:
                        break
                    _ask_msg = await m.reply_text(
                        f"<b>[{_idx}/{_total}] Topic:</b> <code>{_topic_name}</code>\n\n"
                        f"Send the <b>Topic ID</b> (number), <code>/d</code> to skip this topic,\n"
                        f"or <code>/d</code> on the first prompt to skip <b>all</b> remaining topics:",
                        parse_mode=enums.ParseMode.HTML
                    )
                    try:
                        _tid_input = await safe_listen(bot, m.chat.id, user_id, timeout=30)
                        if _tid_input is None:
                            _tid_val = '/d'
                        else:
                            _tid_val = _tid_input.text.strip()
                            await _tid_input.delete(True)
                    except asyncio.TimeoutError:
                        _tid_val = '/d'

                    await _ask_msg.delete()

                    if _tid_val == '/d':
                        # First /d skips all remaining topic ID prompts
                        _skip_all_topics = True
                        break
                    elif _tid_val.lstrip('-').isdigit():
                        _named_topic_id_map[_topic_name] = int(_tid_val)

                await _tid_prompt.delete()

            # Apply all resolved topic IDs to links (with parent fallback)
            # Config mapping always wins over any [id] hardcoded in the TXT file
            for _i in range(len(link_topic_ids)):
                _c = link_chapters[_i] if _i < len(link_chapters) else ""
                if _c:
                    _resolved = _resolve_from_map(_c, _named_topic_id_map)
                    if _resolved is not None:
                        link_topic_ids[_i] = _resolved

            # Save full topic map to history so future resumes need zero prompts
            if _hist_file_hash and _HISTORY_ENABLED and _named_topic_id_map:
                try:
                    _he = get_history().get_entry(_hist_file_hash)
                    if _he:
                        existing = _he["metadata"].get("topic_map", {})
                        existing.update(_named_topic_id_map)
                        _he["metadata"]["topic_map"] = existing
                        get_history()._save_history()
                except Exception:
                    pass

    if thumb.startswith("http://") or thumb.startswith("https://"):
        getstatusoutput(f"wget '{thumb}' -O 'thumb.jpg'")
        thumb = "thumb.jpg"
    else:
        thumb = thumb

    # ── Start progress tracking + live Telegram progress message ────────────
    _tg_prog_msg     = None
    _tg_prog_counter = 0

    def _build_prog_text(cur, tot, ok, fail, now_file, log_list, done=False, web_url=""):
        import html as _html
        pct    = round(cur / tot * 100, 1) if tot else 0
        filled = int(pct / 10)
        bar    = "█" * filled + "░" * (10 - filled)
        _safe_batch = _html.escape(str(b_name or ""))
        _safe_file  = _html.escape(str(now_file or "Starting…")[:80])
        status = "✅ Complete!" if done else f"▶ <i>{_safe_file}</i>"
        txt = (
            f"<b>📥 {_safe_batch}</b>\n"
            f"<code>{bar}</code> <b>{pct}%</b>\n"
            f"🔗 <b>{cur}/{tot}</b>  •  ✅ <b>{ok}</b>  •  ❌ <b>{fail}</b>\n\n"
            f"{status}"
        )
        recent = (log_list or [])[-5:]
        if recent:
            txt += "\n\n<b>Recent:</b>"
            for _le in reversed(recent):
                _icon  = "✅" if _le.get("ok") else "❌"
                _lname = _html.escape((_le.get("name") or "").split("http")[0].strip()[:60])
                txt += f"\n{_icon} <code>#{_le.get('i',0)}</code> {_lname}"
        if web_url:
            txt += f"\n\n🌐 <a href='{web_url}/progress'>Live web view</a>"
        return txt

    try:
        from progress_tracker import start_batch, get_public_url
        _start_idx = int(raw_text) - 1 if raw_text.isdigit() else 0
        start_batch(b_name, file_name if m.document else "direct input", len(links), channel_id, _start_idx)
        _prog_url = get_public_url()
        try:
            _tg_prog_msg = await bot.send_message(
                m.chat.id,
                _build_prog_text(_start_idx, len(links), 0, 0, "Starting…", [], web_url=_prog_url),
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True,
            )
            print(f"[TG_PROG] Live progress message sent: {_tg_prog_msg.id}")
        except Exception as _ep:
            print(f"[TG_PROG] Failed to send initial progress message: {_ep}")
            _tg_prog_msg = None
    except Exception as _ep2:
        print(f"[TG_PROG] Outer init error: {_ep2}")
        _tg_prog_msg  = None
        _prog_url     = ""
    # ─────────────────────────────────────────────────────────────────────────

    try:
        if m.document and raw_text == "1":
            batch_message = await bot.send_message(chat_id=channel_id, text=f"<blockquote><b>🎯Target Batch : {b_name}</b></blockquote>")
            if "/d" not in raw_text7:
                await bot.send_message(chat_id=m.chat.id, text=f"<blockquote><b><i>🎯Target Batch : {b_name}</i></b></blockquote>\n\n🔄 Your Task is under processing, please check your Set Channel📱. Once your task is complete, I will inform you 📩")
                await bot.pin_chat_message(channel_id, batch_message.id)
                message_id = batch_message.id
                pinning_message_id = message_id + 1
                await bot.delete_messages(channel_id, pinning_message_id)
        else:
             if "/d" not in raw_text7:
                await bot.send_message(chat_id=m.chat.id, text=f"<blockquote><b><i>🎯Target Batch : {b_name}</i></b></blockquote>\n\n🔄 Your Task is under processing, please check your Set Channel📱. Once your task is complete, I will inform you 📩")
    except Exception as e:
        await m.reply_text(f"**Fail Reason »**\n<blockquote><i>{e}</i></blockquote>\n\n✦𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲 ✦ {CREDIT}🌟`")

        
    failed_count = 0
    failed_links = []        # collects "name : url" for each failure
    nav_index = []           # (label, msg_id) — chapter headings or numbered names
    _nav_seen_chapters = set()   # chapters already added to nav_index
    _parsed = parse_number_or_range(raw_text)
    if _parsed is None:
        await m.reply_text("**⚠️ Invalid start number. Please try again.**")
        globals.processing_request = False
        return
    count = _parsed[0]
    arg = _parsed[0]
    range_end = min(_parsed[1], len(links))
    _last_t_name = None   # tracks topic name extracted from filenames (topic == "/yes")

    _notice_kw_set = {'notices', 'notice', 'announcement', 'announcements', 'important'}

    async def _send_topic_header(chap, topic_id=None):
        """Send a styled announcement header to the channel BEFORE the first file of a new topic."""
        if not chap or chap in _nav_seen_chapters:
            return
        _nav_seen_chapters.add(chap)
        try:
            is_notice = chap.strip().lower() in _notice_kw_set

            if is_notice:
                # ── Notices: special pinned announcement ─────────────────────
                _header_text = (
                    f"📢 <b>NOTICE / ANNOUNCEMENT</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"<b>📌 {chap}</b>\n\n"
                    f"<i>Please read the notices below before starting your studies.</i>\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"<b>📚 Batch : {b_name}</b>"
                )
            else:
                # ── Regular topic: simple plain header ───────────────────────
                _header_text = (
                    f"<b>━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"{chap.upper()}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
                    f"<blockquote><b>Batch : {b_name}</b></blockquote>"
                )

            send_kwargs = {
                "chat_id": channel_id,
                "text": _header_text,
                "disable_web_page_preview": True,
            }
            if topic_id:
                send_kwargs["message_thread_id"] = topic_id
            _hm = await bot.send_message(**send_kwargs)
            nav_index.append((chap, _hm.id))

            # Pin — Notices with notification, others silently
            try:
                await bot.pin_chat_message(
                    channel_id, _hm.id,
                    disable_notification=(not is_notice)
                )
                # Delete the automatic "X pinned a message" service notification
                # Telegram sends it as the very next message in the chat
                await asyncio.sleep(0.5)
                try:
                    await bot.delete_messages(channel_id, _hm.id + 1)
                except Exception:
                    pass
            except Exception as _pin_err:
                print(f"[Pin] Failed to pin {'notice' if is_notice else 'header'} "
                      f"(msg {_hm.id}) in {channel_id}: {_pin_err}")
                try:
                    await bot.send_message(
                        m.chat.id,
                        f"⚠️ <b>Pin failed for: {chap}</b>\n"
                        f"<blockquote><i>{_pin_err}</i></blockquote>\n"
                        f"Make sure the bot is an <b>Admin</b> with <b>Pin Messages</b> permission.",
                        disable_web_page_preview=True,
                    )
                except Exception:
                    pass

            # Notify operator
            try:
                _icon = "📢" if is_notice else "📖"
                await bot.send_message(
                    m.chat.id,
                    f"<blockquote><b>{_icon} Now Uploading : {chap}</b></blockquote>",
                    disable_web_page_preview=True,
                )
            except Exception:
                pass
            return _hm.id
        except Exception as _hdr_err:
            print(f"[TopicHeader] Error sending header for '{chap}': {_hdr_err}")
        return None

    # Mutable dict updated at the start of every loop iteration so that
    # _pin_heading can record the correct date / type without passing extra args
    _cal_cur = {"date_iso": None, "date_display": None, "item_type": "video"}

    # Track topic transitions for "Forward All" messages
    _fwd_prev_chap = None
    _fwd_prev_topic_id = None
    _fwd_prev_start_msg_id = None
    _fwd_prev_last_msg_id = None
    _fwd_msg_ids = []          # ALL message IDs for the current topic (for forward all)

    def _local_msg_url(msg_id, thread_id=None):
        cid = str(channel_id)
        cid_short = cid[4:] if cid.startswith("-100") else cid.lstrip("-")
        if thread_id:
            return f"https://t.me/c/{cid_short}/{thread_id}/{msg_id}"
        return f"https://t.me/c/{cid_short}/{msg_id}"

    async def _pin_heading(chap, fallback_label, msg_id, topic_id=None):
        nonlocal _fwd_prev_last_msg_id, _fwd_msg_ids
        if chap:
            _fwd_prev_last_msg_id = msg_id
            _fwd_msg_ids.append(msg_id)
        # Topic headers are already sent before upload via _send_topic_header.
        # Only track nav entries for files that have no chapter heading.
        if not chap:
            nav_index.append((fallback_label, msg_id))
        # Record to calendar (best-effort)
        try:
            from calendar_data import record_item
            # Strip leading "001 " style number prefix (format is "NNN title")
            clean_title = re.sub(r'^\d+\s+', '', fallback_label).strip()
            record_item(
                _cal_cur["date_iso"], _cal_cur["date_display"],
                clean_title, chap or 'General',
                msg_id, channel_id, topic_id,
                _cal_cur["item_type"], b_name
            )
        except Exception as _cal_err:
            print(f"[Calendar] Failed to record item '{fallback_label}': {_cal_err}")

    async def _send_forward_all_marker(chap, topic_id=None):
        """Send a 'Forward All' marker message at the end of a topic upload."""
        nonlocal _fwd_msg_ids
        from pyrogram.types import InlineKeyboardButton as _IKB, InlineKeyboardMarkup as _IKM
        if not chap:
            return
        try:
            _fwd_text = (
                f"<b>✅ {chap.upper()} — UPLOAD COMPLETE</b>\n\n"
                f"<blockquote>📋 <b>COPY ALL THIS TOPIC</b>\n"
                f"Click the button below to choose where to copy all messages (no sender name shown).</blockquote>"
            )
            _buttons = []
            # Primary: callback button that actually copies messages
            _fwd_key = _store_fwd_range(channel_id, _fwd_msg_ids, chap)
            _msg_count = len(_fwd_msg_ids)
            _buttons.append([_IKB(f"📤 Copy All ({_msg_count} msgs)", callback_data=_fwd_key)])
            # Secondary: URL links for manual navigation (start/end)
            _url_row = []
            if _fwd_prev_start_msg_id:
                _url_row.append(_IKB("⬆️ Start", url=_local_msg_url(_fwd_prev_start_msg_id, topic_id)))
            if _fwd_prev_last_msg_id:
                _url_row.append(_IKB("✅ End", url=_local_msg_url(_fwd_prev_last_msg_id, topic_id)))
            if _url_row:
                _buttons.append(_url_row)
            _fwd_kwargs = {
                "chat_id": channel_id,
                "text": _fwd_text,
                "disable_web_page_preview": True,
            }
            if _buttons:
                _fwd_kwargs["reply_markup"] = _IKM(_buttons)
            if topic_id:
                _fwd_kwargs["message_thread_id"] = topic_id
            await bot.send_message(**_fwd_kwargs)
            # Reset message ID list for next topic
            _fwd_msg_ids = []
        except Exception as _fe:
            print(f"[ForwardAll] Failed to send marker for '{chap}': {_fe}")

    try:
        for i in range(arg - 1, range_end):
            # Resolve topic_id for this link (set by [id] prefix on its section heading)
            _link_topic_id = link_topic_ids[i] if i < len(link_topic_ids) else None

            # ── Send topic header BEFORE the first file of each new topic ────
            _chap_now = link_chapters[i] if i < len(link_chapters) else ""

            # ── Send "Forward All" marker when topic changes ─────────────────
            if _fwd_prev_chap is not None and _chap_now != _fwd_prev_chap:
                _notice_check = _fwd_prev_chap.strip().lower() in _notice_kw_set
                if not _notice_check:
                    await _send_forward_all_marker(_fwd_prev_chap, _fwd_prev_topic_id)

            _fwd_prev_chap = _chap_now
            _fwd_prev_topic_id = _link_topic_id

            _new_header_id = await _send_topic_header(_chap_now, _link_topic_id)
            if _new_header_id:
                _fwd_prev_start_msg_id = _new_header_id
                _fwd_prev_last_msg_id = _new_header_id
                _fwd_msg_ids = [_new_header_id]
            _topic_part = f"┃\n┣📖𝐓𝐨𝐩𝐢𝐜 » {_chap_now}\n" if _chap_now else ""

            if globals.cancel_requested:
                if _hist_file_hash and _HISTORY_ENABLED:
                    try:
                        _stop_url = "https://" + links[i][1] if len(links[i]) > 1 else links[i][0]
                        await update_download_progress(_hist_file_hash, max(0, i - 1), "completed", _stop_url)
                        await mark_download_paused(_hist_file_hash)
                    except Exception:
                        pass
                await m.reply_text("🚦**STOPPED**🚦\n\n💾 **Progress saved.** Send the same file again with /history to resume.")
                globals.processing_request = False
                globals.cancel_requested = False
                return
  
            Vxy = links[i][1].replace("file/d/","uc?export=download&id=").replace("www.youtube-nocookie.com/embed", "youtu.be").replace("?modestbranding=1", "").replace("/view?usp=sharing","")
            if "youtube.com/embed/" in Vxy or "youtube-nocookie.com/embed/" in Vxy:
                _vid = Vxy.split("/embed/")[1].split("?")[0].split("&")[0].split("/")[0]
                Vxy = f"www.youtube.com/watch?v={_vid}"
            url = "https://" + Vxy
            link0 = "https://" + Vxy
            cw_keys_string = ""  # Reset per-iteration for CareerWill DRM DASH

            _raw_name = links[i][0]

            # ── Update live progress + periodic history save + Telegram edit ──
            try:
                from progress_tracker import update as _pt_update
                _pt_update(i + 1, len(links), _raw_name[:80], count, failed_count)
            except Exception:
                pass
            # Save resume position to history every 5 files so auto-resume works
            if _hist_file_hash and _HISTORY_ENABLED and i > 0 and (i % 5) == 0:
                try:
                    _he = get_history().get_entry(_hist_file_hash)
                    if _he:
                        from datetime import datetime as _dtnow
                        _he["metadata"]["last_successful_index"] = i - 1
                        _he["current_index"] = i
                        _he["status"] = "in_progress"
                        _he["updated_at"] = _dtnow.now().isoformat()
                        get_history()._save_history()
                except Exception:
                    pass
            # Edit the live Telegram progress message every 5 files
            _tg_prog_counter += 1
            if _tg_prog_msg and (_tg_prog_counter % 5 == 0):
                try:
                    import json as _pjson
                    try:
                        with open("/tmp/bot_progress.json") as _pf:
                            _pd = _pjson.load(_pf)
                    except Exception:
                        _pd = {}
                    await _tg_prog_msg.edit_text(
                        _build_prog_text(
                            i + 1, len(links), count, failed_count,
                            _raw_name[:80], _pd.get("log"), web_url=_prog_url
                        ),
                        parse_mode=enums.ParseMode.HTML,
                        disable_web_page_preview=True,
                    )
                    print(f"[TG_PROG] Edited at file {i+1}/{len(links)}")
                except Exception as _ee:
                    print(f"[TG_PROG] Edit failed at file {i+1}: {_ee}")
            # ─────────────────────────────────────────────────────────────────

            # Extract content date from {DATE-DD-Month-YYYY} before stripping
            try:
                from calendar_data import extract_date_from_raw
                _cal_cur["date_iso"], _cal_cur["date_display"] = extract_date_from_raw(_raw_name)
            except Exception:
                _cal_cur["date_iso"] = _cal_cur["date_display"] = None
            # Set default type; updated below when we know the URL type
            _cal_cur["item_type"] = "video"
            # Strip new-format prefixes from display name
            _raw_name = re.sub(r'^\([^)]+\)\s*', '', _raw_name)         # remove (Category)
            _raw_name = re.sub(r'^\[[^\]]+\]\s*', '', _raw_name)        # remove [Topic]
            _raw_name = re.sub(r'\{DATE-[^}]+\}\s*', '', _raw_name)     # remove {DATE-...}
            name1 = _raw_name.replace("(", "[").replace(")", "]").replace("_", "").replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("#", "").replace("|", "").replace("@", "").replace("*", "").replace("&", "").replace(".", "").replace("https", "").replace("http", "").strip()
            if m.text:
                if "youtu" in url:
                    oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
                    response = requests.get(oembed_url)
                    audio_title = response.json().get('title', 'YouTube Video')
                    audio_title = audio_title.replace("_", " ")
                    name = f'{audio_title[:60]}'
                    namef = f'{audio_title[:60]}'
                    name1 = f'{audio_title}'
                else:
                    name = f'{name1[:60]}'
                    namef = f'{name1[:60]}'
            else:
                if endfilename == "/d":
                    name = f'{str(count).zfill(3)}) {name1[:60]}'
                    namef = f'{name1[:60]}'
                else:
                    name = f'{str(count).zfill(3)}) {name1[:60]} {endfilename}'
                    namef = f'{name1[:60]} {endfilename}'
                
            if "visionias" in url:
                async with ClientSession() as session:
                    async with session.get(url, headers={'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Accept-Language': 'en-US,en;q=0.9', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'Pragma': 'no-cache', 'Referer': 'http://www.visionias.in/', 'Sec-Fetch-Dest': 'iframe', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'cross-site', 'Upgrade-Insecure-Requests': '1', 'User-Agent': 'Mozilla/5.0 (Linux; Android 12; RMX2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36', 'sec-ch-ua': '"Chromium";v="107", "Not=A?Brand";v="24"', 'sec-ch-ua-mobile': '?1', 'sec-ch-ua-platform': '"Android"',}) as resp:
                        text = await resp.text()
                        url = re.search(r"(https://.*?playlist.m3u8.*?)\"", text).group(1)

            if "acecwply" in url:
                cmd = f'yt-dlp -o "{name}.%(ext)s" -f "bestvideo[height<={raw_text2}]+bestaudio" --hls-prefer-ffmpeg --no-keep-video --remux-video mkv --no-warning "{url}"'
         
            elif "https://cpvod.testbook.com/" in url or "classplusapp.com/drm/" in url:
                url = url.replace("https://cpvod.testbook.com/","https://media-cdn.classplusapp.com/drm/")
                url = f"https://covercel.vercel.app/extract_keys?url={url}@bots_updatee&user_id={user_id}"
                mpd, keys = helper.get_mps_and_keys(url)
                url = mpd
                keys_string = " ".join([f"--key {key}" for key in keys])

            elif "classplusapp" in url:
                signed_api = f"https://covercel.vercel.app/extract_keys?url={url}@bots_updatee&user_id={user_id}"
                response = requests.get(signed_api, timeout=20)
                url = response.text.strip()
                url = response.json()['url']  
                
            elif "tencdn.classplusapp" in url:
                headers = {'host': 'api.classplusapp.com', 'x-access-token': f'{cptoken}', 'accept-language': 'EN', 'api-version': '18', 'app-version': '1.4.73.2', 'build-number': '35', 'connection': 'Keep-Alive', 'content-type': 'application/json', 'device-details': 'Xiaomi_Redmi 7_SDK-32', 'device-id': 'c28d3cb16bbdac01', 'region': 'IN', 'user-agent': 'Mobile-Android', 'webengage-luid': '00000187-6fe4-5d41-a530-26186858be4c', 'accept-encoding': 'gzip'}
                params = {"url": f"{url}"}
                response = requests.get('https://api.classplusapp.com/cams/uploader/video/jw-signed-url', headers=headers, params=params)
                url = response.json()['url']  
           
            elif 'videos.classplusapp' in url:
                url = requests.get(f'https://api.classplusapp.com/cams/uploader/video/jw-signed-url?url={url}', headers={'x-access-token': f'{cptoken}'}).json()['url']
            
            elif 'media-cdn.classplusapp.com' in url or 'media-cdn-alisg.classplusapp.com' in url or 'media-cdn-a.classplusapp.com' in url: 
                headers = {'host': 'api.classplusapp.com', 'x-access-token': f'{cptoken}', 'accept-language': 'EN', 'api-version': '18', 'app-version': '1.4.73.2', 'build-number': '35', 'connection': 'Keep-Alive', 'content-type': 'application/json', 'device-details': 'Xiaomi_Redmi 7_SDK-32', 'device-id': 'c28d3cb16bbdac01', 'region': 'IN', 'user-agent': 'Mobile-Android', 'webengage-luid': '00000187-6fe4-5d41-a530-26186858be4c', 'accept-encoding': 'gzip'}
                params = {"url": f"{url}"}
                response = requests.get('https://api.classplusapp.com/cams/uploader/video/jw-signed-url', headers=headers, params=params)
                url = response.json()['url']

            if "edge.api.brightcove.com" in url:
                bcov = f'bcov_auth={cwtoken}'
                url = url.split("bcov_auth")[0]+bcov

            elif "childId" in url and "parentId" in url and "anonymouspwplayer" not in url:
                url = f"https://anonymouspwplayerr-3cfbfedeb317.herokuapp.com/pw?url={url}&token={pwtoken}"
                        
            elif 'encrypted.m' in url:
                appxkey = url.split('*')[1]
                url = url.split('*')[0]

            elif '*' in url and '.mpd' in url.split('*')[0]:
                # CareerWill DRM DASH with ClearKey: mpd_url*kid:key
                _cw_parts = url.split('*', 1)
                url = _cw_parts[0].strip()
                _cw_creds = _cw_parts[1].strip().split(':')
                cw_kid = _cw_creds[0] if len(_cw_creds) > 0 else ""
                cw_key = _cw_creds[1] if len(_cw_creds) > 1 else ""
                cw_keys_string = f"{cw_kid}:{cw_key}"  # Mark as CareerWill DRM

            if "youtu" in url:
                ytf = f"bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"
            elif "embed" in url:
                ytf = f"bestvideo[height<={raw_text2}]+bestaudio/best[height<={raw_text2}]"
            else:
                ytf = f"b[height<={raw_text2}]/bv[height<={raw_text2}]+ba/b/bv+ba"

            if "jw-prod" in url:
                cmd = f'yt-dlp -o "{name}.mp4" "{url}"'
            elif "webvideos.classplusapp." in url:
               cmd = f'yt-dlp --add-header "referer:https://web.classplusapp.com/" --add-header "x-cdn-tag:empty" -f "{ytf}" "{url}" -o "{name}.mp4"'
            elif "youtube.com" in url or "youtu.be" in url:
                cmd = f'yt-dlp -k --allow-unplayable-formats --geo-bypass --cookies youtube_cookies.txt --extractor-args "youtube:player_client=tv_simply,ios,android_vr" -f "{ytf}" -S "res~{raw_text2},+size,+br" --fixup never --merge-output-format mp4 "{url}" -o "{name}".mp4'
            else:
                cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{name}.mp4"'

            try:
                if m.text:
                    cc = f'{name1} [{res}p] .mkv'
                    cc1 = f'{name1} .pdf'
                    cczip = f'{name1} .zip'
                    ccimg = f'{name1} .jpg'
                    ccm = f'{name1} .mp3'
                    cchtml = f'{name1} .html'
                else:
                    if topic == "/yes":
                        raw_title = links[i][0]
                        t_match = re.search(r"[\(\[]([^\)\]]+)[\)\]]", raw_title)
                        if t_match:
                            t_name = t_match.group(1).strip()
                            v_name = re.sub(r"^[\(\[]([^\)\]]+)[\)\]]\s*", "", raw_title)
                            v_name = re.sub(r"[\(\[]([^\)\]]+)[\)\]]", "", v_name)
                            v_name = re.sub(r":.*", "", v_name).strip()
                        else:
                            t_name = "Untitled"
                            v_name = re.sub(r":.*", "", raw_title).strip()

                        # ── Send bold ALL-CAPS topic header when topic changes ──
                        if t_name != _last_t_name:
                            _last_t_name = t_name
                            _t_header_text = (
                                f"<b>╔══════════════════════════╗\n"
                                f"        📌  {t_name.upper()}  📌\n"
                                f"╚══════════════════════════╝</b>"
                            )
                            try:
                                _t_send_kw = {
                                    "chat_id": channel_id,
                                    "text": _t_header_text,
                                    "disable_web_page_preview": True,
                                }
                                if _link_topic_id:
                                    _t_send_kw["message_thread_id"] = _link_topic_id
                                _t_hm = await bot.send_message(**_t_send_kw)
                                try:
                                    await bot.pin_chat_message(
                                        channel_id, _t_hm.id, disable_notification=True
                                    )
                                except Exception:
                                    pass
                                if t_name not in _nav_seen_chapters:
                                    nav_index.append((t_name, _t_hm.id))
                                    _nav_seen_chapters.add(t_name)
                            except Exception:
                                pass

                        if caption == "/cc1":
                            cc = f'[🎥]Vid Id : {str(count).zfill(3)}\n**Video Title :** `{v_name} [{res}p] .mkv`\n<blockquote><b>Batch Name : {b_name}\nTopic Name : {t_name}</b></blockquote>\n\n**Extracted by➤**{CR}\n'
                            cc1 = f'[📕]Pdf Id : {str(count).zfill(3)}\n**File Title :** `{v_name} .pdf`\n<blockquote><b>Batch Name : {b_name}\nTopic Name : {t_name}</b></blockquote>\n\n**Extracted by➤**{CR}\n'
                            cczip = f'[📁]Zip Id : {str(count).zfill(3)}\n**Zip Title :** `{v_name} .zip`\n<blockquote><b>Batch Name : {b_name}\nTopic Name : {t_name}</b></blockquote>\n\n**Extracted by➤**{CR}\n'
                            ccimg = f'[🖼️]Img Id : {str(count).zfill(3)}\n**Img Title :** `{v_name} .jpg`\n<blockquote><b>Batch Name : {b_name}\nTopic Name : {t_name}</b></blockquote>\n\n**Extracted by➤**{CR}\n'
                            cchtml = f'[🌐]Html Id : {str(count).zfill(3)}\n**Html Title :** `{v_name} .html`\n<blockquote><b>Batch Name : {b_name}\nTopic Name : {t_name}</b></blockquote>\n\n**Extracted by➤**{CR}\n'
                            ccyt = f'[🎥]Vid Id : {str(count).zfill(3)}\n**Video Title :** `{v_name} .mp4`\n<a href="{url}">__**Click Here to Watch Stream**__</a>\n<blockquote><b>Batch Name : {b_name}\nTopic Name : {t_name}</b></blockquote>\n\n**Extracted by➤**{CR}\n'
                            ccm = f'[🎵]Mp3 Id : {str(count).zfill(3)}\n**Audio Title :** `{v_name} .mp3`\n<blockquote><b>Batch Name : {b_name}\nTopic Name : {t_name}</b></blockquote>\n\n**Extracted by➤**{CR}\n'
                        elif caption == "/cc2":
                            cc = f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<blockquote>⋅ ─  {t_name}  ─ ⋅</blockquote>\n\n<b>🎞️ Title :</b> {v_name}\n<b>├── Extention :  {CR} .mkv</b>\n<b>├── Resolution : [{res}]</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 Extracted By : {CR}**"
                            cc1 = f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<blockquote>⋅ ─  {t_name}  ─ ⋅</blockquote>\n\n<b>📁 Title :</b> {v_name}\n<b>├── Extention :  {CR} .pdf</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 Extracted By : {CR}**"
                            cczip = f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<blockquote>⋅ ─  {t_name}  ─ ⋅</blockquote>\n\n<b>📒 Title :</b> {v_name}\n<b>├── Extention :  {CR} .zip</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 Extracted By : {CR}**"
                            ccimg = f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<blockquote>⋅ ─  {t_name}  ─ ⋅</blockquote>\n\n<b>🖼️ Title :</b> {v_name}\n<b>├── Extention :  {CR} .jpg</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 Extracted By : {CR}**"
                            ccm = f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<blockquote>⋅ ─  {t_name}  ─ ⋅</blockquote>\n\n<b>🎵 Title :</b> {v_name}\n<b>├── Extention :  {CR} .mp3</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 Extracted By : {CR}**"
                            cchtml = f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<blockquote>⋅ ─  {t_name}  ─ ⋅</blockquote>\n\n<b>🌐 Title :</b> {v_name}\n<b>├── Extention :  {CR} .html</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 Extracted By : {CR}**"
                        else:
                            cc = f'<blockquote>⋅ ─ {t_name} ─ ⋅</blockquote>\n<b>{str(count).zfill(3)}.</b> {name1} [{res}p] .mkv'
                            cc1 = f'<blockquote>⋅ ─ {t_name} ─ ⋅</blockquote>\n<b>{str(count).zfill(3)}.</b> {name1} .pdf'
                            cczip = f'<blockquote>⋅ ─ {t_name} ─ ⋅</blockquote>\n<b>{str(count).zfill(3)}.</b> {name1} .zip'
                            ccimg = f'<blockquote>⋅ ─ {t_name} ─ ⋅</blockquote>\n<b>{str(count).zfill(3)}.</b> {name1} .jpg'
                            ccm = f'<blockquote>⋅ ─ {t_name} ─ ⋅</blockquote>\n<b>{str(count).zfill(3)}.</b> {name1} .mp3'
                            cchtml = f'<blockquote>⋅ ─ {t_name} ─ ⋅</blockquote>\n<b>{str(count).zfill(3)}.</b> {name1} .html'
                    else:
                        if caption == "/cc1":
                            cc = f'[🎥]Vid Id : {str(count).zfill(3)}\n**Video Title :** `{name1} [{res}p] .mkv`\n<blockquote><b>Batch Name :</b> {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n'
                            cc1 = f'[📕]Pdf Id : {str(count).zfill(3)}\n**File Title :** `{name1} .pdf`\n<blockquote><b>Batch Name :</b> {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n'
                            cczip = f'[📁]Zip Id : {str(count).zfill(3)}\n**Zip Title :** `{name1} .zip`\n<blockquote><b>Batch Name :</b> {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n' 
                            ccimg = f'[🖼️]Img Id : {str(count).zfill(3)}\n**Img Title :** `{name1} .jpg`\n<blockquote><b>Batch Name :</b> {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n'
                            ccm = f'[🎵]Audio Id : {str(count).zfill(3)}\n**Audio Title :** `{name1} .mp3`\n<blockquote><b>Batch Name :</b> {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n'
                            cchtml = f'[🌐]Html Id : {str(count).zfill(3)}\n**Html Title :** `{name1} .html`\n<blockquote><b>Batch Name :</b> {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n'
                        elif caption == "/cc2":
                            cc = f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<b>🎞️ Title :</b> {name1}\n<b>├── Extention :  {CR} .mkv</b>\n<b>├── Resolution : [{res}]</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 Extracted By : {CR}**"
                            cc1 = f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<b>📁 Title :</b> {name1}\n<b>├── Extention :  {CR} .pdf</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 Extracted By : {CR}**"
                            cczip = f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<b>📒 Title :</b> {name1}\n<b>├── Extention :  {CR} .zip</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 Extracted By : {CR}**"
                            ccimg = f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<b>🖼️ Title :</b> {name1}\n<b>├── Extention :  {CR} .jpg</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 Extracted By : {CR}**"
                            ccm = f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<b>🎵 Title :</b> {name1}\n<b>├── Extention :  {CR} .mp3</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 Extracted By : {CR}**"
                            cchtml = f"——— ✦ {str(count).zfill(3)} ✦ ———\n\n<b>🌐 Title :</b> {name1}\n<b>├── Extention :  {CR} .html</b>\n<blockquote><b>📚 Course : {b_name}</b></blockquote>\n\n**🌟 Extracted By : {CR}**"
                        else:
                            cc = f'<b>{str(count).zfill(3)}.</b> {name1} [{res}p] .mkv'
                            cc1 = f'<b>{str(count).zfill(3)}.</b> {name1} .pdf'
                            cczip = f'<b>{str(count).zfill(3)}.</b> {name1} .zip'
                            ccimg = f'<b>{str(count).zfill(3)}.</b> {name1} .jpg'
                            ccm = f'<b>{str(count).zfill(3)}.</b> {name1} .mp3'
                            cchtml = f'<b>{str(count).zfill(3)}.</b> {name1} .html'
                    
                # ============================================================
                # UPLOAD WITH FLOOD CONTROL
                # ============================================================

                # Update calendar item type based on URL
                if ".pdf" in url or "drive" in url:
                    _cal_cur["item_type"] = "pdf"
                elif any(ext in url for ext in ['.jpg','.jpeg','.png','.webp','.gif']):
                    _cal_cur["item_type"] = "image"
                elif any(ext in url for ext in ['.mp3','.aac','.m4a','.ogg','.wav']):
                    _cal_cur["item_type"] = "audio"
                else:
                    _cal_cur["item_type"] = "video"

                if "drive" in url:
                    try:
                        ka = await helper.download(url, name)
                        # Use safe upload function
                        result, success = await safe_send_document(bot, channel_id, ka, caption=cc1, message_thread_id=_link_topic_id)
                        if result:
                            _chap = link_chapters[i] if i < len(link_chapters) else ""
                            await _pin_heading(_chap, f'{str(count).zfill(3)} {name1}', result.id, topic_id=_link_topic_id)
                        if success:
                            count += 1
                        else:
                            failed_count += 1
                        os.remove(ka)
                    except FloodWait as e:
                        print(f"FloodWait in drive upload: {e.value}s")
                        await asyncio.sleep(e.value + FLOOD_EXTRA_DELAY)
                        failed_count += 1
                        continue    
  
                elif ".pdf" in url:
                    if "cwmediabkt99" in url:
                        max_retries = 15
                        retry_delay = 4
                        success = False
                        failure_msgs = []
                        
                        for attempt in range(max_retries):
                            try:
                                await asyncio.sleep(retry_delay)
                                url_fixed = url.replace(" ", "%20")
                                scraper = cloudscraper.create_scraper()
                                response = scraper.get(url_fixed)

                                if response.status_code == 200:
                                    with open(f'{namef}.pdf', 'wb') as file:
                                        file.write(response.content)
                                    await asyncio.sleep(retry_delay)
                                    # Use safe upload
                                    result, success = await safe_send_document(bot, channel_id, f'{namef}.pdf', caption=cc1, message_thread_id=_link_topic_id)
                                    if result:
                                        _chap = link_chapters[i] if i < len(link_chapters) else ""
                                        await _pin_heading(_chap, f'{str(count).zfill(3)} {name1}', result.id, topic_id=_link_topic_id)
                                    if success:
                                        count += 1
                                    else:
                                        failed_count += 1
                                    os.remove(f'{namef}.pdf')
                                    break
                                else:
                                    failure_msg = await m.reply_text(f"Attempt {attempt + 1}/{max_retries} failed: {response.status_code}")
                                    failure_msgs.append(failure_msg)
                                    
                            except Exception as e:
                                failure_msg = await m.reply_text(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                                failure_msgs.append(failure_msg)
                                await asyncio.sleep(retry_delay)
                                continue 
                        for msg in failure_msgs:
                            await msg.delete()
                            
                    else:
                        try:
                            cmd = f'yt-dlp -o "{namef}.pdf" "{url}"'
                            download_cmd = f'{cmd} {helper._YTDLP_EXTRA}'
                            _proc = await asyncio.create_subprocess_shell(
                                download_cmd,
                                stdout=None,
                                stderr=None,
                            )
                            await _proc.wait()
                            # Use safe upload
                            result, success = await safe_send_document(bot, channel_id, f'{namef}.pdf', caption=cc1, message_thread_id=_link_topic_id)
                            if result:
                                _chap = link_chapters[i] if i < len(link_chapters) else ""
                                await _pin_heading(_chap, f'{str(count).zfill(3)} {name1}', result.id, topic_id=_link_topic_id)
                            if success:
                                count += 1
                            else:
                                failed_count += 1
                            os.remove(f'{namef}.pdf')
                        except FloodWait as e:
                            print(f"FloodWait in pdf upload: {e.value}s")
                            await asyncio.sleep(e.value + FLOOD_EXTRA_DELAY)
                            failed_count += 1
                            continue    

                elif ".ws" in url and url.endswith(".ws"):
                    try:
                        await helper.pdf_download(f"{api_url}utkash-ws?url={url}&authorization={api_token}",f"{name}.html")
                        time.sleep(1)
                        result, success = await safe_send_document(bot, channel_id, f"{name}.html", caption=cchtml, message_thread_id=_link_topic_id)
                        if result:
                            _chap = link_chapters[i] if i < len(link_chapters) else ""
                            await _pin_heading(_chap, f'{str(count).zfill(3)} {name1}', result.id, topic_id=_link_topic_id)
                        if success:
                            count += 1
                        else:
                            failed_count += 1
                        os.remove(f'{name}.html')
                    except FloodWait as e:
                        print(f"FloodWait in ws upload: {e.value}s")
                        await asyncio.sleep(e.value + FLOOD_EXTRA_DELAY)
                        failed_count += 1
                        continue    
                            
                elif any(ext in url for ext in [".jpg", ".jpeg", ".png"]):
                    try:
                        ext = url.split('.')[-1]
                        cmd = f'yt-dlp -o "{namef}.{ext}" "{url}"'
                        download_cmd = f'{cmd} {helper._YTDLP_EXTRA}'
                        _proc = await asyncio.create_subprocess_shell(
                            download_cmd,
                            stdout=None,
                            stderr=None,
                        )
                        await _proc.wait()
                        # Use safe upload
                        result, success = await safe_send_photo(bot, channel_id, f'{namef}.{ext}', caption=ccimg, message_thread_id=_link_topic_id)
                        if result:
                            _chap = link_chapters[i] if i < len(link_chapters) else ""
                            await _pin_heading(_chap, f'{str(count).zfill(3)} {name1}', result.id, topic_id=_link_topic_id)
                        if success:
                            count += 1
                        else:
                            failed_count += 1
                        os.remove(f'{namef}.{ext}')
                    except FloodWait as e:
                        print(f"FloodWait in image upload: {e.value}s")
                        await asyncio.sleep(e.value + FLOOD_EXTRA_DELAY)
                        failed_count += 1
                        continue    

                elif any(ext in url for ext in [".mp3", ".wav", ".m4a"]):
                    try:
                        ext = url.split('.')[-1]
                        cmd = f'yt-dlp -o "{namef}.{ext}" "{url}"'
                        download_cmd = f'{cmd} {helper._YTDLP_EXTRA}'
                        _proc = await asyncio.create_subprocess_shell(
                            download_cmd,
                            stdout=None,
                            stderr=None,
                        )
                        await _proc.wait()
                        # Use safe upload
                        result, success = await safe_send_document(bot, channel_id, f'{namef}.{ext}', caption=ccm, message_thread_id=_link_topic_id)
                        if result:
                            _chap = link_chapters[i] if i < len(link_chapters) else ""
                            await _pin_heading(_chap, f'{str(count).zfill(3)} {name1}', result.id, topic_id=_link_topic_id)
                        if success:
                            count += 1
                        else:
                            failed_count += 1
                        os.remove(f'{namef}.{ext}')
                    except FloodWait as e:
                        print(f"FloodWait in audio upload: {e.value}s")
                        await asyncio.sleep(e.value + FLOOD_EXTRA_DELAY)
                        failed_count += 1
                        continue    
                    
                elif 'encrypted.m' in url:    
                    remaining_links = len(links) - count
                    progress = (count / len(links)) * 100
                    Show1 = f"<blockquote>🚀𝐏𝐫𝐨𝐠𝐫𝐞𝐬𝐬 » {progress:.2f}%</blockquote>\n┃\n" \
                           f"┣🔗𝐈𝐧𝐝𝐞𝐱 » {count}/{len(links)}\n┃\n" \
                           f"╰━🖇️𝐑𝐞𝐦𝐚𝐢𝐧 » {remaining_links}\n" \
                           f"━━━━━━━━━━━━━━━━━━━━━━━━\n" \
                           f"<blockquote><b>⚡Dᴏᴡɴʟᴏᴀᴅɪɴɢ Eɴᴄʀʏᴘᴛᴇᴅ Sᴛᴀʀᴛᴇᴅ...⏳</b></blockquote>\n┃\n" \
                           f'┣💃𝐂𝐫𝐞𝐝𝐢𝐭 » {CR}\n┃\n' \
                           f"╰━📚𝐁𝐚𝐭𝐜𝐡 » {b_name}\n" \
                           f"{_topic_part}" \
                           f"━━━━━━━━━━━━━━━━━━━━━━━━━\n" \
                           f"<blockquote>📚𝐓𝐢𝐭𝐥𝐞 » {namef}</blockquote>\n┃\n" \
                           f"┣🍁𝐐𝐮𝐚𝐥𝐢𝐭𝐲 » {quality}\n┃\n" \
                           f'┣━🔗𝐋𝐢𝐧𝐤 » <a href="{link0}">**Original Link**</a>\n┃\n' \
                           f'╰━━🖇️𝐔𝐫𝐥 » <a href="{url}">**Api Link**</a>\n' \
                           f"━━━━━━━━━━━━━━━━━━━━━━━━━\n" \
                           f"🛑**Send** /stop **to stop process**\n┃\n" \
                           f"╰━✦𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲 ✦ {CREDIT}"
                    Show = f"<i><b>Video Downloading</b></i>\n<blockquote><b>{str(count).zfill(3)}) {name1}</b></blockquote>" 
                    prog = await bot.send_message(channel_id, Show, disable_web_page_preview=True)
                    prog1 = await m.reply_text(Show1, disable_web_page_preview=True)
                    res_file = await helper.download_and_decrypt_video(url, cmd, name, appxkey)  
                    filename = res_file  
                    await prog1.delete(True)
                    await prog.delete(True)
                    if not filename or not os.path.isfile(filename):
                        await bot.send_message(channel_id, f'⚠️**Downloading Failed**⚠️\n**Name** =>> `{str(count).zfill(3)} {name1}`\n**Url** =>> {url}\n\n<blockquote expandable><i><b>Failed Reason: File not downloaded. Check URL or token validity.</b></i></blockquote>', disable_web_page_preview=True)
                        failed_links.append(f"{name1} : {link0}")
                        count += 1
                        failed_count += 1
                        continue
                    _sent = await helper.send_vid(bot, m, cc, filename, vidwatermark, thumb, name, prog, channel_id, topic_id=_link_topic_id)
                    if _sent:
                        _chap = link_chapters[i] if i < len(link_chapters) else ""
                        await _pin_heading(_chap, f'{str(count).zfill(3)} {name1}', _sent.id, topic_id=_link_topic_id)
                    count += 1  
                    await asyncio.sleep(UPLOAD_DELAY)  
                    continue  

                elif 'drmcdni' in url or 'drm/wv' in url or 'drm/common' in url:
                    remaining_links = len(links) - count
                    progress = (count / len(links)) * 100
                    Show1 = f"<blockquote>🚀𝐏𝐫𝐨𝐠𝐫𝐞𝐬𝐬 » {progress:.2f}%</blockquote>\n┃\n" \
                           f"┣🔗𝐈𝐧𝐝𝐞𝐱 » {count}/{len(links)}\n┃\n" \
                           f"╰━🖇️𝐑𝐞𝐦𝐚𝐢𝐧 » {remaining_links}\n" \
                           f"━━━━━━━━━━━━━━━━━━━━━━━━\n" \
                           f"<blockquote><b>⚡Dᴏᴡɴʟᴏᴀᴅɪɴɢ Sᴛᴀʀᴛᴇᴅ...⏳</b></blockquote>\n┃\n" \
                           f'┣💃𝐂𝐫𝐞𝐝𝐢𝐭 » {CR}\n┃\n' \
                           f"╰━📚𝐁𝐚𝐭𝐜𝐡 » {b_name}\n" \
                           f"{_topic_part}" \
                           f"━━━━━━━━━━━━━━━━━━━━━━━━━\n" \
                           f"<blockquote>📚𝐓𝐢𝐭𝐥𝐞 » {namef}</blockquote>\n┃\n" \
                           f"┣🍁𝐐𝐮𝐚𝐥𝐢𝐭𝐲 » {quality}\n┃\n" \
                           f'┣━🔗𝐋𝐢𝐧𝐤 » <a href="{link0}">**Original Link**</a>\n┃\n' \
                           f'╰━━🖇️𝐔𝐫𝐥 » <a href="{url}">**Api Link**</a>\n' \
                           f"━━━━━━━━━━━━━━━━━━━━━━━━━\n" \
                           f"🛑**Send** /stop **to stop process**\n┃\n" \
                           f"╰━✦𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲 ✦ {CREDIT}"
                    Show = f"<i><b>Video Downloading</b></i>\n<blockquote><b>{str(count).zfill(3)}) {name1}</b></blockquote>"
                    prog = await bot.send_message(channel_id, Show, disable_web_page_preview=True)
                    prog1 = await m.reply_text(Show1, disable_web_page_preview=True)
                    res_file = await helper.decrypt_and_merge_video(mpd, keys_string, path, name, raw_text2)
                    filename = res_file
                    await prog1.delete(True)
                    await prog.delete(True)
                    if not filename or not os.path.isfile(filename):
                        await bot.send_message(channel_id, f'⚠️**Downloading Failed**⚠️\n**Name** =>> `{str(count).zfill(3)} {name1}`\n**Url** =>> {url}\n\n<blockquote expandable><i><b>Failed Reason: File not downloaded. Check URL or token validity.</b></i></blockquote>', disable_web_page_preview=True)
                        failed_links.append(f"{name1} : {link0}")
                        count += 1
                        failed_count += 1
                        continue
                    _sent = await helper.send_vid(bot, m, cc, filename, vidwatermark, thumb, name, prog, channel_id, topic_id=_link_topic_id)
                    if _sent:
                        _chap = link_chapters[i] if i < len(link_chapters) else ""
                        await _pin_heading(_chap, f'{str(count).zfill(3)} {name1}', _sent.id, topic_id=_link_topic_id)
                    count += 1
                    await asyncio.sleep(UPLOAD_DELAY)
                    continue

                elif cw_keys_string:
                    # CareerWill DRM DASH - ClearKey decryption (mpd_url*kid:key format)
                    remaining_links = len(links) - count
                    progress = (count / len(links)) * 100
                    Show1 = f"<blockquote>🚀𝐏𝐫𝐨𝐠𝐫𝐞𝐬𝐬 » {progress:.2f}%</blockquote>\n┃\n" \
                           f"┣🔗𝐈𝐧𝐝ᴇx » {count}/{len(links)}\n┃\n" \
                           f"╰━🖇️𝐑ᴇᴍᴀɪɴ » {remaining_links}\n" \
                           f"━━━━━━━━━━━━━━━━━━━━━━━━\n" \
                           f"<blockquote><b>⚡CareerWill DRM Downloading...⏳</b></blockquote>\n┃\n" \
                           f'┣💃𝐂𝐫ᴇᴅɪᴛ » {CR}\n┃\n' \
                           f"╰━📚𝐁ᴀᴛᴄʜ » {b_name}\n" \
                           f"{_topic_part}" \
                           f"━━━━━━━━━━━━━━━━━━━━━━━━━\n" \
                           f"<blockquote>📚𝐓ɪᴛʟᴇ » {namef}</blockquote>\n┃\n" \
                           f"┣🍁𝐐ᴜᴀʟɪᴛʏ » {quality}\n┃\n" \
                           f'╰━━━━━━━━━━━━━━━━━━━━━━━━━\n' \
                           f"🛑**Send** /stop **to stop process**\n┃\n" \
                           f"╰━✦𝐁ᐨ𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲 ✦ {CREDIT}"
                    Show = f"<i><b>🛡️ CareerWill DRM Video Downloading</b></i>\n<blockquote><b>{str(count).zfill(3)}) {name1}</b></blockquote>"
                    prog = await bot.send_message(channel_id, Show, disable_web_page_preview=True)
                    prog1 = await m.reply_text(Show1, disable_web_page_preview=True)
                    try:
                        _cw_path = path
                    except NameError:
                        _cw_path = f"./downloads/{m.chat.id}"
                    # Parse kid:key from cw_keys_string (set during URL transformation)
                    if ':' in cw_keys_string:
                        _cw_kid, _cw_key = cw_keys_string.split(':', 1)
                    else:
                        _cw_kid, _cw_key = cw_keys_string, ""
                    # Default quality fallback
                    _cw_quality = raw_text2 if raw_text2 and raw_text2.isdigit() else "720"
                    try:
                        res_file = await helper.download_careerwill_drm(url, _cw_kid, _cw_key, _cw_path, name, _cw_quality)
                    except Exception as _cw_err:
                        print(f"[CW_DRM] Error: {_cw_err}")
                        res_file = None
                    filename = res_file
                    await prog1.delete(True)
                    await prog.delete(True)
                    if not filename or not os.path.isfile(filename):
                        await bot.send_message(channel_id, f'⚠️**Downloading Failed**⚠️\n**Name** =>> `{str(count).zfill(3)} {name1}`\n**Url** =>> {url}\n\n<blockquote expandable><i><b>Failed Reason: File not downloaded. Check if CloudFront segments are accessible or ClearKey is valid.</b></i></blockquote>', disable_web_page_preview=True)
                        failed_links.append(f"{name1} : {link0}")
                        count += 1
                        failed_count += 1
                        continue
                    _sent = await helper.send_vid(bot, m, cc, filename, vidwatermark, thumb, name, prog, channel_id, topic_id=_link_topic_id)
                    if _sent:
                        _chap = link_chapters[i] if i < len(link_chapters) else ""
                        await _pin_heading(_chap, f'{str(count).zfill(3)} {name1}', _sent.id, topic_id=_link_topic_id)
                    count += 1
                    await asyncio.sleep(UPLOAD_DELAY)
                    continue

                else:
                    remaining_links = len(links) - count
                    progress = (count / len(links)) * 100
                    Show1 = f"<blockquote>🚀𝐏𝐫𝐨𝐠𝐫𝐞𝐬𝐬 » {progress:.2f}%</blockquote>\n┃\n" \
                           f"┣🔗𝐈𝐧𝐝𝐞𝐱 » {count}/{len(links)}\n┃\n" \
                           f"╰━🖇️𝐑𝐞𝐦𝐚𝐢𝐧 » {remaining_links}\n" \
                           f"━━━━━━━━━━━━━━━━━━━━━━━━\n" \
                           f"<blockquote><b>⚡Dᴏᴡɴʟᴏᴀᴅɪɴɢ Sᴛᴀʀᴛᴇᴅ...⏳</b></blockquote>\n┃\n" \
                           f'┣💃𝐂𝐫𝐞𝐝𝐢𝐭 » {CR}\n┃\n' \
                           f"╰━📚𝐁𝐚𝐭𝐜𝐡 » {b_name}\n" \
                           f"{_topic_part}" \
                           f"━━━━━━━━━━━━━━━━━━━━━━━━━\n" \
                           f"<blockquote>📚𝐓𝐢𝐭𝐥𝐞 » {namef}</blockquote>\n┃\n" \
                           f"┣🍁𝐐𝐮𝐚𝐥𝐢𝐭𝐲 » {quality}\n┃\n" \
                           f'┣━🔗𝐋𝐢𝐧𝐤 » <a href="{link0}">**Original Link**</a>\n┃\n' \
                           f'╰━━🖇️𝐔𝐫𝐥 » <a href="{url}">**Api Link**</a>\n' \
                           f"━━━━━━━━━━━━━━━━━━━━━━━━━\n" \
                           f"🛑**Send** /stop **to stop process**\n┃\n" \
                           f"╰━✦𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲 ✦ {CREDIT}"
                    Show = f"<i><b>Video Downloading</b></i>\n<blockquote><b>{str(count).zfill(3)}) {name1}</b></blockquote>"
                    prog = await bot.send_message(channel_id, Show, disable_web_page_preview=True)
                    prog1 = await m.reply_text(Show1, disable_web_page_preview=True)
                    res_file = await helper.download_video(url, cmd, name)
                    filename = res_file
                    await prog1.delete(True)
                    await prog.delete(True)
                    if not filename or not os.path.isfile(filename):
                        _dl_error = getattr(helper, "last_download_error", "") or "File not downloaded. The YouTube video may be private, restricted, or blocked in this server region."
                        await bot.send_message(channel_id, f'⚠️**Downloading Failed**⚠️\n**Name** =>> `{str(count).zfill(3)} {name1}`\n**Url** =>> {url}\n\n<blockquote expandable><i><b>Failed Reason: {_dl_error}</b></i></blockquote>', disable_web_page_preview=True)
                        failed_links.append(f"{name1} : {link0}")
                        count += 1
                        failed_count += 1
                        continue
                    _sent = await helper.send_vid(bot, m, cc, filename, vidwatermark, thumb, name, prog, channel_id, topic_id=_link_topic_id)
                    if _sent:
                        _chap = link_chapters[i] if i < len(link_chapters) else ""
                        await _pin_heading(_chap, f'{str(count).zfill(3)} {name1}', _sent.id, topic_id=_link_topic_id)
                    count += 1
                    # Add delay after video upload
                    await asyncio.sleep(UPLOAD_DELAY)
                
            except Exception as e:
                await bot.send_message(channel_id, f'⚠️**Downloading Failed**⚠️\n**Name** =>> `{str(count).zfill(3)} {name1}`\n**Url** =>> {url}\n\n<blockquote expandable><i><b>Failed Reason: {str(e)}</b></i></blockquote>', disable_web_page_preview=True)
                failed_links.append(f"{name1} : {link0}")
                count += 1
                failed_count += 1
                continue

        # ── Send "Forward All" marker for the last topic after loop ends ──────
        if _fwd_prev_chap:
            _notice_check_last = _fwd_prev_chap.strip().lower() in _notice_kw_set
            if not _notice_check_last:
                await _send_forward_all_marker(_fwd_prev_chap, _fwd_prev_topic_id)

    except Exception as e:
        await m.reply_text(str(e))
        time.sleep(2)

    selected_total = max(0, range_end - arg + 1)
    success_count = max(0, selected_total - failed_count)
    video_count = v2_count + mpd_count + m3u8_count + yt_count + drm_count + zip_count + other_count

    # ── Build channel message URL helper ──────────────────────────────────────
    _chat_username = None
    try:
        _chat_info = await bot.get_chat(channel_id)
        _chat_username = getattr(_chat_info, 'username', None)
    except Exception:
        pass

    def _msg_url(msg_id):
        """Return a clickable t.me link for a message in the target channel."""
        if _chat_username:
            return f"https://t.me/{_chat_username}/{msg_id}"
        cid = str(channel_id)
        if cid.startswith("-100"):
            return f"https://t.me/c/{cid[4:]}/{msg_id}"
        return f"https://t.me/c/{cid}/{msg_id}"

    # ── Navigation index — inline keyboard in channel ────────────────────────
    if nav_index:
        from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        _notice_kw_nav = {'notices', 'notice', 'announcement', 'announcements', 'important'}

        # Build one button per topic; notices get 📢, others get 📚
        _kb_rows = []
        for idx, (nm, mid) in enumerate(nav_index, 1):
            _btn_icon = "📢" if nm.strip().lower() in _notice_kw_nav else "📚"
            _kb_rows.append([InlineKeyboardButton(
                f"{_btn_icon}  {idx}. {nm}",
                url=_msg_url(mid)
            )])

        _nav_text = (
            f"<b>🗂  {b_name}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>📌  Quick Navigation</b>\n\n"
            f"<i>Tap any topic below to jump directly to it 👇</i>"
        )

        # Telegram limits inline keyboards to ~100 buttons; split if needed
        _chunk_size = 50
        for _ci in range(0, len(_kb_rows), _chunk_size):
            _chunk_rows = _kb_rows[_ci:_ci + _chunk_size]
            _suffix = f" <i>(part {_ci // _chunk_size + 1})</i>" if len(_kb_rows) > _chunk_size else ""
            try:
                await bot.send_message(
                    channel_id,
                    _nav_text + _suffix,
                    reply_markup=InlineKeyboardMarkup(_chunk_rows),
                    disable_web_page_preview=True,
                )
            except Exception:
                pass

    if m.document:
        _completion_msg = (
            f"<b>-┈━═.•°✅ Completed ✅°•.═━┈-</b>\n"
            f"<blockquote><b>🎯Batch Name : {b_name}</b></blockquote>\n"
            f"<blockquote>🔗 Total URLs: {len(links)} \n"
            f"┃   ┠📌 Selected URLs: {selected_total}\n"
            f"┃   ┠🔴 Total Failed URLs: {failed_count}\n"
            f"┃   ┠🟢 Total Successful URLs: {success_count}\n"
            f"┃   ┃   ┠🎥 Total Video URLs: {video_count}\n"
            f"┃   ┃   ┠📄 Total PDF URLs: {pdf_count}\n"
            f"┃   ┃   ┠📸 Total IMAGE URLs: {img_count}</blockquote>\n"
        )
        # ── Mark progress as done ─────────────────────────────────────────────
        try:
            from progress_tracker import finish as _pt_finish
            _pt_finish(success_count, failed_count, b_name)
        except Exception:
            pass
        # Final edit of live Telegram progress message
        if _tg_prog_msg:
            try:
                import json as _pjson
                try:
                    with open("/tmp/bot_progress.json") as _pf:
                        _pd = _pjson.load(_pf)
                except Exception:
                    _pd = {}
                await _tg_prog_msg.edit_text(
                    _build_prog_text(
                        selected_total, len(links), success_count, failed_count,
                        "Batch complete!", _pd.get("log"), done=True, web_url=_prog_url
                    ),
                    parse_mode=enums.ParseMode.HTML,
                    disable_web_page_preview=True,
                )
            except Exception:
                pass
        # ─────────────────────────────────────────────────────────────────────

        try:
            await bot.send_message(channel_id, _completion_msg)
        except Exception as _ce:
            print(f"[Completion] Could not send to channel {channel_id}: {_ce}")
        if raw_text7 != "/d":
            try:
                await bot.send_message(m.chat.id, f"<blockquote><b>✅ Your Task is completed, please check your Set Channel📱</b></blockquote>")
            except Exception:
                pass

    # ── Send topics list to user chat ─────────────────────────────────────────
    if m.document and nav_index and raw_text7 != "/d":
        _tl_header = (
            f"<b>📚 Topics Downloaded\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 Batch : {b_name}</b>\n\n"
        )
        _tl_entries = [
            f'<b>{idx}.</b> <a href="{_msg_url(mid)}">{nm}</a>\n<code>{nm}</code>'
            for idx, (nm, mid) in enumerate(nav_index, 1)
        ]
        _tl_chunks = []
        _tl_current = _tl_header
        for _te in _tl_entries:
            _candidate = _tl_current + _te + "\n\n"
            if len(_candidate) > 4000:
                _tl_chunks.append(_tl_current.rstrip())
                _tl_current = _te + "\n\n"
            else:
                _tl_current = _candidate
        if _tl_current.strip():
            _tl_chunks.append(_tl_current.rstrip())
        for _chunk in _tl_chunks:
            try:
                await bot.send_message(m.chat.id, _chunk, disable_web_page_preview=True)
            except Exception:
                pass

    # ── Failed links txt ───────────────────────────────────────────────────────
    if failed_links:
        os.makedirs("downloads", exist_ok=True)
        _safe_b_name = re.sub(r'[^\w\s-]', '', b_name[:30]).strip() or "batch"
        failed_file = f"downloads/failed_{_safe_b_name}.txt"
        with open(failed_file, "w", encoding="utf-8") as _ff:
            _ff.write(f"Failed Links — {b_name}\n")
            _ff.write(f"Total Failed: {failed_count}\n")
            _ff.write("=" * 50 + "\n\n")
            for _fl in failed_links:
                _ff.write(_fl + "\n")
        try:
            await bot.send_document(
                m.chat.id,
                failed_file,
                caption=f"<b>❌ Failed Links — {b_name}</b>\n<blockquote>Total Failed: {failed_count}</blockquote>"
            )
        except Exception:
            pass
        try:
            os.remove(failed_file)
        except Exception:
            pass

    # ── Mark history completed ───────────────────────────────────────────────
    if _hist_file_hash and _HISTORY_ENABLED:
        try:
            await mark_download_completed(_hist_file_hash)
        except Exception:
            pass

    globals.processing_request = False


# ============================================================
# /history command — history-aware DRM entry point
# ============================================================

async def history_drm_handler(bot: Client, m: Message):
    """
    /history command handler.
    - Asks for a .txt file
    - Checks if it was previously downloaded (resumable)
    - If resumable: skips from-where + batch name → just asks channel ID → resumes
    - If new: normal flow (asks all three questions)
    - Calls drm_handler for the actual download
    """
    user_id = m.from_user.id
    logging.info(f"[TRACE][HISTORY_DRM][ENTER] {describe_message(m)}")

    if m.chat.id not in AUTH_USERS:
        await bot.send_message(
            m.chat.id,
            f"<blockquote>__**Oopss! You are not a Premium member\n"
            f"PLEASE /upgrade YOUR PLAN\n"
            f"Your User id**__ - `{m.chat.id}`</blockquote>\n"
        )
        return

    editable = await m.reply_text(
        "**📥 Tracked Download**\n\n"
        "<blockquote><b>Send your .txt file.\n"
        "I will auto-resume if you've downloaded this batch before.</b></blockquote>"
    )

    input_msg: Message = await safe_listen(bot, m.chat.id, user_id, timeout=60)
    logging.info(f"[TRACE][HISTORY_DRM][TXT_RECEIVED] {describe_message(input_msg)}")

    if not input_msg or not input_msg.document or not input_msg.document.file_name.endswith('.txt'):
        await editable.edit("**❌ Please send a .txt file.**")
        return

    await editable.delete()

    # Download temporarily for hashing + link counting
    temp_path = await input_msg.download()
    file_name, _ = os.path.splitext(os.path.basename(temp_path))

    try:
        with open(temp_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        with open(temp_path, "r", errors="ignore") as f:
            content = f.read()

    raw_links = []
    for line in content.split("\n"):
        _l = line.strip()
        if _l.startswith("//"):
            _l = "https:" + _l
        elif "://" not in _l and ": //" in _l:
            _l = _l.replace(": //", ": https://", 1)
        if "://" in _l:
            raw_links.append("https://" + _l.split("://", 1)[1].strip())

    is_resumable = False
    resume_index = 0
    stored_b_name = ""
    stored_channel_id = None
    stored_topic_map = {}
    file_hash = None

    if _HISTORY_ENABLED and raw_links:
        try:
            file_hash, resume_index, _ = await check_and_get_resume_info(
                file_path=temp_path,
                file_name=file_name,
                user_id=user_id,
                links=raw_links,
            )
            summary = get_history().get_progress_summary(file_hash)
            is_resumable = (
                summary.get("can_resume") and
                summary.get("completed", 0) > 0 and
                summary.get("status") != "completed"
            )
            if is_resumable:
                _saved_meta = (get_history().get_entry(file_hash) or {}).get("metadata", {})
                stored_b_name    = _saved_meta.get("batch_name", "")
                stored_channel_id = _saved_meta.get("channel_id")
                stored_topic_map  = _saved_meta.get("topic_map", {})
            else:
                stored_channel_id = None
                stored_topic_map  = {}
        except Exception as e:
            print(f"[History] Error checking history: {e}")
            stored_channel_id = None
            stored_topic_map  = {}

    try:
        os.remove(temp_path)
    except Exception:
        pass

    # ── Show resume scan result ───────────────────────────────────────────────
    if is_resumable:
        summary = get_history().get_progress_summary(file_hash)
        prog    = summary.get("progress_percent", 0)
        done    = summary.get("completed", 0)
        total   = summary.get("total_links", len(raw_links))
        scan_text = (
            f"<b>♻️ Resumable Download Detected!</b>\n\n"
            f"<blockquote>"
            f"📂 <b>File:</b> <code>{file_name}</code>\n"
            f"📊 <b>Progress:</b> {prog}% ({done}/{total} done)\n"
            f"⏩ <b>Resume from:</b> link #{resume_index + 1}\n"
            f"📚 <b>Batch:</b> <code>{stored_b_name or file_name.replace('_', ' ')}</code>"
            f"</blockquote>"
        )
    else:
        scan_text = (
            f"<b>📥 New Download</b>\n\n"
            f"<blockquote>"
            f"📂 <b>File:</b> <code>{file_name}</code>\n"
            f"🔗 <b>Links found:</b> {len(raw_links)}\n"
            f"✨ No previous history — starting fresh."
            f"</blockquote>"
        )
    await m.reply_text(scan_text, parse_mode=enums.ParseMode.HTML)

    # ── Ask for destination chat ID / channel ─────────────────────────────────
    dest_editable = await m.reply_text(
        "<b>📢 Destination Chat</b>\n\n"
        "<blockquote><i>Send the <b>Channel ID</b> or <b>Group ID</b> to upload to.\n"
        "🔹 Make me an admin there first.\n"
        "🔸 Use /id in the target chat to get its ID.\n"
        "Example: <code>-100XXXXXXXXXXX</code>\n\n"
        "Send /d to upload here instead.</i></blockquote>",
        parse_mode=enums.ParseMode.HTML,
    )
    try:
        dest_input: Message = await safe_listen(bot, m.chat.id, user_id, timeout=60)
        if dest_input is None:
            dest_raw = '/d'
        else:
            dest_raw = dest_input.text.strip()
            await dest_input.delete(True)
    except asyncio.TimeoutError:
        dest_raw = '/d'
    await dest_editable.delete()

    if "/d" in dest_raw:
        final_channel_id = m.chat.id
    else:
        final_channel_id = dest_raw

    # Set override so drm_handler knows what to do
    globals.history_override = {
        "file_hash":    file_hash,
        "is_resumable": is_resumable,
        "resume_index": resume_index,
        "b_name":       stored_b_name or file_name.replace('_', ' '),
        "channel_id":   final_channel_id,
        "topic_map":    stored_topic_map,
    }

    # Hand off to drm_handler (it will re-download the file itself)
    await drm_handler(bot, input_msg)
    logging.info(f"[TRACE][HISTORY_DRM][HANDOFF_COMPLETE] {describe_message(input_msg)}")


# ============================================================
# FIX: Updated register_drm_handlers with proper filtering
# ============================================================
def register_drm_handlers(bot):
    from pyrogram import filters as f

    bot.on_message(f.command("history") & f.private, group=0)(history_drm_handler)

    def is_valid_download_message(_, __, message):
        """
        Custom filter to prevent duplicate handler triggers:
        1. Excludes commands (messages starting with /)
        2. Only accepts .txt documents or text with URLs
        3. Checks if user is in active conversation (prevents infinite loops)
        """
        user_id = message.from_user.id
        msg_key = _download_message_key(message)
        logging.debug(
            f"[TRACE][DRM_FILTER][CHECK] key={msg_key} active={user_id in globals.active_conversations} "
            f"listener_consumed={msg_key in globals.listener_consumed_messages if msg_key else False} "
            f"processed={msg_key in globals.processed_download_messages if msg_key else False} "
            f"{describe_message(message)}"
        )

        if BOT_ID and user_id == BOT_ID:
            logging.warning(f"[TRACE][DRM_FILTER][REJECT_SELF_MESSAGE] key={msg_key} bot_id={BOT_ID} {describe_message(message)}")
            return False

        if getattr(message, "outgoing", False):
            logging.warning(f"[TRACE][DRM_FILTER][REJECT_OUTGOING] key={msg_key} {describe_message(message)}")
            return False
        
        if user_id in globals.active_conversations:
            logging.debug(f"[TRACE][DRM_FILTER][REJECT_ACTIVE_CONVERSATION] key={msg_key}")
            return False

        if msg_key and msg_key in globals.listener_consumed_messages:
            logging.warning(f"[TRACE][DRM_FILTER][REJECT_LISTENER_CONSUMED] key={msg_key} {describe_message(message)}")
            return False

        if msg_key and msg_key in globals.processed_download_messages:
            logging.warning(f"[TRACE][DRM_FILTER][REJECT_ALREADY_PROCESSED] key={msg_key} {describe_message(message)}")
            return False
        
        if message.text and message.text.startswith('/'):
            logging.debug(f"[TRACE][DRM_FILTER][REJECT_COMMAND] key={msg_key}")
            return False
        
        if message.document and message.document.file_name:
            fname = message.document.file_name
            if fname.startswith('failed_') or fname.startswith('Failed_'):
                logging.debug(f"[TRACE][DRM_FILTER][REJECT_FAILED_REPORT] key={msg_key} file_name={fname!r}")
                return False
            logging.debug(f"[TRACE][DRM_FILTER][DOCUMENT_DECISION] key={msg_key} file_name={fname!r} accept={fname.endswith('.txt')}")
            return fname.endswith('.txt')
        
        if message.text and '://' in message.text:
            logging.debug(f"[TRACE][DRM_FILTER][ACCEPT_TEXT_URL] key={msg_key}")
            return True
        
        logging.debug(f"[TRACE][DRM_FILTER][REJECT_NO_MATCH] key={msg_key}")
        return False
    
    custom_filter = f.create(is_valid_download_message)
    bot.on_message(f.private & custom_filter, group=10)(drm_handler)

    # ── Register "Forward All" callback handlers ──────────────────────────
    # fwd_<digits> — initial menu (in channel, shows options in user PM)
    bot.on_callback_query(f.regex(r"^fwd_\d+$") & f.user(AUTH_USERS), group=5)(_fwd_all_callback_handler)
    # fwd_saved|<key>, fwd_custom|<key>, fwd_links|<key> — action sub-buttons (in user PM)
    bot.on_callback_query(f.regex(r"^fwd_(saved|custom|links)\|") & f.user(AUTH_USERS), group=6)(_fwd_action_callback_handler)
    # fwd_done, fwd_busy — no-op callbacks
    bot.on_callback_query(f.regex(r"^fwd_(done|busy)$") & f.user(AUTH_USERS), group=7)(lambda c, cb: cb.answer())

    # ── Register "Forward to Custom Chat" text/forward handler ─────────────
    # This listens in PM for the user's chat ID/@username input
    async def _fwd_pm_filter(_, __, message):
        """Only process PM messages from users who have pending forward requests."""
        if not message.chat or message.chat.id != message.from_user.id:
            return False  # Not a PM
        return message.from_user.id in _fwd_pending_chat
    bot.on_message(f.create(_fwd_pm_filter), group=8)(_fwd_chat_input_handler)
