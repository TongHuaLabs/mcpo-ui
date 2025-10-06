#!/bin/sh

CONFIG_FILE="/config/config.json"
DOCKER_SOCKET="/var/run/docker.sock"
CONTAINER_NAME="${MCPO_CONTAINER:-mcpo-server}"

echo "🔍 Watching $CONFIG_FILE for changes..."
echo "📦 Will restart container: $CONTAINER_NAME"

# Initial check
if [ ! -f "$CONFIG_FILE" ]; then
    echo "⚠️  Warning: Config file not found at $CONFIG_FILE"
fi

# Watch for changes using inotifywait
while true; do
    # Wait for modify or close_write events on config.json
    inotifywait -e modify -e close_write "$CONFIG_FILE" 2>/dev/null

    if [ $? -eq 0 ]; then
        echo "📝 Config file changed detected at $(date)"
        echo "⏳ Waiting 2 seconds for file writes to complete..."
        sleep 2

        echo "🔄 Restarting $CONTAINER_NAME..."

        # Use docker CLI to restart the container
        if docker restart "$CONTAINER_NAME" 2>/dev/null; then
            echo "✅ Successfully restarted $CONTAINER_NAME at $(date)"
        else
            echo "❌ Failed to restart $CONTAINER_NAME"
        fi

        echo "---"
    fi
done
