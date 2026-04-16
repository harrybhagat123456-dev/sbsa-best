import json
import os

SETTINGS_FILE = "bot_settings.json"

def load_settings():
    """Load settings from JSON file"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_setting(key, value):
    """Save a single setting to JSON file"""
    settings = load_settings()
    settings[key] = value
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

def get_setting(key, default=None):
    """Get a setting value from JSON file"""
    settings = load_settings()
    return settings.get(key, default)
