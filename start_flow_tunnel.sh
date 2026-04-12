#!/usr/bin/env bash
# start_flow_tunnel.sh — canonical Cloudflare named tunnel start
# Tunnel:   flow  (maps flow.flowbasit.com → localhost:8765)
# No cwd dependency — invoked from any directory or launchd.
# Usage:    ./start_flow_tunnel.sh          (foreground, Ctrl-C to stop)
#           ./start_flow_tunnel.sh --bg     (background, logs → logs/flow_tunnel.log)

set -euo pipefail

TUNNEL_NAME="flow"
LOG_DIR="/Volumes/homelab/Storage/ofa_jack_agent/flow/logs"
LOG="$LOG_DIR/flow_tunnel.log"
PID_FILE="$LOG_DIR/flow_tunnel.pid"

# Verify cloudflared exists
if ! command -v cloudflared &>/dev/null; then
    echo "[tunnel] ERROR: cloudflared not found. Install: brew install cloudflared"
    exit 1
fi

mkdir -p "$LOG_DIR"

# Check if tunnel is already running
if pgrep -f "cloudflared tunnel run $TUNNEL_NAME" &>/dev/null; then
    EXISTING=$(pgrep -f "cloudflared tunnel run $TUNNEL_NAME" | head -1)
    echo "[tunnel] Already running (PID $EXISTING)"
    # Ensure PID file exists even if script was restarted
    echo "$EXISTING" > "$PID_FILE"
    exit 0
fi

if [[ "${1:-}" == "--bg" ]]; then
    echo "[tunnel] Starting tunnel '$TUNNEL_NAME' in background → $LOG"

    # disown detaches from shell job table — survives parent shell exit.
    nohup cloudflared tunnel run "$TUNNEL_NAME" >> "$LOG" 2>&1 &
    TUNNEL_PID=$!
    disown $TUNNEL_PID

    echo $TUNNEL_PID > "$PID_FILE"
    echo "[tunnel] Tunnel PID $TUNNEL_PID — logs: $LOG"
    echo "[tunnel] Stop: kill \$(cat $PID_FILE)"
else
    echo "[tunnel] Starting tunnel '$TUNNEL_NAME' (foreground — Ctrl-C to stop)"
    exec cloudflared tunnel run "$TUNNEL_NAME"
fi
