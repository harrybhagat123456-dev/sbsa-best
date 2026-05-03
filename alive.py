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
    body { background: #0f0f0f; color: #e0e0e0; font-family: 'Segoe UI', monospace; padding: 20px; min-height: 100vh; }
    .card { background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 14px; padding: 24px; max-width: 700px; margin: 0 auto; }
    h1 { color: #4fc3f7; font-size: 22px; margin-bottom: 6px; }
    .subtitle { color: #888; font-size: 13px; margin-bottom: 24px; }
    .status-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; margin-bottom: 18px; }
    .status-active { background: #1b5e20; color: #69f0ae; }
    .status-done   { background: #0d47a1; color: #82b1ff; }
    .status-idle   { background: #333; color: #aaa; }
    .batch { font-size: 19px; font-weight: bold; color: #fff; margin-bottom: 4px; }
    .file  { font-size: 13px; color: #b0bec5; margin-bottom: 18px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .progress-wrap { background: #111; border-radius: 10px; height: 22px; overflow: hidden; margin-bottom: 10px; }
    .progress-bar  { height: 100%; border-radius: 10px; background: linear-gradient(90deg, #1565c0, #42a5f5); transition: width 1s ease; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; }
    .progress-bar span { font-size: 12px; font-weight: bold; color: #fff; }
    .stats { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 12px; }
    .stat { background: #111; border-radius: 8px; padding: 10px 16px; flex: 1; min-width: 100px; text-align: center; }
    .stat-val { font-size: 22px; font-weight: bold; color: #4fc3f7; }
    .stat-lbl { font-size: 11px; color: #777; margin-top: 2px; }
    .current-file { background: #111; border-radius: 8px; padding: 12px; margin-top: 16px; font-size: 13px; color: #cfd8dc; word-break: break-word; }
    .current-file b { color: #90caf9; }
    .updated { font-size: 11px; color: #555; margin-top: 14px; text-align: right; }
    .refresh-note { font-size: 11px; color: #444; margin-top: 4px; text-align: right; }
  </style>
</head>
<body>
  <div class="card">
    <h1>📥 HARRY Bot — Download Progress</h1>
    <div class="subtitle">Live view · auto-refreshes every 3 seconds</div>
    <div id="badge" class="status-badge status-idle">⏸ Idle</div>
    <div id="batch"  class="batch">No active batch</div>
    <div id="file-name" class="file"></div>
    <div class="progress-wrap">
      <div class="progress-bar" id="bar" style="width:0%"><span id="pct">0%</span></div>
    </div>
    <div class="stats">
      <div class="stat"><div class="stat-val" id="s-cur">0</div><div class="stat-lbl">Done</div></div>
      <div class="stat"><div class="stat-val" id="s-tot">0</div><div class="stat-lbl">Total</div></div>
      <div class="stat"><div class="stat-val" id="s-ok" style="color:#69f0ae">0</div><div class="stat-lbl">Success</div></div>
      <div class="stat"><div class="stat-val" id="s-fail" style="color:#ef9a9a">0</div><div class="stat-lbl">Failed</div></div>
    </div>
    <div class="current-file"><b>Current:</b> <span id="cur-file">—</span></div>
    <div class="updated" id="upd"></div>
    <div class="refresh-note">Auto-refresh every 3s</div>
  </div>
  <script>
    async function poll() {
      try {
        const r = await fetch('/progress_data');
        const d = await r.json();
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
        document.getElementById('upd').textContent = 'Last updated: ' + (d.updated_at || '—');
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
