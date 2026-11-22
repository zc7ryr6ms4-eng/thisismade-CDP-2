#!/usr/bin/env bash
# thisismade cdp-2 – Installer für Ubuntu
#
#   wget -qO- https://raw.githubusercontent.com/zc7ryr6ms4-eng/thisismade-CDP-2/main/install.sh | bash
#
# Lädt das neueste .deb-Paket von GitHub und installiert es samt aller
# Abhängigkeiten über apt. Liegt das Skript neben einer .deb-Datei oder im
# Quellordner, wird diese lokal verwendet.
set -euo pipefail

REPO="zc7ryr6ms4-eng/thisismade-CDP-2"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo .)"

if ! command -v apt-get >/dev/null; then
  echo "Dieses Skript ist für Ubuntu/Debian (apt) gedacht." >&2
  exit 1
fi

DEB="$(ls "$HERE"/thisismade-cdp-2_*_all.deb "$HERE"/dist/thisismade-cdp-2_*_all.deb 2>/dev/null | sort -V | tail -1 || true)"

if [[ -z "$DEB" && -f "$HERE/build-deb.sh" ]]; then
  echo "==> Baue Paket aus dem Quellordner"
  bash "$HERE/build-deb.sh"
  DEB="$(ls "$HERE"/dist/thisismade-cdp-2_*_all.deb | sort -V | tail -1)"
fi

if [[ -z "$DEB" ]]; then
  echo "==> Lade neueste Version von github.com/$REPO"
  URL="$(wget -qO- "https://api.github.com/repos/$REPO/releases/latest" \
        | grep -o '"browser_download_url": *"[^"]*_all\.deb"' | head -1 | cut -d'"' -f4)"
  if [[ -z "$URL" ]]; then
    echo "Kein Release gefunden." >&2
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
echo "Fertig! „thisismade cdp-2“ findest du jetzt in der GNOME-Übersicht."
echo "Im Terminal: thisismade-cdp-2 [Ordner oder Dateien]"
