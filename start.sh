#!/bin/bash

# Use PORT from environment (Render sets it), default to 5000 for Replit
export PORT="${PORT:-5000}"

# ── Auto-push latest changes to GitHub on every startup ───────────────────────
echo "[AUTOPUSH] Pushing latest changes to GitHub..."
python3 auto_push.sh
echo "[AUTOPUSH] Done."

# ── Start the alive/web server in the background ──────────────────────────────
python3 alive.py &
ALIVE_PID=$!
echo "[START] Alive server started (PID $ALIVE_PID)"

# ── Graceful shutdown handler ─────────────────────────────────────────────────
# Kill alive server IMMEDIATELY so port 5000 is freed for the next restart.
# Give the bot a few extra seconds to finish its current file before killing it.
cleanup() {
    echo "[START] SIGTERM received — shutting down..."
    kill $ALIVE_PID 2>/dev/null
    sleep 3
    kill $BOT_PID 2>/dev/null
    wait $ALIVE_PID 2>/dev/null
    wait $BOT_PID 2>/dev/null
    echo "[START] Shutdown complete."
    exit 0
}
trap cleanup SIGTERM SIGINT

# ── Bot watchdog loop ─────────────────────────────────────────────────────────
while true; do
    echo "[START] Launching Telegram bot..."
    (cd modules && python3 main.py) &
    BOT_PID=$!

    wait $BOT_PID
    EXIT_CODE=$?

    echo "[START] Bot exited with code $EXIT_CODE."

    if ! kill -0 $ALIVE_PID 2>/dev/null; then
        echo "[START] Alive server died — restarting it..."
        python3 alive.py &
        ALIVE_PID=$!
    fi

    echo "[START] Restarting bot in 10 seconds..."
    sleep 10
done
