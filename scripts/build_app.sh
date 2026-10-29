#!/usr/bin/env bash
# Builds dist/ACE-Vision-<version>.zip (ad-hoc signed, arm64) with a pinned uv bundled.
set -euo pipefail

[ $# -eq 1 ] || { echo "usage: $0 <version>   (e.g. 0.2.0)" >&2; exit 2; }
VERSION="$1"

UV_VERSION="0.13.1"
UV_SHA256="cfe454573412ff7380d15fc7dae5997ab53ffce72fce0a78e91ddbc84001acd2"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
ARCHIVE="uv-aarch64-apple-darwin.tar.gz"
curl -fsSL -o "$TMP/$ARCHIVE" "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/$ARCHIVE"
echo "$UV_SHA256  $TMP/$ARCHIVE" | shasum -a 256 -c - >/dev/null || { echo "uv checksum mismatch" >&2; exit 1; }
tar -xzf "$TMP/$ARCHIVE" -C "$TMP" "uv-aarch64-apple-darwin/uv"
mkdir -p app/build/bin
cp "$TMP/uv-aarch64-apple-darwin/uv" app/build/bin/uv
chmod +x app/build/bin/uv

xcodegen generate --spec app/project.yml
xcodebuild -project app/ACEVision.xcodeproj -scheme ACEVision -configuration Release \
  -derivedDataPath app/build/DerivedData \
  CODE_SIGN_IDENTITY=- MARKETING_VERSION="$VERSION" build

BUILT="app/build/DerivedData/Build/Products/Release/ACEVision.app"
[ -d "$BUILT" ] || { echo "app not found: $BUILT" >&2; exit 1; }
# The user-facing bundle name has a space; the Xcode product is ACEVision.
mkdir "$TMP/stage"
ditto "$BUILT" "$TMP/stage/ACE Vision.app"
mkdir -p dist
rm -f "dist/ACE-Vision-$VERSION.zip"
ditto -c -k --keepParent "$TMP/stage/ACE Vision.app" "dist/ACE-Vision-$VERSION.zip"
echo "dist/ACE-Vision-$VERSION.zip"
