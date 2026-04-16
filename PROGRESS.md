# Telegram Topic Bot v2 — Build Progress

## Overview
Upgrading the Node.js Telegram bot (grammy) with 3 new features:
1. New date format parser
2. Batch date reporting
3. Telegram Mini App calendar navigator

---

## Task List

### PHASE 1 — Core Files (Existing, kept as-is)
- [x] **package.json** — base dependencies (grammy, dotenv)
- [x] **parser.js** — OLD format `(Topic) Title: //url` parsing
- [x] **topicManager.js** — topic creation, message sending
- [x] **index.js** — main upload loop with progress tracking
- [x] **.env.example** — base environment config

---

### PHASE 2 — Feature 1: New Date Format Parser
- [x] **parser.js UPGRADED** — support NEW format `[Topic]{DATE-DD-Month-YYYY}Title: //url`
  - [x] Regex for new format: `^\[(.+?)\]\{DATE-(\d{1,2})-(\w+)-(\d{4})\}\s*(.+?):\s*\/\/(.+)$`
  - [x] Parse month name → month number (full + abbreviated)
  - [x] Return `date`, `dateISO`, `dateObj` fields in entry object
  - [x] OLD format backward compatibility preserved (returns `date: null`)
- [x] **topicManager.js UPGRADED** — `buildMessage()` shows `📅 date` line when date exists

---

### PHASE 3 — Feature 2: Batch Date Reporting
- [x] **index.js UPGRADED** — after upload loop:
  - [x] Find earliest date (Batch Start Date) from all uploaded entries
  - [x] Find latest date (Batch End Date) from all uploaded entries
  - [x] Calculate total days span
  - [x] List all months covered
  - [x] Print formatted report to console
  - [x] Save `batchStartDate`, `batchEndDate`, `batchStartDateISO`, `batchEndDateISO`, `monthsCovered` to progress.json

---

### PHASE 4 — Feature 3: Message ID Tracker
- [x] **messageIdTracker.js CREATED** — new module
  - [x] `recordMessage(entry, message_id, thread_id)` — stores mapping
  - [x] Data structure: `byDate → topic → [{ title, message_id, thread_id, url, type, date }]`
  - [x] `byMonth` index for quick month lookups
  - [x] `saveToFile('./messageIds.json')` — persists to disk
  - [x] Save every 20 messages (not just at end)
- [x] **topicManager.js** — `sendToTopic()` confirmed to return full sent message object
- [x] **index.js** — after each successful send, calls `messageIdTracker.recordMessage()`

---

### PHASE 5 — Feature 3: Express Server + API
- [x] **server.js CREATED** — new file
  - [x] Serves `./webapp` static files
  - [x] `GET /api/calendar?month=2025-03` — returns month data from messageIds.json
  - [x] `GET /api/calendar?month=2025-03&date=2025-03-10` — returns day data
  - [x] Runs on `process.env.PORT || 3000`
  - [x] CORS headers for Telegram Mini App

---

### PHASE 6 — Feature 3: Telegram Mini App UI
- [x] **webapp/index.html CREATED**
  - [x] Telegram Web App SDK included
  - [x] Month view (date cards)
  - [x] Date detail view (content list with deep links)
  - [x] Back button navigation
- [x] **webapp/style.css CREATED**
  - [x] Mobile-first layout
  - [x] Telegram theme colors (CSS variables from `tg.themeParams`)
  - [x] Card shadows, 12px rounded corners
  - [x] Smooth animations
- [x] **webapp/app.js CREATED**
  - [x] Init Telegram Web App SDK
  - [x] Read `?month=` from URL params
  - [x] Fetch `/api/calendar?month=...` → render date cards
  - [x] On date click → fetch detail → render content list
  - [x] Deep links via `Telegram.WebApp.openTelegramLink()`
  - [x] Deep link format: `tg://privatepost?channel=GROUP_ID&post=MSG_ID&thread=THREAD_ID`

---

### PHASE 7 — Feature 3: Bot Calendar Command & Inline Keyboard
- [x] **index.js UPGRADED** — after upload complete:
  - [x] Send calendar message with month picker to group (Notices topic)
  - [x] InlineKeyboard with `📅 Month YYYY (N items)` buttons
  - [x] `/calendar` command handler — resends month picker
  - [x] Callback query handler — answers with Mini App URL for selected month

---

### PHASE 8 — Configuration & Docs
- [x] **package.json UPDATED** — added `express` dependency
- [x] **.env.example UPDATED** — added `WEBAPP_URL`
- [x] **README.md UPDATED** — setup instructions including Mini App + BotFather config

---

## Status Summary

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Core existing files | ✅ Complete |
| 2 | Feature 1 — Date format parser | ✅ Complete |
| 3 | Feature 2 — Batch date reporting | ✅ Complete |
| 4 | Message ID tracker module | ✅ Complete |
| 5 | Express server + API | ✅ Complete |
| 6 | Mini App UI (HTML/CSS/JS) | ✅ Complete |
| 7 | Bot calendar command + inline keyboard | ✅ Complete |
| 8 | Config & docs | ✅ Complete |
| 9 | Node.js 20 runtime installed | ✅ Complete |
| 10 | npm packages installed (grammy, dotenv, express) | ✅ Complete |
| 11 | Syntax check: all JS files pass | ✅ Complete |
| 12 | Parser test: OLD + NEW format both work | ✅ Verified |

---

## Files Created / Modified

| File | Status | Notes |
|------|--------|-------|
| `package.json` | ✅ Updated | Added express |
| `.env.example` | ✅ Updated | Added WEBAPP_URL |
| `parser.js` | ✅ Upgraded | Supports both OLD + NEW format |
| `topicManager.js` | ✅ Upgraded | Date in message, returns sent object |
| `index.js` | ✅ Upgraded | Tracking, reporting, calendar send |
| `messageIdTracker.js` | ✅ Created | New module |
| `server.js` | ✅ Created | New file |
| `webapp/index.html` | ✅ Created | New file |
| `webapp/style.css` | ✅ Created | New file |
| `webapp/app.js` | ✅ Created | New file |
| `README.md` | ✅ Updated | Full setup guide |
