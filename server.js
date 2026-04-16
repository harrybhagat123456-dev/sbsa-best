require('dotenv').config();
const express = require('express');
const fs      = require('fs');
const path    = require('path');

const app          = express();
const PORT         = process.env.PORT || 3000;
const MSG_IDS_FILE = path.join(__dirname, 'messageIds.json');

// ── CORS (needed for Telegram Mini App) ──────────────────────────────────
app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.sendStatus(200);
  next();
});

// ── Serve static webapp files ─────────────────────────────────────────────
app.use(express.static(path.join(__dirname, 'webapp')));

// ── Helper: load messageIds.json ──────────────────────────────────────────
function loadMessageIds() {
  if (!fs.existsSync(MSG_IDS_FILE)) return null;
  try {
    return JSON.parse(fs.readFileSync(MSG_IDS_FILE, 'utf-8'));
  } catch (e) {
    return null;
  }
}

// ── GET /api/calendar ─────────────────────────────────────────────────────
// Query params:
//   ?month=2025-03              → returns all dates + counts for that month
//   ?month=2025-03&date=2025-03-10 → returns all content for that date
app.get('/api/calendar', (req, res) => {
  const data = loadMessageIds();
  if (!data) return res.status(404).json({ error: 'No calendar data yet. Run upload first.' });

  const { month, date } = req.query;

  // Return overview of all months
  if (!month && !date) {
    const months = Object.values(data.byMonth || {}).sort((a, b) => a.key.localeCompare(b.key));
    return res.json({
      batchInfo: data.batchInfo,
      months
    });
  }

  // Return all dates for a month
  if (month && !date) {
    const monthData = (data.byMonth || {})[month];
    if (!monthData) return res.status(404).json({ error: `No data for month ${month}` });

    const dates = (monthData.dates || []).sort().map(d => {
      const dayTopics = data.byDate[d] || {};
      let total = 0;
      for (const items of Object.values(dayTopics)) total += items.length;
      return { date: d, total };
    });

    return res.json({
      month,
      label:     monthData.label,
      totalItems: monthData.totalItems,
      dates
    });
  }

  // Return all content for a specific date
  if (date) {
    const dayData = (data.byDate || {})[date];
    if (!dayData) return res.status(404).json({ error: `No data for date ${date}` });

    const groupId = process.env.GROUP_ID || '';

    const topics = Object.entries(dayData).map(([topicName, items]) => ({
      topic: topicName,
      items: items.map(item => ({
        ...item,
        deepLink: groupId
          ? `tg://privatepost?channel=${groupId}&post=${item.message_id}&thread=${item.thread_id}`
          : null
      }))
    }));

    const totalItems = topics.reduce((sum, t) => sum + t.items.length, 0);

    return res.json({ date, totalItems, topics });
  }

  return res.status(400).json({ error: 'Invalid query parameters' });
});

// ── Catch-all → serve index.html ─────────────────────────────────────────
app.get('*', (req, res) => {
  const indexPath = path.join(__dirname, 'webapp', 'index.html');
  if (fs.existsSync(indexPath)) res.sendFile(indexPath);
  else res.status(404).send('Mini App not found');
});

app.listen(PORT, () => {
  console.log(`\n🌐 Mini App server running on port ${PORT}`);
  console.log(`   Local:    http://localhost:${PORT}`);
  if (process.env.WEBAPP_URL) console.log(`   Public:   ${process.env.WEBAPP_URL}`);
  console.log(`   API:      http://localhost:${PORT}/api/calendar\n`);
});

module.exports = app;
