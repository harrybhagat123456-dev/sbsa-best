import os
import json
import threading
import time
import requests
from flask import Flask, jsonify, Response

DOWNLOAD_FOLDERS = [
    os.path.join(os.path.dirname(__file__), "downloads"),
    os.path.join(os.path.dirname(__file__), "modules", "downloads"),
]
CLEANUP_INTERVAL = 432000       # run cleanup every 5 days
FILE_MAX_AGE_SECONDS = 432000   # delete files older than 5 days

app = Flask(__name__)

PORT = int(os.environ.get("PORT", 5000))

# Support Render, Replit, and any custom public URL
RENDER_URL    = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
REPLIT_DOMAIN = os.environ.get("REPLIT_DEV_DOMAIN", "").rstrip("/")
CUSTOM_URL    = os.environ.get("ALIVE_URL", "").rstrip("/")  # set manually if needed

# Determine the best public URL to self-ping
if CUSTOM_URL:
    PUBLIC_URL = CUSTOM_URL if CUSTOM_URL.startswith("http") else f"https://{CUSTOM_URL}"
elif RENDER_URL:
    PUBLIC_URL = RENDER_URL if RENDER_URL.startswith("http") else f"https://{RENDER_URL}"
elif REPLIT_DOMAIN:
    PUBLIC_URL = f"https://{REPLIT_DOMAIN}"
else:
    PUBLIC_URL = ""


@app.route("/")
def home():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>HARRY - Alive</title>
</head>
<body style="background:#111; color:#fff; font-family:monospace; text-align:center; margin-top:80px;">
    <pre style="color:#4fc3f7; font-size:18px; display:inline-block;">
&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;&#9608;
&#9608;&#9608;&#9617;&#9604;&#9604;&#9604;&#9617;&#9608;&#9617;&#9604;&#9604;&#9600;&#9608;&#9604;&#9617;&#9604;&#9608;&#9608;&#9617;&#9600;&#9608;&#9608;&#9617;&#9604;&#9617;&#9604;&#9608;&#9608;
&#9608;&#9608;&#9604;&#9604;&#9604;&#9600;&#9600;&#9608;&#9617;&#9600;&#9600;&#9617;&#9608;&#9608;&#9617;&#9608;&#9608;&#9617;&#9608;&#9617;&#9608;&#9617;&#9608;&#9608;&#9617;&#9608;&#9608;&#9608;
&#9608;&#9608;&#9617;&#9600;&#9600;&#9600;&#9617;&#9608;&#9617;&#9608;&#9608;&#9617;&#9608;&#9600;&#9617;&#9600;&#9608;&#9608;&#9617;&#9608;&#9608;&#9604;&#9617;&#9608;&#9600;&#9617;&#9600;&#9608;&#9608;
&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;&#9600;
    </pre>
    <br>
    <b style="font-size:20px;">Powered By HARRY</b>
    <br><br>
    <span style="color:#66bb6a; font-size:16px;">&#10003; Bot is alive and running!</span>
    <br><br>
    <p style="color:#aaa; font-size:13px;">
        Add <b>/ping</b> or <b>/health</b> to your UptimeRobot monitor URL to keep this bot alive 24/7.
    </p>
    <br>
    <footer style="color:#555; font-size:12px;">
        &copy; 2025 Video Downloader. All rights reserved.
    </footer>
</body>
</html>
"""


PROGRESS_FILE = "/tmp/bot_progress.json"


@app.route("/progress_data")
def progress_data():
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {"active": False, "status": "idle", "percent": 0, "batch_name": "", "current": 0, "total": 0, "current_file": "No active download", "success": 0, "failed": 0}
    return jsonify(data)


@app.route("/progress")
def progress_page():
    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>HARRY Bot — Download Progress</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #0a0a0f; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; padding: 16px; min-height: 100vh; }
    .card { background: #12121f; border: 1px solid #1e1e3a; border-radius: 14px; padding: 22px; max-width: 760px; margin: 0 auto 16px; }
    h1 { color: #4fc3f7; font-size: 20px; margin-bottom: 4px; }
    .subtitle { color: #555; font-size: 12px; margin-bottom: 20px; }
    .status-badge { display: inline-block; padding: 4px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; margin-bottom: 16px; }
    .status-active { background: #1b5e20; color: #69f0ae; }
    .status-done   { background: #0d47a1; color: #82b1ff; }
    .status-idle   { background: #2a2a2a; color: #888; }
    .batch { font-size: 18px; font-weight: bold; color: #fff; margin-bottom: 3px; }
    .file  { font-size: 12px; color: #607d8b; margin-bottom: 16px; }
    .progress-wrap { background: #0d0d0d; border-radius: 10px; height: 20px; overflow: hidden; margin-bottom: 8px; }
    .progress-bar  { height: 100%; border-radius: 10px; background: linear-gradient(90deg, #1565c0, #42a5f5); transition: width 0.8s ease; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; min-width: 36px; }
    .progress-bar span { font-size: 11px; font-weight: bold; color: #fff; }
    .stats { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 10px; }
    .stat { background: #0d0d0d; border-radius: 8px; padding: 10px 14px; flex: 1; min-width: 80px; text-align: center; border: 1px solid #1a1a2a; }
    .stat-val { font-size: 22px; font-weight: bold; color: #4fc3f7; }
    .stat-lbl { font-size: 10px; color: #555; margin-top: 2px; text-transform: uppercase; letter-spacing: 0.5px; }
    .current-file { background: #0d0d0d; border: 1px solid #1a1a2a; border-radius: 8px; padding: 10px 14px; margin-top: 14px; font-size: 13px; color: #90caf9; font-family: monospace; word-break: break-all; }
    .current-file b { color: #546e7a; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
    .footer-row { display: flex; justify-content: space-between; align-items: center; margin-top: 12px; }
    .updated { font-size: 11px; color: #333; }

    /* ── Console ── */
    .console-card { background: #0a0c0f; border: 1px solid #1a1f2e; border-radius: 14px; padding: 0; max-width: 760px; margin: 0 auto; overflow: hidden; }
    .console-header { background: #0f1117; padding: 10px 18px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #1a1f2e; }
    .console-header span { font-size: 13px; color: #4fc3f7; font-weight: bold; font-family: monospace; }
    .console-header small { font-size: 11px; color: #333; }
    .console-dots { display: flex; gap: 6px; }
    .console-dots i { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
    #console-log { font-family: 'Courier New', monospace; font-size: 12px; padding: 12px 16px; height: 320px; overflow-y: auto; display: flex; flex-direction: column-reverse; }
    .log-line { display: flex; gap: 10px; align-items: baseline; padding: 2px 0; border-bottom: 1px solid #0f1117; }
    .log-idx  { color: #37474f; min-width: 40px; text-align: right; font-size: 11px; flex-shrink: 0; }
    .log-time { color: #37474f; min-width: 60px; font-size: 11px; flex-shrink: 0; }
    .log-ok   { color: #00e676; flex-shrink: 0; }
    .log-fail { color: #ff5252; flex-shrink: 0; }
    .log-name { color: #b0bec5; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .log-empty { color: #2a2a2a; font-size: 12px; text-align: center; padding: 40px 0; width: 100%; }
  </style>
</head>
<body>
  <!-- Stats card -->
  <div class="card">
    <h1>📥 HARRY Bot — Download Progress</h1>
    <div class="subtitle">Live console · auto-refreshes every 3 s</div>
    <div id="badge" class="status-badge status-idle">⏸ Idle</div>
    <div id="batch" class="batch">No active batch</div>
    <div id="file-name" class="file"></div>
    <div class="progress-wrap">
      <div class="progress-bar" id="bar" style="width:0%"><span id="pct">0%</span></div>
    </div>
    <div class="stats">
      <div class="stat"><div class="stat-val" id="s-cur">0</div><div class="stat-lbl">Done</div></div>
      <div class="stat"><div class="stat-val" id="s-tot">0</div><div class="stat-lbl">Total</div></div>
      <div class="stat"><div class="stat-val" id="s-ok"  style="color:#00e676">0</div><div class="stat-lbl">Success</div></div>
      <div class="stat"><div class="stat-val" id="s-fail" style="color:#ff5252">0</div><div class="stat-lbl">Failed</div></div>
    </div>
    <div class="current-file"><b>Now&nbsp;→</b>&nbsp; <span id="cur-file">—</span></div>
    <div class="footer-row">
      <div class="updated" id="upd"></div>
      <div class="updated">Auto-refresh 3 s</div>
    </div>
  </div>

  <!-- Live console -->
  <div class="console-card">
    <div class="console-header">
      <div style="display:flex;align-items:center;gap:12px;">
        <div class="console-dots">
          <i style="background:#ff5f57"></i>
          <i style="background:#febc2e"></i>
          <i style="background:#28c840"></i>
        </div>
        <span>download.log</span>
      </div>
      <small id="log-count">0 entries</small>
    </div>
    <div id="console-log">
      <div class="log-empty" id="log-empty">Waiting for downloads…</div>
    </div>
  </div>

  <script>
    let lastLogLen = 0;

    function escHtml(s) {
      return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }

    async function poll() {
      try {
        const r = await fetch('/progress_data');
        const d = await r.json();

        // ── Stats ──
        const pct = Math.min(100, d.percent || 0);
        document.getElementById('bar').style.width = pct + '%';
        document.getElementById('pct').textContent = pct.toFixed(1) + '%';
        document.getElementById('batch').textContent = d.batch_name || 'No active batch';
        document.getElementById('file-name').textContent = d.file_name || '';
        document.getElementById('s-cur').textContent  = d.current  || 0;
        document.getElementById('s-tot').textContent  = d.total    || 0;
        document.getElementById('s-ok').textContent   = d.success  || 0;
        document.getElementById('s-fail').textContent = d.failed   || 0;
        document.getElementById('cur-file').textContent = d.current_file || '—';
        document.getElementById('upd').textContent = 'Updated: ' + (d.updated_at || '—');

        const badge = document.getElementById('badge');
        if (d.active) {
          badge.className = 'status-badge status-active';
          badge.textContent = '▶ Downloading';
        } else if (d.status === 'done') {
          badge.className = 'status-badge status-done';
          badge.textContent = '✅ Complete';
        } else {
          badge.className = 'status-badge status-idle';
          badge.textContent = '⏸ Idle';
        }

        // ── Console log ──
        const log = d.log || [];
        document.getElementById('log-count').textContent = log.length + ' entries';

        if (log.length === 0) {
          document.getElementById('log-empty').style.display = 'block';
        } else {
          document.getElementById('log-empty').style.display = 'none';
        }

        if (log.length !== lastLogLen) {
          lastLogLen = log.length;
          const box = document.getElementById('console-log');
          // Render newest-first (flex-direction: column-reverse shows bottom entries first)
          const reversed = [...log].reverse();
          const html = reversed.map(e => {
            const icon  = e.ok ? '<span class="log-ok">✔</span>' : '<span class="log-fail">✘</span>';
            const name  = escHtml((e.name || '').replace(/[ \\t]*https?.*$/i, '').trim() || e.name || '\u2014');
            return '<div class="log-line">'
              + '<span class="log-idx">#' + (e.i || 0) + '</span>'
              + '<span class="log-time">' + escHtml(e.time || '') + '</span>'
              + icon
              + '<span class="log-name">' + name + '</span>'
              + '</div>';
          }).join('');
          box.innerHTML = (log.length === 0 ? '<div class="log-empty" id="log-empty">Waiting for downloads…</div>' : '') + html;
        }

      } catch(e) {}
    }

    poll();
    setInterval(poll, 3000);
  </script>
</body>
</html>"""
    return Response(html, mimetype="text/html")


@app.route("/ping")
def ping():
    return jsonify({"status": "alive", "message": "HARRY is running!"}), 200


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


def cleanup_downloads():
    """
    Deletes files older than FILE_MAX_AGE_SECONDS from all download folders.
    Runs every CLEANUP_INTERVAL seconds in the background.
    """
    while True:
        for folder in DOWNLOAD_FOLDERS:
            if not os.path.isdir(folder):
                continue
            now = time.time()
            deleted = 0
            freed = 0
            try:
                for filename in os.listdir(folder):
                    filepath = os.path.join(folder, filename)
                    if not os.path.isfile(filepath):
                        continue
                    try:
                        age = now - os.path.getmtime(filepath)
                        if age > FILE_MAX_AGE_SECONDS:
                            size = os.path.getsize(filepath)
                            os.remove(filepath)
                            deleted += 1
                            freed += size
                    except Exception as e:
                        print(f"[CLEANUP] Could not delete {filepath}: {e}")
                if deleted:
                    print(f"[CLEANUP] {folder} → deleted {deleted} file(s), freed {freed / 1024 / 1024:.2f} MB")
                else:
                    print(f"[CLEANUP] {folder} → nothing to clean")
            except Exception as e:
                print(f"[CLEANUP] Error scanning {folder}: {e}")
        time.sleep(CLEANUP_INTERVAL)


def self_ping():
    """
    Pings /ping on the public URL every 10 minutes to prevent free-tier spin-down.
    Works with Replit (REPLIT_DEV_DOMAIN), Render (RENDER_EXTERNAL_URL),
    or any custom URL set via ALIVE_URL environment variable.

    UptimeRobot should also be configured externally to ping every 5 minutes
    for best 24/7 uptime — especially important on Replit where the browser
    must be kept open otherwise.
    """
    if not PUBLIC_URL:
        print("[ALIVE] No public URL detected — self-ping disabled.")
        print("[ALIVE] To enable self-ping, set one of these env vars:")
        print("[ALIVE]   ALIVE_URL=https://your-replit-url.repl.co")
        print("[ALIVE]   REPLIT_DEV_DOMAIN=your-replit-domain (auto-set on Replit)")
        print("[ALIVE]   RENDER_EXTERNAL_URL=your-render-url (auto-set on Render)")
        print("[ALIVE] Configure UptimeRobot to ping your public URL every 5 mins.")
        return

    print(f"[ALIVE] Self-ping enabled → {PUBLIC_URL}/ping")
    print(f"[ALIVE] Also configure UptimeRobot to ping: {PUBLIC_URL}/ping")

    # Wait for server to fully start before first ping
    time.sleep(30)

    while True:
        try:
            resp = requests.get(f"{PUBLIC_URL}/ping", timeout=10)
            print(f"[ALIVE] Self-ping OK ({resp.status_code})")
        except requests.exceptions.Timeout:
            print("[ALIVE] Self-ping timed out — will retry in 10 mins.")
        except requests.exceptions.ConnectionError:
            print("[ALIVE] Self-ping connection error — will retry in 10 mins.")
        except Exception as e:
            print(f"[ALIVE] Self-ping error: {e}")

        time.sleep(600)  # ping every 10 minutes


if __name__ == "__main__":
    ping_thread = threading.Thread(target=self_ping, daemon=True, name="self-ping")
    ping_thread.start()

    cleanup_thread = threading.Thread(target=cleanup_downloads, daemon=True, name="cleanup")
    cleanup_thread.start()
    print(f"[CLEANUP] Auto-cleanup started → checks every {CLEANUP_INTERVAL // 86400} days, removes files older than {FILE_MAX_AGE_SECONDS // 86400} days")

    print(f"[ALIVE] Web server starting on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, threaded=True, use_reloader=False, debug=False)
