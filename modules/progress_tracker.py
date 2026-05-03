"""
Progress Tracker
================
Writes download progress to /tmp/bot_progress.json so the alive.py
web server (a separate process) can serve it at /progress.
"""

import json
import time
import os

PROGRESS_FILE = "/tmp/bot_progress.json"


def _write(data: dict):
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def start_batch(batch_name: str, file_name: str, total: int, channel_id: str, start_index: int = 0):
    _write({
        "active":      True,
        "batch_name":  batch_name,
        "file_name":   file_name,
        "current":     start_index,
        "total":       total,
        "percent":     round(start_index / total * 100, 1) if total else 0,
        "current_file": "",
        "channel":     str(channel_id),
        "success":     0,
        "failed":      0,
        "status":      "starting",
        "started_at":  time.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at":  time.strftime("%Y-%m-%d %H:%M:%S"),
    })


def update(current: int, total: int, current_file: str, success: int, failed: int, status: str = "downloading"):
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}

    data.update({
        "active":       True,
        "current":      current,
        "total":        total,
        "percent":      round(current / total * 100, 1) if total else 0,
        "current_file": current_file[:80],
        "success":      success,
        "failed":       failed,
        "status":       status,
        "updated_at":   time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    _write(data)


def finish(success: int, failed: int, batch_name: str = ""):
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}

    data.update({
        "active":       False,
        "success":      success,
        "failed":       failed,
        "percent":      100,
        "status":       "done",
        "current_file": "✅ Batch complete",
        "batch_name":   batch_name or data.get("batch_name", ""),
        "updated_at":   time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    _write(data)


def get_public_url() -> str:
    """Return the public URL of this deployment."""
    for var in ("RENDER_EXTERNAL_URL", "REPLIT_DEV_DOMAIN", "ALIVE_URL"):
        val = os.environ.get(var, "").rstrip("/")
        if val:
            return val if val.startswith("http") else f"https://{val}"
    return ""
