import json
import os
import re
import hashlib
from datetime import datetime

CALENDAR_FILE = os.path.join(os.path.dirname(__file__), 'calendar.json')

MONTH_NAMES = [
    '', 'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]
_MONTH_MAP = {m.lower(): i for i, m in enumerate(MONTH_NAMES) if m}
_MONTH_MAP.update({'jan':1,'feb':2,'mar':3,'apr':4,'jun':6,'jul':7,
                   'aug':8,'sep':9,'oct':10,'nov':11,'dec':12})


# ── persistence ────────────────────────────────────────────────────────────

def _load():
    if os.path.exists(CALENDAR_FILE):
        try:
            with open(CALENDAR_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"items": []}

def _save(data):
    try:
        with open(CALENDAR_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[calendar_data] save error: {e}")


# ── date extraction ─────────────────────────────────────────────────────────

def extract_date_from_raw(raw_name: str):
    """
    Look for {DATE-DD-Month-YYYY} in the raw link name.
    Returns (date_iso, date_display) or (None, None).
    """
    m = re.search(r'\{DATE-(\d{1,2})-(\w+)-(\d{4})\}', raw_name)
    if not m:
        return None, None
    day       = int(m.group(1))
    month_str = m.group(2)
    year      = int(m.group(3))
    month_num = _MONTH_MAP.get(month_str.lower())
    if not month_num:
        return None, None
    date_iso     = f"{year}-{month_num:02d}-{day:02d}"
    date_display = f"{day} {MONTH_NAMES[month_num]} {year}"
    return date_iso, date_display


def _today_date():
    now = datetime.now()
    return now.strftime('%Y-%m-%d'), now.strftime('%-d %B %Y')


# ── recording ───────────────────────────────────────────────────────────────

def record_item(date_iso, date_display, title, topic,
                message_id, channel_id, thread_id,
                item_type, batch_name):
    """
    Record one successfully uploaded item.
    If date_iso is None/empty, today's date is used.
    """
    if not date_iso:
        date_iso, date_display = _today_date()

    data = _load()
    data['items'].append({
        'date':         date_iso,
        'date_display': date_display or date_iso,
        'title':        title or 'Untitled',
        'topic':        topic or 'General',
        'message_id':   message_id,
        'channel_id':   channel_id,
        'thread_id':    thread_id,
        'type':         item_type or 'video',
        'batch':        batch_name or '',
    })
    _save(data)


# ── queries ─────────────────────────────────────────────────────────────────

def batch_key(batch_name: str):
    return hashlib.sha1((batch_name or '').encode('utf-8')).hexdigest()[:12]


def get_batches():
    """Return list of dicts {key, name, count} sorted by newest item first."""
    data = _load()
    batches = {}
    for item in data['items']:
        name = item.get('batch') or 'Unnamed Batch'
        key = batch_key(name)
        if key not in batches:
            batches[key] = {'key': key, 'name': name, 'count': 0, 'last_date': item.get('date', '')}
        batches[key]['count'] += 1
        if item.get('date', '') > batches[key].get('last_date', ''):
            batches[key]['last_date'] = item.get('date', '')
    return sorted(batches.values(), key=lambda x: x.get('last_date', ''), reverse=True)


def get_batch_name(key: str):
    for batch in get_batches():
        if batch['key'] == key:
            return batch['name']
    return None


def get_months(batch_key_filter=None):
    """Return list of dicts {key, label, count} sorted oldest first (ascending)."""
    data     = _load()
    month_counts = {}
    for item in data['items']:
        if batch_key_filter and batch_key(item.get('batch') or 'Unnamed Batch') != batch_key_filter:
            continue
        ym = item['date'][:7]
        month_counts[ym] = month_counts.get(ym, 0) + 1

    result = []
    for ym in sorted(month_counts):          # ascending — oldest month first
        year, mon = int(ym[:4]), int(ym[5:7])
        result.append({'key': ym, 'label': f"{MONTH_NAMES[mon]} {year}", 'count': month_counts[ym]})
    return result


def get_dates_for_month(year_month: str, batch_key_filter=None):
    """Return list of dicts {date, display, count} for the given 'YYYY-MM'."""
    data = _load()
    date_counts  = {}
    date_display = {}
    for item in data['items']:
        if batch_key_filter and batch_key(item.get('batch') or 'Unnamed Batch') != batch_key_filter:
            continue
        if item['date'].startswith(year_month):
            d = item['date']
            date_counts[d]  = date_counts.get(d, 0) + 1
            date_display[d] = item.get('date_display', d)

    return [
        {'date': d, 'display': date_display[d], 'count': date_counts[d]}
        for d in sorted(date_counts)
    ]


def get_items_for_date(date_iso: str, batch_key_filter=None):
    """Return all items recorded for date_iso, grouped so same topic is together."""
    data = _load()
    items = [
        i for i in data['items']
        if i['date'] == date_iso
        and (not batch_key_filter or batch_key(i.get('batch') or 'Unnamed Batch') == batch_key_filter)
    ]
    # Sort by topic then title
    items.sort(key=lambda x: (x.get('topic',''), x.get('title','')))
    return items


def get_topics_for_batch(batch_key_filter=None):
    data = _load()
    topics = {}
    for item in data['items']:
        if batch_key_filter and batch_key(item.get('batch') or 'Unnamed Batch') != batch_key_filter:
            continue
        topic = item.get('topic') or 'General'
        if topic not in topics:
            topics[topic] = {
                'topic': topic,
                'message_id': item.get('message_id'),
                'channel_id': item.get('channel_id'),
                'thread_id': item.get('thread_id'),
                'count': 0,
                'first_date': item.get('date', ''),
            }
        topics[topic]['count'] += 1
        if item.get('date', '') < topics[topic].get('first_date', item.get('date', '')):
            topics[topic]['first_date'] = item.get('date', '')
            topics[topic]['message_id'] = item.get('message_id')
            topics[topic]['channel_id'] = item.get('channel_id')
            topics[topic]['thread_id'] = item.get('thread_id')
    return sorted(topics.values(), key=lambda x: (x.get('first_date', ''), x.get('topic', '')))


def make_deep_link(channel_id, message_id, thread_id=None):
    """Build a t.me link to the exact message."""
    cid = str(channel_id)
    if cid.startswith('-100'):
        cid_short = cid[4:]
    elif cid.startswith('-'):
        cid_short = cid[1:]
    else:
        cid_short = cid

    if thread_id:
        return f"https://t.me/c/{cid_short}/{thread_id}/{message_id}"
    return f"https://t.me/c/{cid_short}/{message_id}"


def get_stats():
    """Return dict with total_items, total_months, total_dates, earliest_date, latest_date."""
    data   = _load()
    items  = data['items']
    months = {i['date'][:7] for i in items}
    dates  = {i['date']  for i in items}
    all_dates = sorted(dates)
    earliest_iso = all_dates[0] if all_dates else None
    latest_iso   = all_dates[-1] if all_dates else None

    def _fmt(iso):
        if not iso:
            return None
        try:
            y, mo, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
            return f"{d} {MONTH_NAMES[mo]} {y}"
        except Exception:
            return iso

    return {
        'total_items':    len(items),
        'total_months':   len(months),
        'total_dates':    len(dates),
        'earliest_date':  earliest_iso,
        'latest_date':    latest_iso,
        'earliest_label': _fmt(earliest_iso),
        'latest_label':   _fmt(latest_iso),
    }
