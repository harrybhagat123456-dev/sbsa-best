import os
import threading
import time
import requests
from flask import Flask, jsonify

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
