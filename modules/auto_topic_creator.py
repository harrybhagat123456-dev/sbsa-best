import asyncio
import random
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.handlers import MessageHandler
from pyrogram import raw
from logs import logging

# In-memory state: {user_id: {"state": "WAIT_GROUP_ID", "topics": [...]}}
_user_state = {}


def parse_topics_from_text(text: str) -> list:
    topics = []
    for line in text.splitlines():
        if "📌" in line and "—" in line:
            try:
                name = line.split("📌")[1].split("—")[0].strip()
                if name:
                    topics.append(name[:128])
            except Exception:
                continue
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
            # No 📌 topics — let DRM handler process it normally
            await status.delete()
            return

        # 📌 topics found — handle here, stop propagation to DRM
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
        total = len(topics)
        created = 0
        failed = 0

        # Clear state immediately — prevents duplicate triggers
        _user_state.pop(user_id, None)

        progress_msg = await m.reply_text(
            f"⏳ Starting topic creation for **{total} topics**..."
        )

        for i, topic_name in enumerate(topics, start=1):
            try:
                peer = await client.resolve_peer(group_chat_id)
                await client.invoke(
                    raw.functions.channels.CreateForumTopic(
                        channel=peer,
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
                logging.warning(f"[AutoTopic] Failed to create '{topic_name}': {e}")

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
