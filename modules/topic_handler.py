"""
Telegram Forum Topics Handler
==============================
Handles automatic topic creation and message routing to specific topics
in Telegram groups/channels with the Topics feature enabled.
"""

import os
import re
import json
import asyncio
from datetime import datetime
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from pyrogram.errors import BadRequest, Forbidden, FloodWait, ChatAdminRequired, TopicDeleted
from vars import OWNER
from utils import safe_listen

try:
    from txt_topic_parser import parse_txt_file, get_topics_from_txt, get_content_for_topic
    TXT_PARSER_AVAILABLE = True
except ImportError:
    TXT_PARSER_AVAILABLE = False

TOPIC_CONFIG_FILE = "topic_config.json"
TOPIC_MEMORY_FILE = "topic_memory.json"


# ---------------------------------------------------------------------------
# Topic Memory — persistent JSON store for /gettopicid + /linktopics
# ---------------------------------------------------------------------------

def _load_topic_memory() -> dict:
    """Load topic memory from JSON file."""
    if os.path.exists(TOPIC_MEMORY_FILE):
        try:
            with open(TOPIC_MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"channels": {}, "mappings": {}}


def _save_topic_memory(memory: dict) -> None:
    """Save topic memory atomically."""
    tmp = TOPIC_MEMORY_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)
    os.replace(tmp, TOPIC_MEMORY_FILE)


def _mem_get_channel_topics(channel_id) -> dict:
    """Return saved topics dict for a channel {thread_id_str: {name, id, link}}."""
    mem = _load_topic_memory()
    return mem["channels"].get(str(channel_id), {}).get("topics", {})


def _mem_save_topic(channel_id, thread_id: int, topic_name: str, link: str) -> None:
    """Save a single topic to memory."""
    mem = _load_topic_memory()
    key = str(channel_id)
    if key not in mem["channels"]:
        mem["channels"][key] = {"topics": {}, "last_updated": ""}
    mem["channels"][key]["topics"][str(thread_id)] = {
        "name": topic_name,
        "id": thread_id,
        "link": link,
    }
    mem["channels"][key]["last_updated"] = datetime.now().isoformat()
    _save_topic_memory(mem)


def _mem_get_mapping(channel_id) -> dict:
    """Return saved txt→topic mapping for a channel {txt_name: {topic_id, topic_name, topic_link}}."""
    mem = _load_topic_memory()
    return mem.get("mappings", {}).get(str(channel_id), {})


def _mem_save_mapping(channel_id, mapping: dict) -> None:
    """Persist txt→topic mapping in memory."""
    mem = _load_topic_memory()
    if "mappings" not in mem:
        mem["mappings"] = {}
    mem["mappings"][str(channel_id)] = mapping
    _save_topic_memory(mem)


def _norm(s: str) -> str:
    """Normalise for fuzzy matching."""
    return re.sub(r'[^a-z0-9]', '', s.lower())

DEFAULT_TOPICS = {
    "notices": {"name": "📢 Notices", "icon": "📢"},
    "uploads": {"name": "📤 Uploads", "icon": "📤"},
    "videos": {"name": "🎥 Videos", "icon": "🎥"},
    "pdfs": {"name": "📄 PDFs", "icon": "📄"},
    "general": {"name": "💬 General", "icon": "💬"},
}

CATEGORY_TOPICS = {
    "video": "videos",
    "pdf": "pdfs",
    "notice": "notices",
    "upload": "uploads",
}


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _make_topic_link(chat_id, topic_id: int) -> str:
    """Return standard https://t.me/c/XXXXX/topic_id link."""
    cid = str(int(chat_id))
    if cid.startswith('-100'):
        cid = cid[4:]
    elif cid.startswith('-'):
        cid = cid[1:]
    return f"https://t.me/c/{cid}/{topic_id}"


async def fetch_channel_topics(client: Client, chat_id) -> list:
    """Fetch all forum topics from a channel/group via raw API.
    Returns list of (topic_id, topic_name) tuples.
    """
    from pyrogram import raw
    try:
        peer = await client.resolve_peer(chat_id)
        result = await client.invoke(
            raw.functions.channels.GetForumTopics(
                channel=peer,
                offset_date=0,
                offset_id=0,
                offset_topic=0,
                limit=100,
                q=""
            )
        )
        return [(t.id, t.title) for t in result.topics if hasattr(t, 'title')]
    except Exception as e:
        print(f"[TopicHandler] fetch_channel_topics error: {e}")
        return []


def get_txt_topic_mapping(channel_id) -> dict:
    """Load saved txt→topic_id mapping for a channel.
    Checks both the new topic_memory.json and the legacy topic_config.json.
    Returns {txt_topic_name: topic_id} dict.
    """
    # New memory source: {txt_name: {topic_id, topic_name, topic_link}}
    mem_mapping = _mem_get_mapping(channel_id)
    result = {name: info["topic_id"] for name, info in mem_mapping.items() if "topic_id" in info}

    # Legacy source: {txt_name: topic_id}
    config = load_topic_config()
    legacy = config.get(str(channel_id), {}).get("txt_topic_mapping", {})
    for k, v in legacy.items():
        if k not in result:
            result[k] = v
    return result


def save_txt_topic_mapping(channel_id, mapping: dict):
    """Persist txt→topic_id mapping for a channel."""
    config = load_topic_config()
    key = str(channel_id)
    if key not in config:
        config[key] = {}
    config[key]["txt_topic_mapping"] = mapping
    save_topic_config(config)


def load_topic_config() -> dict:
    if os.path.exists(TOPIC_CONFIG_FILE):
        try:
            with open(TOPIC_CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_topic_config(config: dict):
    with open(TOPIC_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_chat_config(chat_id: int) -> dict:
    config = load_topic_config()
    key = str(chat_id)
    if key not in config:
        config[key] = {
            "topics": {},
            "txt_topics": {},
            "default_topic": None,
            "auto_create": True,
            "category_mapping": CATEGORY_TOPICS.copy(),
        }
        save_topic_config(config)
    return config[key]


def update_chat_config(chat_id: int, chat_config: dict):
    config = load_topic_config()
    config[str(chat_id)] = chat_config
    save_topic_config(config)


# ---------------------------------------------------------------------------
# Core topic operations
# ---------------------------------------------------------------------------

async def create_forum_topic(client: Client, chat_id: int, topic_name: str, icon_color: int = None):
    """Create a forum topic using the raw API for reliability.
    Returns (topic_id, error_str) — topic_id is the message thread ID on success.
    """
    from pyrogram import raw as pyrogram_raw

    async def _do_create():
        peer = await client.resolve_peer(chat_id)
        r = await client.invoke(
            pyrogram_raw.functions.messages.CreateForumTopic(
                peer=peer,
                title=topic_name,
                random_id=client.rnd_id(),
                icon_color=icon_color,
            )
        )
        # Walk all updates to find the service message — its ID is the topic ID
        for update in r.updates:
            msg = getattr(update, "message", None)
            if msg and getattr(msg, "id", None):
                return msg.id
        # Fallback: try updates[1] if the walk found nothing
        if len(r.updates) > 1:
            msg = getattr(r.updates[1], "message", None)
            if msg:
                return msg.id
        return None

    try:
        topic_id = await _do_create()
        if topic_id:
            return topic_id, None
        return None, "Could not extract topic ID from Telegram response"
    except FloodWait as e:
        print(f"[TopicHandler] FloodWait {e.value}s creating '{topic_name}' — waiting...")
        await asyncio.sleep(e.value + 1)
        try:
            topic_id = await _do_create()
            if topic_id:
                return topic_id, None
            return None, "FloodWait retry: could not extract topic ID"
        except Exception as retry_err:
            return None, f"FloodWait retry failed: {retry_err}"
    except ChatAdminRequired:
        return None, "Bot needs Admin + Manage Topics permission"
    except Forbidden as e:
        return None, f"Forbidden: {e}"
    except BadRequest as e:
        return None, f"BadRequest: {e}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


async def get_or_create_topic(client: Client, chat_id: int, topic_name: str,
                               topic_key: str, content_type: str = "video"):
    """Return (topic_id, error) — topic_id is None if creation failed."""
    chat_config = get_chat_config(chat_id)

    if topic_key in chat_config["txt_topics"]:
        return chat_config["txt_topics"][topic_key], None

    try:
        async for topic in client.get_forum_topics(chat_id):
            clean = topic.title.lower().lstrip("🎥📄📁📢📤💬 ").strip()
            if clean == topic_name.lower().lstrip("🎥📄📁📢📤💬 ").strip():
                chat_config["txt_topics"][topic_key] = topic.id
                update_chat_config(chat_id, chat_config)
                return topic.id, None
    except Exception as e:
        print(f"[TopicHandler] get_forum_topics failed: {e}")

    topic_id, err = await create_forum_topic(client, chat_id, topic_name)
    if topic_id:
        chat_config["txt_topics"][topic_key] = topic_id
        update_chat_config(chat_id, chat_config)
    return topic_id, err


async def setup_topics_from_txt(client: Client, chat_id: int, txt_file_path: str) -> tuple:
    """Parse txt file and create topics.
    Returns (created_topics dict, parsed_count int, errors list).
    """
    if not TXT_PARSER_AVAILABLE:
        return {}, 0, ["TXT parser module not available"]

    topics = parse_txt_file(txt_file_path)
    parsed_count = len(topics)
    if not topics:
        return {}, 0, []

    created_topics = {}
    errors = []
    for topic_key, topic in topics.items():
        topic_id, err = await get_or_create_topic(
            client, chat_id, topic.topic_name, topic_key, topic.content_type
        )
        if topic_id:
            created_topics[topic_key] = {
                "topic_id": topic_id,
                "topic_name": topic.topic_name,
                "content_type": topic.content_type,
                "content_count": len(topic.contents),
            }
        else:
            errors.append(f"'{topic.topic_name}': {err or 'unknown error'}")
    return created_topics, parsed_count, errors


async def setup_default_topics(client: Client, chat_id: int) -> dict:
    """Create default topics (notices, uploads, videos, pdfs, general)."""
    chat_config = get_chat_config(chat_id)
    created_topics = {}

    for topic_key, topic_info in DEFAULT_TOPICS.items():
        if topic_key in chat_config["topics"]:
            created_topics[topic_key] = chat_config["topics"][topic_key]
            continue

        topic_id, err = await create_forum_topic(client, chat_id, topic_info["name"])
        if topic_id:
            created_topics[topic_key] = topic_id
            chat_config["topics"][topic_key] = topic_id
        elif err:
            print(f"[TopicHandler] Failed to create default topic '{topic_info['name']}': {err}")

    if "general" in created_topics and not chat_config.get("default_topic"):
        chat_config["default_topic"] = created_topics["general"]

    update_chat_config(chat_id, chat_config)
    return created_topics


async def send_to_topic(client: Client, chat_id: int, topic_name: str, **kwargs):
    """Send a message/document/video to a named topic (falls back gracefully)."""
    chat_config = get_chat_config(chat_id)
    topic_id = (
        chat_config.get("txt_topics", {}).get(topic_name)
        or chat_config["topics"].get(topic_name)
    )
    if topic_id:
        kwargs["message_thread_id"] = topic_id

    async def _send():
        if "video" in kwargs:
            return await client.send_video(chat_id, **kwargs)
        elif "document" in kwargs:
            return await client.send_document(chat_id, **kwargs)
        elif "photo" in kwargs:
            return await client.send_photo(chat_id, **kwargs)
        else:
            return await client.send_message(chat_id, **kwargs)

    try:
        return await _send()
    except Exception as e:
        print(f"[TopicHandler] Error sending to topic: {e}")
        kwargs.pop("message_thread_id", None)
        try:
            return await _send()
        except Exception:
            return None


def get_topic_id_for_category(chat_id: int, category: str):
    chat_config = get_chat_config(chat_id)
    mapping = chat_config.get("category_mapping", CATEGORY_TOPICS)
    topic_name = mapping.get(category.lower())
    if topic_name:
        return (
            chat_config.get("txt_topics", {}).get(topic_name)
            or chat_config["topics"].get(topic_name)
        )
    return chat_config.get("default_topic")


def get_topic_id_for_txt_topic(chat_id: int, txt_topic_key: str):
    chat_config = get_chat_config(chat_id)
    return chat_config.get("txt_topics", {}).get(txt_topic_key)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def create_topic_command(client: Client, message: Message):
    """Command: /createtopic <name>"""
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply_text(
            "**Usage:** `/createtopic <topic_name>`\n\n"
            "**Example:** `/createtopic 📢 Announcements`"
        )
        return

    topic_name = args[1]
    topic_id, err = await create_forum_topic(client, message.chat.id, topic_name)

    if topic_id:
        chat_config = get_chat_config(message.chat.id)
        topic_key = topic_name.lower().replace(" ", "_")
        topic_key = ''.join(c for c in topic_key if c.isalnum() or c == '_')
        chat_config["topics"][topic_key] = topic_id
        update_chat_config(message.chat.id, chat_config)
        await message.reply_text(
            f"**✅ Topic Created!**\n\n"
            f"**Name:** {topic_name}\n"
            f"**ID:** `{topic_id}`\n"
            f"**Key:** `{topic_key}`"
        )
    else:
        await message.reply_text(
            f"**❌ Failed to create topic.**\n\n"
            f"**Reason:** `{err}`\n\n"
            "Make sure:\n"
            "• This group has Topics enabled\n"
            "• Bot is admin with Manage Topics permission"
        )


async def list_topics_command(client: Client, message: Message):
    """Command: /topics — list all configured topics"""
    chat_config = get_chat_config(message.chat.id)
    has_topics = bool(chat_config["topics"]) or bool(chat_config.get("txt_topics", {}))

    if not has_topics:
        await message.reply_text(
            "**📋 No topics configured.**\n\n"
            "• `/createtopic <name>` — create a topic\n"
            "• `/setuptopics` — create default topics\n"
            "• Reply to a txt file with `/parsetxt <channel_id>` — create from file"
        )
        return

    text = "**📋 Configured Topics:**\n\n"

    if chat_config["topics"]:
        text += "**Default Topics:**\n"
        for topic_key, topic_id in chat_config["topics"].items():
            text += f"• `{topic_key}` → `{topic_id}`\n"

    if chat_config.get("txt_topics"):
        text += "\n**TXT-Generated Topics:**\n"
        for topic_key, topic_id in chat_config["txt_topics"].items():
            text += f"• `{topic_key}` → `{topic_id}`\n"

    if chat_config.get("default_topic"):
        text += f"\n**Default Topic:** `{chat_config['default_topic']}`"

    await message.reply_text(text)


async def set_topic_command(client: Client, message: Message):
    """Command: /settopic <category> <topic_id>"""
    if message.from_user and message.from_user.id != OWNER:
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply_text(
            "**Usage:** `/settopic <category> <topic_id>`\n\n"
            "**Categories:** video, pdf, notice, upload\n\n"
            "**Example:** `/settopic video 12345`"
        )
        return

    category = args[1].lower()
    try:
        topic_id = int(args[2])
    except ValueError:
        await message.reply_text("**❌ Topic ID must be a number.**")
        return

    if category not in CATEGORY_TOPICS:
        await message.reply_text(
            f"**❌ Invalid category.**\n\nValid: {', '.join(CATEGORY_TOPICS.keys())}"
        )
        return

    chat_config = get_chat_config(message.chat.id)
    chat_config["topics"][category] = topic_id
    update_chat_config(message.chat.id, chat_config)

    await message.reply_text(
        f"**✅ Topic Mapping Updated!**\n\n"
        f"**Category:** {category}\n"
        f"**Topic ID:** `{topic_id}`"
    )


async def setup_topics_command(client: Client, message: Message):
    """Command: /setuptopics — auto-create default topics"""
    if message.from_user and message.from_user.id != OWNER:
        return

    status = await message.reply_text("**🔄 Setting up default topics...**")
    created = await setup_default_topics(client, message.chat.id)

    if created:
        text = "**✅ Topics Created!**\n\n"
        for topic_key, topic_id in created.items():
            info = DEFAULT_TOPICS.get(topic_key, {"name": topic_key})
            text += f"• {info['name']} → `{topic_id}`\n"
        await status.edit(text)
    else:
        await status.edit(
            "**❌ Failed to create topics.**\n\n"
            "Make sure:\n"
            "• This group has Topics enabled\n"
            "• Bot has 'Manage Topics' permission"
        )


async def parse_txt_command(client: Client, message: Message):
    """Command: /parsetxt <channel_id> — then send txt file when prompted"""
    if message.from_user and message.from_user.id != OWNER:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply_text(
            "**Usage:** `/parsetxt -1001234567890`\n\n"
            "Replace with your actual channel/group ID.\n"
            "Bot will then ask you to send the txt file."
        )
        return

    try:
        channel_id = int(args[1].strip())
    except ValueError:
        await message.reply_text("**❌ Invalid channel ID. Must be a number like `-1001234567890`**")
        return

    prompt = await message.reply_text(
        f"**📂 Send your `.txt` file now.**\n\n"
        f"Channel/Group ID: `{channel_id}`\n"
        f"_Waiting 60 seconds..._"
    )

    file_msg = await safe_listen(client, message.chat.id, message.from_user.id, timeout=60)
    if not file_msg:
        await prompt.edit("**❌ Timed out. Please run `/parsetxt` again.**")
        return

    if not file_msg.document:
        await prompt.edit("**❌ No document received. Please run `/parsetxt` again and send a .txt file.**")
        return

    if not file_msg.document.file_name.endswith('.txt'):
        await prompt.edit("**❌ That is not a `.txt` file. Please run `/parsetxt` again.**")
        return

    await prompt.edit("**📥 Downloading txt file...**")
    txt_path = await file_msg.download()
    await prompt.edit("**🔍 Parsing txt file...**")

    created, parsed_count, errors = await setup_topics_from_txt(client, channel_id, txt_path)

    try:
        os.remove(txt_path)
    except Exception:
        pass

    if parsed_count == 0:
        await prompt.edit(
            "**❌ No topic headings found in the txt file.**\n\n"
            "Supported formats:\n\n"
            "**Format 1** — Topic as a separate heading line:\n"
            "`Notices Videos`\n"
            "`Content Name: https://url`\n\n"
            "**Format 2** — Topic inline with `[...]` prefix:\n"
            "`[Arithmetic] Class-01 | Ratio & Proportion: https://url`\n\n"
            "Lines starting with `#` are treated as comments and skipped."
        )
        return

    if created:
        text = (
            f"**✅ Topics Created in Channel!**\n\n"
            f"**Channel ID:** `{channel_id}`\n"
            f"**Parsed:** {parsed_count} topics | **Created:** {len(created)}\n\n"
        )
        for key, info in created.items():
            text += (
                f"• {info['topic_name']}\n"
                f"  ID: `{info['topic_id']}` | Type: {info['content_type']} | Files: {info['content_count']}\n"
            )
        if errors:
            text += f"\n**⚠️ {len(errors)} topic(s) failed:**\n"
            for e in errors[:5]:
                text += f"• {e}\n"
        await prompt.edit(text)
    else:
        err_sample = errors[0] if errors else "unknown"
        await prompt.edit(
            f"**❌ Found {parsed_count} topics in file but all failed to create.**\n\n"
            f"**First error:** `{err_sample}`\n\n"
            "Make sure:\n"
            "• The group/channel has Topics (Forum mode) enabled\n"
            "• Bot is admin with **Manage Topics** permission\n"
            "• The channel ID is correct (negative number like `-1001234567890`)"
        )


async def set_default_topic_command(client: Client, message: Message):
    """Command: /defaulttopic <topic_id>"""
    if message.from_user and message.from_user.id != OWNER:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply_text("**Usage:** `/defaulttopic <topic_id>`\n\nExample: `/defaulttopic 12345`")
        return

    try:
        topic_id = int(args[1])
        chat_config = get_chat_config(message.chat.id)
        chat_config["default_topic"] = topic_id
        update_chat_config(message.chat.id, chat_config)
        await message.reply_text(f"**✅ Default topic set to:** `{topic_id}`")
    except ValueError:
        await message.reply_text("**❌ Invalid topic ID. Must be a number.**")


async def get_topic_id_command(client: Client, message: Message):
    """Command: /topicid — get current topic ID (works in any group, private or public)"""
    tid = message.message_thread_id
    cid = message.chat.id
    if tid:
        link = _make_topic_link(cid, tid)
        await message.reply_text(
            f"<b>📌 Topic Info:</b>\n\n"
            f"<b>Topic ID:</b> <code>{tid}</code>\n"
            f"<b>Chat ID:</b> <code>{cid}</code>\n"
            f"<b>Link:</b> <a href=\"{link}\">{link}</a>",
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True
        )
    else:
        await message.reply_text(
            "<b>ℹ️ Not inside a topic.</b>\n\n"
            "Send <code>/topicid</code> from <b>inside a forum topic thread</b> to get its ID and link.\n\n"
            "Works in all groups (private &amp; public) as long as the group has Topics enabled.",
            parse_mode=enums.ParseMode.HTML
        )


async def gettopicid_command(client: Client, message: Message):
    """Command: /gettopicid — send inside a forum topic to auto-save its info to memory.
    
    Step 1 of the /linktopics workflow:
      Open each forum topic in your channel → send /gettopicid → bot saves Name + ID + Link.
      Once all topics are collected, run /linktopics to match them with your txt file.
    """
    cid = message.chat.id
    tid = message.message_thread_id

    if not tid:
        await message.reply_text(
            "<b>ℹ️ This is the General topic (no thread ID).</b>\n\n"
            "Please send <code>/gettopicid</code> from inside each <b>specific forum topic</b>.\n\n"
            "<b>How to use:</b>\n"
            "1. Go to your channel\n"
            "2. Open <b>each forum topic</b> one by one\n"
            "3. Send <code>/gettopicid</code> inside each one\n"
            "4. Bot auto-saves: Name, ID, and clickable link\n"
            "5. Then run <code>/linktopics</code> to match with your txt file",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    # Get the topic name via messages.GetForumTopicsByID (correct raw module)
    topic_name = f"Topic {tid}"
    try:
        from pyrogram import raw
        peer = await client.resolve_peer(cid)
        result = await client.invoke(
            raw.functions.messages.GetForumTopicsByID(
                peer=peer,
                topics=[tid],
            )
        )
        if result and result.topics:
            topic_name = result.topics[0].title
    except Exception as e:
        print(f"[gettopicid] GetForumTopicsByID failed: {e}")
        # Fallback: fetch the topic creation service message (ID == thread_id)
        # and read action.title from the raw MessageActionTopicCreate
        try:
            from pyrogram import raw
            peer = await client.resolve_peer(cid)
            msgs = await client.invoke(
                raw.functions.messages.GetMessages(
                    id=[raw.types.InputMessageID(id=tid)]
                )
            )
            for m in getattr(msgs, "messages", []):
                if hasattr(m, "action") and isinstance(
                    m.action, raw.types.MessageActionTopicCreate
                ):
                    topic_name = m.action.title
                    break
        except Exception as e2:
            print(f"[gettopicid] Fallback also failed: {e2}")

    link = _make_topic_link(cid, tid)
    _mem_save_topic(cid, tid, topic_name, link)

    all_topics = _mem_get_channel_topics(cid)
    total = len(all_topics)

    topic_list = "\n".join(
        f"  • {t['name']} — ID: <code>{t['id']}</code>"
        for t in sorted(all_topics.values(), key=lambda x: x["id"])
    )

    await message.reply_text(
        f"<b>✅ Topic saved to memory!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>📌 Name:</b> {topic_name}\n"
        f"<b>🔢 ID:</b> <code>{tid}</code>\n"
        f"<b>💬 Chat ID:</b> <code>{cid}</code>\n"
        f"<b>🔗 Link:</b> <a href=\"{link}\">{link}</a>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>Total topics saved for this channel: {total}</b>\n\n"
        f"{topic_list}\n\n"
        f"💡 Send <code>/gettopicid</code> in the next topic to continue collecting!\n"
        f"When done, run <code>/linktopics</code> to match with your txt file.",
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def showtopics_command(client: Client, message: Message):
    """Command: /showtopics — show all saved topics across all channels."""
    mem = _load_topic_memory()
    channels = mem.get("channels", {})
    mappings = mem.get("mappings", {})

    if not channels:
        await message.reply_text(
            "<b>📭 No channels saved yet.</b>\n\n"
            "Send <code>/gettopicid</code> inside each forum topic of a channel to start collecting!\n\n"
            "<b>Workflow:</b>\n"
            "1. Go into each forum topic → send <code>/gettopicid</code>\n"
            "2. Run <code>/linktopics</code> to match with your txt file",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    lines = ["<b>📊 Saved Topics Overview</b>\n━━━━━━━━━━━━━━━━━━\n"]
    for ch_id, ch_data in channels.items():
        topics = ch_data.get("topics", {})
        mapping = mappings.get(ch_id, {})
        lines.append(f"<b>💬 Channel:</b> <code>{ch_id}</code>")
        lines.append(f"   Topics saved: {len(topics)}")
        if mapping:
            lines.append(f"   Mappings: {len(mapping)}")
        if topics:
            for t in sorted(topics.values(), key=lambda x: x["id"]):
                lines.append(
                    f"   • <b>{t['name']}</b> — ID: <code>{t['id']}</code>\n"
                    f"     <a href=\"{t['link']}\">{t['link']}</a>"
                )
        lines.append("")

    text = "\n".join(lines)
    MAX = 3800
    chunks = [text[i:i+MAX] for i in range(0, len(text), MAX)] if len(text) > MAX else [text]
    await message.reply_text(chunks[0], parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)
    for c in chunks[1:]:
        await message.reply_text(c, parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)


async def showmapping_command(client: Client, message: Message):
    """Command: /showmapping <channel_id> — show saved topic mapping for a channel."""
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply_text(
            "<b>Usage:</b> <code>/showmapping -1001234567890</code>",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    ch_id = args[1].strip()
    mapping = _mem_get_mapping(ch_id)

    if not mapping:
        await message.reply_text(
            f"<b>📭 No mapping found for channel:</b> <code>{ch_id}</code>\n\n"
            f"Run <code>/linktopics</code> to create one.",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    lines = [f"<b>🔗 Topic Mapping for</b> <code>{ch_id}</code> ({len(mapping)} topics)\n━━━━━━━━━━━━━━━━━━\n"]
    for txt_name, info in mapping.items():
        tid = info.get("topic_id", "?")
        tname = info.get("topic_name", txt_name)
        tlink = info.get("topic_link", "")
        lines.append(
            f"<b>📄 {txt_name}</b>\n"
            f"   → {tname} (ID: <code>{tid}</code>)\n"
            + (f"   🔗 <a href=\"{tlink}\">{tlink}</a>" if tlink else "")
        )

    text = "\n\n".join(lines)
    MAX = 3800
    chunks = [text[i:i+MAX] for i in range(0, len(text), MAX)] if len(text) > MAX else [text]
    await message.reply_text(chunks[0], parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)
    for c in chunks[1:]:
        await message.reply_text(c, parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)


async def clearmemory_command(client: Client, message: Message):
    """Command: /clearmemory <channel_id|all> — clear saved topic memory."""
    if message.from_user and message.from_user.id != OWNER:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply_text(
            "<b>Usage:</b>\n"
            "<code>/clearmemory -1001234567890</code> — clear one channel\n"
            "<code>/clearmemory all</code> — clear everything",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    target = args[1].strip()
    mem = _load_topic_memory()

    if target.lower() == "all":
        _save_topic_memory({"channels": {}, "mappings": {}})
        await message.reply_text("🗑️ <b>All memory cleared!</b>", parse_mode=enums.ParseMode.HTML)
    elif target in mem.get("channels", {}):
        mem["channels"].pop(target, None)
        mem.get("mappings", {}).pop(target, None)
        _save_topic_memory(mem)
        await message.reply_text(
            f"🗑️ Memory cleared for channel: <code>{target}</code>",
            parse_mode=enums.ParseMode.HTML,
        )
    else:
        await message.reply_text(
            f"<b>❌ Channel not found in memory:</b> <code>{target}</code>",
            parse_mode=enums.ParseMode.HTML,
        )


async def parse_topics_command(client: Client, message: Message):
    """Command: /parsetopics — send a txt file to preview topics found in it.
    Shows topic names and any [id] prefixes already set.
    """
    prompt = await message.reply_text(
        "<b>📂 Send your .txt file now.</b>\n\n"
        "<i>I will show all topic headings found and whether they have IDs set.</i>\n\n"
        "<i>Waiting 60 seconds...</i>",
        parse_mode=enums.ParseMode.HTML
    )

    file_msg = await safe_listen(client, message.chat.id, message.from_user.id, timeout=60)
    if not file_msg:
        await prompt.edit("**❌ Timed out. Please run `/parsetopics` again.**")
        return

    if not file_msg.document:
        await prompt.edit("**❌ No file received. Please run `/parsetopics` again.**")
        return

    if not file_msg.document.file_name.endswith('.txt'):
        await prompt.edit("**❌ That is not a `.txt` file. Please run `/parsetopics` again.**")
        return

    await prompt.edit("**🔍 Parsing topics from file...**")
    txt_path = await file_msg.download()

    try:
        import re as _re
        topics_found = []
        seen_topic_names = set()
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # Handle inline [Topic Name] prefix on content lines (with URL)
                if '://' in line:
                    inline_match = _re.match(r'^\[([^\]]+)\]\s*(.*)', line)
                    if inline_match:
                        topic_name = inline_match.group(1).strip()
                        if topic_name and topic_name not in seen_topic_names:
                            seen_topic_names.add(topic_name)
                            # Check if topic_name is a numeric ID
                            if topic_name.isdigit():
                                rest = inline_match.group(2).strip()
                                # rest may have content name before ://
                                name_part = rest.split('://')[0].strip().rstrip(':').strip()
                                topics_found.append((name_part or topic_name, int(topic_name)))
                            else:
                                topics_found.append((topic_name, None))
                    continue
                # Match [numeric_id] Topic Name or [Topic Name]
                bracket_match = _re.match(r'^\[([^\]]+)\]\s*(.*)', line)
                if bracket_match:
                    _inner = bracket_match.group(1).strip()
                    _after = bracket_match.group(2).strip()
                    if _inner.lstrip('-').isdigit():
                        # [12345] Topic Name → numeric ID prefix
                        topics_found.append((_after or _inner, int(_inner)))
                    else:
                        # [TopicName] or [TopicName] extra text → use inner as topic
                        _label = _inner + (' ' + _after if _after else '')
                        topics_found.append((_label.strip(), None))
                else:
                    topics_found.append((line, None))
    except Exception as e:
        await prompt.edit(f"**❌ Failed to read file:** `{e}`")
        return
    finally:
        try:
            os.remove(txt_path)
        except Exception:
            pass

    if not topics_found:
        await prompt.edit(
            "<b>❌ No topic headings found.</b>\n\n"
            "Lines without <code>://</code> (and not starting with <code>#</code>) are treated as topic names.\n\n"
            "<b>Example format:</b>\n"
            "<code>[12345] Batch Demo Videos videos</code>\n"
            "<code>Content Name://url...</code>",
            parse_mode=enums.ParseMode.HTML
        )
        return

    def esc(text):
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    no_id = sum(1 for _, t in topics_found if t is None)

    topic_lines = []
    for idx, (name, tid) in enumerate(topics_found, 1):
        if tid:
            topic_lines.append(
                f"<b>{idx}.</b> <code>{esc(name)}</code>\n"
                f"    ↳ ID: <code>{tid}</code> ✅"
            )
        else:
            topic_lines.append(
                f"<b>{idx}.</b> <code>{esc(name)}</code>\n"
                f"    ↳ No ID set ⚠️"
            )

    if no_id:
        footer = (
            f"\n<b>⚠️ {no_id} topic(s) have no ID yet.</b>\n"
            "Go into each topic in your group → send <code>/topicid</code> → copy the ID.\n"
            "Then edit your txt file:\n"
            "<code>[12345] Topic Name</code>"
        )
    else:
        footer = "\n<b>✅ All topics have IDs — ready to upload!</b>"

    # Split into chunks of max 4000 chars to avoid MESSAGE_TOO_LONG
    MAX_LEN = 4000
    chunks = []
    current = f"<b>📋 Topics found ({len(topics_found)}):</b>\n\n"
    for line in topic_lines:
        entry = line + "\n\n"
        if len(current) + len(entry) > MAX_LEN:
            chunks.append(current.rstrip())
            current = entry
        else:
            current += entry
    current += footer
    chunks.append(current.rstrip())

    await prompt.edit(chunks[0], parse_mode=enums.ParseMode.HTML)
    for chunk in chunks[1:]:
        await message.reply_text(chunk, parse_mode=enums.ParseMode.HTML)


async def link_topics_command(client: Client, message: Message):
    """Command: /linktopics
    Flow (memory-based — no API fetch needed):
      1. Ask for channel ID
      2. Show all topics saved via /gettopicid
      3. Ask for txt file
      4. Parse topic names from txt
      5. Auto-match txt topics → saved topics (case-insensitive, partial)
      6. Save mapping permanently
    After this, DRM upload auto-routes videos to correct topics.
    """
    user_id = message.from_user.id if message.from_user else OWNER

    def esc(t):
        return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    prompt = await message.reply_text(
        "<b>🔗 Link Topics Setup</b>\n\n"
        "Send the <b>Channel ID</b> where your forum topics are.\n"
        "<i>Example: <code>-1001234567890</code></i>\n\n"
        "⚠️ Make sure you've already sent <code>/gettopicid</code> in each topic first!\n\n"
        "<i>Waiting 60 seconds...</i>",
        parse_mode=enums.ParseMode.HTML,
    )

    # Step 1 — channel ID
    cid_msg = await safe_listen(client, message.chat.id, user_id, timeout=60)
    if not cid_msg:
        await prompt.edit("❌ Timed out.")
        return
    await cid_msg.delete(True)

    if not cid_msg.text:
        await prompt.edit(
            "❌ Please send the channel ID as text (e.g. <code>-1001234567890</code>).",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    raw_cid = cid_msg.text.strip()
    # Accept plain numbers too
    if raw_cid.lstrip("-").isdigit():
        if not raw_cid.startswith("-100") and not raw_cid.startswith("-"):
            raw_cid = "-100" + raw_cid
        try:
            channel_id = int(raw_cid)
        except ValueError:
            await prompt.edit("❌ Invalid channel ID.", parse_mode=enums.ParseMode.HTML)
            return
    else:
        try:
            channel_id = int(raw_cid)
        except ValueError:
            await prompt.edit(
                "❌ Invalid channel ID. Must be a number like <code>-1001234567890</code>.",
                parse_mode=enums.ParseMode.HTML,
            )
            return

    # Step 2 — show saved topics from memory
    saved_topics = _mem_get_channel_topics(channel_id)

    if not saved_topics:
        await prompt.edit(
            f"<b>❌ No topics found in memory for channel <code>{channel_id}</code>.</b>\n\n"
            f"<b>Please do this first:</b>\n"
            f"1. Open your channel in Telegram\n"
            f"2. Go into <b>each forum topic</b> one by one\n"
            f"3. Send <code>/gettopicid</code> in each topic\n"
            f"4. Then run <code>/linktopics</code> again!\n\n"
            f"<i>The bot cannot list topics via API — you must collect them manually with /gettopicid.</i>",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    # Build display + norm lookup
    ch_norm_map = {}   # normalised_name → {name, id, link}
    lines_display = []
    for tinfo in sorted(saved_topics.values(), key=lambda x: x["id"]):
        lines_display.append(
            f"• <b>{esc(tinfo['name'])}</b>\n"
            f"  ID: <code>{tinfo['id']}</code> | "
            f"<a href=\"{tinfo['link']}\">{tinfo['link']}</a>"
        )
        ch_norm_map[_norm(tinfo["name"])] = tinfo

    # Check for existing mapping
    existing_mapping = _mem_get_mapping(channel_id)
    extra = (
        f"\n\n✅ <b>{len(existing_mapping)} topic(s) already mapped.</b> Uploading a new txt will update it."
        if existing_mapping else ""
    )

    header = (
        f"<b>✅ {len(saved_topics)} topic(s) saved for channel <code>{channel_id}</code>:</b>\n\n"
        + "\n\n".join(lines_display)
        + extra
        + "\n\n<b>📎 Now send your <code>.txt</code> file</b> with topic names.\n"
        "<i>Waiting 60 seconds...</i>"
    )

    MAX = 3800
    chunks = [header[i:i+MAX] for i in range(0, len(header), MAX)] if len(header) > MAX else [header]
    await prompt.edit(chunks[0], parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)
    for c in chunks[1:]:
        await message.reply_text(c, parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)

    # Step 3 — receive txt file
    file_msg = await safe_listen(client, message.chat.id, user_id, timeout=60)
    if not file_msg or not file_msg.document:
        await message.reply_text(
            "❌ No file received. Run <code>/linktopics</code> again.",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    if not file_msg.document.file_name.endswith(".txt"):
        await message.reply_text("❌ That is not a <code>.txt</code> file.", parse_mode=enums.ParseMode.HTML)
        return

    status = await message.reply_text("<b>🔍 Parsing txt topics and matching...</b>", parse_mode=enums.ParseMode.HTML)
    txt_path = await file_msg.download()

    # Step 4 — parse topic names from txt
    txt_topic_names = []
    try:
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "://" in line:
                    # Inline [TopicName] prefix
                    m = re.match(r"^\[([^\]]+)\]\s*(.*)", line)
                    if m:
                        prefix = m.group(1).strip()
                        if not prefix.lstrip("-").isdigit():
                            if prefix not in txt_topic_names:
                                txt_topic_names.append(prefix)
                else:
                    # Heading line — may have [id] prefix
                    m = re.match(r"^\[(\d+)\]\s*(.*)", line)
                    if m:
                        heading = m.group(2).strip()
                    else:
                        heading = line
                    if heading and heading not in txt_topic_names:
                        txt_topic_names.append(heading)
    except Exception as e:
        await status.edit(f"❌ Failed to read file: <code>{e}</code>", parse_mode=enums.ParseMode.HTML)
        return
    finally:
        try:
            os.remove(txt_path)
        except Exception:
            pass

    if not txt_topic_names:
        await status.edit("❌ No topic names found in the txt file.")
        return

    # Step 5 — auto-match
    new_mapping = {}   # txt_name → {topic_id, topic_name, topic_link}
    unmatched = []

    for txt_name in txt_topic_names:
        txt_norm = _norm(txt_name)
        best = None
        best_score = 0

        for cnorm, tinfo in ch_norm_map.items():
            # Exact normalised
            if txt_norm == cnorm:
                best = tinfo
                best_score = 3
                break
            # Substring
            if txt_norm in cnorm or cnorm in txt_norm:
                score = 2.5 if len(txt_norm) <= len(cnorm) else 2
                if score > best_score:
                    best = tinfo
                    best_score = score
            # Word overlap
            tw = set(txt_norm.split())
            cw = set(cnorm.split())
            overlap = len(tw & cw)
            if overlap > 0:
                score = 1 + overlap / max(len(tw), len(cw))
                if score > best_score:
                    best = tinfo
                    best_score = score

        if best:
            new_mapping[txt_name] = {
                "topic_id": best["id"],
                "topic_name": best["name"],
                "topic_link": best["link"],
                "match_quality": "exact" if best_score >= 3 else "partial",
            }
        else:
            unmatched.append(txt_name)

    # Step 6 — save mapping (merge with existing)
    merged = dict(existing_mapping)
    merged.update(new_mapping)
    _mem_save_mapping(channel_id, merged)
    # Also persist to legacy topic_config for backward compat
    legacy_map = {name: info["topic_id"] for name, info in merged.items()}
    save_txt_topic_mapping(channel_id, legacy_map)

    # Build result
    result_lines = [f"<b>✅ Topic Mapping Saved for channel <code>{channel_id}</code></b>\n"]

    if new_mapping:
        result_lines.append(f"<b>🟢 Matched ({len(new_mapping)}):</b>")
        for txt_name, info in new_mapping.items():
            q = "✅" if info["match_quality"] == "exact" else "🔍"
            result_lines.append(
                f"{q} <code>{esc(txt_name)}</code>\n"
                f"   → {esc(info['topic_name'])} (ID: <code>{info['topic_id']}</code>)\n"
                f"   <a href=\"{info['topic_link']}\">{info['topic_link']}</a>"
            )

    if unmatched:
        result_lines.append(f"\n<b>🔴 Unmatched ({len(unmatched)}):</b>")
        for n in unmatched:
            result_lines.append(
                f"• <code>{esc(n)}</code>\n"
                f"  <i>Go into its topic → send /gettopicid → run /linktopics again</i>"
            )

    result_lines.append(
        "\n<b>💾 Mapping saved permanently!</b>\n"
        "Videos will now be routed automatically based on this mapping."
    )

    result_text = "\n\n".join(result_lines)
    MAX = 3800
    r_chunks = [result_text[i:i+MAX] for i in range(0, len(result_text), MAX)] if len(result_text) > MAX else [result_text]
    await status.edit(r_chunks[0], parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)
    for c in r_chunks[1:]:
        await message.reply_text(c, parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)


# ---------------------------------------------------------------------------
# /maketopics — bulk-create forum topics from a .txt file
# Parses lines like: 📌 Topic Name — 123 links
# ---------------------------------------------------------------------------

def _parse_pinned_topics(text: str) -> list:
    """
    Extract unique topic names from a .txt file.
    Handles ALL formats used by this bot:
      1. [Topic Name]          — bracket prefix (standalone or before URL)
      2. (Topic Name)          — paren prefix at start of a link name
      3. Plain heading lines   — any non-URL, non-# line (e.g. "Arithmetic")
      4. 📌 Topic Name — X    — pinned-list format
    Returns a deduped list in order of first appearance.
    """
    seen   = set()
    topics = []

    def _add(name: str):
        name = name.strip()[:128]
        key  = name.lower()
        if key and key not in seen:
            seen.add(key)
            topics.append(name)

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue

        # Format 4: 📌 Topic Name — 123 links
        if '📌' in line and '—' in line:
            try:
                name = line.split('📌')[1].split('—')[0].strip()
                if name:
                    _add(name)
            except Exception:
                pass
            continue

        # Format 2: [Topic Name] standalone or inline prefix before URL
        bracket = re.match(r'^\[([^\]]+)\]\s*(.*)', line)
        if bracket:
            inner = bracket.group(1).strip()
            if not inner.lstrip('-').isdigit():   # skip numeric IDs like [12345]
                _add(inner)
            continue

        # Format 3: (Topic Name) at start of a content line
        if '://' in line or ': //' in line:
            name_part = re.split(r':\s*//', line, maxsplit=1)[0].strip()
            cat = re.match(r'^\(([^)]+)\)', name_part)
            if cat:
                _add(cat.group(1).strip())
            continue

        # Format 1: Plain heading line (non-URL, non-# line)
        heading = re.sub(r'\|\s*-?\d+\s*$', '', line).strip()
        if heading:
            _add(heading)

    return topics


async def maketopics_command(client: Client, message: Message):
    """
    /maketopics — send a .txt file whose lines look like:
        📌 Arithmetic — 591 links
        📌 English/Grammar — 204 links
    Bot will create those as Telegram forum topics in any group you specify.
    """
    if message.from_user and message.from_user.id != OWNER:
        await message.reply_text("Owner only command.")
        return

    # Step 1: ask for the .txt file
    prompt = await message.reply_text(
        "<b>📂 Send your .txt file now.</b>\n\n"
        "<i>Each line should look like:</i>\n"
        "<code>📌 Arithmetic — 591 links</code>\n\n"
        "<i>Waiting 60 seconds...</i>",
        parse_mode=enums.ParseMode.HTML,
    )

    file_msg = await safe_listen(client, message.chat.id, message.from_user.id, timeout=60)
    if not file_msg:
        await prompt.edit("<b>❌ Timed out. Run /maketopics again.</b>", parse_mode=enums.ParseMode.HTML)
        return
    if not (file_msg.document and file_msg.document.file_name.endswith(".txt")):
        await prompt.edit("<b>❌ Please send a .txt file.</b>", parse_mode=enums.ParseMode.HTML)
        return

    await prompt.edit("<b>📥 Reading file...</b>", parse_mode=enums.ParseMode.HTML)
    path = await file_msg.download()
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    finally:
        try:
            os.remove(path)
        except Exception:
            pass

    topics = _parse_pinned_topics(content)
    if not topics:
        await prompt.edit(
            "<b>❌ No topics found.</b>\n\n"
            "Make sure lines follow this format:\n"
            "<code>📌 Topic Name — 123 links</code>",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    # Step 2: show parsed list, ask for Group Chat ID
    lines = [f"<b>✅ Found {len(topics)} topics:</b>"]
    for i, t in enumerate(topics, 1):
        lines.append(f"{i}. {t}")
    lines.append("")
    lines.append("<b>Now send the Group Chat ID</b> where I should create these topics.")
    lines.append("<i>(e.g. -1001234567890 — get it via @getidsbot)</i>")

    await prompt.edit("\n".join(lines), parse_mode=enums.ParseMode.HTML)

    # Step 3: wait for Group Chat ID
    id_msg = await safe_listen(client, message.chat.id, message.from_user.id, timeout=60)
    if not id_msg:
        await prompt.edit("<b>❌ Timed out. Run /maketopics again.</b>", parse_mode=enums.ParseMode.HTML)
        return

    raw_id = id_msg.text.strip() if id_msg.text else ""
    try:
        group_chat_id = int(raw_id)
    except ValueError:
        await message.reply_text(
            "❌ Invalid Chat ID. Please send a number like <code>-1001234567890</code>",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    # Step 4: create topics one by one
    total   = len(topics)
    created = 0
    failed  = 0

    status_msg = await message.reply_text(
        f"<b>⏳ Starting topic creation for {total} topics...</b>",
        parse_mode=enums.ParseMode.HTML,
    )

    for idx, topic_name in enumerate(topics, 1):
        topic_id, err = await create_forum_topic(client, group_chat_id, topic_name)
        if err:
            err_lower = err.lower()
            if "admin" in err_lower or "forbidden" in err_lower or "manage" in err_lower:
                await status_msg.edit(
                    "❌ Bot does not have <b>Manage Topics</b> permission.\n"
                    "Make it admin with that permission and try again.",
                    parse_mode=enums.ParseMode.HTML,
                )
                return
            if "chat not found" in err_lower or "peer_id_invalid" in err_lower:
                await status_msg.edit(
                    "❌ Group not found. Check the Chat ID and make sure the bot is a member.",
                    parse_mode=enums.ParseMode.HTML,
                )
                return
            failed += 1
            await message.reply_text(
                f"❌ ({idx}/{total}) Failed: <b>{topic_name}</b>\n<i>{err}</i>",
                parse_mode=enums.ParseMode.HTML,
            )
        else:
            created += 1
            await message.reply_text(
                f"✅ ({idx}/{total}) Created: <b>{topic_name}</b>",
                parse_mode=enums.ParseMode.HTML,
            )
        await asyncio.sleep(1.5)

    await status_msg.edit(
        f"<b>🏁 Done!</b>  ✅ {created} created  ❌ {failed} failed\n\n"
        f"Send another .txt file with /maketopics to run again.",
        parse_mode=enums.ParseMode.HTML,
    )


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

def register_topic_handlers(bot: Client):
    bot.on_message(filters.command("createtopic"))(create_topic_command)
    bot.on_message(filters.command("topics"))(list_topics_command)
    bot.on_message(filters.command("settopic"))(set_topic_command)
    bot.on_message(filters.command("setuptopics"))(setup_topics_command)
    bot.on_message(filters.command("parsetxt"))(parse_txt_command)
    bot.on_message(filters.command("defaulttopic"))(set_default_topic_command)
    bot.on_message(filters.command("topicid"))(get_topic_id_command)
    bot.on_message(filters.command("gettopicid"))(gettopicid_command)
    bot.on_message(filters.command("parsetopics"))(parse_topics_command)
    bot.on_message(filters.command("linktopics"))(link_topics_command)
    bot.on_message(filters.command("showtopics"))(showtopics_command)
    bot.on_message(filters.command("showmapping"))(showmapping_command)
    bot.on_message(filters.command("clearmemory"))(clearmemory_command)
    bot.on_message(filters.command("maketopics") & filters.private)(maketopics_command)

    @bot.on_message(filters.group & filters.service)
    async def _on_group_join(client, message: Message):
        if not message.new_chat_members:
            return
        me = await client.get_me()
        for member in message.new_chat_members:
            if member.id == me.id:
                try:
                    await setup_default_topics(client, message.chat.id)
                    await message.reply_text(
                        "**✅ Bot Added!**\n\n"
                        "Default topics created:\n"
                        "• 📢 Notices\n• 📤 Uploads\n• 🎥 Videos\n• 📄 PDFs\n• 💬 General\n\n"
                        "Use `/topics` to see IDs.\n"
                        "Reply to a txt file with `/parsetxt <channel_id>` to create topics from file."
                    )
                except Exception as e:
                    print(f"[TopicHandler] Auto-setup failed: {e}")
                break

    print("[TopicHandler] Handlers registered: /createtopic /topics /settopic /setuptopics /parsetxt /defaulttopic /topicid /gettopicid /parsetopics /linktopics /showtopics /showmapping /clearmemory /maketopics")
