const fs = require('fs');

class MessageIdTracker {
  constructor() {
    this.byDate  = {};   // "2025-03-10" → { "TopicName": [{title, message_id, thread_id, url, type, date}] }
    this.byMonth = {};   // "2025-03"    → { label, dates: [], totalItems }
    this.batchInfo = { startDate: null, endDate: null, totalItems: 0 };
    this._pendingSaves = 0;
    this._saveEvery    = 20;
    this._filePath     = null;
  }

  // Record one successfully sent message
  recordMessage(entry, messageId, threadId) {
    if (!entry.dateISO) return;   // skip entries without a date

    const dateKey  = entry.dateISO;             // "2025-03-10"
    const monthKey = dateKey.substring(0, 7);   // "2025-03"

    // — byDate —
    if (!this.byDate[dateKey]) this.byDate[dateKey] = {};
    if (!this.byDate[dateKey][entry.topic]) this.byDate[dateKey][entry.topic] = [];
    this.byDate[dateKey][entry.topic].push({
      title:      entry.title,
      message_id: messageId,
      thread_id:  threadId,
      url:        entry.url.startsWith('//') ? 'https:' + entry.url : entry.url,
      type:       entry.type,
      date:       entry.date
    });

    // — byMonth —
    if (!this.byMonth[monthKey]) {
      this.byMonth[monthKey] = {
        label:      this._monthLabel(monthKey),
        key:        monthKey,
        dates:      [],
        totalItems: 0
      };
    }
    const monthEntry = this.byMonth[monthKey];
    if (!monthEntry.dates.includes(dateKey)) monthEntry.dates.push(dateKey);
    monthEntry.totalItems++;

    this.batchInfo.totalItems++;
    this._pendingSaves++;

    // Periodic save every N records
    if (this._filePath && this._pendingSaves >= this._saveEvery) {
      this.saveToFile(this._filePath).catch(() => {});
      this._pendingSaves = 0;
    }
  }

  // Compute batch start/end from byDate keys
  computeBatchDateRange() {
    const allDates = Object.keys(this.byDate).sort();
    if (!allDates.length) return;
    this.batchInfo.startDate    = this.byDate[allDates[0]];
    this.batchInfo.startDateISO = allDates[0];
    this.batchInfo.endDate      = this.byDate[allDates[allDates.length - 1]];
    this.batchInfo.endDateISO   = allDates[allDates.length - 1];
  }

  getMonthsArray() {
    return Object.values(this.byMonth).sort((a, b) => a.key.localeCompare(b.key));
  }

  async saveToFile(filePath) {
    this._filePath = filePath;
    const data = {
      batchInfo: this.batchInfo,
      byDate:    this.byDate,
      byMonth:   this.byMonth
    };
    return new Promise((resolve, reject) => {
      fs.writeFile(filePath, JSON.stringify(data, null, 2), 'utf-8', err => {
        if (err) reject(err);
        else resolve();
      });
    });
  }

  static loadFromFile(filePath) {
    const tracker = new MessageIdTracker();
    if (fs.existsSync(filePath)) {
      try {
        const raw = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
        tracker.byDate    = raw.byDate    || {};
        tracker.byMonth   = raw.byMonth   || {};
        tracker.batchInfo = raw.batchInfo || { startDate: null, endDate: null, totalItems: 0 };
      } catch (e) {
        console.warn('Could not load messageIds.json, starting fresh.');
      }
    }
    tracker._filePath = filePath;
    return tracker;
  }

  _monthLabel(monthKey) {
    const [year, month] = monthKey.split('-').map(Number);
    const names = ['January','February','March','April','May','June',
                   'July','August','September','October','November','December'];
    return `${names[month - 1]} ${year}`;
  }
}

module.exports = MessageIdTracker;
