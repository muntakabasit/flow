#!/usr/bin/env bash
set -uo pipefail

REPO="$HOME/ofa_jack_agent/projects/flow"
PORT=8765
WS_URL="wss://flow.flowbasit.com/ws"
PYTHON="$REPO/.venv/bin/python3"

PASS=0
FAIL=0

pass() {
  echo "PASS: $1"
  PASS=$((PASS + 1))
}

fail() {
  echo "FAIL: $1"
  FAIL=$((FAIL + 1))
}

echo "Flow Health"
echo "==========="

echo
echo "Daemon status"
LAUNCHD_LIST=$(sudo launchctl list | grep com.flow || true)
SERVER_PID=$(echo "$LAUNCHD_LIST" | awk '$3 == "com.flow.server" && $1 ~ /^[0-9]+$/ { print $1; exit }')
TUNNEL_PID=$(echo "$LAUNCHD_LIST" | awk '$3 == "com.flow.tunnel" && $1 ~ /^[0-9]+$/ { print $1; exit }')

if [[ -n "$SERVER_PID" ]]; then
  pass "com.flow.server daemon running (PID $SERVER_PID)"
else
  fail "com.flow.server daemon running (No PID)"
fi

if [[ -n "$TUNNEL_PID" ]]; then
  pass "com.flow.tunnel daemon running (PID $TUNNEL_PID)"
else
  fail "com.flow.tunnel daemon running (No PID)"
fi

echo
echo "Local port"
PORT_PID=""
if command -v lsof >/dev/null 2>&1; then
  PORT_PID=$(lsof -ti :"$PORT" -sTCP:LISTEN 2>/dev/null | head -1 || true)
fi

if [[ -n "$PORT_PID" ]]; then
  pass "localhost:$PORT listening (PID $PORT_PID)"
elif command -v nc >/dev/null 2>&1 && nc -z localhost "$PORT" >/dev/null 2>&1; then
  pass "localhost:$PORT listening"
else
  fail "localhost:$PORT listening"
fi

echo
echo "WebSocket"
if [[ ! -x "$PYTHON" ]]; then
  fail "Python not found or not executable: $PYTHON"
else
  WS_ERR=$("$PYTHON" - "$WS_URL" 2>&1 <<'PY'
import asyncio
import sys

try:
    import websockets
except ImportError as exc:
    print(f"missing websockets: {exc}", file=sys.stderr)
    sys.exit(2)

async def main(url):
    async with websockets.connect(url, open_timeout=8, close_timeout=4):
        return

try:
    asyncio.run(main(sys.argv[1]))
except Exception as exc:
    print(exc, file=sys.stderr)
    sys.exit(1)
PY
  )
  WS_EXIT=$?

  if [[ $WS_EXIT -eq 0 ]]; then
    pass "WebSocket handshake succeeded ($WS_URL)"
  else
    fail "WebSocket handshake failed ($WS_URL): $WS_ERR"
  fi
fi

echo
echo "Summary"
echo "======="
echo "PASS: $PASS"
echo "FAIL: $FAIL"

if [[ $FAIL -eq 0 ]]; then
  echo "OVERALL: PASS"
  exit 0
else
  echo "OVERALL: FAIL"
  exit 1
fi
