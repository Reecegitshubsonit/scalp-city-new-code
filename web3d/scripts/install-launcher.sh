#!/usr/bin/env bash
# Installs the icon and desktop entry, and pins it to the GNOME dock. Safe to run again.
set -eu
DIR="$(cd "$(dirname "$0")/.." && pwd)"
ICONS="$HOME/.local/share/icons/hicolor/scalable/apps"
APPS="$HOME/.local/share/applications"
mkdir -p "$ICONS" "$APPS"
cp "$DIR/assets/scalp-city.svg" "$ICONS/scalp-city.svg"
chmod +x "$DIR/scripts/launch.sh" "$DIR/scripts/stop.sh"
cat > "$APPS/scalp-city.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Scalp City
Comment=3D dashboard for the paper-trading bots
Exec=$DIR/scripts/launch.sh
Icon=scalp-city
Terminal=false
Categories=Office;Finance;
Actions=Stop;

[Desktop Action Stop]
Name=Stop view server
Exec=$DIR/scripts/stop.sh
DESKTOP
update-desktop-database "$APPS" 2>/dev/null || true
gtk-update-icon-cache -q "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
if command -v gsettings >/dev/null; then
  cur="$(gsettings get org.gnome.shell favorite-apps)"
  case "$cur" in
    *scalp-city.desktop*) echo "already in the dock" ;;
    *) gsettings set org.gnome.shell favorite-apps "$(echo "$cur" | sed "s/]$/, 'scalp-city.desktop']/")" && echo "added to the dock" ;;
  esac
fi
