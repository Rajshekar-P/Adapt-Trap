#!/usr/bin/env bash
set -euo pipefail

APP_NAME=nodepot-lite
IMAGE_TAG=nodepot-lite:latest
HOST_PORT=80
CONTAINER_PORT=80
MONGO_URI_DEFAULT="mongodb://192.168.186.135:27017/adapttrap"

echo "[*] Removing old container if exists..."
docker rm -f "$APP_NAME" >/dev/null 2>&1 || true

echo "[*] Building image with host network (faster npm)..."
docker build --network=host -t "$IMAGE_TAG" .

echo "[*] Starting container..."
docker run -d --name "$APP_NAME" \
  -p ${HOST_PORT}:${CONTAINER_PORT} \
  -e PORT=${CONTAINER_PORT} \
  -e MONGO_URI="${MONGO_URI:-$MONGO_URI_DEFAULT}" \
  "$IMAGE_TAG"

echo "[+] Nodepot-lite up at http://$(hostname -I | awk '{print $1}'):${HOST_PORT}"
