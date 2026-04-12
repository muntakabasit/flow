#!/usr/bin/env bash
# start_flow_tunnel.sh — canonical Cloudflare named tunnel start
# Tunnel:   flow  (maps flow.flowbasit.com → localhost:8765)
# No repo dependency — can be run from any directory or as a launchd agent.
# Usage:    ./start_flow_tunnel.sh          (foreground, Ctrl-C to stop)
#           ./start_flow_tunnel.sh --bg     (background, logs to ~/.flow/tunnel.log)

set -euo pipefail

TUNNEL_NAME="flow"
STATE_DIR="$HOME/.flow"
LOG="$STATE_DIR/tunnel.log"
PID_FILE="$STATE_DIR/tunnel.pid"

# Verify cloudflared exists
if ! command -v cloudflared &>/dev/null; then
    echo "[tunnel] ERROR: cloudflared not found. Install: brew install cloudflared"
    exit 1
fi

# Check if tunnel is already running
if pgrep -f "cloudflared tunnel run $TUNNEL_NAME" &>/dev/null; then
    EXISTING=$(pgrep -f "cloudflared tunnel run $TUNNEL_NAME" | head -1)
    echo "[tunnel] Already running (PID $EXISTING)"
    exit 0
fi

mkdir -p "$STATE_DIR"

if [[ "${1:-}" == "--bg" ]]; then
    echo "[tunnel] Starting tunnel '$TUNNEL_NAME' in background → $LOG"
    nohup cloudflared tunnel run "$TUNNEL_NAME" >> "$LOG" 2>&1 &
    echo "[tunnel] Tunnel PID $!"
    echo $! > "$PID_FILE"
else
    echo "[tunnel] Starting tunnel '$TUNNEL_NAME' (foreground)"
    exec cloudflared tunnel run "$TUNNEL_NAME"
fi
