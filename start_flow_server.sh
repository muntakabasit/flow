#!/usr/bin/env bash
# start_flow_server.sh — canonical Flow server start
# Repo:     /Volumes/homelab/Storage/ofa_jack_agent/flow/
# Entry:    server_local.py
# Port:     8765
# Usage:    ./start_flow_server.sh          (foreground, Ctrl-C to stop)
#           ./start_flow_server.sh --bg     (background, logs → logs/flow_server.log)

set -euo pipefail

REPO="/Volumes/homelab/Storage/ofa_jack_agent/flow"
ENTRY="server_local.py"
PORT=8765
LOG="$REPO/logs/flow_server.log"
PID_FILE="$REPO/logs/flow_server.pid"

cd "$REPO"
mkdir -p "$REPO/logs"

# Kill any stale process on port 8765 before starting.
STALE=$(lsof -ti :$PORT 2>/dev/null || true)
if [ -n "$STALE" ]; then
    echo "[flow] Killing stale process on port $PORT (PID $STALE)"
    kill -9 $STALE 2>/dev/null || true
    sleep 0.5
fi

if [[ "${1:-}" == "--bg" ]]; then
    echo "[flow] Starting server in background → $LOG"

    # nohup alone is not enough on macOS — the child still belongs to the shell's
    # process group and receives SIGHUP when the parent exits.
    # disown removes it from the job table so it survives shell exit.
    nohup python3 "$ENTRY" >> "$LOG" 2>&1 &
    SERVER_PID=$!
    disown $SERVER_PID

    echo $SERVER_PID > "$PID_FILE"
    echo "[flow] Server PID $SERVER_PID — logs: $LOG"
    echo "[flow] Stop: kill \$(cat $PID_FILE)"
else
    echo "[flow] Starting server on port $PORT (foreground — Ctrl-C to stop)"
    exec python3 "$ENTRY"
fi
