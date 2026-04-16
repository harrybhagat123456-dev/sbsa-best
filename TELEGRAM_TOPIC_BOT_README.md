# Telegram Topic Bot v2

A Node.js Telegram bot (grammy) that reads categorised educational content links from a text file, creates forum topics in a supergroup, uploads each link to the correct topic, and provides a **Telegram Mini App calendar navigator** for browsing uploaded content by month and date.

---

## Features

- Parses two input formats (old and new with dates)
- Creates Telegram forum topics automatically
- Routes each link to the correct topic thread
- Tracks upload progress and supports resume
- Date-aware: shows 📅 date in messages (new format)
- Batch date reporting: start date, end date, months covered
- Sends a month-picker inline keyboard after upload
- Telegram Mini App calendar: month → date → content → deep link to exact message in group

---

## Input File Formats

### OLD FORMAT (still supported)
```
(Topic) Title of content: //domain.com/video.mpd&parentId=xxx&childId=yyy
(Notices) Check this out: //example.com/file.pdf
```

### NEW FORMAT (with date)
```
[Topic]{DATE-DD-Month-YYYY}Title of content: //domain.com/video.mpd&parentId=xxx
[Ethics]{DATE-10-March-2025}Ethics 01: What is Ethics: //cdn.example.com/master.mpd
[Geography]{DATE-15-April-2025}Geography Notes.pdf: //static.example.com/notes.pdf
[Notices]{DATE-05-May-2025}New Feature Update: //example.com/video.mpd
```

Both formats can be mixed in the same file.

---

## Setup

### 1. Install dependencies
```bash
npm install
```

### 2. Configure environment
Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Your bot token from @BotFather |
| `GROUP_ID`  | Your supergroup ID (e.g. `-1001234567890`) |
| `INPUT_FILE`| Path to your input text file |
| `WEBAPP_URL`| Public URL of this Replit app (set after first deploy) |
| `MESSAGE_DELAY` | Milliseconds between messages (default: 1500) |
| `BATCH_SIZE`    | Messages per batch before pausing (default: 20) |
| `BATCH_PAUSE`   | Milliseconds pause between batches (default: 5000) |

### 3. Enable Forum/Topics in your Telegram supergroup
Open group settings → Topics → Enable

### 4. Add your bot as admin in the group
Required permissions: Send messages, Manage topics

### 5. Run the upload
```bash
npm start
```

### 6. Start the Mini App server (in a second terminal or combined with main process)
```bash
node server.js
```

---

## Bot Commands

| Command | Description |
|---------|-------------|
| `/calendar` | Sends the month-picker inline keyboard to browse content |

---

## Telegram Mini App Setup (@BotFather)

1. Open @BotFather → `/newapp`
2. Set the Web App URL to your Replit app public URL (e.g. `https://your-project.replit.app`)
3. Optionally: `/setmenubutton` → set the menu button to open the Web App

---

## Files

| File | Purpose |
|------|---------|
| `parser.js` | Parses OLD and NEW format lines from input file |
| `topicManager.js` | Creates topics, sends messages, returns message IDs |
| `messageIdTracker.js` | Tracks date→topic→message_id mapping, saves to `messageIds.json` |
| `index.js` | Main upload loop + bot command handlers |
| `server.js` | Express server serving the Mini App + `/api/calendar` API |
| `webapp/index.html` | Mini App HTML shell |
| `webapp/style.css` | Mobile-first Telegram-themed styles |
| `webapp/app.js` | Mini App logic (fetch, render, deep links) |
| `progress.json` | Auto-generated: upload progress + batch dates |
| `messageIds.json` | Auto-generated: date→message_id map for calendar |

---

## Deep Link Format

The Mini App generates deep links to open specific messages in the group:
```
tg://privatepost?channel=-100XXXXXXXXXX&post=MESSAGE_ID&thread=THREAD_ID
```
Tapping this link in Telegram jumps directly to that message in the correct topic thread.

---

## Resume Interrupted Upload

If the upload is interrupted, simply run `npm start` again — it will resume from where it left off using `progress.json`.

To start from scratch:
```bash
node index.js --reset
```

---

## Two Modes

| Mode | When | Command |
|------|------|---------|
| **Upload mode** | `INPUT_FILE` exists and has unprocessed lines | `npm start` |
| **Listener mode** | All lines uploaded or no `INPUT_FILE` | `npm start` (auto-detected) |
