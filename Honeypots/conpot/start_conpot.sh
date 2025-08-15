#!/bin/bash

# Variables
CONPOT_SESSION="conpot"
LOGGER_SESSION="conpotlog"
CONPOT_DIR="$HOME/conpot-github"
LOGGER_DIR="$HOME/conpot"
CONPOT_CMD="./bin/conpot -c $CONPOT_DIR/conpot.cfg -t $CONPOT_DIR/conpot/templates/default"
LOGGER_CMD="python3 $LOGGER_DIR/conpot_mongodb.py"

# Start Conpot
if tmux has-session -t $CONPOT_SESSION 2>/dev/null; then
    echo "🟡 Conpot already running in tmux session: $CONPOT_SESSION"
else
    echo "✅ Starting Conpot in tmux session: $CONPOT_SESSION"
    tmux new-session -d -s $CONPOT_SESSION "cd $CONPOT_DIR && $CONPOT_CMD"
    sleep 2
fi

# Start Logger
if tmux has-session -t $LOGGER_SESSION 2>/dev/null; then
    echo "🟡 MongoDB Logger already running in tmux session: $LOGGER_SESSION"
else
    echo "✅ Starting MongoDB log forwarder in tmux session: $LOGGER_SESSION"
    tmux new-session -d -s $LOGGER_SESSION "cd $LOGGER_DIR && $LOGGER_CMD"
    sleep 2
fi

echo "🎯 Use 'tmux attach -t conpot' or 'tmux attach -t conpotlog' to view logs."
