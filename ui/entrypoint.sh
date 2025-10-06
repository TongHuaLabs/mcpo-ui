#!/bin/bash
set -e

CONFIG_FILE="/config/config.json"
EXAMPLE_CONFIG="/app/config.example.json"

# Ensure config directory exists
mkdir -p "$(dirname "$CONFIG_FILE")"

# Initialize config.json if it doesn't exist or is invalid
if [ ! -f "$CONFIG_FILE" ]; then
    echo "📝 Initializing config file with default time server at $CONFIG_FILE"
    cp "$EXAMPLE_CONFIG" "$CONFIG_FILE"
else
    # Validate JSON structure
    if ! python3 -c "import json; json.load(open('$CONFIG_FILE'))" 2>/dev/null; then
        echo "⚠️  Config file corrupted, reinitializing with default time server..."
        cp "$EXAMPLE_CONFIG" "$CONFIG_FILE"
    else
        echo "✅ Config file exists and is valid"
    fi
fi

# Start Streamlit
exec streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true
