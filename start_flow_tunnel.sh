#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

mkdir -p logs

if pgrep -f "cloudflared tunnel run flow" > /dev/null; then
  echo "[tunnel] Already running (PID $(pgrep -f 'cloudflared tunnel run flow' | head -n1))"
  exit 0
fi

echo "[tunnel] Starting cloudflared tunnel..."
nohup cloudflared tunnel run flow > "$SCRIPT_DIR/logs/flow_tunnel.log" 2>&1 &
echo $! > "$SCRIPT_DIR/logs/flow_tunnel.pid"
echo "[tunnel] PID $(cat "$SCRIPT_DIR/logs/flow_tunnel.pid")"
