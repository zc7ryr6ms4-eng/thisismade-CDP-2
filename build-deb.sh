#!/usr/bin/env bash
# Baut das Debian/Ubuntu-Paket dist/thisismade-cdp-2_<version>_all.deb
set -euo pipefail
cd "$(dirname "$0")"

VERSION="${1:-$(python3 -c 'import re;print(re.search(r"VERSION = \"([^\"]+)\"", open("tmplayer/app.py").read()).group(1))')}"
PKG=thisismade-cdp-2
APP_ID=io.github.thisismade.cdp2
ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT
chmod 755 "$ROOT"

install -d "$ROOT/DEBIAN" "$ROOT/usr/bin" "$ROOT/usr/share/$PKG/tmplayer" \
           "$ROOT/usr/share/applications" "$ROOT/usr/share/metainfo" \
           "$ROOT/usr/share/icons/hicolor/scalable/apps" "$ROOT/usr/share/doc/$PKG"

install -m644 tmplayer/*.py "$ROOT/usr/share/$PKG/tmplayer/"
install -m755 data/thisismade-cdp-2 "$ROOT/usr/bin/$PKG"
install -m644 data/$APP_ID.desktop "$ROOT/usr/share/applications/"
install -m644 data/$APP_ID.metainfo.xml "$ROOT/usr/share/metainfo/"
install -m644 data/$APP_ID.svg "$ROOT/usr/share/icons/hicolor/scalable/apps/"
install -m644 LICENSE "$ROOT/usr/share/doc/$PKG/copyright"

SIZE=$(du -sk "$ROOT/usr" | cut -f1)
cat > "$ROOT/DEBIAN/control" <<EOF
Package: $PKG
Version: $VERSION
Section: sound
Priority: optional
Architecture: all
Installed-Size: $SIZE
Maintainer: Thisismade <noreply@github.com>
Homepage: https://github.com/zc7ryr6ms4-eng/thisismade-CDP-2
Depends: python3 (>= 3.10), python3-gi, python3-gi-cairo, python3-cairo, gir1.2-gtk-4.0, gir1.2-gdkpixbuf-2.0, gir1.2-gstreamer-1.0, gstreamer1.0-plugins-base, gstreamer1.0-plugins-good
Recommends: gstreamer1.0-plugins-bad, gstreamer1.0-libav, gstreamer1.0-pipewire | gstreamer1.0-pulseaudio
Description: CD-Player-Software für GNOME
 Musikplayer, der wie ein professionelles CD-Deck funktioniert: drehende
 Disc zum Scratchen, Display mit Pegelanzeige, Tempo-Fader mit Key Lock,
 drei Memory-Cues, Shuttle-Suchlauf, direkte Titelwahl, Wiederholen und
 Zufall. Spielt Ordner, Dateien, Playlists und Audio-CDs. Integriert sich
 in die GNOME-Mediensteuerung (MPRIS).
EOF

mkdir -p dist
dpkg-deb --root-owner-group -Zxz --build "$ROOT" "dist/${PKG}_${VERSION}_all.deb"
echo "Gebaut: dist/${PKG}_${VERSION}_all.deb"
