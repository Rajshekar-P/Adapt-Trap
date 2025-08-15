#!/bin/bash

echo "[*] Enabling FTP plugin on port 2244..."
sed -i '/\[FTP\]/,/enabled/s/enabled *= *No/enabled = Yes/' ~/honeypy/HoneyPy/etc/services.cfg
sed -i '/\[FTP\]/,/port/s/port *= *tcp:[0-9]*/port = tcp:2244/' ~/honeypy/HoneyPy/etc/services.cfg

echo "[*] Restarting MongoDB logger service..."
sudo systemctl restart honeypy-mongo-logger

echo "[*] Restarting HoneyPy..."
cd ~/honeypy/HoneyPy
source honeypy-env/bin/activate
python3 Honey.py <<EOF
start
exit
EOF

echo "[✓] HoneyPy FTP plugin (port 2244) fully restored!"
