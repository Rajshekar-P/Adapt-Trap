#!/bin/bash

echo "[*] Stopping HoneyPy in tmux..."

# Gracefully stop HoneyPy services and exit
tmux send-keys -t honeypy_session "stop" C-m
sleep 1
tmux send-keys -t honeypy_session "exit" C-m
sleep 1

# Kill tmux session
tmux kill-session -t honeypy_session 2>/dev/null

echo "[+] HoneyPy stopped and tmux session terminated."
