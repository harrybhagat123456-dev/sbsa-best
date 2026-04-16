const { Bot, InlineKeyboard } = require('grammy');

class TopicManager {
  constructor(botToken, groupId) {
    this.bot = new Bot(botToken);
    this.groupId = parseInt(groupId);
    this.topicThreadIds = new Map();
    this.rateLimitCount = 0;
    this.lastResetTime = Date.now();
    this.messagesSent = 0;
    this.totalMessages = 0;
  }

  async initialize() {
    try {
      const botInfo = await this.bot.api.getMe();
      console.log(`Bot: @${botInfo.username} (${botInfo.first_name})`);
      const chat = await this.bot.api.getChat(this.groupId);
      console.log(`Group: ${chat.title}`);
      if (chat.is_forum) console.log('Forum/Topics mode is ENABLED');
      else console.log('WARNING: Forum/Topics mode is NOT enabled!');
      return true;
    } catch (error) {
      console.error('Failed to initialize bot:', error.message);
      return false;
    }
  }

  async createTopic(topicName, emoji = '📁') {
    if (this.topicThreadIds.has(topicName)) return this.topicThreadIds.get(topicName);
    try {
      const result = await this.bot.api.createForumTopic(this.groupId, topicName, {
        icon_custom_emoji_id: '',
        icon_color: this.getTopicColor(topicName)
      });
      try {
        await this.bot.api.sendMessage(this.groupId, `${emoji} <b>${topicName}</b>`, {
          message_thread_id: result.message_thread_id,
          parse_mode: 'HTML'
        });
      } catch (e) {}
      this.topicThreadIds.set(topicName, result.message_thread_id);
      await this.sleep(1500);
      return result.message_thread_id;
    } catch (error) {
      console.error(`Failed to create topic "${topicName}":`, error.message);
      return null;
    }
  }

  getTopicColor(topicName) {
    const colors = [0x6FB9F0, 0xFFD67E, 0xCB86DB, 0x8EEE98, 0xFF93B2, 0xFB6F5F];
    let hash = 0;
    for (let i = 0; i < topicName.length; i++) hash = topicName.charCodeAt(i) + ((hash << 5) - hash);
    return colors[Math.abs(hash) % colors.length];
  }

  // Returns the full sent message object (with message_id) or false on failure
  async sendToTopic(topicName, entry) {
    let threadId = this.topicThreadIds.get(topicName);
    if (!threadId) {
      const emoji = this.getTopicEmoji(topicName);
      threadId = await this.createTopic(topicName, emoji);
      if (!threadId) return false;
    }

    const message = this.buildMessage(entry);
    try {
      await this.checkRateLimit();
      const sent = await this.bot.api.sendMessage(this.groupId, message.text, {
        message_thread_id: threadId,
        parse_mode: 'HTML',
        disable_web_page_preview: entry.type === 'pdf'
      });
      this.messagesSent++;
      // Return BOTH the message object AND the threadId so the caller can track both
      return { message: sent, threadId };
    } catch (error) {
      if (error.message && (error.message.includes('thread') || error.message.includes('topic'))) {
        this.topicThreadIds.delete(topicName);
        const emoji = this.getTopicEmoji(topicName);
        threadId = await this.createTopic(topicName, emoji);
        if (threadId) {
          try {
            const sent = await this.bot.api.sendMessage(this.groupId, message.text, {
              message_thread_id: threadId,
              parse_mode: 'HTML',
              disable_web_page_preview: entry.type === 'pdf'
            });
            this.messagesSent++;
            return { message: sent, threadId };
          } catch (retryError) {
            console.error('Retry failed:', retryError.message);
            return false;
          }
        }
      }
      console.error(`Failed to send to topic "${topicName}":`, error.message);
      return false;
    }
  }

  buildMessage(entry) {
    let icon;
    switch (entry.type) {
      case 'video': icon = '🎬'; break;
      case 'pdf':   icon = '📄'; break;
      default:      icon = '🔗';
    }
    let cleanUrl = entry.url;
    if (cleanUrl.startsWith('//')) cleanUrl = 'https:' + cleanUrl;

    const dateStr = entry.date ? `\n📅 <i>${entry.date}</i>` : '';
    const text = `${icon} <b>${this.escapeHtml(entry.title)}</b>${dateStr}\n<a href="${cleanUrl}">${this.getUrlLabel(entry)}</a>`;
    return { text, url: cleanUrl };
  }

  getUrlLabel(entry) {
    switch (entry.type) {
      case 'video': return '▶️ Watch Video';
      case 'pdf':   return '📕 View PDF';
      default:      return '🔗 Open Link';
    }
  }

  escapeHtml(text) {
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  getTopicEmoji(topicName) {
    const emojiMap = {
      'Notices': '📢',
      'Ethics, Integrity and Aptitude': '⚖️',
      'Geography': '🌍',
      'Polity': '🏛️',
      'Economy': '💰',
      'Science and Technology': '🔬',
      'History': '📜',
      'Current Affairs': '📰',
      'Society, Social Issues, Social Justice': '👥',
      'World History': '🗺️',
      'Art & Culture': '🎨',
      'International Relations': '🌐',
      'Environment': '🌱',
      'Ancient History': '🏛️',
      'Governance': '📊',
      'Post Independence': '🇮🇳',
      'Medieval History': '⚔️',
      'Internal Security': '🛡️',
      'Disaster Management': '🚨',
      'Essay': '✍️',
      'Webinar': '🎓',
      'Starter Kit': '🎒',
      'Samvaad': '💬',
    };
    return emojiMap[topicName] || '📁';
  }

  // Send the batch calendar message with month inline keyboard to the group
  async sendCalendarMessage(monthsData, batchStartDate, batchEndDate, noticesThreadId = null) {
    const headerText = (
      `📅 <b>Batch Calendar — Content Navigator</b>\n` +
      `━━━━━━━━━━━━━━━━━━━━\n` +
      `From: <b>${batchStartDate}</b> → To: <b>${batchEndDate}</b>\n\n` +
      `Tap a month to browse content by date 👇`
    );

    const rows = monthsData.map(m => ([{
      text: `📅 ${m.label} (${m.totalItems} items)`,
      callback_data: JSON.stringify({ action: 'open_month', month: m.key })
    }]));

    const sendOpts = {
      parse_mode: 'HTML',
      reply_markup: { inline_keyboard: rows }
    };
    if (noticesThreadId) sendOpts.message_thread_id = noticesThreadId;

    try {
      const sent = await this.bot.api.sendMessage(this.groupId, headerText, sendOpts);
      console.log('Calendar message sent. Message ID:', sent.message_id);
      return sent;
    } catch (err) {
      console.error('Failed to send calendar message:', err.message);
      return null;
    }
  }

  async checkRateLimit() {
    const now = Date.now();
    if (now - this.lastResetTime > 1000) {
      this.rateLimitCount = 0;
      this.lastResetTime = now;
    }
    this.rateLimitCount++;
    if (this.rateLimitCount > 20) await this.sleep(1000);
  }

  stop() { try { this.bot.stop(); } catch (e) {} }
  sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }
}

module.exports = TopicManager;
