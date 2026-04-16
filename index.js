require('dotenv').config();
const fs   = require('fs');
const path = require('path');
const { Bot, InlineKeyboard } = require('grammy');
const FileParser       = require('./parser');
const TopicManager     = require('./topicManager');
const MessageIdTracker = require('./messageIdTracker');

const BOT_TOKEN     = process.env.BOT_TOKEN;
const GROUP_ID      = process.env.GROUP_ID;
const INPUT_FILE    = process.env.INPUT_FILE;
const WEBAPP_URL    = process.env.WEBAPP_URL || '';
const MESSAGE_DELAY = parseInt(process.env.MESSAGE_DELAY) || 1500;
const BATCH_SIZE    = parseInt(process.env.BATCH_SIZE)    || 20;
const BATCH_PAUSE   = parseInt(process.env.BATCH_PAUSE)   || 5000;
const PROGRESS_FILE  = './progress.json';
const MSG_IDS_FILE   = './messageIds.json';

// ── Progress helpers ───────────────────────────────────────────────────────
function loadProgress() {
  if (fs.existsSync(PROGRESS_FILE)) {
    try { return JSON.parse(fs.readFileSync(PROGRESS_FILE, 'utf-8')); }
    catch (e) {}
  }
  return { lastSentLine: 0, sentTopics: {}, totalSent: 0, startTime: null };
}
function saveProgress(progress) {
  fs.writeFileSync(PROGRESS_FILE, JSON.stringify(progress, null, 2));
}

// ── Batch date helpers ─────────────────────────────────────────────────────
function computeBatchDates(entries) {
  const dated = entries.filter(e => e.dateObj instanceof Date && !isNaN(e.dateObj));
  if (!dated.length) return null;
  dated.sort((a, b) => a.dateObj - b.dateObj);
  const first = dated[0];
  const last  = dated[dated.length - 1];

  const daySpan = Math.round((last.dateObj - first.dateObj) / (1000 * 60 * 60 * 24));

  // Unique months
  const monthSet = new Set(dated.map(e => e.dateISO.substring(0, 7)));
  const monthNames = ['January','February','March','April','May','June',
                      'July','August','September','October','November','December'];
  const monthsCovered = [...monthSet].sort().map(mk => {
    const [y, m] = mk.split('-').map(Number);
    return `${monthNames[m - 1]} ${y}`;
  });

  return {
    startDate:     first.date,
    startDateISO:  first.dateISO,
    endDate:       last.date,
    endDateISO:    last.dateISO,
    daySpan,
    monthsCovered,
    monthKeys:     [...monthSet].sort()
  };
}

function printBatchDateReport(info) {
  console.log('\n============================================');
  console.log('  BATCH DATES');
  console.log('============================================');
  console.log(`📅 Batch Start Date: ${info.startDate}`);
  console.log(`📅 Batch End Date:   ${info.endDate}`);
  console.log(`📊 Total Days Span:  ${info.daySpan} days`);
  console.log(`📊 Months Covered:   ${info.monthsCovered.join(', ')}`);
  console.log('============================================\n');
}

// ── /calendar command + callback handler (bot listener mode) ───────────────
async function startBotHandlers(botToken) {
  const bot = new Bot(botToken);
  console.log('Starting bot listener (calendar commands)...');

  bot.command('calendar', async ctx => {
    if (!fs.existsSync(MSG_IDS_FILE)) {
      return ctx.reply('No calendar data yet. Run the upload first.');
    }
    try {
      const data   = JSON.parse(fs.readFileSync(MSG_IDS_FILE, 'utf-8'));
      const months = Object.values(data.byMonth || {}).sort((a, b) => a.key.localeCompare(b.key));
      if (!months.length) return ctx.reply('No dated content found in the calendar.');

      const info = data.batchInfo || {};
      const headerText =
        `📅 <b>Batch Calendar — Content Navigator</b>\n` +
        `━━━━━━━━━━━━━━━━━━━━\n` +
        (info.startDate && info.endDate
          ? `From: <b>${info.startDate}</b> → To: <b>${info.endDate}</b>\n\n`
          : '') +
        `Tap a month to browse content by date 👇`;

      const rows = months.map(m => ([{
        text: `📅 ${m.label} (${m.totalItems} items)`,
        callback_data: JSON.stringify({ action: 'open_month', month: m.key })
      }]));

      await ctx.reply(headerText, {
        parse_mode: 'HTML',
        reply_markup: { inline_keyboard: rows }
      });
    } catch (err) {
      console.error('/calendar error:', err.message);
      ctx.reply('Error loading calendar data.');
    }
  });

  bot.on('callback_query', async ctx => {
    try {
      const data = JSON.parse(ctx.callbackQuery.data || '{}');
      if (data.action === 'open_month' && data.month) {
        const webUrl = WEBAPP_URL
          ? `${WEBAPP_URL.replace(/\/$/, '')}/index.html?month=${data.month}`
          : null;
        if (webUrl) {
          await ctx.answerCallbackQuery({ url: webUrl });
        } else {
          await ctx.answerCallbackQuery({
            text: 'Set WEBAPP_URL in .env to enable the Mini App.',
            show_alert: true
          });
        }
      }
    } catch (e) {
      await ctx.answerCallbackQuery({ text: 'Error', show_alert: false });
    }
  });

  bot.start();
  return bot;
}

// ── Main upload flow ───────────────────────────────────────────────────────
async function main() {
  if (!BOT_TOKEN || BOT_TOKEN === 'YOUR_BOT_TOKEN_HERE') {
    console.error('❌ BOT_TOKEN not set!'); process.exit(1);
  }
  if (!GROUP_ID || GROUP_ID === 'YOUR_GROUP_ID_HERE') {
    console.error('❌ GROUP_ID not set!'); process.exit(1);
  }

  // No input file → bot listener mode only
  if (!INPUT_FILE || !fs.existsSync(INPUT_FILE)) {
    console.log('No INPUT_FILE found — starting bot in listener mode (calendar commands only).');
    await startBotHandlers(BOT_TOKEN);
    return;
  }

  if (process.argv.includes('--reset') && fs.existsSync(PROGRESS_FILE)) fs.unlinkSync(PROGRESS_FILE);

  const parser    = new FileParser(INPUT_FILE);
  const progress  = loadProgress();
  const startLine = parseInt(process.env.RESUME_FROM_LINE) || progress.lastSentLine;
  const { entries, topics, totalLines } = parser.parse(startLine);

  if (entries.length === 0) {
    console.log('No new entries to upload — starting bot in listener mode.');
    await startBotHandlers(BOT_TOKEN);
    return;
  }

  const manager = new TopicManager(BOT_TOKEN, GROUP_ID);
  const initialized = await manager.initialize();
  if (!initialized) { console.error('Failed to initialize bot.'); process.exit(1); }

  // Create all topics upfront
  for (const [topicName] of topics) {
    const emoji = manager.getTopicEmoji(topicName);
    await manager.createTopic(topicName, emoji);
  }

  // Load or create tracker
  const tracker = MessageIdTracker.loadFromFile(MSG_IDS_FILE);
  tracker._saveEvery = BATCH_SIZE;

  manager.messagesSent  = 0;
  manager.totalMessages = entries.length;
  progress.startTime    = progress.startTime || new Date().toISOString();

  let successCount = 0, failCount = 0, batchCount = 0;
  const uploadedEntries = [];

  for (const entry of entries) {
    const result = await manager.sendToTopic(entry.topic, entry);
    if (result && result.message && result.message.message_id) {
      successCount++;
      uploadedEntries.push(entry);
      progress.lastSentLine = entry.lineNumber + 1;
      progress.totalSent    = (progress.totalSent || 0) + 1;

      // Record message ID for calendar
      tracker.recordMessage(entry, result.message.message_id, result.threadId);

      if (successCount % 10 === 0) {
        saveProgress(progress);
        await tracker.saveToFile(MSG_IDS_FILE);
      }
    } else {
      failCount++;
    }

    batchCount++;
    if (batchCount >= BATCH_SIZE) {
      await new Promise(r => setTimeout(r, BATCH_PAUSE));
      batchCount = 0;
    } else {
      await new Promise(r => setTimeout(r, MESSAGE_DELAY));
    }
  }

  console.log(`\n✅ Done! Sent: ${successCount}, Failed: ${failCount}`);

  // ── Batch date report ─────────────────────────────────────────────────────
  const allUploadedEntries = entries; // includes all parsed for dates
  const batchDates = computeBatchDates(allUploadedEntries);
  if (batchDates) {
    printBatchDateReport(batchDates);
    progress.batchStartDate    = batchDates.startDate;
    progress.batchEndDate      = batchDates.endDate;
    progress.batchStartDateISO = batchDates.startDateISO;
    progress.batchEndDateISO   = batchDates.endDateISO;
    progress.monthsCovered     = batchDates.monthsCovered;

    // Update tracker batch info
    tracker.batchInfo.startDate    = batchDates.startDate;
    tracker.batchInfo.startDateISO = batchDates.startDateISO;
    tracker.batchInfo.endDate      = batchDates.endDate;
    tracker.batchInfo.endDateISO   = batchDates.endDateISO;
  }

  saveProgress(progress);
  await tracker.saveToFile(MSG_IDS_FILE);

  // ── Send calendar message to group ────────────────────────────────────────
  const months = tracker.getMonthsArray();
  if (months.length > 0 && batchDates) {
    const noticesThreadId = manager.topicThreadIds.get('Notices') || null;
    await manager.sendCalendarMessage(
      months,
      batchDates.startDate,
      batchDates.endDate,
      noticesThreadId
    );
  }

  // ── Keep bot alive for calendar commands ──────────────────────────────────
  console.log('Upload complete. Starting bot listener for /calendar commands...');
  await startBotHandlers(BOT_TOKEN);
}

main().catch(err => { console.error('Fatal error:', err); process.exit(1); });
