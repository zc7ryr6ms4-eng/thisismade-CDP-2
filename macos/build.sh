#!/usr/bin/env bash
# Baut "thisismade cdp-2.app" (Universal: Apple Silicon + Intel).
#   ./build.sh            → build/thisismade cdp-2.app
#   ./build.sh --dmg      → zusätzlich build/thisismade-cdp-2.dmg
#   ./build.sh --install  → nach /Programme installieren und starten
# Benötigt nur die Xcode Command Line Tools (xcode-select --install).
set -euo pipefail
cd "$(dirname "$0")"

NAME="thisismade cdp-2"
EXE="thisismade-cdp-2"
APP="build/$NAME.app"
MIN_OS="13.0"

if ! xcrun --find swiftc >/dev/null 2>&1; then
  echo "Swift fehlt. Installiere die Xcode Command Line Tools mit:  xcode-select --install" >&2
  exit 1
fi
SDK="$(xcrun --sdk macosx --show-sdk-path)"

rm -rf build
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources" build/obj

for ARCH in arm64 x86_64; do
  echo "==> Kompiliere für $ARCH"
  xcrun swiftc -O -swift-version 5 -sdk "$SDK" -target "$ARCH-apple-macos$MIN_OS" \
    -framework AppKit -framework AVFoundation -framework MediaPlayer \
    Sources/*.swift -o "build/obj/$EXE-$ARCH"
done
lipo -create "build/obj/$EXE-arm64" "build/obj/$EXE-x86_64" -output "$APP/Contents/MacOS/$EXE"

cp Info.plist "$APP/Contents/Info.plist"
iconutil -c icns AppIcon.iconset -o "$APP/Contents/Resources/AppIcon.icns"
printf 'APPL????' > "$APP/Contents/PkgInfo"
codesign --force --deep --sign - "$APP"
echo "==> Fertig: $APP"

if [[ "${1:-}" == "--dmg" ]]; then
  rm -rf build/dmg && mkdir build/dmg
  cp -R "$APP" build/dmg/
  ln -s /Applications build/dmg/Programme
  hdiutil create -volname "$NAME" -srcfolder build/dmg -ov -format UDZO "build/$EXE.dmg"
  echo "==> DMG: build/$EXE.dmg"
fi

if [[ "${1:-}" == "--install" ]]; then
  rm -rf "/Applications/$NAME.app"
  cp -R "$APP" /Applications/
  xattr -dr com.apple.quarantine "/Applications/$NAME.app" 2>/dev/null || true
  echo "==> Installiert in /Programme"
  open "/Applications/$NAME.app"
fi
