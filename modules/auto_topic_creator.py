import re
import asyncio
from pyrogram import Client, filters
from pyrogram.raw import functions
from pyrogram.errors import FloodWait
from pyrogram.types import Message
from logs import logging

# In-memory state: {user_id: {"state": ..., "topics": [...], "orig_msg": Message}}
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


def _extract_topic_id(result) -> int | None:
    """Extract the new topic's thread ID from a CreateForumTopic raw result."""
    for update in result.updates:
        msg = getattr(update, "message", None)
        if msg and getattr(msg, "id", None):
            return msg.id
    if len(result.updates) > 1:
        msg = getattr(result.updates[1], "message", None)
        if msg:
            return msg.id
    return None


def register_auto_topic_handlers(bot: Client):

    # ── Step 1: .txt file uploaded ────────────────────────────────────────────
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

        # Topics found — ask user whether to create them
        _user_state[m.from_user.id] = {
            "state":    "WAIT_YN",
            "topics":   topics,
            "orig_msg": m,
        }

        topic_list = "\n".join(f"{i+1}. {t}" for i, t in enumerate(topics))
        await status.edit_text(
            f"✅ Found **{len(topics)} topics**:\n\n{topic_list}\n\n"
            f"Do you want to create these topics in a Telegram group?\n"
            f"Reply **y** to create them, or **n** to skip and start downloading."
        )

        # Stop propagation — DRM handler must NOT also fire on this upload
        m.stop_propagation()

    # ── Step 2: y / n reply ───────────────────────────────────────────────────
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
    async def handle_text_input(client: Client, m: Message):
        user_id    = m.from_user.id
        state_data = _user_state.get(user_id)
        if not state_data:
            return

        state = state_data.get("state")

        # ── y/n question ──────────────────────────────────────────────────────
        if state == "WAIT_YN":
            answer = m.text.strip().lower()
            if answer not in ("y", "n", "yes", "no"):
                await m.reply_text("Please reply **y** (yes) or **n** (no).")
                return

            if answer in ("n", "no"):
                # Skip topic creation — pass file straight to DRM
                orig = state_data["orig_msg"]
                _user_state.pop(user_id, None)
                await m.reply_text("⏩ Skipping topic creation. Starting download flow...")
                from drm_handler import drm_handler
                await drm_handler(client, orig)
                return

            # y — ask for group chat ID
            state_data["state"] = "WAIT_GROUP_ID"
            await m.reply_text(
                "Send me the **Group Chat ID** where I should create these topics.\n"
                "_(It looks like: `-1001234567890` — use /id in your group to get it)_"
            )
            return

        # ── group chat ID input ───────────────────────────────────────────────
        if state == "WAIT_GROUP_ID":
            raw_id = m.text.strip()
            try:
                group_chat_id = int(raw_id)
            except ValueError:
                await m.reply_text("❌ Invalid Chat ID. Please send a number like `-1001234567890`")
                return

            topics   = state_data["topics"]
            orig_msg = state_data["orig_msg"]
            total    = len(topics)
            created  = 0
            failed   = 0
            mapping  = {}   # topic_name → topic_id

            _user_state.pop(user_id, None)

            progress_msg = await m.reply_text(
                f"⏳ Starting topic creation for **{total} topics**..."
            )

            # Resolve peer once
            try:
                peer = await client.resolve_peer(group_chat_id)
            except Exception as e:
                await progress_msg.edit_text(
                    f"❌ Could not find the group.\n"
                    f"Check the Chat ID and make sure the bot is a member.\n`{e}`"
                )
                return

            for i, topic_name in enumerate(topics, start=1):
                try:
                    result = await client.invoke(
                        functions.messages.CreateForumTopic(
                            peer=peer,
                            title=topic_name,
                            random_id=client.rnd_id(),
                        )
                    )
                    topic_id = _extract_topic_id(result)
                    if topic_id:
                        mapping[topic_name] = topic_id
                    created += 1
                    await progress_msg.edit_text(
                        f"⏳ ({i}/{total}) ✅ Created: **{topic_name}**"
                        + (f" (id: `{topic_id}`)" if topic_id else "")
                    )
                except FloodWait as fw:
                    await asyncio.sleep(fw.value + 1)
                    try:
                        result = await client.invoke(
                            functions.messages.CreateForumTopic(
                                peer=peer,
                                title=topic_name,
                                random_id=client.rnd_id(),
                            )
                        )
                        topic_id = _extract_topic_id(result)
                        if topic_id:
                            mapping[topic_name] = topic_id
                        created += 1
                        await progress_msg.edit_text(
                            f"⏳ ({i}/{total}) ✅ Created: **{topic_name}**"
                            + (f" (id: `{topic_id}`)" if topic_id else "")
                        )
                    except Exception as retry_err:
                        failed += 1
                        logging.warning(f"[AutoTopic] FloodWait retry failed '{topic_name}': {retry_err}")
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

                await asyncio.sleep(1.2)

            # Save the topic mapping so the DRM handler can route links to the right topics
            if mapping:
                from topic_handler import save_txt_topic_mapping
                save_txt_topic_mapping(group_chat_id, mapping)
                logging.info(f"[AutoTopic] Saved topic mapping for {group_chat_id}: {len(mapping)} entries")

            await progress_msg.edit_text(
                f"🏁 **Topics created!**\n\n"
                f"✅ {created} created   ❌ {failed} failed\n"
                f"💾 Topic mapping saved for group `{group_chat_id}`\n\n"
                f"▶️ Starting download flow now..."
            )

            # Hand off to the DRM handler to ask download questions
            from drm_handler import drm_handler
            await drm_handler(client, orig_msg)

    print("[AutoTopicCreator] Handlers registered: auto .txt → forum topic creator")
