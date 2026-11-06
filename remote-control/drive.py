#!/usr/bin/env python3
"""
OpenBot 小车 · Mac 端蓝牙遥控（过渡方案，不用编译 iOS App）

用法：
    cd ~/WorkBuddy/2026-11-02-09-38-25/openbot
    ./tools/drive.py

按键（终端里按住不放 = 持续，松开约 0.5 秒自动停）：
    W  前进     S  后退     A  左转     D  右转
    空格  立即刹车
    1 2 3 4  速度档（慢 70 / 中 130 / 快 190 / 满 255）
    Q  退出（退出时自动刹车）

协议（来自 openbot.ino 源码）：
    服务 61653dc3-4021-4d1e-ba83-8b4eec61d613
    写入 06386c14-86ea-4d71-811c-48f97c58f8c9 （WRITE_NR）
    通知 9bf1103b-834c-47cf-b149-c9e4bcf778a7
    帧格式：'c' + ':' + 左 + ',' + 右 + '\\n'，取值 -255..255（左正右正 = 前进）
    心跳：'h' + ':' + 毫秒 + '\\n' —— 固件靠它做断连保护，收不到就自动停
"""

import argparse
import asyncio
import os
import select
import sys
import termios
import time
import tty

from bleak import BleakClient, BleakScanner

SERVICE_UUID = "61653dc3-4021-4d1e-ba83-8b4eec61d613"
RX_UUID = "06386c14-86ea-4d71-811c-48f97c58f8c9"
TX_UUID = "9bf1103b-834c-47cf-b149-c9e4bcf778a7"

SPEEDS = {"1": 70, "2": 130, "3": 190, "4": 255}
KEY_TTL = 0.5      # 松开按键后多久自动停（秒）
HEARTBEAT_MS = 400  # 固件超过这个时间没收到心跳就自动停车

HELP = """
┌─────────────────────────────────────────────┐
│  W 前进   S 后退   A 左转   D 右转          │
│  空格 刹车    1-4 速度档    Q 退出           │
│  提示：按住不放才会持续走，松手约 0.5 秒停   │
└─────────────────────────────────────────────┘
"""


class Keyboard:
    """cbreak 模式下的非阻塞单键读取"""

    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)

    def restore(self):
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)

    def read(self):
        chars = []
        while select.select([sys.stdin], [], [], 0)[0]:
            data = os.read(self.fd, 32).decode("utf-8", "ignore")
            if not data:
                break
            chars.extend(data)
        return chars


def control_from_keys(pressed, speed):
    """pressed: {方向: 最后一次按下的时间戳} -> (左, 右)"""
    now = time.monotonic()
    active = {k for k, t in pressed.items() if now - t < KEY_TTL}

    fwd = ("fwd" in active) - ("back" in active)
    turn = ("right" in active) - ("left" in active)

    if fwd != 0:
        base = int(fwd * speed)
        if turn > 0:                      # 右转：左轮快、右轮慢
            return base, int(base * 0.35)
        if turn < 0:                      # 左转：右轮快、左轮慢
            return int(base * 0.35), base
        return base, base

    if turn != 0:                         # 原地转：两轮反向
        return int(turn * speed), int(-turn * speed)

    return 0, 0


def describe(left, right, speed):
    if left == 0 and right == 0:
        motion = "■ 停止"
    elif left > 0 and right > 0:
        motion = "▲ 前进" if left == right else ("◀ 前进左转" if left < right else "▶ 前进右转")
    elif left < 0 and right < 0:
        motion = "▼ 后退" if left == right else ("◀ 后退左转" if left > right else "▶ 后退右转")
    else:
        motion = "◀ 原地左转" if left < 0 else "▶ 原地右转"
    return f"  {motion:<10} 左 {left:>4}  右 {right:>4}   速度档 {speed:>3}"


async def find_car(name, timeout):
    print(f"扫描 BLE 找 {name} ...（首次运行 macOS 会弹窗要蓝牙权限，点「允许」）")
    devices = await BleakScanner.discover(timeout=timeout)
    for d in devices:
        if (d.name or "") == name:
            return d
    others = [d.name for d in devices if d.name]
    if others:
        print("没找到目标。这台 Mac 扫到的设备：")
        for n in others[:12]:
            print("   ", n)
    return None


async def run(args):
    device = await find_car(args.name, args.scan_timeout)
    if device is None:
        print(f"\n找不到 {args.name}，常见原因：")
        print("  1. 车里跑的还是方向测试固件（它不广播蓝牙）")
        print("  2. 车没通电，或电源开关没打开")
        print("  3. macOS 没给终端蓝牙权限：系统设置 → 隐私与安全性 → 蓝牙 → 勾上终端/iTerm")
        return 1

    print(f"找到 {device.name} ({device.address})，连接中 ...")
    async with BleakClient(device) as client:
        if not client.is_connected:
            print("连接失败，重试一次或换个位置靠近车。")
            return 1

        try:
            await client.start_notify(
                TX_UUID, lambda _, data: print(data.decode("utf-8", "replace"), end="")
            )
        except Exception as exc:
            print(f"（日志订阅失败，不影响开车：{exc}）")

        print(HELP)
        keys = Keyboard()
        pressed = {}
        speed = args.speed
        last = None
        quit_now = False

        try:
            while not quit_now:
                now = time.monotonic()
                for ch in keys.read():
                    low = ch.lower()
                    if low == "w":
                        pressed["fwd"] = now
                    elif low == "s":
                        pressed["back"] = now
                    elif low == "a":
                        pressed["left"] = now
                    elif low == "d":
                        pressed["right"] = now
                    elif ch == " ":
                        pressed.clear()
                    elif ch in SPEEDS:
                        speed = SPEEDS[ch]
                        pressed.clear()
                        print(f"  速度档 -> {speed}")
                    elif low == "q":
                        quit_now = True

                left, right = control_from_keys(pressed, speed)
                if quit_now:
                    left = right = 0

                payload = f"c:{left},{right}\n".encode()
                await client.write_gatt_char(RX_UUID, payload, response=False)
                # 心跳不带冒号（"h400"）：旧固件用 atol(msg_buf) 解析，
                # 带冒号会解析成 0，导致控制量被立刻清零
                await client.write_gatt_char(
                    RX_UUID, f"h{HEARTBEAT_MS}\n".encode(), response=False
                )

                state = (left, right, speed)
                if state != last:
                    print(describe(left, right, speed))
                    last = state

                await asyncio.sleep(0.05)  # 20 Hz

        finally:
            keys.restore()
            for _ in range(3):
                try:
                    await client.write_gatt_char(RX_UUID, b"c:0,0\n", response=False)
                except Exception:
                    break
                await asyncio.sleep(0.05)
            print("\n已刹车，断开连接。")
    return 0


def main():
    parser = argparse.ArgumentParser(description="OpenBot 小车 Mac 蓝牙遥控")
    parser.add_argument("--name", default="OpenBotCar", help="BLE 设备名（默认 OpenBotCar）")
    parser.add_argument("--speed", type=int, default=130, help="初始速度 0-255（默认 130）")
    parser.add_argument("--scan-timeout", type=float, default=10.0, help="扫描秒数（默认 10）")
    args = parser.parse_args()
    try:
        sys.exit(asyncio.run(run(args)))
    except KeyboardInterrupt:
        print("\n中断退出")


if __name__ == "__main__":
    main()
