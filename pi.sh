#!/usr/bin/env bash
# APRS & Packet as a station server on a Raspberry Pi (Pi 3B or newer, Raspberry Pi OS Bookworm or newer).
#
#   curl -fsSL https://raw.githubusercontent.com/michalsiman/aprs-kiss-app/main/packaging/raspberry/install.sh | bash
#
# Run it as the Pi's normal user (it asks for sudo where needed); run it again to update.
# The Pi's screen shows the whole app on the whole screen, by touch; the web has it too.
#   --dashboard    the screen shows only a dashboard (lamps, counters, last frames) instead of the app
#   --no-display   nothing on a screen (a Pi with no display: only the web)
#   --touch-5inch  the touch of the cheap 5" HDMI displays (Waveshare 5inch HDMI LCD and its clones:
#                  800×480, a resistive XPT2046 touch on the GPIO pins, a stylus)
#   --port N       the web port (default 8080)
#   --version vX.Y.Z   a given release instead of the newest
#   --beta         the newest beta too (otherwise the newest stable release)
set -euo pipefail

# all in a function: with `curl … | bash` the whole script is read before anything runs (apt or pip reading
# the standard input cannot eat the rest of it)
main() {

REPO=michalsiman/aprs-kiss-app
PREFIX=/opt/aprs-kiss
PORT=8080
DISPLAY_ON=1
PAGE=""
TOUCH5=0
BETA=0
TAG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --no-display) DISPLAY_ON=0 ;;
    --dashboard) PAGE="display" ;;
    --touch-5inch) TOUCH5=1 ;;
    --beta) BETA=1 ;;
    --port) PORT="$2"; shift ;;
    --version) TAG="$2"; shift ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done
[ "$(id -u)" -ne 0 ] || { echo "Run it as your normal user, not as root (it uses sudo itself)." >&2; exit 1; }
USER_NAME=$(id -un)
say() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }

say "System packages"
sudo apt-get update -qq
PKGS="python3-venv python3-pip python3 curl"
if [ "$DISPLAY_ON" = 1 ]; then
  if apt-cache show chromium >/dev/null 2>&1; then PKGS="$PKGS chromium"; else PKGS="$PKGS chromium-browser"; fi
  # a keyboard on the screen when a text field is tapped (Wayland: labwc, wayfire)
  apt-cache show squeekboard >/dev/null 2>&1 && PKGS="$PKGS squeekboard"
fi
sudo apt-get install -y -qq $PKGS
# a TNC on USB (serial), a sound card for Direwolf
sudo usermod -aG dialout,audio,plugdev "$USER_NAME" || true

say "The app"
sudo mkdir -p "$PREFIX"
sudo chown "$USER_NAME": "$PREFIX"
[ -x "$PREFIX/venv/bin/python" ] || python3 -m venv "$PREFIX/venv"
"$PREFIX/venv/bin/pip" install -q --upgrade pip
# the newest stable release with a wheel (Python package); a beta when no stable one has it yet, or with --beta
WHEEL=$(curl -fsSL "https://api.github.com/repos/$REPO/releases?per_page=30" | python3 -c '
import json, sys
tag, beta = sys.argv[1], sys.argv[2] == "1"
releases = [r for r in json.load(sys.stdin) if not r.get("draft")]
def wheel(r):
    return next((a["browser_download_url"] for a in r.get("assets", []) if a["name"].endswith(".whl")), "")
pick = [r for r in releases if r["tag_name"] == tag] if tag else (
    [r for r in releases if wheel(r) and (beta or not r.get("prerelease"))] or [r for r in releases if wheel(r)])
print(wheel(pick[0]) if pick else "")
' "$TAG" "$BETA")
[ -n "$WHEEL" ] || { echo "No release with the Raspberry Pi package (.whl) found${TAG:+ for $TAG}." >&2; exit 1; }
SRC="aprs-kiss[server] @ $WHEEL"
echo "Installing $SRC"
"$PREFIX/venv/bin/pip" install -q --upgrade "$SRC"

HAS_PW=$("$PREFIX/venv/bin/python" -c "from aprs_kiss_app.server import load_password; from aprs_kiss_core.config import data_dir; print(1 if load_password(data_dir()) else 0)")
if [ "$HAS_PW" = 0 ] && [ -r /dev/tty ]; then
  say "A password for the web (the web can transmit: set one; Enter = none)"
  "$PREFIX/venv/bin/aprs-kiss-server" --set-password </dev/tty || true
fi

say "The service (runs at boot, restarts by itself)"
sudo tee /etc/systemd/system/aprs-kiss.service >/dev/null <<UNIT
[Unit]
Description=APRS & Packet station server
After=network-online.target
Wants=network-online.target

[Service]
User=$USER_NAME
ExecStart=$PREFIX/venv/bin/aprs-kiss-server --port $PORT
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
Environment=APRS_KISS_WEB_URL=http://$(hostname).local:$PORT

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable aprs-kiss.service >/dev/null
sudo systemctl restart aprs-kiss.service

if [ "$TOUCH5" = 1 ]; then
  say "Touch of the 5\" HDMI display (XPT2046 on the GPIO pins)"
  CFG=/boot/firmware/config.txt
  [ -f "$CFG" ] || CFG=/boot/config.txt
  if ! grep -q "aprs-kiss: 5inch HDMI touch" "$CFG"; then
    sudo tee -a "$CFG" >/dev/null <<'TOUCH'

# aprs-kiss: 5inch HDMI touch display (Waveshare 5inch HDMI LCD and clones), 800x480
hdmi_group=2
hdmi_mode=87
hdmi_cvt 800 480 60 6 0 0 0
hdmi_drive=1
dtparam=spi=on
dtoverlay=ads7846,cs=1,penirq=25,penirq_pull=2,speed=50000,keep_vref_on=0,swapxy=0,pmax=255,xohms=150,xmin=200,xmax=3900,ymin=200,ymax=3900
TOUCH
  fi
fi

if [ "$DISPLAY_ON" = 1 ]; then
  say "The display (a kiosk browser after the desktop starts)"
  BROWSER=$(command -v chromium || command -v chromium-browser)
  cat > "$PREFIX/kiosk.sh" <<KIOSK
#!/bin/sh
# waits for the server, then shows the app (or its dashboard) on the whole screen
until curl -fs -o /dev/null http://127.0.0.1:$PORT/; do sleep 2; done
IME=""
[ -n "\$WAYLAND_DISPLAY" ] && IME="--enable-wayland-ime"  # the on-screen keyboard pops up in text fields
exec $BROWSER --kiosk --noerrdialogs --disable-infobars --no-first-run --password-store=basic \\
  --disable-translate --disable-pinch --overscroll-history-navigation=0 --check-for-update-interval=31536000 \\
  --ozone-platform-hint=auto \$IME http://127.0.0.1:$PORT/$PAGE
KIOSK
  chmod +x "$PREFIX/kiosk.sh"
  # labwc (Raspberry Pi OS from late 2024), wayfire (2023–2024) and LXDE/X11 (older, XDG autostart)
  mkdir -p "$HOME/.config/labwc" "$HOME/.config/autostart"
  touch "$HOME/.config/labwc/autostart"
  grep -q "aprs-kiss/kiosk.sh" "$HOME/.config/labwc/autostart" || echo "$PREFIX/kiosk.sh &" >> "$HOME/.config/labwc/autostart"
  if [ -f "$HOME/.config/wayfire.ini" ] && ! grep -q "aprs-kiss/kiosk.sh" "$HOME/.config/wayfire.ini"; then
    grep -q "^\[autostart\]" "$HOME/.config/wayfire.ini" || printf '\n[autostart]\n' >> "$HOME/.config/wayfire.ini"
    sed -i "/^\[autostart\]/a aprs_kiss = $PREFIX/kiosk.sh" "$HOME/.config/wayfire.ini"
  fi
  cat > "$HOME/.config/autostart/aprs-kiss-display.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=APRS & Packet display
Exec=$PREFIX/kiosk.sh
X-GNOME-Autostart-enabled=true
DESKTOP
  if command -v raspi-config >/dev/null; then
    sudo raspi-config nonint do_boot_behaviour B4 || true  # the desktop, logged in by itself
    sudo raspi-config nonint do_blanking 1 || true  # the screen never goes dark
  fi
fi

ADDR=$(hostname -I 2>/dev/null | awk '{print $1}')
say "Done"
cat <<END
The station server runs: http://$(hostname).local:$PORT  or  http://${ADDR:-<the Pi's address>}:$PORT
(open it on a phone or a computer in the same network and set everything there)
Dashboard: http://${ADDR:-localhost}:$PORT/display
$( [ "$DISPLAY_ON" = 1 ] && echo "The Pi's screen shows the $( [ -n "$PAGE" ] && echo dashboard || echo app ) after a restart: sudo reboot")

Change the web password: $PREFIX/venv/bin/aprs-kiss-server --set-password && sudo systemctl restart aprs-kiss

The log:      journalctl -u aprs-kiss -f
Update:       run this script again
Stop / start: sudo systemctl stop aprs-kiss / sudo systemctl start aprs-kiss
END
}

main "$@"
