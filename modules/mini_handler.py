from pyrogram import Client, filters
from pyrogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
import calendar_data as cd


# ── keyboard builders ───────────────────────────────────────────────────────

def _batches_kb(batches):
    rows = []
    for b in batches:
        rows.append([InlineKeyboardButton(
            f"📦  {b['name']}  ·  {b['count']} items",
            callback_data=f"cal_b:{b['key']}"
        )])
    rows.append([InlineKeyboardButton("📅  All Batches Calendar", callback_data="cal_b:all")])
    return InlineKeyboardMarkup(rows)


def _topicnav_batches_kb(batches):
    rows = []
    for b in batches:
        rows.append([InlineKeyboardButton(
            f"📚  {b['name']}  ·  {b['count']} items",
            callback_data=f"tn_b:{b['key']}"
        )])
    rows.append([InlineKeyboardButton("📚  All Batches Topics", callback_data="tn_b:all")])
    return InlineKeyboardMarkup(rows)


def _months_kb(months, batch_key="all"):
    rows = []
    for m in months:
        rows.append([InlineKeyboardButton(
            f"📅  {m['label']}  ·  {m['count']} items",
            callback_data=f"cal_m:{batch_key}:{m['key']}"
        )])
    rows.append([InlineKeyboardButton("📦  All Batch Names", callback_data="cal_back:batches")])
    return InlineKeyboardMarkup(rows)


def _dates_kb(year_month, dates, batch_key="all"):
    rows = []
    for d in dates:
        rows.append([InlineKeyboardButton(
            f"📌  {d['display']}  ·  {d['count']} items",
            callback_data=f"cal_d:{batch_key}:{d['date']}"
        )])
    rows.append([InlineKeyboardButton("◀️  Back to Months", callback_data=f"cal_b:{batch_key}")])
    rows.append([InlineKeyboardButton("📦  All Batch Names", callback_data="cal_back:batches")])
    return InlineKeyboardMarkup(rows)


def _date_back_kb(year_month, batch_key="all"):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("◀️  Back to Dates", callback_data=f"cal_m:{batch_key}:{year_month}")
    ], [
        InlineKeyboardButton("📦  All Batch Names", callback_data="cal_back:batches")
    ]])


# ── shared text builders ────────────────────────────────────────────────────

def _batches_text(batches):
    total = sum(b['count'] for b in batches)
    return (
        "<b>📚  Batch Content</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦  <b>Total Batches :</b>  {len(batches)}\n"
        f"📁  <b>Total Content :</b>  {total} items\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Tap a batch name first, then choose the calendar month 👇"
    )


def _months_text(months, batch_name=None):
    stats = cd.get_stats()
    total = sum(m['count'] for m in months)
    start  = stats['earliest_label'] or "—"
    title = batch_name if batch_name else "All Batches"

    header = (
        "<b>📚  Batch Content Calendar</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦  <b>Batch :</b>  {title}\n"
        f"🗓  <b>Batch Started :</b>  {start}\n"
        f"📦  <b>Total Content :</b>  {total} items across {len(months)} month(s)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Tap a month to browse uploaded content 👇"
    )
    return header


def _date_items_text(date_iso, items):
    date_display = items[0].get('date_display', date_iso) if items else date_iso
    lines = [
        f"<b>📅  {date_display}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"<b>{len(items)} item(s)</b> uploaded on this date\n",
    ]
    current_topic = None
    for item in items:
        topic = item.get('topic') or 'General'
        if topic != current_topic:
            current_topic = topic
            lines.append(f"\n<b>📚  {topic}</b>")

        icon  = {'video': '🎬', 'pdf': '📄', 'image': '🖼️', 'audio': '🎵'}.get(item.get('type', 'video'), '📎')
        title = item.get('title', 'Untitled')
        link  = cd.make_deep_link(item['channel_id'], item['message_id'], item.get('thread_id'))
        lines.append(f'{icon}  <a href="{link}">{title}</a>')

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3990] + "\n\n… <i>(list truncated)</i>"
    return text


async def _send_topic_nav(target, batch_key="all"):
    key_filter = None if batch_key == "all" else batch_key
    topics = cd.get_topics_for_batch(key_filter)
    if not topics:
        await target.reply_text("<b>📚 No topic navigation data found yet.</b>")
        return

    batch_name = "All Batches" if batch_key == "all" else (cd.get_batch_name(batch_key) or "Selected Batch")
    rows = []
    for idx, topic in enumerate(topics, 1):
        link = cd.make_deep_link(topic['channel_id'], topic['message_id'], topic.get('thread_id'))
        rows.append([InlineKeyboardButton(
            f"📚 {idx}. {topic['topic']} · {topic['count']} items",
            url=link
        )])

    text = (
        f"<b>📚 Topic Navigation</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>Batch:</b> {batch_name}\n"
        f"📌 <b>Total Topics:</b> {len(topics)}\n\n"
        f"Tap any topic below to jump to its uploaded content 👇"
    )
    for start in range(0, len(rows), 50):
        suffix = f"\n\n<i>Part {start // 50 + 1}</i>" if len(rows) > 50 else ""
        await target.reply_text(
            text + suffix,
            reply_markup=InlineKeyboardMarkup(rows[start:start + 50]),
            disable_web_page_preview=True
        )


# ── handler registration ────────────────────────────────────────────────────

def register_mini_handlers(bot: Client):

    # ── /mini command — works in ALL chats, usable by ANYONE ───────────────

    @bot.on_message(filters.command("mini"))
    async def mini_command(client: Client, m: Message):
        batches = cd.get_batches()
        if not batches:
            await m.reply_text(
                "<b>📅  No calendar data yet.</b>\n\n"
                "<b>How it works:</b>\n"
                "Every time a batch upload runs, each item is automatically recorded here "
                "using the date from its <code>{DATE-DD-Month-YYYY}</code> tag in the title.\n\n"
                "<b>Example title format:</b>\n"
                "<code>Geography Notes {DATE-5-September-2025}: //your-link</code>\n\n"
                "Once a batch upload completes, tap /mini again to browse content by month and date."
            )
            return
        await m.reply_text(_batches_text(batches), reply_markup=_batches_kb(batches))

    @bot.on_message(filters.command("topicnav"))
    async def topicnav_command(client: Client, m: Message):
        batches = cd.get_batches()
        if not batches:
            await m.reply_text("<b>📚 No uploaded batch data found yet.</b>")
            return

        query = ""
        try:
            query = " ".join(m.command[1:]).strip()
        except Exception:
            query = ""

        if query:
            match = next((b for b in batches if b['name'].lower() == query.lower()), None)
            if not match:
                match = next((b for b in batches if query.lower() in b['name'].lower()), None)
            if match:
                await _send_topic_nav(m, match['key'])
                return
            await m.reply_text("<b>Batch not found.</b>\n\nChoose one below 👇", reply_markup=_topicnav_batches_kb(batches))
            return

        await m.reply_text(
            "<b>📚 Topic Navigation</b>\n\nChoose a batch to repost its topic navigation 👇",
            reply_markup=_topicnav_batches_kb(batches)
        )

    @bot.on_callback_query(filters.regex(r'^tn_b:'))
    async def topicnav_batch(client: Client, cq: CallbackQuery):
        batch_key = cq.data.split(':', 1)[1]
        await cq.answer("Sending topic navigation...")
        await _send_topic_nav(cq.message, batch_key)

    # ── back → batches ─────────────────────────────────────────────────────

    @bot.on_callback_query(filters.regex(r'^cal_back:batches$'))
    async def cal_back_batches(client: Client, cq: CallbackQuery):
        batches = cd.get_batches()
        if not batches:
            await cq.answer("No data yet.", show_alert=True)
            return
        await cq.message.edit_text(_batches_text(batches), reply_markup=_batches_kb(batches))
        await cq.answer()

    # ── batch tapped → months ──────────────────────────────────────────────

    @bot.on_callback_query(filters.regex(r'^cal_b:'))
    async def cal_batch(client: Client, cq: CallbackQuery):
        batch_key = cq.data.split(':', 1)[1]
        key_filter = None if batch_key == "all" else batch_key
        months = cd.get_months(key_filter)
        if not months:
            await cq.answer("No calendar data for this batch.", show_alert=True)
            return
        batch_name = None if batch_key == "all" else cd.get_batch_name(batch_key)
        await cq.message.edit_text(_months_text(months, batch_name), reply_markup=_months_kb(months, batch_key))
        await cq.answer()

    # ── month tapped → show dates ──────────────────────────────────────────

    @bot.on_callback_query(filters.regex(r'^cal_m:'))
    async def cal_month(client: Client, cq: CallbackQuery):
        parts = cq.data.split(':', 2)
        if len(parts) == 3:
            batch_key, year_month = parts[1], parts[2]
        else:
            batch_key, year_month = "all", parts[1]
        key_filter = None if batch_key == "all" else batch_key
        dates = cd.get_dates_for_month(year_month, key_filter)
        if not dates:
            await cq.answer("No content for this month.", show_alert=True)
            return

        months     = cd.get_months(key_filter)
        month_label = next((m['label'] for m in months if m['key'] == year_month), year_month)
        total       = sum(d['count'] for d in dates)
        batch_name = "All Batches" if batch_key == "all" else (cd.get_batch_name(batch_key) or "Selected Batch")

        text = (
            f"<b>📅  {month_label}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 <b>{batch_name}</b>\n"
            f"<b>{total} items</b> across <b>{len(dates)} date(s)</b>\n\n"
            "Tap a date to see its content 👇"
        )
        await cq.message.edit_text(text, reply_markup=_dates_kb(year_month, dates, batch_key))
        await cq.answer()

    # ── date tapped → show items with links ───────────────────────────────

    @bot.on_callback_query(filters.regex(r'^cal_d:'))
    async def cal_date(client: Client, cq: CallbackQuery):
        parts = cq.data.split(':', 2)
        if len(parts) == 3:
            batch_key, date_iso = parts[1], parts[2]
        else:
            batch_key, date_iso = "all", parts[1]
        key_filter = None if batch_key == "all" else batch_key
        items    = cd.get_items_for_date(date_iso, key_filter)
        if not items:
            await cq.answer("No content for this date.", show_alert=True)
            return

        year_month = date_iso[:7]
        text       = _date_items_text(date_iso, items)
        await cq.message.edit_text(
            text,
            reply_markup=_date_back_kb(year_month, batch_key),
            disable_web_page_preview=True
        )
        await cq.answer()
