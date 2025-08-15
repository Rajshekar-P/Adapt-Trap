#!/bin/bash

# Variables
CONPOT_SESSION="conpot"
LOGGER_SESSION="conpotlog"

# Stop Conpot
if tmux has-session -t $CONPOT_SESSION 2>/dev/null; then
    echo "🛑 Stopping Conpot..."
    tmux send-keys -t $CONPOT_SESSION C-c
    sleep 2
    tmux kill-session -t $CONPOT_SESSION
else
    echo "⚠️  Conpot session not running."
fi

# Stop Logger
if tmux has-session -t $LOGGER_SESSION 2>/dev/null; then
    echo "🛑 Stopping MongoDB Logger..."
    tmux send-keys -t $LOGGER_SESSION C-c
    sleep 2
    tmux kill-session -t $LOGGER_SESSION
else
    echo "⚠️  MongoDB Logger session not running."
fi

echo "✅ Conpot and logger stopped."
