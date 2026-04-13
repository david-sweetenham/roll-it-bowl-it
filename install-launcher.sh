#!/bin/bash
# install-launcher.sh — installs a desktop launcher for Roll It & Bowl It
# Works on any Linux desktop that supports .desktop files (KDE, GNOME, XFCE, etc.)
# Run from the project root: bash install-launcher.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_FILE="$DESKTOP_DIR/roll-it-bowl-it.desktop"

mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.1
Type=Application
Name=Roll It & Bowl It
GenericName=Dice Cricket
Comment=Dice Cricket Done Digitally
Exec=$SCRIPT_DIR/start.sh
Icon=$SCRIPT_DIR/static/ribi.svg
Terminal=false
Categories=Game;BoardGame;
Keywords=cricket;dice;sport;simulation;
StartupNotify=true
EOF

chmod +x "$DESKTOP_FILE"

# Refresh the desktop database so the entry appears immediately
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$DESKTOP_DIR"
fi

echo "Launcher installed: $DESKTOP_FILE"
echo ""
echo "The app will appear as 'Roll It & Bowl It' in your application menu."
echo "On KDE: right-click it in the menu → Pin to Taskbar"
echo "On GNOME: find it in Activities, then drag to the dock"
