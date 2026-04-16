/* ─── Telegram Mini App — Batch Calendar ─────────────────────────────────── */

// Init Telegram Web App
const tg = window.Telegram && window.Telegram.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  // Apply theme colors as CSS variables
  const tp = tg.themeParams || {};
  const root = document.documentElement.style;
  if (tp.bg_color)           root.setProperty('--bg',           tp.bg_color);
  if (tp.text_color)         root.setProperty('--text',         tp.text_color);
  if (tp.hint_color)         root.setProperty('--hint',         tp.hint_color);
  if (tp.link_color)         root.setProperty('--link',         tp.link_color);
  if (tp.button_color)       root.setProperty('--btn',          tp.button_color);
  if (tp.button_text_color)  root.setProperty('--btn-text',     tp.button_text_color);
  if (tp.secondary_bg_color) root.setProperty('--secondary-bg', tp.secondary_bg_color);
  if (tp.secondary_bg_color) root.setProperty('--card-bg',      tp.secondary_bg_color);
}

// ── State ──────────────────────────────────────────────────────────────────
const params        = new URLSearchParams(window.location.search);
const initialMonth  = params.get('month') || null;  // e.g. "2025-03"
let   currentMonth  = null;

// ── DOM refs ───────────────────────────────────────────────────────────────
const $loading      = document.getElementById('loading');
const $error        = document.getElementById('error-screen');
const $errorMsg     = document.getElementById('error-msg');
const $overview     = document.getElementById('overview-view');
const $monthView    = document.getElementById('month-view');
const $dateView     = document.getElementById('date-view');
const $overviewRange= document.getElementById('overview-range');
const $monthTitle   = document.getElementById('month-title');
const $dateTitle    = document.getElementById('date-title');
const $monthGrid    = document.getElementById('month-grid');
const $dateGrid     = document.getElementById('date-grid');
const $contentList  = document.getElementById('content-list');

// ── Helpers ────────────────────────────────────────────────────────────────
function showOnly(el) {
  [$loading, $error, $overview, $monthView, $dateView].forEach(e => {
    if (e) e.style.display = 'none';
  });
  if (el) el.style.display = '';
}

function showError(msg) {
  $errorMsg.textContent = msg;
  showOnly($error);
}

async function apiFetch(qs) {
  const base = window.location.origin;
  const url  = `${base}/api/calendar${qs}`;
  const res  = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

function typeIcon(type) {
  return type === 'video' ? '🎬' : type === 'pdf' ? '📄' : '🔗';
}

function formatDateLabel(isoDate) {
  const d = new Date(isoDate + 'T00:00:00');
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
}

// ── Back buttons ───────────────────────────────────────────────────────────
document.getElementById('back-to-overview').addEventListener('click', () => {
  if (initialMonth) {
    // We arrived here from a direct month link, go back via Telegram back button behaviour
    if (tg && tg.close) tg.close();
  } else {
    showOnly($overview);
  }
});

document.getElementById('back-to-month').addEventListener('click', () => {
  showOnly($monthView);
  if (tg && tg.BackButton) {
    tg.BackButton.hide();
  }
});

// ── Views ──────────────────────────────────────────────────────────────────

// Overview — all months
async function loadOverview() {
  showOnly($loading);
  try {
    const data = await apiFetch('');
    const { batchInfo, months } = data;

    if (batchInfo && batchInfo.startDate && batchInfo.endDate) {
      $overviewRange.textContent = `${batchInfo.startDate}  →  ${batchInfo.endDate}`;
    }

    $monthGrid.innerHTML = '';
    if (!months || !months.length) {
      $monthGrid.innerHTML = '<p class="empty">No dated content found.</p>';
    } else {
      months.forEach(m => {
        const card = document.createElement('div');
        card.className = 'card month-card';
        card.innerHTML = `
          <div class="card-left">
            <div class="card-title">📅 ${m.label}</div>
            <div class="card-sub">${m.totalItems} item${m.totalItems !== 1 ? 's' : ''} across ${(m.dates || []).length} dates</div>
          </div>
          <span class="card-badge">${m.totalItems}</span>
          <span class="card-arrow">›</span>`;
        card.addEventListener('click', () => loadMonth(m.key, m.label));
        $monthGrid.appendChild(card);
      });
    }

    showOnly($overview);
  } catch (err) {
    showError(`Could not load calendar data.\n${err.message}`);
  }
}

// Month — list of dates
async function loadMonth(monthKey, monthLabel) {
  showOnly($loading);
  currentMonth = monthKey;
  try {
    const data = await apiFetch(`?month=${monthKey}`);
    $monthTitle.textContent = data.label || monthLabel || monthKey;

    $dateGrid.innerHTML = '';
    if (!data.dates || !data.dates.length) {
      $dateGrid.innerHTML = '<p class="empty">No dates found for this month.</p>';
    } else {
      data.dates.forEach(d => {
        const label = formatDateLabel(d.date);
        const card  = document.createElement('div');
        card.className = 'card date-card';
        card.innerHTML = `
          <div class="card-left">
            <div class="card-title">${label}</div>
            <div class="card-sub">${d.total} item${d.total !== 1 ? 's' : ''}</div>
          </div>
          <span class="card-badge">${d.total}</span>
          <span class="card-arrow">›</span>`;
        card.addEventListener('click', () => loadDate(d.date));
        $dateGrid.appendChild(card);
      });
    }

    showOnly($monthView);
    if (tg && tg.BackButton) tg.BackButton.show();
  } catch (err) {
    showError(`Could not load month data.\n${err.message}`);
  }
}

// Date — content items
async function loadDate(isoDate) {
  showOnly($loading);
  try {
    const month = currentMonth || isoDate.substring(0, 7);
    const data  = await apiFetch(`?month=${month}&date=${isoDate}`);
    $dateTitle.textContent = `${formatDateLabel(isoDate)} — ${data.totalItems} items`;

    $contentList.innerHTML = '';
    if (!data.topics || !data.topics.length) {
      $contentList.innerHTML = '<p class="empty">No content found for this date.</p>';
    } else {
      data.topics.forEach(topicObj => {
        const section = document.createElement('div');
        section.className = 'topic-section';

        const label = document.createElement('div');
        label.className = 'topic-label';
        label.textContent = topicObj.topic;
        section.appendChild(label);

        topicObj.items.forEach(item => {
          const card = document.createElement('div');
          card.className = 'content-card';
          card.innerHTML = `
            <div class="content-icon">${typeIcon(item.type)}</div>
            <div class="content-body">
              <div class="content-title">${item.title}</div>
              ${item.date ? `<div class="content-date">📅 ${item.date}</div>` : ''}
              <div class="content-open">Open in Group →</div>
            </div>`;

          card.addEventListener('click', () => {
            if (item.deepLink) {
              if (tg && tg.openTelegramLink) {
                tg.openTelegramLink(item.deepLink);
              } else {
                window.open(item.deepLink, '_blank');
              }
            }
          });

          section.appendChild(card);
        });

        $contentList.appendChild(section);
      });
    }

    showOnly($dateView);
  } catch (err) {
    showError(`Could not load date data.\n${err.message}`);
  }
}

// ── Entry point ────────────────────────────────────────────────────────────
(async () => {
  if (initialMonth) {
    // Opened directly with a month param (from inline keyboard button)
    await loadMonth(initialMonth, null);
  } else {
    // No month param — show full overview
    await loadOverview();
  }
})();
