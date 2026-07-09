#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

mkdir -p logs

kill $(cat logs/flow_server.pid) 2>/dev/null || true

echo "[flow] Starting server in background → $SCRIPT_DIR/logs/flow_server.log"
nohup python3 server_local.py > "$SCRIPT_DIR/logs/flow_server.log" 2>&1 &
echo $! > "$SCRIPT_DIR/logs/flow_server.pid"
echo "[flow] Server PID $(cat "$SCRIPT_DIR/logs/flow_server.pid")"
echo "[flow] Stop: kill \$(cat $SCRIPT_DIR/logs/flow_server.pid)"
