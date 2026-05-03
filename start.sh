#!/bin/bash

rm -f bot.session bot.session-journal

# Use PORT from environment (Render sets it), default to 5000 for Replit
export PORT="${PORT:-5000}"

# ── Start the alive/web server in the background ──────────────────────────────
# It runs independently; its job is solely to keep Render alive via HTTP pings.
# It is NOT in the same process group as the bot, so bot crashes won't touch it.
python3 alive.py &
ALIVE_PID=$!
echo "[START] Alive server started (PID $ALIVE_PID)"

# ── Graceful shutdown handler ─────────────────────────────────────────────────
# When Render sends SIGTERM, let the current bot operation finish (up to 25 s)
# then kill the alive server cleanly.
cleanup() {
    echo "[START] SIGTERM received — waiting for bot to finish current task..."
    # Give the bot process time to complete any ongoing download/upload
    sleep 5
    kill $BOT_PID 2>/dev/null
    kill $ALIVE_PID 2>/dev/null
    echo "[START] Shutdown complete."
    exit 0
}
trap cleanup SIGTERM SIGINT

# ── Bot watchdog loop ─────────────────────────────────────────────────────────
# If the bot crashes mid-download it is automatically restarted here.
# The alive server keeps running the whole time so Render never drops the service.
while true; do
    echo "[START] Launching Telegram bot..."
    (cd modules && python3 main.py) &
    BOT_PID=$!

    # Wait for the bot process to exit (for any reason)
    wait $BOT_PID
    EXIT_CODE=$?

    echo "[START] Bot exited with code $EXIT_CODE."

    # Restart the alive server if it somehow died
    if ! kill -0 $ALIVE_PID 2>/dev/null; then
        echo "[START] Alive server died — restarting it..."
        python3 alive.py &
        ALIVE_PID=$!
    fi

    echo "[START] Restarting bot in 10 seconds..."
    sleep 10
done
