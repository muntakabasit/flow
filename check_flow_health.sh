#!/usr/bin/env bash
# check_flow_health.sh — verify Flow is fully operational
#
# Three checks — all must pass:
#   1. Port 8765 listening  (server_local.py up and bound)
#   2. cloudflared tunnel process "flow" running
#   3. https://flow.flowbasit.com/ws reachable through Cloudflare
#
# Check 3 pass criteria:
#   101 — WebSocket upgrade accepted (full success)
#   400 — Server responded and rejected curl's headers (server IS alive;
#          curl cannot complete a real WS handshake — 400 is expected)
#
# Check 3 fail criteria:
#   000 — No TCP response (DNS or network unreachable)
#   502 — Cloudflare cannot reach origin (tunnel broken)
#   530 — Cloudflare: origin not connected (cloudflared not registered)
#   other — unexpected; treated as failure
#
# RETRY BEHAVIOUR:
#   Port check:     retries up to 30 times / 1s apart (30s window)
#   Endpoint check: retries up to 10 times / 3s apart (30s window)
#   Both windows cover normal server warmup (mlx-whisper load + Piper prewarm).
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

# 1. Port 8765 — retry up to 30s (1s intervals)
echo "1. Server  localhost:$PORT"
PORT_OK=0
for i in $(seq 1 30); do
    if lsof -i :$PORT -sTCP:LISTEN &>/dev/null; then
        PID=$(lsof -ti :$PORT -sTCP:LISTEN 2>/dev/null | head -1)
        ok "Listening (PID $PID, ready after ${i}s)"
        PORT_OK=1
        break
    fi
    if [ $i -eq 1 ]; then echo "     waiting for port..."; fi
    sleep 1
done
[ $PORT_OK -eq 0 ] && fail "NOT listening after 30s — server failed to start (check logs/flow_server.log)"

# 2. Tunnel process — no retry (process either exists or it doesn't)
echo "2. Tunnel  cloudflared tunnel run $TUNNEL_NAME"
if pgrep -f "cloudflared tunnel run $TUNNEL_NAME" &>/dev/null; then
    TPID=$(pgrep -f "cloudflared tunnel run $TUNNEL_NAME" | head -1)
    ok "Running (PID $TPID)"
else
    fail "NOT running — run ./start_flow_tunnel.sh"
fi

# 3. Public endpoint — retry up to 30s (3s intervals)
echo "3. Endpoint $PUBLIC_URL/ws"
ENDPOINT_OK=0
for i in $(seq 1 10); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time 6 \
        -H "Upgrade: websocket" \
        -H "Connection: Upgrade" \
        -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
        -H "Sec-WebSocket-Version: 13" \
        "$PUBLIC_URL/ws" 2>/dev/null || echo "000")
    case "$HTTP_CODE" in
        101|400)
            ok "Reachable — HTTP $HTTP_CODE (attempt $i)"
            ENDPOINT_OK=1
            break
            ;;
        000)
            [ $i -eq 1 ] && echo "     waiting for endpoint..."
            sleep 3
            ;;
        502)
            fail "Bad gateway ($HTTP_CODE) — Cloudflare cannot reach origin (attempt $i)"
            ENDPOINT_OK=2   # definitive failure, no point retrying
            break
            ;;
        530)
            fail "Origin not connected ($HTTP_CODE) — cloudflared not registered with edge (attempt $i)"
            ENDPOINT_OK=2
            break
            ;;
        *)
            fail "Unexpected HTTP $HTTP_CODE from $PUBLIC_URL (attempt $i)"
            ENDPOINT_OK=2
            break
            ;;
    esac
done
[ $ENDPOINT_OK -eq 0 ] && fail "No response from $PUBLIC_URL after 30s"

echo "────────────────────────────────────────"
if [ $FAIL -eq 0 ]; then
    echo "  PASS — $PASS/$((PASS+FAIL)) checks green"
else
    echo "  FAIL — $FAIL check(s) failed, $PASS passed"
fi
echo ""

[ $FAIL -eq 0 ]
