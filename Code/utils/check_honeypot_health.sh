#!/bin/bash

CONFIG_FILE="./configs/honeypot_creds.json"
echo -e "\n🌐 Honeypot Health Check - $(date)"
echo "-------------------------------------------"

# IPs for each honeypot
declare -A HONEYPOT_IPS=(
  ["cowrie"]="192.168.186.136"
  ["honeypy"]="192.168.186.137"
  ["honeytrap"]="192.168.186.138"
  ["conpot"]="192.168.186.139"
  ["nodepot-lite"]="192.168.186.137"
)

# Custom SSH port for honeytrap
declare -A HONEYPOT_PORTS=(
  ["honeytrap"]="2222"
)

# Loop through honeypots
for honeypot in "${!HONEYPOT_IPS[@]}"; do
  IP="${HONEYPOT_IPS[$honeypot]}"
  PORT="${HONEYPOT_PORTS[$honeypot]:-22}"

  USERNAME=$(jq -r --arg hp "$honeypot" '.[$hp].username' "$CONFIG_FILE")
  PASSWORD=$(jq -r --arg hp "$honeypot" '.[$hp].password' "$CONFIG_FILE")

  echo -e "\n🔍 Checking $honeypot @ $IP ..."

  sshpass -p "$PASSWORD" ssh -p "$PORT" \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=5 \
    -oHostKeyAlgorithms=+ssh-rsa \
    -oPubkeyAcceptedAlgorithms=+ssh-rsa \
    "$USERNAME@$IP" bash <<'EOF'

echo "✅ Connected to $(hostname)"
uptime
echo "-------------------------------------------"

# Function to check listening ports
function check_port() {
  local port=$1
  local service=$2
  if ss -tuln | grep -q ":$port "; then
    echo "🟢 $service service running on port $port"
  else
    echo "🔴 $service service NOT running on port $port"
  fi
}

# Service/Process status checks
case "$HOSTNAME" in
  *cowrie*)
    pgrep -f "twistd.*cowrie" >/dev/null && echo "🟢 Cowrie process is running" || echo "🔴 Cowrie process NOT running"
    check_port 22 "SSH"
    check_port 23 "Telnet"
    ;;
  *honeypy*)
    systemctl is-active --quiet honeypy-mongo-logger && echo "🟢 HoneyPy logger is active" || echo "🔴 HoneyPy logger is NOT running"
    check_port 2244 "FTP"
    check_port 80 "HTTP"
    check_port 2048 "Echo"
    check_port 10008 "MOTD UDP"
    ;;
  *honeytrap*)
    docker ps --filter "name=honeytrap" --format "{{.Status}}" | grep -q "Up" && echo "🟢 Honeytrap Docker is running" || echo "🔴 Honeytrap Docker is NOT running"
    check_port 22 "Fake SSH"
    check_port 23 "Fake Telnet"
    check_port 21 "Echo/FTP"
    ;;
  *conpot*)
    pgrep -f "conpot" >/dev/null && echo "🟢 Conpot is running" || echo "🔴 Conpot is NOT running"
    check_port 8800 "Conpot HTTP"
    check_port 5020 "Modbus"
    check_port 10201 "S7Comm"
    check_port 6230 "IPMI"
    check_port 16100 "SNMP"
    ;;
  *nodepot*)
    docker ps --filter "name=nodepot" --format "{{.Status}}" | grep -q "Up" && echo "🟢 Nodepot Docker is running" || echo "🔴 Nodepot Docker is NOT running"
    check_port 8080 "HTTP Nodepot"
    ;;
esac
EOF

  if [ $? -ne 0 ]; then
    echo "❌ Failed to reach $honeypot ($IP)"
  fi
done

echo -e "\n✅ Health check complete."
