#!/usr/bin/env python3
"""
OpenBot 小车 · 浏览器遥控（Mac / iPhone Safari 都能开）

用法：
    cd ~/WorkBuddy/2026-11-02-09-38-25/openbot
    ./tools/run-webdrive.sh
    然后浏览器打开打印出来的地址（Mac 或 iPhone 同一 WiFi）。

操作：
    键盘 W/S/A/D（支持任意组合同时按住，浏览器有 keyup 事件）
    或 拖动虚拟摇杆（模拟量，转弯更细腻）
    空格 / 点击"停止" 急停

协议与 drive.py 相同：
    'c:左,右\\n' 控制（-255..255），'h400\\n' 心跳（不带冒号，见 drive.py 注释）
"""

import asyncio
import json
import socket
import subprocess

from aiohttp import web, WSMsgType
from bleak import BleakClient, BleakScanner

SERVICE_UUID = "61653dc3-4021-4d1e-ba83-8b4eec61d613"
RX_UUID = "06386c14-86ea-4d71-811c-48f97c58f8c9"
TX_UUID = "9bf1103b-834c-47cf-b149-c9e4bcf778a7"

HEARTBEAT_MS = 400
CAR_NAME = "OpenBotCar"
PORT = 8765

# ---------------------------------------------------------------- 控制计算

class InputState:
    """键盘按键集合 + 摇杆位置（模拟量 -1..1，y 向前为正）"""

    def __init__(self):
        self.keys = set()
        self.stick = None  # (x, y) 或 None

    def control(self):
        """返回 (左, 右)，-255..255"""
        if self.stick is not None:
            x, y = self.stick
            left = y + x
            right = y - x
            m = max(abs(left), abs(right))
            if m > 1.0:  # 对角超界时等比缩回，保持差速比例
                left /= m
                right /= m
            return int(left * 255), int(right * 255)

        fwd = ("w" in self.keys) - ("s" in self.keys)
        turn = ("d" in self.keys) - ("a" in self.keys)
        if fwd == 0 and turn == 0:
            return 0, 0
        if fwd == 0:  # 原地转
            return int(turn * 200), int(-turn * 200)
        base = fwd * 170
        if turn > 0:   # 右转：左快右慢
            return base, int(base * 0.3)
        if turn < 0:   # 左转
            return int(base * 0.3), base
        return base, base


state = InputState()
ble_client: BleakClient | None = None
ble_status = "connecting"


def describe(left, right):
    if left == 0 and right == 0:
        return "■ 停止"
    if left > 0 and right > 0:
        if left == right:
            return "▲ 前进"
        return "◀ 前进左转" if left < right else "▶ 前进右转"
    if left < 0 and right < 0:
        if left == right:
            return "▼ 后退"
        return "◀ 后退左转" if left > right else "▶ 后退右转"
    return "◀ 原地左转" if left < 0 else "▶ 原地右转"


# ---------------------------------------------------------------- BLE

async def find_car():
    print(f"扫描 BLE 找 {CAR_NAME} ...（首次运行要点「允许」蓝牙权限）")
    devices = await BleakScanner.discover(timeout=10.0)
    for d in devices:
        if (d.name or "") == CAR_NAME:
            return d
    return None


async def ble_loop():
    """连接小车并按 20Hz 下发控制；断线自动重连"""
    global ble_client, ble_status
    while True:
        device = await find_car()
        if device is None:
            ble_status = "car-not-found"
            print("没找到 OpenBotCar，5 秒后重试（确认车通电、在附近）")
            await asyncio.sleep(5)
            continue
        try:
            async with BleakClient(device) as client:
                ble_client = client
                ble_status = "connected"
                print(f"已连接 {device.address}")
                try:
                    await client.start_notify(
                        TX_UUID, lambda _, data: None
                    )
                except Exception:
                    pass
                last = None
                while client.is_connected:
                    left, right = state.control()
                    payload = f"c:{left},{right}\n".encode()
                    await client.write_gatt_char(RX_UUID, payload, response=False)
                    await client.write_gatt_char(
                        RX_UUID, f"h{HEARTBEAT_MS}\n".encode(), response=False
                    )
                    if (left, right) != last:
                        print(f"  {describe(left, right):<12} 左 {left:>4} 右 {right:>4}")
                        last = (left, right)
                    await asyncio.sleep(0.05)
        except Exception as exc:
            print(f"BLE 异常：{exc}")
        ble_client = None
        ble_status = "disconnected"
        state.keys.clear()
        state.stick = None
        print("连接断开，2 秒后重连 ...")
        await asyncio.sleep(2)


# ---------------------------------------------------------------- Web

PAGE = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>OpenBot 遥控</title>
<style>
  :root { color-scheme: dark; }
  * { margin:0; padding:0; touch-action:none; -webkit-user-select:none; user-select:none; }
  body { background:#111; color:#eee; font-family:-apple-system,sans-serif;
         display:flex; flex-direction:column; align-items:center; min-height:100vh; }
  h1 { font-size:18px; margin:14px 0 4px; }
  #status { font-size:13px; padding:3px 12px; border-radius:12px; margin-bottom:8px; }
  #status.ok { background:#1b4332; color:#7ee2a8; }
  #status.bad { background:#4a1b1b; color:#ff9a9a; }
  #stick { width:min(70vw,300px); height:min(70vw,300px); border-radius:50%;
           background:radial-gradient(circle,#1c1c1e 60%,#2a2a2e); position:relative;
           border:1px solid #333; margin:8px 0; }
  #knob { width:38%; height:38%; border-radius:50%; background:#3a86ff; opacity:.85;
          position:absolute; left:31%; top:31%; box-shadow:0 2px 10px #0008; }
  #keys { display:grid; grid-template-columns:repeat(3,64px); gap:8px; margin:10px 0; }
  .k { width:64px; height:52px; border-radius:10px; background:#26262a; color:#ddd;
       display:flex; align-items:center; justify-content:center; font-size:20px; }
  .k.on { background:#3a86ff; color:#fff; }
  .k.stop { background:#5c1f1f; color:#ffb3b3; font-size:15px; }
  p { color:#888; font-size:12px; margin:6px 12px; text-align:center; }
</style>
</head>
<body>
<h1>🚗 OpenBot 遥控</h1>
<div id="status" class="bad">连接中…</div>
<div id="stick"><div id="knob"></div></div>
<div id="keys">
  <div class="k" data-k="a">A</div><div class="k" data-k="w">W</div><div class="k" data-k="d">D</div>
  <div class="k stop" data-k="stop">停止</div><div class="k" data-k="s">S</div><div class="k" data-k="x"></div>
</div>
<p>拖动摇杆（模拟量）或按 W/S/A/D —— 支持同时按住多个键画弧线；点「停止」或松开摇杆即停。</p>
<script>
const wsStatus = document.getElementById('status');
const stick = document.getElementById('stick'), knob = document.getElementById('knob');
let ws, stickActive = false;

function setKeysUI(keys) {
  document.querySelectorAll('.k[data-k]').forEach(el => {
    el.classList.toggle('on', keys.has(el.dataset.k));
  });
}

function connect() {
  ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onopen = () => { wsStatus.textContent = '已连接小车'; wsStatus.className = 'ok'; };
  ws.onclose = () => { wsStatus.textContent = '服务器断开，刷新页面重试'; wsStatus.className = 'bad'; };
  ws.onerror = () => {};
}
connect();

function send(obj) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(obj)); }

// ---- 键盘（有真正的 keyup，支持组合键）----
const keys = new Set();
addEventListener('keydown', e => {
  const k = e.key.toLowerCase();
  if ('wasd'.includes(k) && !keys.has(k)) { keys.add(k); send({t:'keys', keys:[...keys]}); setKeysUI(keys); e.preventDefault(); }
  if (k === ' ') { keys.clear(); send({t:'keys', keys:[]}); setKeysUI(keys); e.preventDefault(); }
});
addEventListener('keyup', e => {
  const k = e.key.toLowerCase();
  if (keys.delete(k)) { send({t:'keys', keys:[...keys]}); setKeysUI(keys); }
});

// ---- 触屏按钮 ----
document.querySelectorAll('.k[data-k]').forEach(el => {
  const k = el.dataset.k;
  if (k === 'stop') {
    el.addEventListener('pointerdown', () => { keys.clear(); stickActive = false; send({t:'stick', x:0, y:0}); send({t:'keys', keys:[]}); setKeysUI(keys); });
    return;
  }
  el.addEventListener('pointerdown', e => { keys.add(k); send({t:'keys', keys:[...keys]}); setKeysUI(keys); e.preventDefault(); });
  el.addEventListener('pointerup',   () => { keys.delete(k); send({t:'keys', keys:[...keys]}); setKeysUI(keys); });
  el.addEventListener('pointerleave',() => { if (keys.delete(k)) { send({t:'keys', keys:[...keys]}); setKeysUI(keys); } });
});

// ---- 摇杆 ----
function stickMove(e) {
  const r = stick.getBoundingClientRect();
  let dx = (e.clientX - (r.left + r.width/2)) / (r.width/2);
  let dy = (e.clientY - (r.top + r.height/2)) / (r.height/2);
  const m = Math.hypot(dx, dy);
  if (m > 1) { dx /= m; dy /= m; }
  knob.style.left = (31 + dx*31) + '%';
  knob.style.top  = (31 + dy*31) + '%';
  send({t:'stick', x:+dx.toFixed(3), y:+(-dy).toFixed(3)});  // 屏幕向上 = 前进
}
stick.addEventListener('pointerdown', e => { stickActive = true; stick.setPointerCapture(e.pointerId); stickMove(e); });
stick.addEventListener('pointermove', e => { if (stickActive) stickMove(e); });
['pointerup','pointercancel'].forEach(ev => stick.addEventListener(ev, () => {
  stickActive = false;
  knob.style.left = '31%'; knob.style.top = '31%';
  send({t:'stick', x:0, y:0});
}));
</script>
</body>
</html>"""


async def ws_handler(request):
    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)
    await ws.send_json({"t": "status", "s": ble_status})
    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)
            except ValueError:
                continue
            if data.get("t") == "keys":
                state.keys = set(data.get("keys", []))
            elif data.get("t") == "stick":
                x, y = data.get("x", 0), data.get("y", 0)
                state.stick = (x, y) if (abs(x) > 0.05 or abs(y) > 0.05) else None
    return ws


async def index(_):
    return web.Response(text=PAGE, content_type="text/html")


def lan_ip():
    """拿真实局域网 IP；198.18.x.x 是代理 TUN 的假 IP，要排除"""
    for iface in ("en0", "en1", "en2", "en3"):
        try:
            ip = subprocess.check_output(
                ["ipconfig", "getifaddr", iface], text=True
            ).strip()
            if ip and not ip.startswith(("198.18.", "169.254.")):
                return ip
        except subprocess.CalledProcessError:
            continue
    return "127.0.0.1"


async def main():
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/ws", ws_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"\n遥控页面已就绪，两个地址任选：")
    print(f"  Mac 本机打开   →  http://localhost:{PORT}/   （localhost 永远不走代理）")
    print(f"  iPhone 同WiFi  →  http://{lan_ip()}:{PORT}/")
    print("\n⚠️ iPhone 打不开的话：检查 Mac 的代理软件（Clash 等）是否允许局域网连接\n")
    await ble_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n退出")
