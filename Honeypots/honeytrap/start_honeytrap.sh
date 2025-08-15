#!/bin/bash

echo "==========================="
echo "🚀 Starting Honeytrap Stack"
echo "==========================="

# Step 1: Move to Honeytrap project directory
cd ~/honeytrap || {
  echo "❌ Honeytrap directory not found!"
  exit 1
}

# Step 2: Ensure log folder exists and has correct permissions
mkdir -p ./logs
sudo chown -R $(whoami):$(whoami) ./logs

# Step 3: Start Docker Compose
echo "📦 Starting Honeytrap container via docker-compose..."
sudo docker-compose up -d --force-recreate

# Step 4: Start Docker Log Parser to MongoDB
echo "📡 Starting Docker log to MongoDB forwarder..."
sudo systemctl start honeytrap-dockerlog.service

# Step 5: Show statuses
echo "📄 Status Summary:"
sudo docker ps --filter "name=honeytrap"
sudo systemctl status honeytrap-dockerlog.service --no-pager

echo "✅ Done: Honeytrap is running and logs are forwarding."
