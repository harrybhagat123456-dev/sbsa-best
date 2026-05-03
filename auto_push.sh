#!/usr/bin/env python3
# Auto-push changed files from latest commit to GitHub
# Skips: modules/vars.py (contains credentials)

import os
import sys
import json
import base64
import subprocess
import urllib.request
import urllib.error

REPO  = "harrybhagat123456-dev/sbsa-best"
BASE  = f"https://api.github.com/repos/{REPO}/contents"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
SKIP  = {
    "modules/vars.py",       # credentials
    "modules/bot.session",   # Telegram session (sensitive)
    "modules/logs.txt",      # runtime logs
}

if not TOKEN:
    print("[AUTOPUSH] GITHUB_TOKEN not set — skipping.")
    sys.exit(0)

# Get files changed in latest commit
try:
    result = subprocess.run(
        ["git", "--no-optional-locks", "diff-tree", "--no-commit-id", "-r", "--name-only", "HEAD"],
        capture_output=True, text=True
    )
    changed = [f.strip() for f in result.stdout.splitlines() if f.strip() and f.strip() not in SKIP]
except Exception as e:
    print(f"[AUTOPUSH] Could not get changed files: {e}")
    sys.exit(1)

if not changed:
    print("[AUTOPUSH] No changed files to push.")
    sys.exit(0)

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "Content-Type": "application/json",
}

success = 0
failed  = 0

for filepath in changed:
    if not os.path.isfile(filepath):
        print(f"[AUTOPUSH] SKIP (deleted/missing): {filepath}")
        continue

    try:
        with open(filepath, "rb") as f:
            content = base64.b64encode(f.read()).decode()
    except Exception as e:
        print(f"[AUTOPUSH] SKIP (read error): {filepath} — {e}")
        continue

    api_url = f"{BASE}/{filepath}"

    # Fetch current SHA (needed for update)
    sha = None
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req) as r:
            sha = json.loads(r.read()).get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print(f"[AUTOPUSH] WARN: could not fetch SHA for {filepath}: {e}")

    body = {"message": f"Auto-push: {filepath}", "content": content}
    if sha:
        body["sha"] = sha

    try:
        req2 = urllib.request.Request(
            api_url,
            data=json.dumps(body).encode(),
            headers=headers,
            method="PUT"
        )
        with urllib.request.urlopen(req2) as r:
            code = r.status
        print(f"[AUTOPUSH] OK ({code}): {filepath}")
        success += 1
    except urllib.error.HTTPError as e:
        print(f"[AUTOPUSH] FAIL ({e.code}): {filepath} — {e.reason}")
        failed += 1
    except Exception as e:
        print(f"[AUTOPUSH] FAIL: {filepath} — {e}")
        failed += 1

print(f"[AUTOPUSH] Done — {success} pushed, {failed} failed.")
