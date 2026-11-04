#!/bin/zsh
# 编译 OpenBot 固件（本地车型：ESP32 网页遥控 WIFI 小车 差分转向版）
# 用法：./scripts/build.sh [sketch目录名]
#   默认编译 firmware/openbot；传参可编译其它 sketch，例如：
#   ./scripts/build.sh moto-test
set -e
cd "$(dirname "$0")/.."          # → 仓库根目录
ROOT="$PWD"

SKETCH_NAME="${1:-openbot}"
SKETCH="$ROOT/firmware/$SKETCH_NAME"
[ -d "$SKETCH" ] || { echo "找不到 sketch：$SKETCH"; exit 1; }
[ -x "$ROOT/tools/arduino-cli" ] || { echo "缺少 arduino-cli，先跑 ./scripts/setup-toolchain.sh"; exit 1; }

export ARDUINO_DIRECTORIES_DATA="$ROOT/arduino-data"
export ARDUINO_DIRECTORIES_DOWNLOADS="$ROOT/arduino-dl"
export ARDUINO_DIRECTORIES_USER="$ROOT/arduino-user"

"$ROOT/tools/arduino-cli" compile \
  --fqbn esp32:esp32:esp32 \
  --build-path "$ROOT/firmware/.build-$SKETCH_NAME" \
  --output-dir "$ROOT/firmware/build-$SKETCH_NAME" \
  "$SKETCH"

echo "--- 产物（firmware/build-$SKETCH_NAME）---"
ls -lh "$ROOT/firmware/build-$SKETCH_NAME"
