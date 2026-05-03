import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

logging.basicConfig(level=logging.INFO)

WAIT_GROUP_ID = 1


def parse_topics(text: str) -> list:
    topics = []
    for line in text.splitlines():
        if "📌" in line and "—" in line:
            name = line.split("📌")[1].split("—")[0].strip()
            if name:
                topics.append(name[:128])
    return topics


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    file = await doc.get_file()
    raw = await file.download_as_bytearray()
    text = raw.decode("utf-8", errors="ignore")

    topics = parse_topics(text)

    if not topics:
        await update.message.reply_text(
            "❌ No topics found in the file.\n"
            "Make sure lines follow the format:\n"
            "`📌 Topic Name — 123 links`"
        )
        return ConversationHandler.END

    context.user_data["topics"] = topics

    lines = [f"✅ Found {len(topics)} topics:"]
    for i, t in enumerate(topics, 1):
        lines.append(f"{i}. {t}")
    lines.append("")
    lines.append("Now send me the Group Chat ID where I should create these topics.")
    lines.append("(It looks like: -1001234567890)")

    await update.message.reply_text("\n".join(lines))
    return WAIT_GROUP_ID


async def handle_group_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()

    try:
        group_chat_id = int(raw)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid Chat ID. Please send a number like -1001234567890"
        )
        return WAIT_GROUP_ID

    topics = context.user_data.get("topics", [])
    total = len(topics)

    await update.message.reply_text(f"⏳ Starting topic creation for {total} topics...")

    created = 0
    failed = 0

    try:
        for idx, topic_name in enumerate(topics, 1):
            try:
                await context.bot.create_forum_topic(
                    chat_id=group_chat_id,
                    name=topic_name,
                )
                created += 1
                await update.message.reply_text(f"✅ ({idx}/{total}) Created: {topic_name}")
            except Exception as e:
                err = str(e)
                if "not enough rights" in err or "TOPIC_CREATE_FORBIDDEN" in err:
                    await update.message.reply_text(
                        "❌ Bot does not have Manage Topics permission in this group. "
                        "Make it admin with that permission."
                    )
                    return ConversationHandler.END
                if "chat not found" in err:
                    await update.message.reply_text(
                        "❌ Group not found. Check the Chat ID and make sure the bot is a member of the group."
                    )
                    return ConversationHandler.END
                failed += 1
                logging.warning(f"Failed to create topic '{topic_name}': {e}")
                await update.message.reply_text(f"❌ ({idx}/{total}) Failed: {topic_name} — {err}")
            await asyncio.sleep(1.5)
    except Exception as e:
        await update.message.reply_text(f"❌ Unexpected error: {e}")
        return ConversationHandler.END

    await update.message.reply_text(
        f"🏁 Done! ✅ {created} created  ❌ {failed} failed\n"
        f"Send another .txt file to start again."
    )
    return ConversationHandler.END


conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Document.TXT, handle_file)],
    states={
        WAIT_GROUP_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_group_id)],
    },
    fallbacks=[],
    allow_reentry=True,
)

if __name__ == "__main__":
    load_dotenv()
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(conv_handler)
    app.run_polling()
