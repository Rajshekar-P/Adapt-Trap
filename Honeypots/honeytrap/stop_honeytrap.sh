#!/bin/bash

echo "==========================="
echo "🛑 Stopping Honeytrap Stack"
echo "==========================="

# Step 1: Stop Docker Compose
echo "📦 Stopping Docker container..."
cd ~/honeytrap || exit
sudo docker-compose down

# Step 2: Stop the MongoDB log forwarder service
echo "📡 Stopping MongoDB forwarder service..."
sudo systemctl stop honeytrap-dockerlog.service

# Step 3: Confirm status
echo "📄 Status Summary:"
sudo docker ps --filter "name=honeytrap"
sudo systemctl status honeytrap-dockerlog.service --no-pager

echo "✅ Done: Honeytrap and log forwarder stopped."
