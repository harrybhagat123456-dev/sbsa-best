"""
Download History Module
=======================
This module provides functionality to track download progress for text files,
allowing users to resume downloads from where they left off.

Features:
- Unique file identification using hash
- Progress tracking (completed/failed URLs)
- Resume capability
- History management
"""

import os
import json
import hashlib
import asyncio
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

HISTORY_DIR = os.path.join(os.path.dirname(__file__), "history_data")
HISTORY_DB_FILE = os.path.join(HISTORY_DIR, "download_history.json")

os.makedirs(HISTORY_DIR, exist_ok=True)


class DownloadHistory:
    """
    Manages download history for text files.
    Tracks progress and allows resuming downloads.
    """

    def __init__(self):
        self.history: Dict[str, Dict[str, Any]] = {}
        self._load_history()

    HISTORY_MAX_AGE_DAYS = 7

    def _load_history(self) -> None:
        backup_file = HISTORY_DB_FILE + ".bak"
        loaded = False
        for path in (HISTORY_DB_FILE, backup_file):
            if not os.path.exists(path):
                continue
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.history = data
                print(f"[History] Loaded {len(self.history)} entries from {os.path.basename(path)}")
                loaded = True
                break
            except Exception as e:
                print(f"[History] Could not read {os.path.basename(path)}: {e} — trying backup")
        if not loaded:
            self.history = {}
            print("[History] No valid history found, starting fresh")
        self._cleanup_old_entries()

    def _cleanup_old_entries(self) -> None:
        cutoff = datetime.now() - timedelta(days=self.HISTORY_MAX_AGE_DAYS)
        to_delete = []
        for file_hash, entry in self.history.items():
            try:
                updated = datetime.fromisoformat(entry.get("updated_at", ""))
                if updated < cutoff:
                    to_delete.append(file_hash)
            except Exception:
                pass
        if to_delete:
            for h in to_delete:
                del self.history[h]
            print(f"[History] Pruned {len(to_delete)} entries older than {self.HISTORY_MAX_AGE_DAYS} days")
            self._save_history()

    def _save_history(self) -> None:
        backup_file = HISTORY_DB_FILE + ".bak"
        tmp_file = HISTORY_DB_FILE + ".tmp"
        try:
            with open(tmp_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
            if os.path.exists(HISTORY_DB_FILE):
                shutil.copy2(HISTORY_DB_FILE, backup_file)
            shutil.move(tmp_file, HISTORY_DB_FILE)
        except Exception as e:
            print(f"[History] Error saving history: {e}")
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except Exception:
                    pass

    @staticmethod
    def generate_file_hash(file_path: str) -> str:
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"[History] Error generating hash: {e}")
            return ""

    @staticmethod
    def generate_content_hash(content: str) -> str:
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def get_or_create_entry(self, file_hash: str, file_name: str,
                            total_links: int, user_id: int,
                            links: List[str]) -> Dict[str, Any]:
        if file_hash in self.history:
            entry = self.history[file_hash]
            print(f"[History] Found existing entry for {file_name}")
            return entry

        entry = {
            "file_hash": file_hash,
            "file_name": file_name,
            "user_id": user_id,
            "total_links": total_links,
            "completed_links": [],
            "failed_links": [],
            "skipped_links": [],
            "current_index": 0,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "links": links[:],
            "metadata": {
                "download_type": "youtube",
                "channel_id": None,
                "last_successful_index": -1
            }
        }

        self.history[file_hash] = entry
        self._save_history()
        print(f"[History] Created new entry for {file_name}")
        return entry

    def update_progress(self, file_hash: str, index: int,
                        status: str = "completed", url: str = "") -> None:
        if file_hash not in self.history:
            print(f"[History] Warning: No entry found for hash {file_hash}")
            return

        entry = self.history[file_hash]
        entry["current_index"] = index
        entry["updated_at"] = datetime.now().isoformat()
        entry["status"] = "in_progress"

        if status == "completed" and url not in entry["completed_links"]:
            entry["completed_links"].append(url)
            entry["metadata"]["last_successful_index"] = index
        elif status == "failed" and url not in entry["failed_links"]:
            entry["failed_links"].append(url)
        elif status == "skipped" and url not in entry["skipped_links"]:
            entry["skipped_links"].append(url)

        self._save_history()

    def mark_completed(self, file_hash: str) -> None:
        if file_hash in self.history:
            self.history[file_hash]["status"] = "completed"
            self.history[file_hash]["updated_at"] = datetime.now().isoformat()
            self._save_history()
            print(f"[History] Marked {self.history[file_hash]['file_name']} as completed")

    def mark_paused(self, file_hash: str) -> None:
        if file_hash in self.history:
            self.history[file_hash]["status"] = "paused"
            self.history[file_hash]["updated_at"] = datetime.now().isoformat()
            self._save_history()

    def get_resume_index(self, file_hash: str) -> int:
        if file_hash not in self.history:
            return 0

        entry = self.history[file_hash]

        if entry["status"] == "completed":
            return 0

        last_success = entry["metadata"].get("last_successful_index", -1)
        return last_success + 1

    def get_progress_summary(self, file_hash: str) -> Dict[str, Any]:
        if file_hash not in self.history:
            return {"exists": False}

        entry = self.history[file_hash]
        completed = len(entry["completed_links"])
        failed = len(entry["failed_links"])
        total = entry["total_links"]

        return {
            "exists": True,
            "file_name": entry["file_name"],
            "total_links": total,
            "completed": completed,
            "failed": failed,
            "remaining": total - completed - failed,
            "progress_percent": round((completed / total) * 100, 1) if total > 0 else 0,
            "status": entry["status"],
            "created_at": entry["created_at"],
            "updated_at": entry["updated_at"],
            "can_resume": entry["status"] != "completed"
        }

    def get_user_history(self, user_id: int) -> List[Dict[str, Any]]:
        user_entries = []
        for file_hash, entry in self.history.items():
            if entry.get("user_id") == user_id:
                user_entries.append(self.get_progress_summary(file_hash))
        return user_entries

    def get_all_history(self) -> List[Dict[str, Any]]:
        return [self.get_progress_summary(fh) for fh in self.history]

    def clear_history(self, file_hash: str = None, user_id: int = None) -> int:
        if file_hash:
            if file_hash in self.history:
                del self.history[file_hash]
                self._save_history()
                return 1
            return 0

        if user_id:
            to_delete = [h for h, e in self.history.items() if e.get("user_id") == user_id]
            for h in to_delete:
                del self.history[h]
            self._save_history()
            return len(to_delete)

        count = len(self.history)
        self.history = {}
        self._save_history()
        return count

    def delete_entry(self, file_hash: str) -> bool:
        if file_hash in self.history:
            del self.history[file_hash]
            self._save_history()
            return True
        return False

    def get_entry(self, file_hash: str) -> Optional[Dict[str, Any]]:
        return self.history.get(file_hash)


_history_instance = None


def get_history() -> DownloadHistory:
    global _history_instance
    if _history_instance is None:
        _history_instance = DownloadHistory()
    return _history_instance


def format_progress_message(summary: Dict[str, Any]) -> str:
    if not summary.get("exists"):
        return "**No previous history found for this file.**"

    status_emoji = {
        "pending": "⏳",
        "in_progress": "🔄",
        "completed": "✅",
        "paused": "⏸️"
    }

    emoji = status_emoji.get(summary["status"], "❓")

    msg = (
        f"📂 **File:** `{summary['file_name']}`\n"
        f"{emoji} **Status:** {summary['status'].upper()}\n"
        f"📊 **Progress:** {summary['progress_percent']}%\n"
        f"✅ **Completed:** {summary['completed']}/{summary['total_links']}\n"
    )

    if summary['failed'] > 0:
        msg += f"❌ **Failed:** {summary['failed']}\n"

    if summary['remaining'] > 0:
        msg += f"⏳ **Remaining:** {summary['remaining']}\n"

    if summary['can_resume']:
        msg += f"\n**💾 Resume available from link #{summary['completed'] + 1}**"
    else:
        msg += f"\n**✨ All downloads completed!**"

    return msg


async def check_and_get_resume_info(file_path: str, file_name: str,
                                    user_id: int, links: List[str]) -> Tuple[str, int, Dict]:
    history = get_history()

    file_hash = DownloadHistory.generate_file_hash(file_path)

    if not file_hash:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        file_hash = DownloadHistory.generate_content_hash(content)

    entry = history.get_or_create_entry(
        file_hash=file_hash,
        file_name=file_name,
        total_links=len(links),
        user_id=user_id,
        links=links
    )

    resume_index = history.get_resume_index(file_hash)

    return file_hash, resume_index, entry


async def update_download_progress(file_hash: str, index: int,
                                   status: str, url: str) -> None:
    history = get_history()
    history.update_progress(file_hash, index, status, url)


async def mark_download_completed(file_hash: str) -> None:
    history = get_history()
    history.mark_completed(file_hash)


async def mark_download_paused(file_hash: str) -> None:
    history = get_history()
    history.mark_paused(file_hash)


def get_user_history_list(user_id: int) -> List[Dict]:
    history = get_history()
    return history.get_user_history(user_id)


def clear_user_history(user_id: int = None, file_hash: str = None) -> int:
    history = get_history()
    return history.clear_history(file_hash=file_hash, user_id=user_id)


__all__ = [
    'DownloadHistory',
    'get_history',
    'check_and_get_resume_info',
    'update_download_progress',
    'mark_download_completed',
    'mark_download_paused',
    'get_user_history_list',
    'clear_user_history',
    'format_progress_message'
]
