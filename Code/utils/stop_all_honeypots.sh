#!/bin/bash

echo -e "\n🛑 Stopping All Honeypots - $(date)"
echo "---------------------------------------"

# === Cowrie Stop ===
echo -e "\n🐍 Stopping Cowrie..."
ssh cowrie@192.168.186.136 "~/cowrie/bin/cowrie stop"

# === HoneyPy Stop ===
echo -e "\n🦊 Stopping HoneyPy..."
ssh honeypy@192.168.186.137 <<EOF
sudo systemctl stop honeypy-mongo-logger
~/honeypy/HoneyPy/stop_honeypy.sh
EOF

# === Honeytrap Stop (Docker) ===
echo -e "\n🍯 Stopping Honeytrap container..."
ssh honeytrap@192.168.186.138 "docker stop honeytrap_honeytrap_1 && docker rm honeytrap_honeytrap_1"

# === Conpot Stop ===
echo -e "\n🛠️ Stopping Conpot..."
ssh conpot@192.168.186.139 "pkill -f 'conpot'"

# === Nodepot-lite Stop (Docker) ===
echo -e "\n🌐 Stopping Nodepot-lite..."
ssh honeypy@192.168.186.137 "docker stop nodepot-lite && docker rm nodepot-lite"

echo -e "\n✅ All honeypots stopped.\n"
