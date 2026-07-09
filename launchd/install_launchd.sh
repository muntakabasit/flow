#!/usr/bin/env bash
# install_launchd.sh — install and load Flow launchd agents
#
# Run once on the Mac mini after git pull, or after moving the repo.
# Safe to re-run — bootout + bootstrap handles already-loaded agents.
#
# What this does:
#   1. Creates ~/.flow/ log directory on internal SSD
#   2. Substitutes HOMEPLACEHOLDER in plist templates with real $HOME
#      (launchd plists cannot expand ~ or $HOME — literal paths required)
#   3. Copies generated plists into ~/Library/LaunchAgents/
#   4. Bootstraps both agents into the current GUI session
#
# PREREQUISITES — both must be satisfied before running:
#   A. cloudflared tunnel login completed  (creates ~/.cloudflared/<uuid>.json)
#   B. venv built: cd <repo> && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
#
# After a reboot, both agents start automatically at login.

set -euo pipefail

REPO="$HOME/ofa_jack_agent/projects/flow"
LAUNCHD_DIR="$REPO/launchd"
AGENTS_DIR="$HOME/Library/LaunchAgents"
FLOW_DIR="$HOME/.flow"
GUI_UID=$(id -u)

echo ""
echo "Flow launchd install"
echo "──────────────────────────────────"

# ── Preflight checks ────────────────────────────────────────────────────────

# 1. Repo must be in expected location
if [ ! -f "$REPO/server_local.py" ]; then
    echo "❌ repo not found at $REPO"
    echo "   Expected: $REPO/server_local.py"
    exit 1
fi
echo "✅ Repo:    $REPO"

# 2. Venv python must exist
VENV_PY="$REPO/.venv/bin/python3"
if [ ! -x "$VENV_PY" ]; then
    echo "❌ venv python not found: $VENV_PY"
    echo "   Run: cd $REPO && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi
echo "✅ Venv:    $VENV_PY"

# 3. cloudflared binary must exist
CF_PATH="/opt/homebrew/bin/cloudflared"
if [ ! -x "$CF_PATH" ]; then
    echo "❌ cloudflared not found at $CF_PATH"
    echo "   Run: brew install cloudflared"
    exit 1
fi
echo "✅ cloudflared: $CF_PATH"

# 4. cloudflared tunnel credentials must exist
if [ ! -d "$HOME/.cloudflared" ]; then
    echo "❌ ~/.cloudflared/ missing — tunnel credentials not set up"
    echo "   Run: cloudflared tunnel login"
    echo "        cloudflared tunnel create flow   (if tunnel doesn't exist yet)"
    echo "        cloudflared tunnel route dns flow flow.flowbasit.com"
    exit 1
fi
echo "✅ Credentials: ~/.cloudflared/"

# ── Setup ───────────────────────────────────────────────────────────────────

mkdir -p "$AGENTS_DIR"
mkdir -p "$FLOW_DIR"
echo "✅ Log dir: $FLOW_DIR"

# ── Install plists ──────────────────────────────────────────────────────────

PLISTS=(
    "com.flow.tunnel.plist"   # tunnel first — no dependencies, can start immediately
    "com.flow.server.plist"   # server second — reads venv python from internal SSD
)

for PLIST in "${PLISTS[@]}"; do
    LABEL="${PLIST%.plist}"
    TEMPLATE="$LAUNCHD_DIR/$PLIST"
    DST="$AGENTS_DIR/$PLIST"

    if [ ! -f "$TEMPLATE" ]; then
        echo "❌ template missing: $TEMPLATE"
        exit 1
    fi

    # Substitute HOMEPLACEHOLDER → actual $HOME (plists cannot use ~ or $HOME)
    sed "s|HOMEPLACEHOLDER|$HOME|g" "$TEMPLATE" > "$DST"

    # Unload if already running (safe to fail if not loaded)
    launchctl bootout "gui/$GUI_UID/$LABEL" 2>/dev/null && echo "   unloaded existing: $LABEL" || true

    launchctl bootstrap "gui/$GUI_UID" "$DST"
    echo "✅ Loaded:  $LABEL"
done

# ── Status ──────────────────────────────────────────────────────────────────

echo ""
echo "Waiting 5s for services to start..."
sleep 5
echo ""

echo "launchctl status:"
launchctl list | grep com.flow || echo "⚠️  No com.flow jobs found in launchctl list"

echo ""
echo "Logs (tail -f to watch):"
echo "  tail -f $FLOW_DIR/launchd_server.log"
echo "  tail -f $FLOW_DIR/launchd_tunnel.log"
echo ""
echo "Health check:"
echo "  $REPO/check_flow_health.sh"
echo ""
echo "Stop (without uninstalling):"
echo "  launchctl bootout gui/$GUI_UID/com.flow.server"
echo "  launchctl bootout gui/$GUI_UID/com.flow.tunnel"
echo ""
echo "Uninstall:"
echo "  launchctl bootout gui/$GUI_UID/com.flow.server 2>/dev/null; rm $AGENTS_DIR/com.flow.server.plist"
echo "  launchctl bootout gui/$GUI_UID/com.flow.tunnel 2>/dev/null; rm $AGENTS_DIR/com.flow.tunnel.plist"
