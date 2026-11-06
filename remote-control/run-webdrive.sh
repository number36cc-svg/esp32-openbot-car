#!/usr/bin/env zsh
# 浏览器遥控启动器：Mac / iPhone Safari 均可开车
set -e
cd "$(dirname "$0")"
exec ./.venv/bin/python webdrive.py
