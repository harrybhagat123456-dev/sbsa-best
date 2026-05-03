import os
import json
import random
import threading
import time
import requests
from flask import Flask, jsonify, Response

DOWNLOAD_FOLDERS = [
    os.path.join(os.path.dirname(__file__), "downloads"),
    os.path.join(os.path.dirname(__file__), "modules", "downloads"),
]
CLEANUP_INTERVAL     = 432000   # run cleanup every 5 days
FILE_MAX_AGE_SECONDS = 432000   # delete files older than 5 days

app = Flask(__name__)

PORT = int(os.environ.get("PORT", 5000))

# Support Render, Replit, and any custom public URL
RENDER_URL    = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
REPLIT_DOMAIN = os.environ.get("REPLIT_DEV_DOMAIN", "").rstrip("/")
CUSTOM_URL    = os.environ.get("ALIVE_URL", "").rstrip("/")

if CUSTOM_URL:
    PUBLIC_URL = CUSTOM_URL if CUSTOM_URL.startswith("http") else f"https://{CUSTOM_URL}"
elif RENDER_URL:
    PUBLIC_URL = RENDER_URL if RENDER_URL.startswith("http") else f"https://{RENDER_URL}"
elif REPLIT_DOMAIN:
    PUBLIC_URL = f"https://{REPLIT_DOMAIN}"
else:
    PUBLIC_URL = ""

# ── Sandbox keep-alive state ─────────────────────────────────────────────────
_sandbox = {
    "total_pings": 0,
    "last_ping_time": "—",
    "last_ping_endpoint": "—",
    "last_ping_status": "—",
    "errors": 0,
    "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
}

# Endpoints to rotate through — mimics real browsing activity
_PING_ENDPOINTS = ["/ping", "/health", "/", "/progress_data", "/heartbeat"]
_PING_INTERVAL  = 240   # 4 minutes — safely under Replit's ~5-min sleep timer
_PING_JITTER    = 30    # ±30 s random jitter so it doesn't look like a cron job


@app.route("/")
def home():
    return """<!DOCTYPE html>
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
        Sandbox keep-alive active — pinging every 4 minutes.
    </p>
    <br>
    <footer style="color:#555; font-size:12px;">
        &copy; 2025 Video Downloader. All rights reserved.
    </footer>
    <script>
        // Browser-side heartbeat: keeps the server awake whenever this tab is open
        function bping() {
            fetch('/heartbeat').catch(function(){});
        }
        bping();
        setInterval(bping, 180000); // every 3 minutes from the browser tab
    </script>
</body>
</html>"""


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
          const reversed = [...log].reverse();
          const html = reversed.map(e => {
            const icon  = e.ok ? '<span class="log-ok">✔</span>' : '<span class="log-fail">✘</span>';
            const name  = escHtml((e.name || '').replace(/[ \t]*https?.*$/i, '').trim() || e.name || '\u2014');
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
    // browser-side heartbeat — keeps server alive while this tab is open
    setInterval(function(){ fetch('/heartbeat').catch(function(){}); }, 180000);
  </script>
</body>
</html>"""
    return Response(html, mimetype="text/html")


@app.route("/ping")
def ping():
    return jsonify({"status": "alive", "message": "HARRY is running!", "ts": int(time.time())}), 200


@app.route("/health")
def health():
    return jsonify({"status": "ok", "ts": int(time.time())}), 200


@app.route("/heartbeat")
def heartbeat():
    """Lightweight endpoint hit by browser-side JS and the sandbox loop."""
    return jsonify({"beat": True, "ts": int(time.time())}), 200


@app.route("/sandbox")
def sandbox_status():
    """Shows live keep-alive stats — useful to confirm the sandbox is working."""
    s = _sandbox
    uptime_sec = int(time.time() - time.mktime(time.strptime(s["started_at"], "%Y-%m-%d %H:%M:%S")))
    h, rem = divmod(uptime_sec, 3600)
    m, sec = divmod(rem, 60)
    uptime_str = f"{h}h {m}m {sec}s"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Sandbox Status</title>
  <style>
    body {{ background:#0a0a0f; color:#e0e0e0; font-family:'Segoe UI',sans-serif; padding:32px; }}
    h1   {{ color:#4fc3f7; margin-bottom:4px; }}
    .sub {{ color:#555; font-size:12px; margin-bottom:28px; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:14px; max-width:700px; }}
    .box  {{ background:#12121f; border:1px solid #1e1e3a; border-radius:12px; padding:18px; text-align:center; }}
    .val  {{ font-size:28px; font-weight:bold; color:#4fc3f7; }}
    .lbl  {{ font-size:11px; color:#555; margin-top:4px; text-transform:uppercase; letter-spacing:.5px; }}
    .ok   {{ color:#00e676; }} .err {{ color:#ff5252; }}
    .info {{ max-width:700px; margin-top:20px; background:#12121f; border:1px solid #1e1e3a; border-radius:12px; padding:18px; font-size:13px; }}
    .info b {{ color:#4fc3f7; }}
  </style>
  <script>setTimeout(function(){{location.reload()}},10000);</script>
</head>
<body>
  <h1>🛡️ Sandbox Keep-Alive</h1>
  <div class="sub">Auto-refreshes every 10 s</div>
  <div class="grid">
    <div class="box"><div class="val">{s['total_pings']}</div><div class="lbl">Total Pings</div></div>
    <div class="box"><div class="val ok">{s['total_pings'] - s['errors']}</div><div class="lbl">Successful</div></div>
    <div class="box"><div class="val {'err' if s['errors'] else 'ok'}">{s['errors']}</div><div class="lbl">Errors</div></div>
    <div class="box"><div class="val">{uptime_str}</div><div class="lbl">Uptime</div></div>
  </div>
  <div class="info">
    <b>Last ping:</b> {s['last_ping_time']}<br>
    <b>Endpoint:</b>  <code>{s['last_ping_endpoint']}</code><br>
    <b>Status:</b>    {s['last_ping_status']}<br>
    <b>Interval:</b>  every ~{_PING_INTERVAL//60} min ± {_PING_JITTER}s jitter<br>
    <b>Started:</b>   {s['started_at']}
  </div>
</body>
</html>"""
    return Response(html, mimetype="text/html")


def cleanup_downloads():
    while True:
        for folder in DOWNLOAD_FOLDERS:
            if not os.path.isdir(folder):
                continue
            now = time.time()
            deleted = freed = 0
            try:
                for filename in os.listdir(folder):
                    filepath = os.path.join(folder, filename)
                    if not os.path.isfile(filepath):
                        continue
                    try:
                        if now - os.path.getmtime(filepath) > FILE_MAX_AGE_SECONDS:
                            size = os.path.getsize(filepath)
                            os.remove(filepath)
                            deleted += 1
                            freed += size
                    except Exception as e:
                        print(f"[CLEANUP] Could not delete {filepath}: {e}")
                if deleted:
                    print(f"[CLEANUP] {folder} → deleted {deleted} file(s), freed {freed/1024/1024:.2f} MB")
            except Exception as e:
                print(f"[CLEANUP] Error scanning {folder}: {e}")
        time.sleep(CLEANUP_INTERVAL)


def sandbox_keep_alive():
    """
    Sandbox keep-alive loop.

    Pings localhost:{PORT} every ~4 minutes (rotating endpoints, random jitter)
    so the Flask server always stays warm inside the container.

    For Replit free-tier to never sleep you ALSO need an external pinger
    (UptimeRobot, cron-job.org, etc.) hitting your public URL every 5 minutes.
    The public URL is printed at startup for easy copy-paste.
    """
    LOCAL_BASE = f"http://127.0.0.1:{PORT}"

    if PUBLIC_URL:
        print(f"[SANDBOX] Public URL  → {PUBLIC_URL}")
        print(f"[SANDBOX] ⚠ Point UptimeRobot at: {PUBLIC_URL}/ping  (every 5 min)")
        print(f"[SANDBOX] Status page → {PUBLIC_URL}/sandbox")
    else:
        print("[SANDBOX] No public URL detected — external pinger cannot be configured.")
        print("[SANDBOX] Set REPLIT_DEV_DOMAIN, RENDER_EXTERNAL_URL, or ALIVE_URL.")

    print(f"[SANDBOX] Internal keep-alive → {LOCAL_BASE}")
    print(f"[SANDBOX] Interval: every ~{_PING_INTERVAL//60} min ± {_PING_JITTER}s")

    # Wait for Flask to fully bind before first ping
    time.sleep(5)

    ep_cycle = 0
    while True:
        endpoint = _PING_ENDPOINTS[ep_cycle % len(_PING_ENDPOINTS)]
        ep_cycle += 1
        url = LOCAL_BASE + endpoint
        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "HARRY-Sandbox/1.0"})
            _sandbox["total_pings"]       += 1
            _sandbox["last_ping_time"]     = time.strftime("%Y-%m-%d %H:%M:%S")
            _sandbox["last_ping_endpoint"] = endpoint
            _sandbox["last_ping_status"]   = f"HTTP {resp.status_code}"
            print(f"[SANDBOX] ✓ {endpoint} → {resp.status_code}  (ping #{_sandbox['total_pings']})")
        except requests.exceptions.Timeout:
            _sandbox["errors"] += 1
            _sandbox["last_ping_status"] = "timeout"
            print(f"[SANDBOX] ✗ {endpoint} → timeout")
        except requests.exceptions.ConnectionError as _ce:
            _sandbox["errors"] += 1
            _sandbox["last_ping_status"] = "connection error"
            print(f"[SANDBOX] ✗ {endpoint} → connection error ({_ce})")
        except Exception as e:
            _sandbox["errors"] += 1
            _sandbox["last_ping_status"] = str(e)[:60]
            print(f"[SANDBOX] ✗ {endpoint} → {e}")

        # Random jitter makes traffic look natural
        sleep_time = _PING_INTERVAL + random.randint(-_PING_JITTER, _PING_JITTER)
        time.sleep(max(60, sleep_time))


if __name__ == "__main__":
    sandbox_thread = threading.Thread(target=sandbox_keep_alive, daemon=True, name="sandbox")
    sandbox_thread.start()

    cleanup_thread = threading.Thread(target=cleanup_downloads, daemon=True, name="cleanup")
    cleanup_thread.start()
    print(f"[CLEANUP] Auto-cleanup started → checks every {CLEANUP_INTERVAL//86400} days, removes files older than {FILE_MAX_AGE_SECONDS//86400} days")

    print(f"[ALIVE] Web server starting on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, threaded=True, use_reloader=False, debug=False)
