#!/usr/bin/env bash
# check_flow_health.sh — verify Flow is fully operational
# Checks: port 8765 listening, tunnel process running, public endpoint reachable
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
echo "Flow Health Check — $(date '+%Y-%m-%d %H:%M:%S')"
echo "────────────────────────────────────────"

# 1. Port 8765 listening
echo "1. Server port $PORT"
if lsof -i :$PORT -sTCP:LISTEN &>/dev/null; then
    PID=$(lsof -ti :$PORT -sTCP:LISTEN 2>/dev/null | head -1)
    ok "Listening (PID $PID)"
else
    fail "NOT listening — server is down"
fi

# 2. Named tunnel process
echo "2. Cloudflare tunnel ($TUNNEL_NAME)"
if pgrep -f "cloudflared tunnel run $TUNNEL_NAME" &>/dev/null; then
    TPID=$(pgrep -f "cloudflared tunnel run $TUNNEL_NAME" | head -1)
    ok "Running (PID $TPID)"
else
    fail "NOT running — run ./start_flow_tunnel.sh"
fi

# 3. Public endpoint reachable (HTTP upgrade handshake returns 101 or 400,
#    not 502/530 which means tunnel is broken)
echo "3. Public endpoint ($PUBLIC_URL)"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time 8 \
    -H "Upgrade: websocket" \
    -H "Connection: Upgrade" \
    -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
    -H "Sec-WebSocket-Version: 13" \
    "$PUBLIC_URL/ws" 2>/dev/null || echo "000")

case "$HTTP_CODE" in
    101) ok "WebSocket upgrade accepted ($HTTP_CODE)" ;;
    400) ok "Endpoint reachable — server responded ($HTTP_CODE, expected for curl)" ;;
    000) fail "No response — network or DNS issue" ;;
    502) fail "Bad gateway ($HTTP_CODE) — tunnel running but server is down" ;;
    530) fail "Origin unreachable ($HTTP_CODE) — Cloudflare tunnel not connected" ;;
    *)   fail "Unexpected response ($HTTP_CODE)" ;;
esac

echo "────────────────────────────────────────"
echo "Result: $PASS passed, $FAIL failed"
echo ""

[ $FAIL -eq 0 ]
