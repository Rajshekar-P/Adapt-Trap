#!/bin/bash

echo "[*] Starting HoneyPy in tmux..."

# Kill existing session if any
tmux kill-session -t honeypy_session 2>/dev/null

# Start a new tmux session and run HoneyPy
tmux new-session -d -s honeypy_session "source ~/honeypy/honeypy-env/bin/activate && python3 ~/honeypy/HoneyPy/Honey.py"

# Wait and send 'start' command to HoneyPy
sleep 2
tmux send-keys -t honeypy_session "start" C-m

echo "[+] HoneyPy started in tmux. Use 'tmux attach -t honeypy_session' to view."
