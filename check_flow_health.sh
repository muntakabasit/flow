#!/usr/bin/env bash
# check_flow_health.sh — verify Flow is fully operational
#
# Three checks, all must pass:
#   1. Port 8765 is listening on localhost (server_local.py is up)
#   2. cloudflared tunnel process "flow" is running
#   3. https://flow.flowbasit.com/ws is reachable through Cloudflare
#
# Check 3 pass criteria:
#   101 — WebSocket upgrade accepted (full success)
#   400 — Server responded and rejected curl's headers (server IS alive;
#          curl cannot complete a real WS handshake — 400 is expected and correct)
#
# Check 3 fail criteria:
#   000 — No TCP response (DNS failure or network down)
#   502 — Cloudflare reached but cannot contact origin (tunnel process may be
#          running but disconnected from Cloudflare edge)
#   530 — Cloudflare: origin not connected (cloudflared not registered)
#   anything else — unexpected; treat as failure
#
# Usage:  ./check_flow_health.sh
# Exit:   0 = all green  |  1 = one or more checks failed

set -uo pipefail

PORT=8765
TUNNEL_NAME="flow"
PUBLIC_URL="https://flow.flowbasit.com"
PASS=0
FAIL=0

ok()   { echo "  ✅ $1"; ((PASS++)) || true; }
fail() { echo "  ❌ $1"; ((FAIL++)) || true; }

echo ""
echo "Flow Health — $(date '+%Y-%m-%d %H:%M:%S')"
echo "────────────────────────────────────────"

# 1. Port 8765 listening
echo "1. Server  localhost:$PORT"
if lsof -i :$PORT -sTCP:LISTEN &>/dev/null; then
    PID=$(lsof -ti :$PORT -sTCP:LISTEN 2>/dev/null | head -1)
    ok "Listening (PID $PID)"
else
    fail "NOT listening — run ./start_flow_server.sh"
fi

# 2. Named tunnel process running
echo "2. Tunnel  cloudflared tunnel run $TUNNEL_NAME"
if pgrep -f "cloudflared tunnel run $TUNNEL_NAME" &>/dev/null; then
    TPID=$(pgrep -f "cloudflared tunnel run $TUNNEL_NAME" | head -1)
    ok "Running (PID $TPID)"
else
    fail "NOT running — run ./start_flow_tunnel.sh"
fi

# 3. Public endpoint reachable
echo "3. Endpoint $PUBLIC_URL/ws"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time 8 \
    -H "Upgrade: websocket" \
    -H "Connection: Upgrade" \
    -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
    -H "Sec-WebSocket-Version: 13" \
    "$PUBLIC_URL/ws" 2>/dev/null || echo "000")

case "$HTTP_CODE" in
    101) ok "WebSocket upgrade accepted ($HTTP_CODE)" ;;
    400) ok "Server reachable — responded $HTTP_CODE (correct for curl WS probe)" ;;
    000) fail "No response — DNS or network unreachable" ;;
    502) fail "Bad gateway ($HTTP_CODE) — Cloudflare cannot reach origin" ;;
    530) fail "Origin not connected ($HTTP_CODE) — cloudflared not registered with Cloudflare edge" ;;
    *)   fail "Unexpected HTTP $HTTP_CODE from $PUBLIC_URL" ;;
esac

echo "────────────────────────────────────────"
if [ $FAIL -eq 0 ]; then
    echo "  PASS — $PASS/$((PASS+FAIL)) checks green"
else
    echo "  FAIL — $FAIL check(s) failed"
fi
echo ""

[ $FAIL -eq 0 ]
