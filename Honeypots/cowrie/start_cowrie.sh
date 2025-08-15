#!/bin/bash

echo "🚀 Starting Cowrie Environment Initialization..."
COWRIE_DIR="/home/cowrie/cowrie"
VENV_PATH="$COWRIE_DIR/cowrie-env/bin/activate"
LOG_FILE="$COWRIE_DIR/var/log/cowrie/cowrie.log"

# Step 1: Activate Python Virtual Environment
if [ -f "$VENV_PATH" ]; then
    echo "✅ Activating Cowrie virtual environment..."
    source "$VENV_PATH"
else
    echo "❌ Cowrie virtual environment not found at $VENV_PATH"
    exit 1
fi

# Step 2: Start Cowrie Service
echo "🔁 Starting Cowrie service..."
$COWRIE_DIR/bin/cowrie start

# Wait briefly and check logs
sleep 2
if [ -f "$LOG_FILE" ]; then
    echo "📄 Tail of Cowrie log:"
    tail -n 5 "$LOG_FILE"
else
    echo "⚠️ Cowrie log not found!"
fi

# Step 3: Start MongoDB Logger Systemd Service
echo "🛰️ Starting cowrie-mongo-logger systemd service..."
sudo systemctl restart cowrie-mongo-logger

# Step 4: Check if MongoDB logger is running
echo "📡 Checking status of cowrie-mongo-logger..."
sudo systemctl is-active --quiet cowrie-mongo-logger && echo "✅ cowrie-mongo-logger is running." || echo "❌ cowrie-mongo-logger failed."

# Step 5: Check ports
echo "🌐 Listening ports (filtered for 2222/2223):"
sudo ss -tulnp | grep 222

echo "🎉 Cowrie setup complete."
