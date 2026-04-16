import random
import time
import math
import os
from vars import CREDIT
from pyrogram.errors import FloodWait
from pyrogram import filters as pyro_filters
from datetime import datetime, timedelta
import globals as _globals
from logs import logging


def message_key(message):
    chat_id = getattr(getattr(message, "chat", None), "id", None)
    message_id = getattr(message, "id", None)
    return f"{chat_id}:{message_id}" if chat_id is not None and message_id is not None else None


def describe_message(message):
    if not message:
        return "None"
    chat = getattr(message, "chat", None)
    user = getattr(message, "from_user", None)
    doc = getattr(message, "document", None)
    text = getattr(message, "text", None)
    caption = getattr(message, "caption", None)
    file_name = getattr(doc, "file_name", None) if doc else None
    return (
        f"key={message_key(message)} chat_id={getattr(chat, 'id', None)} "
        f"chat_type={getattr(chat, 'type', None)} user_id={getattr(user, 'id', None)} "
        f"message_id={getattr(message, 'id', None)} text={text[:80] if text else None!r} "
        f"caption={caption[:80] if caption else None!r} document={bool(doc)} file_name={file_name!r}"
    )


def _prune_message_registry(registry, ttl=3600):
    now = time.time()
    stale_before = now - ttl
    for key, seen_at in list(registry.items()):
        if seen_at < stale_before:
            registry.pop(key, None)


def mark_listener_consumed(message, source="safe_listen"):
    key = message_key(message)
    if not key:
        return None
    _prune_message_registry(_globals.listener_consumed_messages)
    _globals.listener_consumed_messages[key] = time.time()
    logging.debug(f"[TRACE][LISTENER_CONSUMED][{source}] {describe_message(message)}")
    return key


async def safe_listen(bot, chat_id, user_id, timeout=60, filters=None, cancel_on_command=False):
    """
    Wrapper for bot.listen() that registers the user as 'in active conversation'
    so that the drm_handler on_message filter does not also fire on the same message.
    Uses a reference counter so an outer lock (e.g. from drm_handler) is not dropped
    prematurely when a nested safe_listen call finishes.
    Set cancel_on_command=True to treat slash-command replies as cancellation (None).
    """
    logging.debug(
        f"[TRACE][SAFE_LISTEN][START] chat_id={chat_id} user_id={user_id} timeout={timeout} "
        f"filters={filters!r} cancel_on_command={cancel_on_command} "
        f"active_before={dict(_globals.active_conversations)}"
    )
    _globals.active_conversations[user_id] = _globals.active_conversations.get(user_id, 0) + 1
    try:
        result = await bot.listen(
            filters=filters,
            timeout=timeout,
            chat_id=chat_id,
            user_id=user_id,
        )
        logging.debug(f"[TRACE][SAFE_LISTEN][RESULT] {describe_message(result)}")
        mark_listener_consumed(result)
        if cancel_on_command and result and result.text and result.text.strip().startswith('/'):
            logging.debug(f"[TRACE][SAFE_LISTEN][CANCEL_COMMAND] {describe_message(result)}")
            return None
        return result
    except Exception as e:
        logging.exception(f"[TRACE][SAFE_LISTEN][ERROR] chat_id={chat_id} user_id={user_id} error={e}")
        return None
    finally:
        _count = _globals.active_conversations.get(user_id, 0) - 1
        if _count <= 0:
            _globals.active_conversations.pop(user_id, None)
        else:
            _globals.active_conversations[user_id] = _count
        logging.debug(
            f"[TRACE][SAFE_LISTEN][END] chat_id={chat_id} user_id={user_id} "
            f"active_after={dict(_globals.active_conversations)}"
        )


class Timer:
    def __init__(self, time_between=5):
        self.start_time = time.time()
        self.time_between = time_between

    def can_send(self):
        if time.time() > (self.start_time + self.time_between):
            self.start_time = time.time()
            return True
        return False


def hrb(value, digits=2, delim="", postfix=""):
    """Return a human-readable file size."""
    if value is None:
        return None
    chosen_unit = "B"
    for unit in ("KB", "MB", "GB", "TB"):
        if value > 1000:
            value /= 1024
            chosen_unit = unit
        else:
            break
    return f"{value:.{digits}f}" + delim + chosen_unit + postfix


def hrt(seconds, precision=0):
    """Return a human-readable time delta as a string."""
    pieces = []
    value = timedelta(seconds=seconds)

    if value.days:
        pieces.append(f"{value.days}day")

    seconds = value.seconds

    if seconds >= 3600:
        hours = int(seconds / 3600)
        pieces.append(f"{hours}hr")
        seconds -= hours * 3600

    if seconds >= 60:
        minutes = int(seconds / 60)
        pieces.append(f"{minutes}min")
        seconds -= minutes * 60

    if seconds > 0 or not pieces:
        pieces.append(f"{seconds}sec")

    if not precision:
        return "".join(pieces)

    return "".join(pieces[:precision])


timer = Timer()


async def progress_bar(current, total, reply, start):
    if timer.can_send():
        now = time.time()
        diff = now - start
        if diff < 1:
            return
        else:
            perc = f"{current * 100 / total:.1f}%"
            elapsed_time = round(diff)
            speed = current / elapsed_time
            remaining_bytes = total - current
            if speed > 0:
                eta_seconds = remaining_bytes / speed
                eta = hrt(eta_seconds, precision=1)
            else:
                eta = "-"
            sp = str(hrb(speed)) + "/s"
            tot = hrb(total)
            cur = hrb(current)
            bar_length = 10
            completed_length = int(current * bar_length / total)
            remaining_length = bar_length - completed_length

            symbol_pairs = [
                ("🟩", "⬜")
            ]
            chosen_pair = random.choice(symbol_pairs)
            completed_symbol, remaining_symbol = chosen_pair

            progress_bar = completed_symbol * completed_length + remaining_symbol * remaining_length

            try:
                await reply.edit(f'<blockquote>`╭──⌯═════𝐁𝐨𝐭 𝐒𝐭𝐚𝐭𝐢𝐜𝐬══════⌯──╮\n├⚡ {progress_bar}\n├⚙️ Progress ➤ | {perc} |\n├🚀 Speed ➤ | {sp} |\n├📟 Processed ➤ | {cur} |\n├🧲 Size ➤ | {tot} |\n├🕑 ETA ➤ | {eta} |\n╰─═══✨🦋{CREDIT}🦋✨═══─╯`</blockquote>')
            except FloodWait as e:
                time.sleep(e.x)
