#!/usr/bin/env bash
# 从官方 1.1.4 包重建 1.1.8 补丁包。
# 用法: WAIFU_ORIG=<官方包路径> ./build.sh
set -euo pipefail
: "${WAIFU_ORIG:?请通过 WAIFU_ORIG 指定官方 1.1.4 包路径}"
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$(mktemp -d)"
unzip -q "$WAIFU_ORIG" -d "$WORK"
cp "$HERE/src/ui/settings.ui.ts" "$WORK/src/ui/"
cp "$HERE/src/settings.ts"       "$WORK/src/"
cp "$HERE/manifest.json"         "$WORK/"
cd "$WORK"
zip -qr "$HERE/../../waifu-1.1.8.toolpkg" .
echo "built: $HERE/../../waifu-1.1.8.toolpkg"
