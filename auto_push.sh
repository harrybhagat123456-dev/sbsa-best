#!/bin/bash
# Auto-push changed files from latest commit to GitHub
# Skips: modules/vars.py (contains credentials)

REPO="harrybhagat123456-dev/sbsa-best"
BASE="https://api.github.com/repos/$REPO/contents"
TOKEN="$GITHUB_TOKEN"

if [ -z "$TOKEN" ]; then
    echo "[AUTOPUSH] GITHUB_TOKEN not set — skipping push."
    exit 0
fi

# Get files changed in latest commit, excluding vars.py
CHANGED=$(git --no-optional-locks diff-tree --no-commit-id -r --name-only HEAD 2>/dev/null | grep -v "^modules/vars\.py$")

if [ -z "$CHANGED" ]; then
    echo "[AUTOPUSH] No changed files to push."
    exit 0
fi

SUCCESS=0
FAILED=0

for filepath in $CHANGED; do
    # Skip if file no longer exists locally (deleted)
    if [ ! -f "$filepath" ]; then
        echo "[AUTOPUSH] SKIP (deleted): $filepath"
        continue
    fi

    # Get current SHA from GitHub (needed for update)
    SHA=$(curl -s -H "Authorization: token $TOKEN" \
        "$BASE/$filepath" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('sha',''))" 2>/dev/null)

    CONTENT=$(base64 -w 0 "$filepath" 2>/dev/null)
    if [ -z "$CONTENT" ]; then
        echo "[AUTOPUSH] SKIP (binary/empty): $filepath"
        continue
    fi

    if [ -n "$SHA" ]; then
        # File exists on GitHub — update it
        HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$BASE/$filepath" \
            -H "Authorization: token $TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"message\":\"Auto-push: $filepath\",\"content\":\"$CONTENT\",\"sha\":\"$SHA\"}")
    else
        # File doesn't exist on GitHub — create it
        HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$BASE/$filepath" \
            -H "Authorization: token $TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"message\":\"Auto-push: $filepath\",\"content\":\"$CONTENT\"}")
    fi

    if [ "$HTTP" = "200" ] || [ "$HTTP" = "201" ]; then
        echo "[AUTOPUSH] OK ($HTTP): $filepath"
        SUCCESS=$((SUCCESS + 1))
    else
        echo "[AUTOPUSH] FAIL ($HTTP): $filepath"
        FAILED=$((FAILED + 1))
    fi
done

echo "[AUTOPUSH] Done — $SUCCESS pushed, $FAILED failed."
