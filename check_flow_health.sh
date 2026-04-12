#!/usr/bin/env bash
# check_flow_health.sh — verify Flow is fully operational
#
# Three checks — all must pass:
#   1. Port 8765 listening  (server_local.py up and bound)
#   2. cloudflared tunnel process "flow" running
#   3. wss://flow.flowbasit.com/ws — real WebSocket handshake (Python websockets)
#
# Check 3 pass:  connects and closes cleanly (exit 0)
# Check 3 fail:  timeout / connection refused / handshake error (exit nonzero)
#
# RETRY BEHAVIOUR:
#   Port check:     retries up to 30 times / 1s apart (30s window)
#   Endpoint check: retries up to 10 times / 3s apart (30s window)
#   Both windows cover normal server warmup (mlx-whisper load + Piper prewarm).
#
# Python used: repo venv (venv/bin/python3) if present, else system python3.
# Requires:    websockets>=12.0 (already in requirements.txt).
#
# Usage:  ./check_flow_health.sh
# Exit:   0 = all green  |  1 = one or more checks failed

set -uo pipefail

REPO="/Volumes/homelab/Storage/ofa_jack_agent/flow"
PORT=8765
TUNNEL_NAME="flow"
WS_URL="wss://flow.flowbasit.com/ws"
PASS=0
FAIL=0

ok()   { echo "  ✅ $1"; ((PASS++)) || true; }
fail() { echo "  ❌ $1"; ((FAIL++)) || true; }

# Prefer repo venv python so websockets version is guaranteed.
if [ -x "$REPO/venv/bin/python3" ]; then
    PYTHON="$REPO/venv/bin/python3"
else
    PYTHON="python3"
fi

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

# 3. Real WebSocket handshake — retry up to 30s (3s intervals)
echo "3. WebSocket $WS_URL"
ENDPOINT_OK=0
for i in $(seq 1 10); do
    WS_ERR=$("$PYTHON" - "$WS_URL" 2>&1 <<'PYEOF'
import asyncio, sys
try:
    import websockets
except ImportError:
    print("websockets not installed — run: pip install websockets", file=sys.stderr)
    sys.exit(2)

async def check(url):
    try:
        async with websockets.connect(url, open_timeout=8, close_timeout=4) as ws:
            pass   # handshake succeeded — close immediately
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

asyncio.run(check(sys.argv[1]))
PYEOF
    )
    WS_EXIT=$?

    if [ $WS_EXIT -eq 0 ]; then
        ok "WebSocket handshake succeeded (attempt $i)"
        ENDPOINT_OK=1
        break
    elif [ $WS_EXIT -eq 2 ]; then
        fail "websockets library missing — run: pip install 'websockets>=12'"
        ENDPOINT_OK=2
        break
    else
        if [ $i -eq 1 ]; then echo "     waiting for endpoint..."; fi
        [ -n "$WS_ERR" ] && echo "     attempt $i: $WS_ERR"
        sleep 3
    fi
done
[ $ENDPOINT_OK -eq 0 ] && fail "WebSocket handshake failed after 30s ($WS_URL)"

echo "────────────────────────────────────────"
if [ $FAIL -eq 0 ]; then
    echo "  PASS — $PASS/$((PASS+FAIL)) checks green"
else
    echo "  FAIL — $FAIL check(s) failed, $PASS passed"
fi
echo ""

[ $FAIL -eq 0 ]
