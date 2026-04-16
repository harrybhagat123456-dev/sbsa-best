const fs = require('fs');
const path = require('path');

const MONTH_MAP = {
  january: 1, february: 2, march: 3, april: 4, may: 5, june: 6,
  july: 7, august: 8, september: 9, october: 10, november: 11, december: 12,
  jan: 1, feb: 2, mar: 3, apr: 4, jun: 6, jul: 7, aug: 8,
  sep: 9, oct: 10, nov: 11, dec: 12
};

function parseMonthName(name) {
  return MONTH_MAP[name.toLowerCase()] || null;
}

function formatDate(day, month, year) {
  const monthNames = [
    '', 'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];
  return `${day} ${monthNames[month]} ${year}`;
}

function toISO(day, month, year) {
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

class FileParser {
  constructor(filePath) {
    this.filePath = filePath;
    this.entries = [];
    this.topics = new Map();
  }

  parse(startLine = 0) {
    if (!fs.existsSync(this.filePath)) {
      throw new Error(`File not found: ${this.filePath}`);
    }
    const content = fs.readFileSync(this.filePath, 'utf-8');
    const lines = content.split('\n').filter(line => line.trim().length > 0);
    console.log(`Total lines in file: ${lines.length}`);
    console.log(`Starting from line: ${startLine}`);

    for (let i = startLine; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;
      const parsed = this.parseLine(line, i);
      if (parsed) {
        this.entries.push(parsed);
        if (!this.topics.has(parsed.topic)) {
          this.topics.set(parsed.topic, []);
        }
        this.topics.get(parsed.topic).push(parsed);
      }
    }
    console.log(`Parsed ${this.entries.length} entries across ${this.topics.size} topics`);
    return { entries: this.entries, topics: this.topics, totalLines: lines.length, parsedFromLine: startLine };
  }

  parseLine(line, lineNumber) {
    // NEW FORMAT: [Topic]{DATE-DD-Month-YYYY}Title: //url
    const newMatch = line.match(/^\[(.+?)\]\{DATE-(\d{1,2})-(\w+)-(\d{4})\}\s*(.+?):\s*\/\/(.+)$/);
    if (newMatch) {
      return this._buildNewEntry(newMatch, line, lineNumber, true);
    }

    // NEW FORMAT (no colon before URL): [Topic]{DATE-DD-Month-YYYY}Title //url
    const newAltMatch = line.match(/^\[(.+?)\]\{DATE-(\d{1,2})-(\w+)-(\d{4})\}\s*(.+?)\s*\/\/(.+)$/);
    if (newAltMatch) {
      return this._buildNewEntry(newAltMatch, line, lineNumber, false);
    }

    // OLD FORMAT: (Topic) Title: //url
    const oldMatch = line.match(/^\((.+?)\)\s*(.+?):\s*\/\/(.+)$/);
    if (oldMatch) {
      const topic = oldMatch[1].trim();
      const title = oldMatch[2].trim();
      const url = '//' + oldMatch[3].trim();
      return {
        topic, title, url,
        date: null, dateISO: null, dateObj: null,
        fullLine: line, lineNumber,
        type: this.detectType(url)
      };
    }

    // OLD FORMAT (no colon before URL): (Topic) Title //url
    const oldAltMatch = line.match(/^\((.+?)\)\s*(.+?)\s*\/\/(.+)$/);
    if (oldAltMatch) {
      const topic = oldAltMatch[1].trim();
      const title = oldAltMatch[2].trim();
      const url = '//' + oldAltMatch[3].trim();
      return {
        topic, title, url,
        date: null, dateISO: null, dateObj: null,
        fullLine: line, lineNumber,
        type: this.detectType(url)
      };
    }

    return null;
  }

  _buildNewEntry(match, line, lineNumber, hasColon) {
    const topic    = match[1].trim();
    const day      = parseInt(match[2], 10);
    const monthStr = match[3];
    const year     = parseInt(match[4], 10);
    const title    = match[5].trim();
    const url      = '//' + match[6].trim();

    const monthNum = parseMonthName(monthStr);
    if (!monthNum) return null;

    const dateFormatted = formatDate(day, monthNum, year);
    const dateISO       = toISO(day, monthNum, year);
    const dateObj       = new Date(year, monthNum - 1, day);

    return {
      topic, title, url,
      date: dateFormatted,
      dateISO,
      dateObj,
      fullLine: line, lineNumber,
      type: this.detectType(url)
    };
  }

  detectType(url) {
    if (url.includes('.mpd') || url.includes('youtube.com/embed')) return 'video';
    else if (url.includes('.pdf')) return 'pdf';
    else return 'link';
  }

  getTopicSummary() {
    const summary = [];
    for (const [topic, entries] of this.topics) {
      const videos = entries.filter(e => e.type === 'video').length;
      const pdfs   = entries.filter(e => e.type === 'pdf').length;
      summary.push({ topic, total: entries.length, videos, pdfs });
    }
    return summary.sort((a, b) => b.total - a.total);
  }
}

module.exports = FileParser;
