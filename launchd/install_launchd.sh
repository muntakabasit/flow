#!/usr/bin/env bash
# install_launchd.sh — install and load Flow launchd agents
# Run once on the Mac mini after git pull.
# Safe to re-run: unloads before reloading if already installed.

set -euo pipefail

REPO="/Volumes/homelab/Storage/ofa_jack_agent/flow"
LAUNCHD_DIR="$REPO/launchd"
AGENTS_DIR="$HOME/Library/LaunchAgents"
GUI_UID=$(id -u)

PLISTS=(
    "com.flow.tunnel.plist"   # tunnel first — server needs the public endpoint
    "com.flow.server.plist"
)

mkdir -p "$AGENTS_DIR"
mkdir -p "$REPO/logs"

# Verify cloudflared path matches plist
CF_PATH=$(grep -A1 'cloudflared' "$LAUNCHD_DIR/com.flow.tunnel.plist" | grep string | head -1 | sed 's/.*<string>\(.*\)<\/string>.*/\1/')
if [ ! -x "$CF_PATH" ]; then
    echo "⚠️  cloudflared not found at $CF_PATH"
    echo "   Update ProgramArguments in com.flow.tunnel.plist to: $(which cloudflared 2>/dev/null || echo 'NOT FOUND')"
    exit 1
fi

for PLIST in "${PLISTS[@]}"; do
    LABEL="${PLIST%.plist}"
    SRC="$LAUNCHD_DIR/$PLIST"
    DST="$AGENTS_DIR/$PLIST"

    # Unload if already running (ignore errors — may not be loaded)
    launchctl bootout "gui/$GUI_UID/$LABEL" 2>/dev/null || true

    cp "$SRC" "$DST"
    launchctl bootstrap "gui/$GUI_UID" "$DST"
    echo "✅ Loaded: $LABEL"
done

echo ""
echo "Waiting 5s then checking status..."
sleep 5
launchctl list | grep com.flow || echo "(no com.flow jobs found — check logs)"
