#!/bin/bash

echo "[*] Restarting HoneyPy..."

# Stop HoneyPy (clean shutdown)
~/honeypy/HoneyPy/stop_honeypy.sh

# Wait a moment to ensure proper shutdown
sleep 2

# Start HoneyPy again
~/honeypy/HoneyPy/start_honeypy.sh

echo "[+] HoneyPy restarted."
