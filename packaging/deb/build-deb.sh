#!/bin/sh
# Make a Debian/Ubuntu/Mint package from the `flet build linux` output.
# Usage: packaging/deb/build-deb.sh BUILD_DIR VERSION OUT_DIR
set -eu
BUILD=$1
VERSION=$2
OUT=$3
ID=io.github.michalsiman.aprs_kiss_app
HERE=$(cd "$(dirname "$0")/.." && pwd)
ROOT=$(mktemp -d)
trap 'rm -rf "$ROOT"' EXIT

mkdir -p "$ROOT/opt/aprs-kiss" "$ROOT/usr/bin" "$ROOT/DEBIAN"
cp -a "$BUILD/." "$ROOT/opt/aprs-kiss/"
cat > "$ROOT/usr/bin/aprs-kiss" <<'SH'
#!/bin/sh
exec /opt/aprs-kiss/aprs-kiss "$@"
SH
chmod 755 "$ROOT/usr/bin/aprs-kiss"
install -Dm644 "$HERE/linux/$ID.desktop" "$ROOT/usr/share/applications/$ID.desktop"
install -Dm644 "$HERE/linux/$ID.metainfo.xml" "$ROOT/usr/share/metainfo/$ID.metainfo.xml"
install -Dm644 "$HERE/linux/icons/scalable.svg" "$ROOT/usr/share/icons/hicolor/scalable/apps/$ID.svg"
for s in 64 128 256 512; do
  install -Dm644 "$HERE/linux/icons/$s.png" "$ROOT/usr/share/icons/hicolor/${s}x${s}/apps/$ID.png"
done

SIZE=$(du -sk "$ROOT" | cut -f1)
cat > "$ROOT/DEBIAN/control" <<CTRL
Package: aprs-kiss
Version: $VERSION
Architecture: amd64
Maintainer: Michal Šiman (OK1SIM) <michalsiman@users.noreply.github.com>
Installed-Size: $SIZE
Depends: libc6 (>= 2.34), libgtk-3-0t64 | libgtk-3-0, libstdc++6, libepoxy0, libgstreamer1.0-0, libgstreamer-plugins-base1.0-0
Recommends: gstreamer1.0-plugins-good
Section: hamradio
Priority: optional
Homepage: https://github.com/michalsiman/aprs-kiss-app
Description: APRS station and packet radio terminal for a KISS TNC
 Turns a radio with a KISS TNC (Quansheng UV-K5 with F4HWN, Direwolf, a hardware
 TNC) into an APRS station and a packet radio terminal: map of stations heard,
 APRS messages with acknowledgement, a terminal for BBSes and nodes, packet chat,
 a frame monitor and APRS-IS with an optional iGate.
 .
 For a serial TNC your user needs to be in the dialout group.
CTRL
mkdir -p "$OUT"
dpkg-deb --root-owner-group --build "$ROOT" "$OUT/aprs-kiss_${VERSION}_amd64.deb"
