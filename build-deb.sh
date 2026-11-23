#!/usr/bin/env bash
# Baut das Debian/Ubuntu-Paket dist/thisismade-cdp-2r_<version>_<arch>.deb
# Voraussetzung: cargo sowie libgtk-4-dev und libgstreamer1.0-dev
set -euo pipefail
cd "$(dirname "$0")"

VERSION="${1:-$(sed -n 's/^version = "\(.*\)"/\1/p' Cargo.toml | head -1)}"
PKG=thisismade-cdp-2r
APP_ID=io.github.thisismade.cdp2r
ARCH="$(dpkg --print-architecture)"

if [[ ! -x target/release/$PKG || "${REBUILD:-1}" == 1 ]]; then
  cargo build --release --locked 2>/dev/null || cargo build --release
fi

ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT
chmod 755 "$ROOT"

install -d "$ROOT/DEBIAN" "$ROOT/usr/bin" "$ROOT/usr/share/applications" "$ROOT/usr/share/metainfo" \
           "$ROOT/usr/share/icons/hicolor/scalable/apps" "$ROOT/usr/share/doc/$PKG"

install -m755 "target/release/$PKG" "$ROOT/usr/bin/$PKG"
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
Architecture: $ARCH
Installed-Size: $SIZE
Maintainer: Thisismade <noreply@github.com>
Homepage: https://github.com/zc7ryr6ms4-eng/thisismade-CDP-2r
Depends: libc6, libgtk-4-1 (>= 4.14), libglib2.0-0t64 | libglib2.0-0, libcairo2, libpango-1.0-0, libgdk-pixbuf-2.0-0, libgstreamer1.0-0, gstreamer1.0-plugins-base, gstreamer1.0-plugins-good
Recommends: gstreamer1.0-plugins-bad, gstreamer1.0-libav, gstreamer1.0-pipewire | gstreamer1.0-pulseaudio, fonts-inter
Description: CD-Player-Software für GNOME (Rust)
 thisismade CDP-2r ist die Rust-Fassung des thisismade cdp-2: ein
 Musikplayer, der wie ein professionelles CD-Deck funktioniert: drehende
 Disc zum Scratchen, Display mit Pegelanzeige, Tempo-Fader mit Key Lock,
 drei Memory-Cues, Shuttle-Suchlauf, direkte Titelwahl, Wiederholen und
 Zufall. Spielt Ordner, Dateien, Playlists und Audio-CDs. Integriert sich
 in die GNOME-Mediensteuerung (MPRIS).
EOF

mkdir -p dist
dpkg-deb --root-owner-group -Zxz --build "$ROOT" "dist/${PKG}_${VERSION}_${ARCH}.deb"
echo "Gebaut: dist/${PKG}_${VERSION}_${ARCH}.deb"
