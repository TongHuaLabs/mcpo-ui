#!/bin/bash
set -e

CONFIG_DIR="/config"
CONFIG_FILE="$CONFIG_DIR/config.json"
MCPO_PID=""
UI_PID=""
CADDY_PID=""
WATCHER_PID=""

# Validate required environment variables
if [ -z "$MCPO_API_KEY" ]; then
    echo "❌ Error: MCPO_API_KEY environment variable is required"
    exit 1
fi

# Graceful shutdown handler
shutdown() {
    echo "🛑 Shutting down gracefully..."
    [ ! -z "$CADDY_PID" ] && kill "$CADDY_PID" 2>/dev/null || true
    [ ! -z "$MCPO_PID" ] && kill "$MCPO_PID" 2>/dev/null || true
    [ ! -z "$UI_PID" ] && kill "$UI_PID" 2>/dev/null || true
    [ ! -z "$WATCHER_PID" ] && kill "$WATCHER_PID" 2>/dev/null || true
    exit 0
}
trap shutdown SIGTERM SIGINT

# Initialize config if not exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "📋 Initializing config file..."
    cp /app/config.example.json "$CONFIG_FILE"
fi

# Function to start MCPO
start_mcpo() {
    echo "🚀 Starting MCPO server..."
    mcpo --api-key "$MCPO_API_KEY" --config "$CONFIG_FILE" --port 8000 &
    MCPO_PID=$!
    echo "✅ MCPO started with PID $MCPO_PID"
}

# Function to restart MCPO
restart_mcpo() {
    if [ ! -z "$MCPO_PID" ] && kill -0 "$MCPO_PID" 2>/dev/null; then
        echo "🔄 Stopping MCPO (PID $MCPO_PID)..."
        kill "$MCPO_PID"
        wait "$MCPO_PID" 2>/dev/null || true
    fi
    start_mcpo
}

# Start Streamlit UI in background (on localhost only, Caddy will proxy)
echo "🎨 Starting Streamlit UI..."
streamlit run /app/app.py --server.port=8501 --server.address=127.0.0.1 --server.headless=true &
UI_PID=$!
echo "✅ UI started with PID $UI_PID"
sleep 2  # Give UI time to start
if ! kill -0 "$UI_PID" 2>/dev/null; then
    echo "❌ Failed to start UI"
    exit 1
fi

# Start Caddy reverse proxy with optional basic auth
echo "🌐 Starting Caddy reverse proxy..."
caddy run --config /app/Caddyfile --adapter caddyfile 2>&1 &
CADDY_PID=$!
echo "✅ Caddy started with PID $CADDY_PID"
sleep 1  # Give Caddy time to start
if ! kill -0 "$CADDY_PID" 2>/dev/null; then
    echo "❌ Failed to start Caddy"
    exit 1
fi

# Start MCPO
start_mcpo
sleep 2  # Give MCPO time to start
if ! kill -0 "$MCPO_PID" 2>/dev/null; then
    echo "❌ Failed to start MCPO"
    exit 1
fi

# Watch entire config directory for changes (including credentials, etc.)
echo "👀 Watching $CONFIG_DIR for changes..."
LAST_RESTART=0
inotifywait -m -r -e modify -e close_write -e create -e delete "$CONFIG_DIR" 2>/dev/null |
while read -r directory events filename; do
    # Debounce: only restart if 3+ seconds since last restart
    NOW=$(date +%s)
    if [ $((NOW - LAST_RESTART)) -lt 3 ]; then
        continue
    fi

    echo "📝 Config change detected: $filename at $(date)"
    echo "⏳ Waiting 2 seconds for writes to complete..."
    sleep 2
    restart_mcpo
    LAST_RESTART=$(date +%s)
    echo "---"
done &
WATCHER_PID=$!

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
