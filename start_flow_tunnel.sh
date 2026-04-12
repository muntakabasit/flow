#!/usr/bin/env bash
# start_flow_tunnel.sh — canonical Cloudflare named tunnel start
# Tunnel:   flow  (maps flow.flowbasit.com → localhost:8765)
# Usage:    ./start_flow_tunnel.sh          (foreground, Ctrl-C to stop)
#           ./start_flow_tunnel.sh --bg     (background, logs to flow_tunnel.log)

set -euo pipefail

TUNNEL_NAME="flow"
LOG="/Volumes/homelab/Storage/ofa_jack_agent/flow/logs/flow_tunnel.log"

# Verify cloudflared exists
if ! command -v cloudflared &>/dev/null; then
    echo "[tunnel] ERROR: cloudflared not found. Install: brew install cloudflared"
    exit 1
fi

# Check if tunnel is already running
if pgrep -f "cloudflared tunnel run $TUNNEL_NAME" &>/dev/null; then
    echo "[tunnel] Already running ($(pgrep -f "cloudflared tunnel run $TUNNEL_NAME"))"
    exit 0
fi

mkdir -p "$(dirname "$LOG")"

if [[ "${1:-}" == "--bg" ]]; then
    echo "[tunnel] Starting tunnel '$TUNNEL_NAME' in background → $LOG"
    nohup cloudflared tunnel run "$TUNNEL_NAME" >> "$LOG" 2>&1 &
    echo "[tunnel] Tunnel PID $!"
    echo $! > "/Volumes/homelab/Storage/ofa_jack_agent/flow/logs/flow_tunnel.pid"
else
    echo "[tunnel] Starting tunnel '$TUNNEL_NAME' (foreground)"
    exec cloudflared tunnel run "$TUNNEL_NAME"
fi
