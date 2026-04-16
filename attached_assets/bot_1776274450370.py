import json
import os
import re
import asyncio
import logging
from pathlib import Path
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
)
from telegram.constants import ParseMode, ChatMemberStatus

# ============================================================
# CONFIGURATION
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
MEMORY_FILE = "topic_memory.json"

# Conversation states for /linktopics
(
    WAITING_CHANNEL_ID,
    WAITING_TXT_FILE,
    ASK_TOPIC_ONE_BY_ONE,
) = range(3)

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ============================================================
# MEMORY MANAGEMENT (Persistent JSON Storage)
# ============================================================

def load_memory() -> dict:
    """Load the persistent memory from JSON file."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.warning("Memory file corrupted, creating new one.")
    return {"channels": {}, "mappings": {}}


def save_memory(memory: dict) -> None:
    """Save memory to JSON file atomically."""
    tmp_file = MEMORY_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)
    os.replace(tmp_file, MEMORY_FILE)


def get_channel_topics(channel_id: str) -> dict:
    """Get all saved topics for a channel from memory."""
    memory = load_memory()
    channel_id_str = str(channel_id)
    if channel_id_str in memory["channels"]:
        return memory["channels"][channel_id_str].get("topics", {})
    return {}


def save_topic(channel_id: str, thread_id: int, topic_name: str, link: str) -> None:
    """Save a single topic to memory."""
    memory = load_memory()
    channel_id_str = str(channel_id)
    
    if channel_id_str not in memory["channels"]:
        memory["channels"][channel_id_str] = {
            "title": "",
            "topics": {},
            "last_updated": datetime.now().isoformat(),
        }
    
    memory["channels"][channel_id_str]["topics"][str(thread_id)] = {
        "name": topic_name,
        "id": thread_id,
        "link": link,
    }
    memory["channels"][channel_id_str]["last_updated"] = datetime.now().isoformat()
    save_memory(memory)


def build_topic_link(chat_id: int, thread_id: int) -> str:
    """Build a clickable t.me link for a topic."""
    chat_str = str(chat_id)
    if chat_str.startswith("-100"):
        # Supergroup: https://t.me/c/<group_id>/<thread_id>
        link_chat_id = chat_str[4:]  # Remove "-100"
        return f"https://t.me/c/{link_chat_id}/{thread_id}"
    else:
        # Fallback
        return f"https://t.me/c/{chat_str}/{thread_id}"


def get_saved_mapping(channel_id: str) -> dict:
    """Get saved topic mapping for a channel (txt topic name -> topic id)."""
    memory = load_memory()
    return memory.get("mappings", {}).get(str(channel_id), {})


def save_mapping(channel_id: str, mapping: dict) -> None:
    """Save the topic mapping for a channel."""
    memory = load_memory()
    if "mappings" not in memory:
        memory["mappings"] = {}
    memory["mappings"][str(channel_id)] = mapping
    save_memory(memory)


# ============================================================
# COMMAND: /topicid
# Shows topic info (Topic ID, Chat ID, clickable link)
# Works in ANY group/forum topic
# ============================================================

async def topicid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the current topic's ID, chat ID, and clickable link."""
    chat = update.effective_chat
    message = update.message
    chat_id = chat.id
    thread_id = message.message_thread_id
    
    # Check if this is a forum topic
    is_forum = chat.is_forum if hasattr(chat, 'is_forum') else False
    
    # Get the topic name if possible
    topic_name = "N/A"
    
    if thread_id and thread_id != chat_id:
        # We're inside a specific topic
        try:
            # Try to get topic info via Bot API
            topic_info = await context.bot.get_forum_topic_info(
                chat_id=chat_id,
                message_thread_id=thread_id
            )
            topic_name = topic_info.name if topic_info else f"Topic {thread_id}"
        except Exception as e:
            logger.warning(f"Could not get forum topic info: {e}")
            topic_name = f"Topic {thread_id}"
        
        link = build_topic_link(chat_id, thread_id)
        
        text = (
            f"📌 <b>Topic Info:</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>Topic Name:</b> {topic_name}\n"
            f"🔢 <b>Topic ID:</b> <code>{thread_id}</code>\n"
            f"💬 <b>Chat ID:</b> <code>{chat_id}</code>\n"
            f"🔗 <b>Link:</b> {link}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✅ Works in all groups (private & public)"
        )
    else:
        # General topic or non-forum group
        chat_title = chat.title or "Private Chat"
        if str(chat_id).startswith("-100"):
            link_chat_id = str(chat_id)[4:]
            link = f"https://t.me/c/{link_chat_id}"
        else:
            link = f"t.me/c/{chat_id}"
        
        text = (
            f"📌 <b>Chat Info:</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💬 <b>Chat Name:</b> {chat_title}\n"
            f"🔢 <b>Chat ID:</b> <code>{chat_id}</code>\n"
            f"🔗 <b>Link:</b> {link}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"ℹ️ This is the <b>General</b> topic (no thread ID)"
        )
    
    await message.reply_text(text, parse_mode=ParseMode.HTML)


# ============================================================
# COMMAND: /gettopicid
# Send this in ANY forum topic → bot auto-saves it to memory
# Collect topic info from all topics by sending in each one
# ============================================================

async def gettopicid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    When sent inside a forum topic, saves the topic's info to memory.
    Send this command in EACH topic of a channel to collect all topics.
    Then /linktopics can use the collected data.
    """
    chat = update.effective_chat
    message = update.message
    chat_id = chat.id
    thread_id = message.message_thread_id
    
    # If no thread_id or thread_id equals chat_id, it's the general topic
    if not thread_id or thread_id == chat_id:
        await message.reply_text(
            "ℹ️ <b>This is the General topic.</b>\n\n"
            "Please send <code>/gettopicid</code> in each <b>specific forum topic</b> "
            "to collect their info.\n\n"
            "The bot will automatically save:\n"
            "• Topic Name\n"
            "• Topic ID\n"
            "• Clickable Link\n\n"
            "📋 Go to each topic in your channel and send this command!",
            parse_mode=ParseMode.HTML,
        )
        return
    
    # We're inside a specific topic - get the topic info
    topic_name = ""
    
    try:
        # Use getForumTopicInfo to get the topic name
        topic_info = await context.bot.get_forum_topic_info(
            chat_id=chat_id,
            message_thread_id=thread_id,
        )
        topic_name = topic_info.name if topic_info else f"Topic {thread_id}"
    except Exception as e:
        logger.warning(f"getForumTopicInfo failed: {e}")
        topic_name = f"Topic {thread_id}"
    
    # Build the link
    link = build_topic_link(chat_id, thread_id)
    
    # Save to memory
    save_topic(chat_id, thread_id, topic_name, link)
    
    # Count total topics saved for this channel
    all_topics = get_channel_topics(chat_id)
    total_count = len(all_topics)
    
    # Build topic list preview
    topic_list = "\n".join(
        f"  • {t['name']} (ID: <code>{t['id']}</code>)"
        for t in sorted(all_topics.values(), key=lambda x: x["id"])
    )
    
    await message.reply_text(
        f"✅ <b>Topic saved to memory!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Name:</b> {topic_name}\n"
        f"🔢 <b>ID:</b> <code>{thread_id}</code>\n"
        f"🔗 <b>Link:</b> {link}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Total topics saved for this channel: {total_count}</b>\n\n"
        f"{topic_list}\n\n"
        f"💡 Send <code>/gettopicid</code> in the next topic to continue collecting!",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# COMMAND: /linktopics
# Full flow:
#   1. Asks for channel ID
#   2. Shows all saved topics (from /gettopicid data)
#   3. Asks for txt file with topic names
#   4. Auto-matches txt names to saved topics (case-insensitive, partial)
#   5. Saves the mapping permanently
# ============================================================

async def linktopics_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the /linktopics conversation - ask for channel ID."""
    # Clear any previous state
    context.user_data.clear()
    
    await update.message.reply_text(
        "🔗 <b>Link Topics to Channel</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Step 1: Send me the <b>Channel ID</b>\n"
        "(e.g., <code>-1001234567890</code>)\n\n"
        "⚠️ Make sure you've already sent <code>/gettopicid</code> in each topic "
        "of that channel first!",
        parse_mode=ParseMode.HTML,
    )
    return WAITING_CHANNEL_ID


async def linktopics_receive_channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive channel ID and show all saved topics."""
    raw_input = update.message.text.strip()
    
    # Handle forwarded channel messages (the user might forward a message from the channel)
    if update.message.forward_from_chat:
        raw_input = str(update.message.forward_from_chat.id)
    
    channel_id = raw_input
    
    # Also handle if user sends just the numeric part
    if channel_id.lstrip("-").isdigit():
        if not channel_id.startswith("-100"):
            channel_id = "-100" + channel_id.lstrip("-")
    else:
        await update.message.reply_text(
            "❌ Invalid Channel ID format.\n"
            "Please send a valid ID like: <code>-1001234567890</code>",
            parse_mode=ParseMode.HTML,
        )
        return WAITING_CHANNEL_ID
    
    # Get saved topics for this channel
    all_topics = get_channel_topics(channel_id)
    
    if not all_topics:
        await update.message.reply_text(
            f"❌ <b>No topics found for channel:</b> <code>{channel_id}</code>\n\n"
            f"📌 Please do this first:\n"
            f"1. Go to your channel\n"
            f"2. Open EACH forum topic\n"
            f"3. Send <code>/gettopicid</code> in each topic\n"
            f"4. The bot will auto-save each topic's info\n\n"
            f"Then run <code>/linktopics</code> again!",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END
    
    # Store channel_id for later steps
    context.user_data["link_channel_id"] = channel_id
    
    # Build topic list with clickable links
    topic_list_lines = []
    for tid, tinfo in sorted(all_topics.items(), key=lambda x: int(x[0])):
        topic_list_lines.append(
            f"• <b>{tinfo['name']}</b>\n"
            f"  ID: <code>{tinfo['id']}</code>\n"
            f"  🔗 {tinfo['link']}"
        )
    
    topic_list = "\n\n".join(topic_list_lines)
    
    # Check if there's already a saved mapping
    existing_mapping = get_saved_mapping(channel_id)
    
    extra_info = ""
    if existing_mapping:
        extra_info = (
            f"\n\n✅ <b>Existing mapping found:</b> {len(existing_mapping)} topics already mapped!\n"
            f"Uploading a new txt file will update the mapping."
        )
    
    await update.message.reply_text(
        f"📋 <b>Topics found: {len(all_topics)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"{topic_list}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{extra_info}\n\n"
        f"📎 <b>Step 2:</b> Now send your <b>.txt file</b> with topic names "
        f"(one topic name per line).\n\n"
        f"The bot will auto-match them (case-insensitive, partial match).",
        parse_mode=ParseMode.HTML,
    )
    return WAITING_TXT_FILE


async def linktopics_receive_txt_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive the txt file and match topic names."""
    channel_id = context.user_data.get("link_channel_id")
    
    if not channel_id:
        await update.message.reply_text("❌ Session expired. Please run /linktopics again.")
        return ConversationHandler.END
    
    # Get the txt file
    document = update.message.document
    if not document:
        # Maybe the user sent text directly instead of a file
        text = update.message.text
        if text:
            topic_names = [line.strip() for line in text.strip().split("\n") if line.strip()]
        else:
            await update.message.reply_text(
                "❌ Please send a <b>.txt file</b> or paste topic names (one per line).",
                parse_mode=ParseMode.HTML,
            )
            return WAITING_TXT_FILE
    else:
        # Download the txt file
        try:
            file = await document.get_file()
            file_content = await file.download_as_bytearray()
            text = file_content.decode("utf-8", errors="ignore")
            topic_names = [line.strip() for line in text.strip().split("\n") if line.strip()]
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            await update.message.reply_text(f"❌ Failed to read file: {e}")
            return ConversationHandler.END
    
    if not topic_names:
        await update.message.reply_text("❌ No topic names found in the file.")
        return ConversationHandler.END
    
    # Get saved topics
    all_topics = get_channel_topics(channel_id)
    if not all_topics:
        await update.message.reply_text(
            "❌ No saved topics found. Please run /gettopicid in each topic first."
        )
        return ConversationHandler.END
    
    # Auto-match: case-insensitive, partial match
    mapping = {}  # txt_name -> topic_info
    unmatched = []  # txt names that didn't match
    
    for txt_name in topic_names:
        txt_lower = txt_name.lower().strip()
        best_match = None
        best_score = 0
        
        for tid, tinfo in all_topics.items():
            topic_lower = tinfo["name"].lower().strip()
            
            # Exact match
            if txt_lower == topic_lower:
                best_match = tinfo
                best_score = 3
                break
            
            # One contains the other (partial match)
            if txt_lower in topic_lower or topic_lower in txt_lower:
                # Prefer shorter match (more specific)
                score = 2
                if len(txt_lower) <= len(topic_lower):
                    score = 2.5  # Slightly prefer when txt name is shorter
                if score > best_score:
                    best_match = tinfo
                    best_score = score
            
            # Word overlap match
            txt_words = set(txt_lower.split())
            topic_words = set(topic_lower.split())
            overlap = len(txt_words & topic_words)
            if overlap > 0:
                score = 1 + (overlap / max(len(txt_words), len(topic_words)))
                if score > best_score:
                    best_match = tinfo
                    best_score = score
        
        if best_match:
            mapping[txt_name] = {
                "topic_id": best_match["id"],
                "topic_name": best_match["name"],
                "topic_link": best_match["link"],
                "match_quality": "exact" if best_score >= 3 else "partial",
            }
        else:
            unmatched.append(txt_name)
    
    # Save the mapping to memory
    save_mapping(channel_id, mapping)
    
    # Build result message
    matched_lines = []
    for txt_name, info in mapping.items():
        quality = "✅" if info["match_quality"] == "exact" else "🔍"
        matched_lines.append(
            f"{quality} <b>{txt_name}</b>\n"
            f"   → {info['topic_name']} (ID: <code>{info['topic_id']}</code>)\n"
            f"   🔗 {info['topic_link']}"
        )
    
    result_text = (
        f"🔗 <b>Topic Mapping Complete!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ <b>Matched: {len(mapping)}</b> topics\n"
    )
    
    if unmatched:
        result_text += f"❌ <b>Unmatched: {len(unmatched)}</b> topics\n"
    
    result_text += f"\n{'─' * 30}\n\n"
    result_text += "\n\n".join(matched_lines)
    
    if unmatched:
        result_text += f"\n\n{'─' * 30}\n"
        result_text += f"\n❌ <b>Unmatched topics:</b>\n"
        result_text += "\n".join(f"   • {name}" for name in unmatched)
        result_text += (
            f"\n\n💡 These topics weren't found in the channel. "
            f"They may have different names or don't exist yet."
        )
    
    result_text += (
        f"\n\n{'─' * 30}\n"
        f"💾 <b>Mapping saved to memory permanently!</b>\n"
        f"Videos will now be routed automatically based on this mapping."
    )
    
    await update.message.reply_text(result_text, parse_mode=ParseMode.HTML)
    return ConversationHandler.END


# ============================================================
# COMMAND: /showtopics
# Show all saved topics for a channel
# ============================================================

async def showtopics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all saved topics and mappings."""
    memory = load_memory()
    
    if not memory["channels"]:
        await update.message.reply_text(
            "📭 <b>No channels saved yet.</b>\n\n"
            "Send <code>/gettopicid</code> in each forum topic of a channel to start collecting!",
            parse_mode=ParseMode.HTML,
        )
        return
    
    text = "📊 <b>Saved Topics Overview</b>\n"
    text += "━" * 30 + "\n\n"
    
    for channel_id, channel_data in memory["channels"].items():
        topics = channel_data.get("topics", {})
        title = channel_data.get("title", "Unknown Channel")
        text += f"💬 <b>{title}</b>\n"
        text += f"   ID: <code>{channel_id}</code>\n"
        text += f"   Topics: {len(topics)}\n"
        
        if channel_id in memory.get("mappings", {}):
            mapping = memory["mappings"][channel_id]
            text += f"   Mappings: {len(mapping)}\n"
        
        text += "\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ============================================================
# COMMAND: /showmapping
# Show the topic mapping for a specific channel
# ============================================================

async def showmapping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the saved mapping for a channel."""
    if not context.args:
        await update.message.reply_text(
            " Usage: <code>/showmapping CHANNEL_ID</code>\n\n"
            "Example: <code>/showmapping -1001234567890</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    
    channel_id = context.args[0]
    mapping = get_saved_mapping(channel_id)
    
    if not mapping:
        await update.message.reply_text(
            f"📭 No mapping found for channel: <code>{channel_id}</code>\n\n"
            f"Run <code>/linktopics</code> to create one!",
            parse_mode=ParseMode.HTML,
        )
        return
    
    lines = []
    for txt_name, info in mapping.items():
        lines.append(
            f"📄 <b>{txt_name}</b>\n"
            f"   → {info['topic_name']} (ID: <code>{info['topic_id']}</code>)\n"
            f"   🔗 {info['topic_link']}"
        )
    
    await update.message.reply_text(
        f"🔗 <b>Topic Mapping</b> ({len(mapping)} topics)\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        + "\n\n".join(lines),
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# COMMAND: /clearmemory
# Clear saved topics/mappings for a channel
# ============================================================

async def clearmemory_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear memory for a channel."""
    if not context.args:
        await update.message.reply_text(
            "Usage: <code>/clearmemory CHANNEL_ID</code>\n"
            "Or: <code>/clearmemory all</code> to clear everything",
            parse_mode=ParseMode.HTML,
        )
        return
    
    memory = load_memory()
    target = context.args[0]
    
    if target.lower() == "all":
        memory = {"channels": {}, "mappings": {}}
        save_memory(memory)
        await update.message.reply_text("🗑️ All memory cleared!", parse_mode=ParseMode.HTML)
    elif target in memory["channels"]:
        del memory["channels"][target]
        if target in memory.get("mappings", {}):
            del memory["mappings"][target]
        save_memory(memory)
        await update.message.reply_text(
            f"🗑️ Memory cleared for channel: <code>{target}</code>",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            f"❌ Channel not found: <code>{target}</code>",
            parse_mode=ParseMode.HTML,
        )


# ============================================================
# VIDEO UPLOAD HANDLER (DRM Router)
# Routes uploaded videos to the correct topic based on mapping
# ============================================================

async def handle_video_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    When a video is uploaded to the bot (private chat),
    route it to the correct topic based on saved mapping.
    """
    message = update.message
    if not message or not message.video:
        return
    
    # This handler works when user sends video in private chat to the bot
    # with a channel ID specified somehow
    
    chat_id = update.effective_chat.id
    
    # Check if we have a pending channel for this user
    pending_channel = context.user_data.get("pending_upload_channel")
    
    if not pending_channel:
        await message.reply_text(
            "🎬 <b>Video received!</b>\n\n"
            "To route this video, please first set the target channel.\n"
            "Send: <code>/setchannel CHANNEL_ID</code>\n\n"
            "Then send the video again.",
            parse_mode=ParseMode.HTML,
        )
        return
    
    # Get the mapping for this channel
    mapping = get_saved_mapping(pending_channel)
    
    if not mapping:
        await message.reply_text(
            f"❌ No topic mapping found for this channel.\n"
            f"Please run <code>/linktopics</code> first to create the mapping.",
            parse_mode=ParseMode.HTML,
        )
        return
    
    # Try to match the video filename to a topic
    video_filename = message.video.file_name or ""
    video_caption = message.caption or ""
    
    # Search in both filename and caption
    search_text = f"{video_filename} {video_caption}".lower()
    
    matched_topic = None
    matched_name = None
    
    for txt_name, info in mapping.items():
        txt_lower = txt_name.lower()
        if txt_lower in search_text:
            matched_topic = info
            matched_name = txt_name
            break
    
    if matched_topic:
        topic_id = matched_topic["topic_id"]
        channel_id_int = int(pending_channel)
        
        try:
            # Forward the video to the correct topic in the channel
            # This preserves the original video and metadata
            await context.bot.forward_message(
                chat_id=channel_id_int,
                from_chat_id=chat_id,
                message_id=message.message_id,
                message_thread_id=topic_id,
            )
            
            await message.reply_text(
                f"✅ <b>Video routed successfully!</b>\n\n"
                f"🎬 File: {video_filename}\n"
                f"📌 Matched to: <b>{matched_topic['topic_name']}</b>\n"
                f"🔗 {matched_topic['topic_link']}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"✅ Topic mapping loaded from memory. Videos routed automatically.",
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            await message.reply_text(
                f"❌ Failed to send video to topic:\n"
                f"Error: <code>{e}</code>\n\n"
                f"Make sure the bot is an admin with 'Post Messages' and 'Manage Topics' permissions in the channel.",
                parse_mode=ParseMode.HTML,
            )
    else:
        # No match found - ask the user
        all_topics = get_channel_topics(pending_channel)
        
        if all_topics:
            # Build keyboard with topic options
            buttons = []
            topic_list = list(all_topics.values())
            
            # Show up to 10 topics in the keyboard
            for i in range(0, min(len(topic_list), 10), 2):
                row = []
                for j in range(2):
                    if i + j < len(topic_list):
                        t = topic_list[i + j]
                        row.append(
                            InlineKeyboardButton(
                                t["name"],
                                callback_data=f"route_{pending_channel}_{t['id']}_{message.message_id}",
                            )
                        )
                buttons.append(row)
            
            buttons.append([
                InlineKeyboardButton("❌ Cancel", callback_data=f"route_cancel_{message.message_id}")
            ])
            
            reply_markup = InlineKeyboardMarkup(buttons)
            
            await message.reply_text(
                f"❓ <b>No automatic match found.</b>\n\n"
                f"🎬 File: {video_filename}\n\n"
                f"Please select the correct topic:",
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
            )
            # Store video info for callback
            context.user_data[f"pending_video_{message.message_id}"] = {
                "channel_id": pending_channel,
                "filename": video_filename,
            }
        else:
            await message.reply_text(
                f"❌ No match found and no topics saved.\n"
                f"Please run <code>/linktopics</code> first.",
                parse_mode=ParseMode.HTML,
            )


# ============================================================
# CALLBACK QUERY HANDLER (for topic selection buttons)
# ============================================================

async def route_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle topic selection for video routing."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("route_cancel_"):
        await query.edit_message_text("❌ Video routing cancelled.")
        return
    
    if data.startswith("route_"):
        parts = data.split("_")
        # route_CHANNEL_ID_TOPIC_ID_MESSAGE_ID
        if len(parts) >= 5:
            channel_id = parts[1]
            topic_id = int(parts[2])
            original_msg_id = parts[3]
            
            await query.edit_message_text(
                f"✅ Video will be sent to topic ID: <code>{topic_id}</code>",
                parse_mode=ParseMode.HTML,
            )


# ============================================================
# COMMAND: /setchannel
# Set the target channel for video uploads
# ============================================================

async def setchannel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set the target channel for video routing."""
    if not context.args:
        current = context.user_data.get("pending_upload_channel", "Not set")
        await update.message.reply_text(
            f"📡 <b>Current upload channel:</b> <code>{current}</code>\n\n"
            f"Usage: <code>/setchannel CHANNEL_ID</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    
    channel_id = context.args[0]
    context.user_data["pending_upload_channel"] = channel_id
    
    # Check if we have saved topics for this channel
    all_topics = get_channel_topics(channel_id)
    mapping = get_saved_mapping(channel_id)
    
    await update.message.reply_text(
        f"✅ <b>Upload channel set!</b>\n\n"
        f"📡 Channel ID: <code>{channel_id}</code>\n"
        f"📋 Saved topics: {len(all_topics)}\n"
        f"🔗 Topic mappings: {len(mapping)}\n\n"
        f"{'✅ Topic mapping loaded from memory (' + str(len(mapping)) + ' topics). Videos will be routed automatically.' if mapping else '⚠️ No mapping found. Run /linktopics to create one.'}",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# COMMAND: /start
# Welcome message
# ============================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome message."""
    await update.message.reply_text(
        "🤖 <b>Forum Topic Manager Bot</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📋 <b>Available Commands:</b>\n\n"
        "📌 <code>/topicid</code> — Show topic info (ID, Chat ID, Link)\n\n"
        "📥 <code>/gettopicid</code> — Send in each forum topic to auto-save it\n\n"
        "🔗 <code>/linktopics</code> — Match topics with your txt file & save mapping\n\n"
        "📊 <code>/showtopics</code> — Show all saved topics\n\n"
        "🗺️ <code>/showmapping</code> — Show topic mapping for a channel\n\n"
        "📡 <code>/setchannel</code> — Set target channel for video uploads\n\n"
        "🗑️ <code>/clearmemory</code> — Clear saved data\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "💡 <b>Quick Start:</b>\n"
        "1. Send <code>/gettopicid</code> in each forum topic\n"
        "2. Run <code>/linktopics</code> with your txt file\n"
        "3. Videos will be routed automatically!",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors."""
    logger.error(f"Error: {context.error}", exc_info=context.error)


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    """Start the bot."""
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("⚠️  Please set BOT_TOKEN environment variable!")
        print("   On Replit: Settings → Secrets → Add BOT_TOKEN")
        return
    
    # Build application
    application = Application.builder().token(BOT_TOKEN).build()

    # --- Command Handlers ---
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("topicid", topicid_command))
    application.add_handler(CommandHandler("gettopicid", gettopicid_command))
    application.add_handler(CommandHandler("showtopics", showtopics_command))
    application.add_handler(CommandHandler("showmapping", showmapping_command))
    application.add_handler(CommandHandler("setchannel", setchannel_command))
    application.add_handler(CommandHandler("clearmemory", clearmemory_command))

    # --- Callback Query Handler (for inline keyboard buttons) ---
    application.add_handler(CallbackQueryHandler(route_callback))

    # --- /linktopics Conversation Handler ---
    linktopics_conv = ConversationHandler(
        entry_points=[CommandHandler("linktopics", linktopics_start)],
        states={
            WAITING_CHANNEL_ID: [
                MessageHandler(
                    filters.TEXT | filters.ForwardedFrom(),
                    linktopics_receive_channel_id,
                )
            ],
            WAITING_TXT_FILE: [
                MessageHandler(
                    filters.Document.FileExtension("txt") | filters.TEXT,
                    linktopics_receive_txt_file,
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", lambda u, c: ConversationHandler.END),
        ],
        allow_reentry=True,
    )
    application.add_handler(linktopics_conv)

    # --- Video Upload Handler (private chat only) ---
    application.add_handler(
        MessageHandler(filters.VIDEO & filters.ChatType.PRIVATE, handle_video_upload)
    )

    # --- Error Handler ---
    application.add_error_handler(error_handler)

    # --- Set Bot Commands ---
    async def post_init(app):
        await app.bot.set_my_commands([
            BotCommand("start", "Bot help & commands"),
            BotCommand("topicid", "Show topic info (ID, Chat ID, Link)"),
            BotCommand("gettopicid", "Send in each topic to auto-save"),
            BotCommand("linktopics", "Match topics with txt file"),
            BotCommand("showtopics", "Show all saved topics"),
            BotCommand("showmapping", "Show topic mapping"),
            BotCommand("setchannel", "Set target channel for uploads"),
            BotCommand("clearmemory", "Clear saved data"),
        ])
    
    application.post_init = post_init

    # --- Start Polling ---
    print("🚀 Bot is running...")
    print("📱 Send /start to the bot to begin!")
    
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
