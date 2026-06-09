#!/bin/bash
# Opened in a fresh Ghostty window by the LaunchAgent each morning.
# Runs the digest, then waits so you can actually read it before the window closes.
"$HOME/.local/bin/email-digest"
echo
echo "────────────────────────────────────────────────────────"
read -r -p "Press enter to close..."
