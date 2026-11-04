#!/bin/zsh
# ob —— OpenBot 小车命令行工具
# 用法：
#   ./scripts/ob.sh status        看当前状态（串口/固件/备份/芯片/引脚）
#   ./scripts/ob.sh build         编译正式固件
#   ./scripts/ob.sh flash         烧录正式固件（自动 230400，避开 CH340 高速失败）
#   ./scripts/ob.sh test          编译并烧录「方向自动测试固件」
#   ./scripts/ob.sh monitor       串口实时日志（Ctrl+C 退出）
#   ./scripts/ob.sh backup        备份当前车上的整片固件（4MB）
#   ./scripts/ob.sh restore       烧回备份（卖家原厂网页遥控版）
#   ./scripts/ob.sh pinmap        打印引脚对照表
#
# 可用环境变量覆盖：
#   OB_PORT=/dev/cu.usbserial-XXXX   串口设备
#   PATH 里需要有 esptool（brew install esptool）
set -u
cd "$(dirname "$0")/.."          # → 仓库根目录
ROOT="$PWD"
export ARDUINO_DIRECTORIES_DATA="$ROOT/arduino-data"
export ARDUINO_DIRECTORIES_DOWNLOADS="$ROOT/arduino-dl"
export ARDUINO_DIRECTORIES_USER="$ROOT/arduino-user"
export PATH="/opt/homebrew/bin:$PATH"

PORT="${OB_PORT:-/dev/cu.usbserial-10}"
SKETCH_NAME="openbot"
BUILD="$ROOT/firmware/build-$SKETCH_NAME"
BACKUP="$ROOT/firmware-backup/original-firmware-4MB.bin"
BAUD=230400

hr() { printf '─%.0s' {1..52}; echo; }

flash_bin() {   # $1 = 产物目录
  esptool --port "$PORT" --baud "$BAUD" --before default-reset --after hard-reset \
    write-flash --flash-mode dio --flash-freq 40m --flash-size 4MB \
    0x1000 "$1/$SKETCH_NAME.ino.bootloader.bin" \
    0x8000 "$1/$SKETCH_NAME.ino.partitions.bin" \
    0x10000 "$1/$SKETCH_NAME.ino.bin"
}

case "${1:-status}" in
  status)
    hr; echo "  OpenBot 小车 · 状态"; hr
    echo "仓库      : $ROOT"
    echo "串口      : $PORT"
    [ -e "$PORT" ] && echo "            ✅ 已连接" || echo "            ❌ 没找到（USB 插了吗？）"
    if [ -f "$BUILD/openbot.ino.bin" ]; then
      SZ=$(stat -f%z "$BUILD/openbot.ino.bin")
      printf "编译产物  : %.2f MB / 上限 1.25 MB（%.0f%%）  构建于 %s\n" \
        $((SZ/1048576.0)) $((SZ*100/1310720)) "$(stat -f%Sm "$BUILD/openbot.ino.bin")"
    else
      echo "编译产物  : 还没编译过（./scripts/ob.sh build）"
    fi
    [ -f "$BACKUP" ] && echo "原厂备份  : ✅ $(du -h "$BACKUP" | cut -f1)" || echo "原厂备份  : ❌ 没有（./scripts/ob.sh backup）"
    echo
    if [ -e "$PORT" ] && command -v esptool >/dev/null; then
      echo "芯片信息  :"
      esptool --port "$PORT" flash-id 2>/dev/null | grep -E "Chip type|MAC|Detected flash" | sed 's/^/            /'
    else
      echo "芯片信息  : 跳过（串口不在或没装 esptool）"
    fi
    echo; ./scripts/ob.sh pinmap
    ;;

  build)
    hr; echo "  编译 $SKETCH_NAME"; hr
    "$ROOT/scripts/build.sh" "$SKETCH_NAME"
    ;;

  flash)
    hr; echo "  烧录到 $PORT"; hr
    echo "⚠️  确认电池开关已关（USB 与电池同时供电会伤板）"
    flash_bin "$BUILD"
    ;;

  test)
    hr; echo "  编译 + 烧录「方向自动测试固件」"; hr
    echo "⚠️  烧完后：拔 USB → 装电池 → 把车架空 → 开开关"
    "$ROOT/scripts/build.sh" moto-test
    SKETCH_NAME="moto-test"
    flash_bin "$ROOT/firmware/build-moto-test"
    ;;

  monitor)
    hr; echo "  串口监视（115200，Ctrl+C 退出）"; hr
    "$ROOT/tools/arduino-cli" monitor -p "$PORT" -c baudrate=115200
    ;;

  backup)
    hr; echo "  备份当前固件（4MB，约 3 分钟）"; hr
    mkdir -p "$(dirname "$BACKUP")"
    esptool --port "$PORT" --baud "$BAUD" read-flash 0 0x400000 "$BACKUP"
    ;;

  restore)
    hr; echo "  烧回备份（卖家原厂网页遥控版）"; hr
    [ -f "$BACKUP" ] || { echo "没有备份文件，先跑 ./scripts/ob.sh backup"; exit 1; }
    esptool --port "$PORT" --baud "$BAUD" write-flash 0x0 "$BACKUP"
    ;;

  pinmap)
    echo "引脚对照表："
    echo "  左电机  IN1=GPIO19   IN2=GPIO21   （左前+左后并联）"
    echo "  右电机  IN1=GPIO32   IN2=GPIO33   （右前+右后并联）"
    echo "  停止    = 两脚同时高（刹车）；同时低 = 滑行"
    echo "  启动死区 = 占空比 ≥75%（固件按 VOLTAGE_MIN/MAX=4.5/6.0 补偿）"
    echo "  烧录    = esptool @230400，偏移 0x1000/0x8000/0x10000"
    ;;

  *)
    sed -n '2,16p' "$0"
    ;;
esac
