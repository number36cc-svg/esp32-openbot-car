#!/bin/zsh
# 一键准备编译环境：arduino-cli + ESP32 核心 + esptool 检查
# 用法：./scripts/setup-toolchain.sh
# 说明：所有工具都装在项目目录内（tools/、arduino-data/），不污染系统
set -e
cd "$(dirname "$0")/.."          # → 仓库根目录
ROOT="$PWD"

echo "────────────────────────────────────────────"
echo "  1/4  检查 arduino-cli"
echo "────────────────────────────────────────────"
if [ -x "$ROOT/tools/arduino-cli" ]; then
  echo "已存在：$("$ROOT/tools/arduino-cli" version)"
else
  mkdir -p "$ROOT/tools"
  case "$(uname -m)" in
    arm64)  ARCH="macOS_ARM64" ;;
    x86_64) ARCH="macOS_64bit" ;;
    *)      echo "未知架构：$(uname -m)，请手动下载 arduino-cli"; exit 1 ;;
  esac
  URL="https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_${ARCH}.tar.gz"
  echo "下载 $URL"
  curl -fL -o "$ROOT/tools/arduino-cli.tar.gz" "$URL"
  tar xzf "$ROOT/tools/arduino-cli.tar.gz" -C "$ROOT/tools"
  rm -f "$ROOT/tools/arduino-cli.tar.gz"
  echo "完成：$("$ROOT/tools/arduino-cli" version)"
fi

export ARDUINO_DIRECTORIES_DATA="$ROOT/arduino-data"
export ARDUINO_DIRECTORIES_DOWNLOADS="$ROOT/arduino-dl"
export ARDUINO_DIRECTORIES_USER="$ROOT/arduino-user"

echo
echo "────────────────────────────────────────────"
echo "  2/4  配置板管理器索引"
echo "────────────────────────────────────────────"
"$ROOT/tools/arduino-cli" config init --overwrite >/dev/null
"$ROOT/tools/arduino-cli" config set board_manager.additional_urls \
  https://espressif.github.io/arduino-esp32/package_esp32_index.json
"$ROOT/tools/arduino-cli" core update-index

echo
echo "────────────────────────────────────────────"
echo "  3/4  安装 ESP32 核心 2.0.17（约 1GB，请耐心）"
echo "────────────────────────────────────────────"
if "$ROOT/tools/arduino-cli" core list 2>/dev/null | grep -q "esp32:esp32.*2.0.17"; then
  echo "已安装，跳过"
else
  "$ROOT/tools/arduino-cli" core install esp32:esp32@2.0.17
fi

echo
echo "────────────────────────────────────────────"
echo "  4/4  检查 esptool"
echo "────────────────────────────────────────────"
if command -v esptool >/dev/null; then
  echo "esptool：$(esptool version 2>/dev/null | head -1)"
else
  echo "缺少 esptool，请执行：brew install esptool"
fi

echo
echo "✅ 环境就绪。下一步：./scripts/build.sh"
