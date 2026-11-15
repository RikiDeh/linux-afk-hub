#!/usr/bin/env bash
set -e

echo "=== Installing Linux AFK Game Studio ==="

MISSING_DEPS=()
for cmd in gamescope python3 gcc; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        MISSING_DEPS+=("$cmd")
    fi
done

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    echo "Notice: Missing required dependencies: ${MISSING_DEPS[*]}"
    echo "Arch / CachyOS : sudo pacman -S gamescope gcc python-gobject python-evdev libxtst libx11 xdotool"
    echo "Ubuntu / Debian: sudo apt install gamescope gcc python3-gi python3-evdev libxtst-dev libx11-dev xdotool"
    echo "Fedora         : sudo dnf install gamescope gcc python3-gobject python3-evdev libXtst-devel libX11-devel xdotool"
    echo ""
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
mkdir -p "$BIN_DIR" "$APP_DIR"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Compiling playback engine (tinytask-play)..."
gcc -O2 "$SCRIPT_DIR/src/tinytask-play.c" -lX11 -lXtst -o "$BIN_DIR/tinytask-play"

echo "Installing recorder, AHK engine & GUI..."
install -m 755 "$SCRIPT_DIR/src/tinytask-rec.py" "$BIN_DIR/tinytask-rec"
install -m 755 "$SCRIPT_DIR/src/ahk_engine.py" "$BIN_DIR/ahk_engine.py"
install -m 755 "$SCRIPT_DIR/src/afk-hub.py" "$BIN_DIR/afk-hub"

echo "Configuring desktop integration..."
sed "s|/home/shikideh|$HOME|g" "$SCRIPT_DIR/assets/afk-hub.desktop" > "$APP_DIR/afk-hub.desktop"
chmod +x "$APP_DIR/afk-hub.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR" 2>/dev/null || true
fi

echo "Installation complete."
echo "Launch with: afk-hub"
