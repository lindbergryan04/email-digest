#!/bin/bash
# Set up the daily morning digest: opens a Ghostty window with your digest at
# 8am (or the first time your laptop wakes after 8am). Run this once.
set -e

HERE="$(cd "$(dirname "$0")" && pwd)"
PLIST="$HOME/Library/LaunchAgents/com.email-digest.plist"

mkdir -p "$HOME/.email-digest" "$HOME/Library/LaunchAgents"

cp "$HERE/morning-digest.sh" "$HOME/.email-digest/morning-digest.sh"
chmod +x "$HOME/.email-digest/morning-digest.sh"

cp "$HERE/com.email-digest.plist" "$PLIST"

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "Installed. Your digest will open in Ghostty each morning (8am, or first wake after)."
echo "Try it right now:  launchctl start com.email-digest"
echo "Uninstall:         launchctl unload \"$PLIST\" && rm \"$PLIST\""
