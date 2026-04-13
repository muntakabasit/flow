#!/usr/bin/env bash
# install_launchd.sh — install and load Flow launchd agents
# Run once on the Mac mini after git pull. Safe to re-run.
#
# What this does:
#   1. Creates ~/.flow/ with the volume-wait launcher and log directory
#   2. Substitutes HOMEPLACEHOLDER in plists with real $HOME (plists cannot
#      expand ~ or $HOME themselves — literal paths required)
#   3. Installs generated plists into ~/Library/LaunchAgents/
#   4. Bootstraps both agents into the current GUI session
#
# After a reboot:
#   - Tunnel starts immediately (cloudflared is on internal SSD)
#   - Server wrapper waits up to 120s for /Volumes/homelab to mount,
#     then delegates to start_flow_server.sh

set -euo pipefail

REPO="/Volumes/homelab/Storage/ofa_jack_agent/flow"
LAUNCHD_DIR="$REPO/launchd"
AGENTS_DIR="$HOME/Library/LaunchAgents"
FLOW_DIR="$HOME/.flow"
GUI_UID=$(id -u)

# Verify cloudflared at the path frozen in com.flow.tunnel.plist
CF_PATH="/opt/homebrew/bin/cloudflared"
if [ ! -x "$CF_PATH" ]; then
    echo "⚠️  cloudflared not found at $CF_PATH"
    echo "   Run: which cloudflared"
    echo "   Then update ProgramArguments[0] in launchd/com.flow.tunnel.plist"
    exit 1
fi

mkdir -p "$AGENTS_DIR"
mkdir -p "$FLOW_DIR"

# ── Create the volume-wait launcher ────────────────────────────────────────
# This script lives on the internal SSD (home dir) so launchd can always find
# it at boot. It polls for /Volumes/homelab before delegating to the real server.
cat > "$FLOW_DIR/launch_server.sh" << 'LAUNCHER'
#!/usr/bin/env bash
VOLUME="/Volumes/homelab"
REPO="$VOLUME/Storage/ofa_jack_agent/flow"
MAX_WAIT=120

echo "[flow-launcher] $(date '+%H:%M:%S') waiting for $VOLUME..."
for i in $(seq 1 $MAX_WAIT); do
    if [ -d "$REPO" ]; then
        echo "[flow-launcher] $(date '+%H:%M:%S') volume ready after ${i}s — starting server"
        exec /bin/bash "$REPO/start_flow_server.sh"
    fi
    sleep 1
done

echo "[flow-launcher] ERROR: $VOLUME not mounted after ${MAX_WAIT}s — giving up"
exit 1
LAUNCHER
chmod +x "$FLOW_DIR/launch_server.sh"
echo "✅ Created $FLOW_DIR/launch_server.sh"

# ── Generate plists with real $HOME substituted ────────────────────────────
PLISTS=(
    "com.flow.tunnel.plist"   # tunnel first — no volume dep, starts immediately
    "com.flow.server.plist"   # server second — waits for volume via launcher
)

for PLIST in "${PLISTS[@]}"; do
    LABEL="${PLIST%.plist}"
    TEMPLATE="$LAUNCHD_DIR/$PLIST"
    DST="$AGENTS_DIR/$PLIST"

    # Substitute HOMEPLACEHOLDER → actual $HOME (sed in-place to temp file)
    sed "s|HOMEPLACEHOLDER|$HOME|g" "$TEMPLATE" > "$DST"

    # Unload if already running (safe to fail if not loaded)
    launchctl bootout "gui/$GUI_UID/$LABEL" 2>/dev/null || true

    launchctl bootstrap "gui/$GUI_UID" "$DST"
    echo "✅ Loaded: $LABEL"
done

echo ""
echo "Waiting 5s then checking status..."
sleep 5
echo ""
launchctl list | grep com.flow || echo "⚠️  No com.flow jobs found — check $FLOW_DIR/*.log"
echo ""
echo "Logs:"
echo "  tail -f $FLOW_DIR/launchd_server.log"
echo "  tail -f $FLOW_DIR/launchd_tunnel.log"
echo ""
echo "Stop:"
echo "  launchctl bootout gui/$GUI_UID/com.flow.server"
echo "  launchctl bootout gui/$GUI_UID/com.flow.tunnel"
