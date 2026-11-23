#!/usr/bin/env bash
# thisismade CDP-2r – Installer für Ubuntu
#
#   wget -qO- https://raw.githubusercontent.com/zc7ryr6ms4-eng/thisismade-CDP-2r/main/install.sh | bash
#
# Lädt das neueste .deb-Paket von GitHub und installiert es samt aller
# Abhängigkeiten über apt. Liegt das Skript neben einer .deb-Datei oder im
# Quellordner (mit Rust/cargo), wird diese lokal verwendet bzw. gebaut.
set -euo pipefail

REPO="zc7ryr6ms4-eng/thisismade-CDP-2r"
PKG=thisismade-cdp-2r
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo .)"

if ! command -v apt-get >/dev/null; then
  echo "Dieses Skript ist für Ubuntu/Debian (apt) gedacht." >&2
  exit 1
fi
ARCH="$(dpkg --print-architecture)"

DEB="$(ls "$HERE"/${PKG}_*_"$ARCH".deb "$HERE"/dist/${PKG}_*_"$ARCH".deb 2>/dev/null | sort -V | tail -1 || true)"

if [[ -z "$DEB" && -f "$HERE/build-deb.sh" && -f "$HERE/Cargo.toml" ]] && command -v cargo >/dev/null; then
  echo "==> Baue Paket aus dem Quellordner"
  sudo apt-get install -y libgtk-4-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev
  bash "$HERE/build-deb.sh"
  DEB="$(ls "$HERE"/dist/${PKG}_*_"$ARCH".deb | sort -V | tail -1)"
fi

if [[ -z "$DEB" ]]; then
  echo "==> Suche neuestes Release auf github.com/$REPO"
  URL="$(wget -qO- "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null \
        | grep -o "\"browser_download_url\": *\"[^\"]*_${ARCH}\.deb\"" | head -1 | cut -d'"' -f4 || true)"
  if [[ -z "$URL" ]]; then
    echo "Kein fertiges Paket für $ARCH gefunden. Bitte aus dem Quellcode bauen (siehe README)." >&2
    exit 1
  fi
  DEB="$TMP/$(basename "$URL")"
  wget -q --show-progress -O "$DEB" "$URL"
fi

echo "==> Installiere $(basename "$DEB") (fragt nach deinem Passwort)"
cp "$DEB" "$TMP/pkg.deb"
chmod 644 "$TMP/pkg.deb"
sudo apt-get update -qq || true
sudo apt-get install -y "$TMP/pkg.deb"

echo
echo "Fertig! „thisismade CDP-2r“ findest du jetzt in der GNOME-Übersicht."
echo "Im Terminal: $PKG [Ordner oder Dateien]"
