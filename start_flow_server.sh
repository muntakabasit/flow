#!/usr/bin/env bash
# start_flow_server.sh — canonical Flow server start
# Repo:     /Volumes/homelab/Storage/ofa_jack_agent/flow/
# Entry:    server_local.py
# Port:     8765
# Usage:    ./start_flow_server.sh          (foreground, Ctrl-C to stop)
#           ./start_flow_server.sh --bg     (background, logs to flow_server.log)

set -euo pipefail

REPO="/Volumes/homelab/Storage/ofa_jack_agent/flow"
ENTRY="server_local.py"
PORT=8765
LOG="$REPO/logs/flow_server.log"

cd "$REPO"

# Kill any stale process on port 8765 before starting.
STALE=$(lsof -ti :$PORT 2>/dev/null || true)
if [ -n "$STALE" ]; then
    echo "[flow] Killing stale process on port $PORT (PID $STALE)"
    kill -9 $STALE 2>/dev/null || true
    sleep 0.5
fi

mkdir -p "$REPO/logs"

if [[ "${1:-}" == "--bg" ]]; then
    echo "[flow] Starting server in background → $LOG"
    nohup python3 "$ENTRY" >> "$LOG" 2>&1 &
    echo "[flow] Server PID $!"
    echo $! > "$REPO/logs/flow_server.pid"
else
    echo "[flow] Starting server on port $PORT (foreground)"
    exec python3 "$ENTRY"
fi
