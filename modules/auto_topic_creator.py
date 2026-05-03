import re
import random
import asyncio
from pyrogram import Client, filters
from pyrogram.raw import functions, types
from pyrogram.types import Message
from logs import logging

# In-memory state: {user_id: {"state": "WAIT_GROUP_ID", "topics": [...]}}
_user_state = {}


def parse_topics_from_text(text: str) -> list:
    """
    Extract unique topic names from a .txt file.
    Handles ALL formats used by this bot:
      1. [Topic Name]          — bracket prefix (standalone or inline before URL)
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

        # Format 2: [Topic Name] standalone or as inline prefix before URL
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


def register_auto_topic_handlers(bot: Client):

    @bot.on_message(filters.private & filters.document, group=0)
    async def handle_txt_file(client: Client, m: Message):
        if not m.document or not m.document.file_name.endswith(".txt"):
            return

        status = await m.reply_text("📥 Reading your file...")

        try:
            file_path = await client.download_media(m, in_memory=True)
            text = bytes(file_path.getbuffer()).decode("utf-8", errors="ignore")
        except Exception as e:
            await status.edit_text(f"❌ Failed to read file: {e}")
            return

        topics = parse_topics_from_text(text)

        if not topics:
            # No topics found — let DRM handler process it normally
            await status.delete()
            return

        # Topics found — handle here, stop propagation to DRM
        _user_state[m.from_user.id] = {"state": "WAIT_GROUP_ID", "topics": topics}

        topic_list = "\n".join(f"{i+1}. {t}" for i, t in enumerate(topics))
        await status.edit_text(
            f"✅ Found **{len(topics)} topics**:\n\n{topic_list}\n\n"
            f"Now send me the **Group Chat ID** where I should create these topics.\n"
            f"_(It looks like: `-1001234567890` — use /id in your group to get it)_"
        )

        # Stop propagation so the DRM handler does NOT also process this file
        m.stop_propagation()

    @bot.on_message(
        filters.private & filters.text & ~filters.command([
            "start", "stop", "id", "info", "logs", "reset",
            "cookies", "getcookies", "ytcookies", "ytcookie",
            "y2t", "ytm", "t2t", "t2h", "json",
            "history", "yth", "viewhistory", "clearhistory",
            "createtopic", "topics", "settopic", "setuptopics",
            "parsetxt", "defaulttopic", "parsetopics", "topicid",
            "gettopicid", "linktopics", "showtopics", "showmapping",
            "clearmemory", "maketopics",
            "broadcast", "broadusers",
            "addauth", "rmauth", "users", "allhistory",
            "addaccount", "listaccounts", "removeaccount", "switchslot",
            "upgrade", "storage", "cleanup", "mini",
        ]),
        group=0,
    )
    async def handle_group_id_input(client: Client, m: Message):
        user_id = m.from_user.id
        state_data = _user_state.get(user_id)

        if not state_data or state_data.get("state") != "WAIT_GROUP_ID":
            return

        raw_id = m.text.strip()
        try:
            group_chat_id = int(raw_id)
        except ValueError:
            await m.reply_text(
                "❌ Invalid Chat ID. Please send a number like `-1001234567890`"
            )
            return

        topics = state_data["topics"]
        total  = len(topics)
        created = 0
        failed  = 0

        # Clear state immediately — prevents duplicate triggers
        _user_state.pop(user_id, None)

        progress_msg = await m.reply_text(
            f"⏳ Starting topic creation for **{total} topics**..."
        )

        # resolve_peer → InputPeerChannel, then convert to InputChannel
        try:
            peer    = await client.resolve_peer(group_chat_id)
            channel = types.InputChannel(
                channel_id=peer.channel_id,
                access_hash=peer.access_hash,
            )
        except Exception as e:
            await progress_msg.edit_text(
                f"❌ Could not find the group.\n"
                f"Check the Chat ID and make sure the bot is a member.\n`{e}`"
            )
            return

        for i, topic_name in enumerate(topics, start=1):
            try:
                await client.invoke(
                    functions.channels.CreateForumTopic(
                        channel=channel,
                        title=topic_name,
                        random_id=random.randint(1, 2**31),
                    )
                )
                created += 1
                await progress_msg.edit_text(
                    f"⏳ ({i}/{total}) ✅ Created: **{topic_name}**"
                )
            except Exception as e:
                err_str = str(e)
                failed += 1
                logging.warning(f"[AutoTopic] Failed to create '{topic_name}': {err_str}")

                if "CHAT_ADMIN_REQUIRED" in err_str or "not enough rights" in err_str.lower():
                    await progress_msg.edit_text(
                        "❌ Bot is not admin or doesn't have **Manage Topics** permission.\n"
                        "Make it admin with that permission, then try again."
                    )
                    return

                if "chat not found" in err_str.lower() or "CHANNEL_INVALID" in err_str:
                    await progress_msg.edit_text(
                        "❌ Group not found. Check the Chat ID and make sure bot is a member."
                    )
                    return

                await progress_msg.edit_text(
                    f"⏳ ({i}/{total}) ❌ Failed: **{topic_name}**\n`{err_str[:100]}`"
                )

            await asyncio.sleep(1.5)

        await progress_msg.edit_text(
            f"🏁 **Done!**\n\n"
            f"✅ {created} created\n"
            f"❌ {failed} failed\n\n"
            f"Send another `.txt` file to create more topics."
        )

    print("[AutoTopicCreator] Handlers registered: auto .txt → forum topic creator")
