#!/bin/zsh
# 启动 Mac 端蓝牙遥控：首次运行会自动建虚拟环境并装 bleak
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "首次运行，准备依赖（约 30 秒）..."
  python3 -m venv .venv
  ./.venv/bin/pip -q install --upgrade pip
  ./.venv/bin/pip -q install bleak
fi
exec ./.venv/bin/python drive.py "$@"
