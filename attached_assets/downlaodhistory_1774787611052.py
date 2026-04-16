""
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
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# History database file path
HISTORY_DIR = "history_data"
HISTORY_DB_FILE = os.path.join(HISTORY_DIR, "download_history.json")
FILE_HASHES_DIR = os.path.join(HISTORY_DIR, "file_hashes")

# Ensure directories exist
os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(FILE_HASHES_DIR, exist_ok=True)


class DownloadHistory:
    """
    Manages download history for text files.
    Tracks progress and allows resuming downloads.
    """
    
    def __init__(self):
        self.history: Dict[str, Dict[str, Any]] = {}
        self._load_history()
    
    def _load_history(self) -> None:
        """Load history from JSON file."""
        try:
            if os.path.exists(HISTORY_DB_FILE):
                with open(HISTORY_DB_FILE, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
                print(f"[History] Loaded {len(self.history)} history entries")
            else:
                self.history = {}
                print("[History] No existing history found, starting fresh")
        except Exception as e:
            print(f"[History] Error loading history: {e}")
            self.history = {}
    
    def _save_history(self) -> None:
        """Save history to JSON file."""
        try:
            with open(HISTORY_DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[History] Error saving history: {e}")
    
    @staticmethod
    def generate_file_hash(file_path: str) -> str:
        """
        Generate a unique hash for a file based on its content.
        Uses MD5 for fast hashing of text files.
        
        Args:
            file_path: Path to the file
            
        Returns:
            MD5 hash string of the file content
        """
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                # Read in chunks for large files
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"[History] Error generating hash: {e}")
            return ""
    
    @staticmethod
    def generate_content_hash(content: str) -> str:
        """
        Generate a unique hash from text content.
        
        Args:
            content: Text content to hash
            
        Returns:
            MD5 hash string of the content
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get_or_create_entry(self, file_hash: str, file_name: str, 
                            total_links: int, user_id: int,
                            links: List[str]) -> Dict[str, Any]:
        """
        Get existing history entry or create a new one.
        
        Args:
            file_hash: Unique hash of the file
            file_name: Original file name
            total_links: Total number of links in the file
            user_id: Telegram user ID
            links: List of all links in the file
            
        Returns:
            History entry dictionary
        """
        if file_hash in self.history:
            entry = self.history[file_hash]
            print(f"[History] Found existing entry for {file_name}")
            return entry
        
        # Create new entry
        entry = {
            "file_hash": file_hash,
            "file_name": file_name,
            "user_id": user_id,
            "total_links": total_links,
            "completed_links": [],
            "failed_links": [],
            "skipped_links": [],
            "current_index": 0,
            "status": "pending",  # pending, in_progress, completed, paused
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "links": links[:],  # Store copy of links
            "metadata": {
                "download_type": "unknown",
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
        """
        Update download progress for a file.
        
        Args:
            file_hash: File hash
            index: Current link index being processed
            status: Status of the link (completed, failed, skipped)
            url: The URL that was processed
        """
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
        """Mark a file download as completed."""
        if file_hash in self.history:
            self.history[file_hash]["status"] = "completed"
            self.history[file_hash]["updated_at"] = datetime.now().isoformat()
            self._save_history()
            print(f"[History] Marked {self.history[file_hash]['file_name']} as completed")
    
    def mark_paused(self, file_hash: str) -> None:
        """Mark a file download as paused."""
        if file_hash in self.history:
            self.history[file_hash]["status"] = "paused"
            self.history[file_hash]["updated_at"] = datetime.now().isoformat()
            self._save_history()
    
    def get_resume_index(self, file_hash: str) -> int:
        """
        Get the index from which to resume downloading.
        
        Args:
            file_hash: File hash
            
        Returns:
            Index to resume from (0 if new file)
        """
        if file_hash not in self.history:
            return 0
        
        entry = self.history[file_hash]
        
        # If completed, start from beginning (re-download)
        if entry["status"] == "completed":
            return 0
        
        # Resume from last successful index + 1
        last_success = entry["metadata"].get("last_successful_index", -1)
        return last_success + 1
    
    def get_progress_summary(self, file_hash: str) -> Dict[str, Any]:
        """
        Get a summary of download progress.
        
        Args:
            file_hash: File hash
            
        Returns:
            Dictionary with progress summary
        """
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
        """
        Get all history entries for a specific user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            List of history entries
        """
        user_entries = []
        for file_hash, entry in self.history.items():
            if entry.get("user_id") == user_id:
                user_entries.append(self.get_progress_summary(file_hash))
        return user_entries
    
    def clear_history(self, file_hash: str = None, user_id: int = None) -> int:
        """
        Clear history entries.
        
        Args:
            file_hash: Specific file hash to clear (optional)
            user_id: Clear all entries for this user (optional)
            
        Returns:
            Number of entries cleared
        """
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
        
        # Clear all
        count = len(self.history)
        self.history = {}
        self._save_history()
        return count
    
    def delete_entry(self, file_hash: str) -> bool:
        """
        Delete a specific history entry.
        
        Args:
            file_hash: File hash to delete
            
        Returns:
            True if deleted, False if not found
        """
        if file_hash in self.history:
            del self.history[file_hash]
            self._save_history()
            return True
        return False
    
    def set_metadata(self, file_hash: str, key: str, value: Any) -> None:
        """Set metadata for a history entry."""
        if file_hash in self.history:
            self.history[file_hash]["metadata"][key] = value
            self._save_history()
    
    def get_entry(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Get a history entry by hash."""
        return self.history.get(file_hash)


# Global history instance
_history_instance = None

def get_history() -> DownloadHistory:
    """Get or create the global history instance."""
    global _history_instance
    if _history_instance is None:
        _history_instance = DownloadHistory()
    return _history_instance


def format_progress_message(summary: Dict[str, Any]) -> str:
    """
    Format a progress summary into a readable message.
    
    Args:
        summary: Progress summary dictionary
        
    Returns:
        Formatted message string
    """
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


# History management functions for bot integration
async def check_and_get_resume_info(file_path: str, file_name: str, 
                                    user_id: int, links: List[str]) -> Tuple[str, int, Dict]:
    """
    Check if a file has been processed before and get resume information.
    
    Args:
        file_path: Path to the uploaded file
        file_name: Original file name
        user_id: Telegram user ID
        links: List of all links in the file
        
    Returns:
        Tuple of (file_hash, resume_index, history_entry)
    """
    history = get_history()
    
    # Generate file hash
    file_hash = DownloadHistory.generate_file_hash(file_path)
    
    if not file_hash:
        # Fallback to content hash if file access fails
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        file_hash = DownloadHistory.generate_content_hash(content)
    
    # Get or create entry
    entry = history.get_or_create_entry(
        file_hash=file_hash,
        file_name=file_name,
        total_links=len(links),
        user_id=user_id,
        links=links
    )
    
    # Get resume index
    resume_index = history.get_resume_index(file_hash)
    
    return file_hash, resume_index, entry


async def update_download_progress(file_hash: str, index: int, 
                                   status: str, url: str) -> None:
    """Update download progress in history."""
    history = get_history()
    history.update_progress(file_hash, index, status, url)


async def mark_download_completed(file_hash: str) -> None:
    """Mark a download as completed."""
    history = get_history()
    history.mark_completed(file_hash)


async def mark_download_paused(file_hash: str) -> None:
    """Mark a download as paused."""
    history = get_history()
    history.mark_paused(file_hash)


def get_user_history_list(user_id: int) -> List[Dict]:
    """Get history list for a user."""
    history = get_history()
    return history.get_user_history(user_id)


def clear_user_history(user_id: int = None, file_hash: str = None) -> int:
    """Clear history for a user or specific file."""
    history = get_history()
    return history.clear_history(file_hash=file_hash, user_id=user_id)


# Export for use in other modules
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