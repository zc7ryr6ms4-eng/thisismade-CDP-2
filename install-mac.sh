#!/usr/bin/env bash
# thisismade cdp-2 – Installer für macOS
#
#   curl -fsSL https://raw.githubusercontent.com/zc7ryr6ms4-eng/thisismade-CDP-2/main/install-mac.sh | bash
#
# Lädt die neueste fertige App (DMG) von GitHub, kopiert sie nach /Programme und
# startet sie. Gibt es noch kein Release, wird die App aus dem Quellcode gebaut
# (dafür werden die Xcode Command Line Tools benötigt).
set -euo pipefail
REPO="zc7ryr6ms4-eng/thisismade-CDP-2"
NAME="thisismade cdp-2"
TMP="$(mktemp -d)"
trap 'hdiutil detach "$TMP/mnt" -quiet 2>/dev/null || true; rm -rf "$TMP"' EXIT

URL="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null \
      | grep -o '"browser_download_url": *"[^"]*\.dmg"' | head -1 | cut -d'"' -f4 || true)"

if [[ -n "$URL" ]]; then
  echo "==> Lade $(basename "$URL")"
  curl -fL --progress-bar -o "$TMP/app.dmg" "$URL"
  mkdir "$TMP/mnt"
  hdiutil attach "$TMP/app.dmg" -nobrowse -quiet -mountpoint "$TMP/mnt"
  rm -rf "/Applications/$NAME.app"
  cp -R "$TMP/mnt/$NAME.app" /Applications/
else
  echo "==> Kein fertiges Release gefunden – baue aus dem Quellcode"
  if ! xcrun --find swiftc >/dev/null 2>&1; then
    echo "Bitte zuerst die Xcode Command Line Tools installieren:  xcode-select --install" >&2
    echo "und dieses Skript danach erneut ausführen." >&2
    exit 1
  fi
  curl -fsSL "https://github.com/$REPO/archive/refs/heads/main.tar.gz" | tar xz -C "$TMP"
  bash "$TMP"/thisismade-CDP-2-main/macos/build.sh
  rm -rf "/Applications/$NAME.app"
  cp -R "$TMP/thisismade-CDP-2-main/macos/build/$NAME.app" /Applications/
fi

xattr -dr com.apple.quarantine "/Applications/$NAME.app" 2>/dev/null || true
echo "==> Installiert: /Programme/$NAME"
open "/Applications/$NAME.app"
