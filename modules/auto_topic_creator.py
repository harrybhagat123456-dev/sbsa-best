import re
import asyncio
from collections import OrderedDict
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
            if not inner.lstrip('-').isdigit():
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


def build_parent_topic_tree(topics: list) -> OrderedDict:
    """
    Group topics by their parent (part before the first '/').

    e.g. ["Arithmetic", "English/Grammar", "English/Vocab", "English"]
    →  OrderedDict({
         "Arithmetic": ["Arithmetic"],
         "English":    ["English/Grammar", "English/Vocab", "English"],
       })

    Each entry creates EXACTLY ONE forum topic (the parent).
    All children are mapped to that same forum topic ID so the DRM
    handler routes their links into the correct thread.
    """
    tree: OrderedDict = OrderedDict()
    for t in topics:
        parent = t.split('/')[0].strip()
        if parent not in tree:
            tree[parent] = []
        if t not in tree[parent]:
            tree[parent].append(t)
    return tree


def format_topic_tree(tree: OrderedDict) -> str:
    """Build a human-readable grouped topic list for Telegram messages."""
    lines = []
    for parent, children in tree.items():
        sub = [c for c in children if c != parent and '/' in c]
        if sub:
            lines.append(f"📁 **{parent}**")
            for s in sub:
                lines.append(f"    └ {s.split('/', 1)[1]}")
        else:
            lines.append(f"📌 **{parent}**")
    return "\n".join(lines)


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
            # No topics — let DRM handler process normally
            await status.delete()
            return

        tree = build_parent_topic_tree(topics)
        parent_count = len(tree)
        total_count  = len(topics)

        _user_state[m.from_user.id] = {
            "state":    "WAIT_YN",
            "topics":   topics,
            "orig_msg": m,
        }

        tree_text = format_topic_tree(tree)
        await status.edit_text(
            f"✅ Found **{total_count} topic entries** → **{parent_count} forum topics** will be created:\n\n"
            f"{tree_text}\n\n"
            f"_(Sub-topics share their parent's forum thread)_\n\n"
            f"Do you want to create these **{parent_count} topics** in a Telegram group?\n"
            f"Reply **y** to create them, or **n** to skip and start downloading."
        )

        m.stop_propagation()

    # ── Step 2 & 3: y/n → group ID ───────────────────────────────────────────
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

        # ── y/n ───────────────────────────────────────────────────────────────
        if state == "WAIT_YN":
            answer = m.text.strip().lower()
            if answer not in ("y", "n", "yes", "no"):
                await m.reply_text("Please reply **y** (yes) or **n** (no).")
                return

            if answer in ("n", "no"):
                orig = state_data["orig_msg"]
                _user_state.pop(user_id, None)
                await m.reply_text("⏩ Skipping topic creation. Starting download flow...")
                from drm_handler import drm_handler
                await drm_handler(client, orig)
                return

            state_data["state"] = "WAIT_GROUP_ID"
            await m.reply_text(
                "Send me the **Group Chat ID** where I should create these topics.\n"
                "_(It looks like: `-1001234567890` — use /id in your group to get it)_"
            )
            return

        # ── group chat ID ─────────────────────────────────────────────────────
        if state == "WAIT_GROUP_ID":
            raw_id = m.text.strip()
            try:
                group_chat_id = int(raw_id)
            except ValueError:
                await m.reply_text("❌ Invalid Chat ID. Send a number like `-1001234567890`")
                return

            topics   = state_data["topics"]
            orig_msg = state_data["orig_msg"]
            _user_state.pop(user_id, None)

            tree    = build_parent_topic_tree(topics)
            parents = list(tree.keys())
            total   = len(parents)
            created = 0
            reused  = 0
            failed  = 0
            mapping = {}   # full_topic_name → forum_topic_id

            progress_msg = await m.reply_text(
                f"⏳ Checking existing topics in group..."
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

            # Fetch existing topics once — avoids creating duplicates
            from topic_handler import fetch_channel_topics
            existing_raw = await fetch_channel_topics(client, group_chat_id)
            # {lowercase_title: topic_id}
            existing = {title.strip().lower(): tid for tid, title in existing_raw}
            if existing:
                await progress_msg.edit_text(
                    f"🔍 Found **{len(existing)}** existing topics in the group.\n"
                    f"⏳ Matching against **{total}** required topics..."
                )
                await asyncio.sleep(0.8)

            for i, parent_name in enumerate(parents, start=1):
                children  = tree[parent_name]   # all full names (parent + sub-topics)
                sub_count = len([c for c in children if c != parent_name])
                sub_note  = f" (+{sub_count} sub-topics)" if sub_count else ""

                # ── Reuse if topic already exists ─────────────────────────────
                existing_id = existing.get(parent_name.strip().lower())
                if existing_id:
                    for child in children:
                        mapping[child] = existing_id
                    mapping[parent_name] = existing_id
                    reused += 1
                    await progress_msg.edit_text(
                        f"⏳ ({i}/{total}) ♻️ **{parent_name}**{sub_note} — already exists (id: `{existing_id}`)"
                    )
                    await asyncio.sleep(0.3)
                    continue
                # ─────────────────────────────────────────────────────────────

                try:
                    result = await client.invoke(
                        functions.messages.CreateForumTopic(
                            peer=peer,
                            title=parent_name,
                            random_id=client.rnd_id(),
                        )
                    )
                    topic_id = _extract_topic_id(result)
                    if topic_id:
                        for child in children:
                            mapping[child] = topic_id
                        mapping[parent_name] = topic_id
                    created += 1

                    await progress_msg.edit_text(
                        f"⏳ ({i}/{total}) ✅ **{parent_name}**{sub_note}"
                        + (f" — thread `{topic_id}`" if topic_id else "")
                    )

                except FloodWait as fw:
                    await asyncio.sleep(fw.value + 1)
                    try:
                        result = await client.invoke(
                            functions.messages.CreateForumTopic(
                                peer=peer,
                                title=parent_name,
                                random_id=client.rnd_id(),
                            )
                        )
                        topic_id = _extract_topic_id(result)
                        if topic_id:
                            for child in children:
                                mapping[child] = topic_id
                            mapping[parent_name] = topic_id
                        created += 1
                        await progress_msg.edit_text(
                            f"⏳ ({i}/{total}) ✅ **{parent_name}** (after FloodWait)"
                        )
                    except Exception as retry_err:
                        failed += 1
                        logging.warning(f"[AutoTopic] Retry failed '{parent_name}': {retry_err}")

                except Exception as e:
                    err_str = str(e)
                    failed += 1
                    logging.warning(f"[AutoTopic] Failed '{parent_name}': {err_str}")

                    if "CHAT_ADMIN_REQUIRED" in err_str or "not enough rights" in err_str.lower():
                        await progress_msg.edit_text(
                            "❌ Bot needs **Manage Topics** admin permission in the group."
                        )
                        return

                    if "chat not found" in err_str.lower() or "CHANNEL_INVALID" in err_str:
                        await progress_msg.edit_text(
                            "❌ Group not found. Check the Chat ID and make sure bot is a member."
                        )
                        return

                    await progress_msg.edit_text(
                        f"⏳ ({i}/{total}) ❌ **{parent_name}**\n`{err_str[:100]}`"
                    )

                await asyncio.sleep(1.2)

            # Save mapping so DRM routes English/Grammar → English thread, etc.
            if mapping:
                from topic_handler import save_txt_topic_mapping
                save_txt_topic_mapping(group_chat_id, mapping)
                logging.info(
                    f"[AutoTopic] Saved mapping for {group_chat_id}: "
                    f"{len(mapping)} entries ({total} parent topics)"
                )

            await progress_msg.edit_text(
                f"🏁 **Done!**\n\n"
                f"✅ {created} created   ♻️ {reused} reused   ❌ {failed} failed\n"
                f"💾 {len(mapping)} topic name mappings saved\n"
                f"   _(sub-topics routed to parent threads)_\n\n"
                f"▶️ Starting download flow..."
            )

            from drm_handler import drm_handler
            await drm_handler(client, orig_msg)

    print("[AutoTopicCreator] Handlers registered: auto .txt → forum topic creator")
