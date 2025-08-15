#!/bin/bash

echo -e "\n🔁 Resetting All Honeypots to Original State - $(date)"
echo "---------------------------------------------------------"

CONFIG_PATH="./configs/honeypot_creds.json"

# === Get credentials and IP ===
get_creds() {
    key="$1"
    user=$(jq -r --arg k "$key" '.[$k].username' "$CONFIG_PATH")
    pass=$(jq -r --arg k "$key" '.[$k].password' "$CONFIG_PATH")
    case "$key" in
        cowrie) ip="192.168.186.136" ;;
        honeypy) ip="192.168.186.137" ;;
        honeytrap) ip="192.168.186.138" ;;
        conpot) ip="192.168.186.139" ;;
        nodepot-lite) ip="192.168.186.137" ;;
        *) echo "❌ Unknown host: $key" && exit 1 ;;
    esac
}

# === Cowrie Reset ===
echo -e "\n🐍 Resetting Cowrie..."
get_creds "cowrie"
sshpass -p "$pass" ssh -o StrictHostKeyChecking=no "$user@$ip" "touch ~/cowrie/etc/enable_telnet.flag && ~/cowrie/bin/cowrie restart"

# === HoneyPy Reset ===
echo -e "\n🦊 Resetting HoneyPy (FTP, HTTP, Echo, MOTD)..."
get_creds "honeypy"
sshpass -p "$pass" ssh -o StrictHostKeyChecking=no "$user@$ip" 'bash -s' <<'EOF'
sed -i '/\[FTP\]/,/enabled/s/enabled *= *No/enabled = Yes/' ~/honeypy/HoneyPy/etc/services.cfg
sed -i '/\[HTTP\]/,/enabled/s/enabled *= *No/enabled = Yes/' ~/honeypy/HoneyPy/etc/services.cfg
sed -i '/\[Echo\]/,/enabled/s/enabled *= *No/enabled = Yes/' ~/honeypy/HoneyPy/etc/services.cfg
sed -i '/\[MOTD\]/,/enabled/s/enabled *= *No/enabled = Yes/' ~/honeypy/HoneyPy/etc/services.cfg
sudo systemctl restart honeypy-mongo-logger
~/honeypy/HoneyPy/start_honeypy.sh
EOF

# === Honeytrap Reset ===
echo -e "\n🍯 Resetting Honeytrap container..."
get_creds "honeytrap"
sshpass -p "$pass" ssh -o StrictHostKeyChecking=no "$user@$ip" "docker restart honeytrap_honeytrap_1"

# === Conpot Reset ===
echo -e "\n🛠️ Resetting Conpot..."
get_creds "conpot"
sshpass -p "$pass" ssh -o StrictHostKeyChecking=no "$user@$ip" "pkill -f 'conpot'; cd ~/conpot-github && nohup ./bin/conpot -c conpot.cfg -t templates/default > conpot.log 2>&1 &"

# === Nodepot-lite Reset ===
echo -e "\n🌐 Resetting Nodepot-lite..."
get_creds "nodepot-lite"
sshpass -p "$pass" ssh -o StrictHostKeyChecking=no "$user@$ip" "docker restart nodepot-lite || (cd ~/nodepot-lite && docker run -d --name nodepot-lite -p 80:80 -v ~/nodepot-lite/uploads:/app/uploads nodepot-lite)"

# === Plugin State Reset ===
echo -e "\n🧠 Resetting plugin_states in MongoDB..."

python3 <<'EOF'
from pymongo import MongoClient
from datetime import datetime, timezone

client = MongoClient("mongodb://localhost:27017/")
db = client["adapttrap"]
plugin_states = db["plugin_states"]

plugins = ["ssh", "ftp", "http", "telnet"]
for plugin in plugins:
    plugin_states.update_one(
        {"plugin": plugin},
        {"$set": {"status": "enabled", "last_updated": datetime.now(timezone.utc)}},
        upsert=True
    )
    print(f"✅ MongoDB: {plugin} → enabled")

print("✅ All plugin_states reset.")
EOF

echo -e "\n✅ All honeypots and plugin states reset successfully.\n"
