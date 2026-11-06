# esp32-openbot-car · 把一台 ¥84 的 ESP32 玩具车，改成 iPhone 驱动的 AI 机器人

> 一辆淘宝 ¥83.69 的「ESP32 网页遥控 WiFi 小车」套件，刷上 [OpenBot](https://github.com/ob-f/OpenBot) 固件，
> 用 iPhone 当大脑（摄像头 + 神经网络 + BLE）、ESP32 当小脑（电机 + 传感器）、Mac 当训练中心。
>
> 目标不是"做个遥控车"，而是**亲手走一遍具身智能的完整链路**：
> `视觉感知 → 决策 → 执行 → 数据采集 → 模型训练 → 端侧部署`。
>
> 本仓库记录的是**从拆快递到跑通 AI 的全过程**：源码、接线、刷机脚本、踩过的坑，以及每个技术选择的"为什么"。

![status](https://img.shields.io/badge/固件-已刷入%20%C2%B7%20BLE%20已广播-success)
![status](https://img.shields.io/badge/首次BLE驾驶-成功-success)
![status](https://img.shields.io/badge/浏览器遥控-上线%20%C2%B7%20摇杆%2B组合键-success)
![status](https://img.shields.io/badge/iOS%20App-Xcode%20下载中-yellow)
![license](https://img.shields.io/badge/license-MIT-blue)

🌐 **在线入口（手机可直接看）**：https://number36cc-svg.github.io/esp32-openbot-car/
— 项目控制台 / 四周计划 / 踩坑记录，一页跳转。

---

## 1. 这台车是什么

淘宝整车套件 **「ESP32 网页遥控 WIFI 小车 差分转向版」，¥83.69**。卖家卖的是"手机浏览器遥控车"，我们只要它的**硬件底座**，固件整块换掉。

| 项 | 实车规格（实测，非商品页文案） |
|---|---|
| 主控 | **ESP32-D0WD-V3** 双核 240MHz / 4MB Flash / MAC `d4:d4:da:6c:48:7c` |
| 电机驱动 | **MX1508 × 2**（双 H 桥 × 2，四路输出） |
| 底盘 | 四轮直驱 **差速转向**（左右各 2 个 TT 马达并联，无舵机） |
| 供电 | 4 × 5 号电池 → 板载**升压到 6V**（供电机）+ **降压到 3.3V**（供 ESP32） |
| 尺寸 | 27 × 15 × 8 cm |
| 编码器 / 超声波 / 电量检测 / 摄像头 / LED | **全部没有**（板子上就没有这些电路） |
| 串口 | CH340（macOS 免驱，识别为 `/dev/cu.usbserial-*`） |

**为什么是这台**：它把电机、驱动、电源、底盘全部焊好装好了，到手只剩"刷固件 + 核方向"两件事。对第一次做机器人的人，省掉的是最容易劝退的那半天焊接和接线。

## 2. 系统架构

```
        ┌──────────────────────────────┐
        │  iPhone 16（大脑 + 眼睛）      │   OpenBot iOS App
        │  摄像头 1280×720 → 300×300    │   · 目标检测 / 人物跟随
        │  MobileNetV3-SSD (TFLite)     │   · 端到端驾驶策略
        │  控制器（居中 / 差速换算）      │   · 数据采集与上传
        └──────────────┬───────────────┘
                       │ BLE（自定义 GATT 服务 61653DC3-…-8B4EEC61D613）
                       │ 0x0F 指令帧：左右轮速度 -255…255
        ┌──────────────▼───────────────┐
        │  ESP32（小脑）                 │  本仓库 firmware/openbot
        │  LEDC PWM 5kHz                │  · 协议解析 / 看门狗
        │  左右各一组 IN1/IN2            │  · 死区补偿 / 刹车语义
        └──────────────┬───────────────┘
                       │ GPIO 19/21（左）  GPIO 32/33（右）
        ┌──────────────▼───────────────┐
        │  MX1508 × 2 → TT 马达 × 4      │
        └──────────────────────────────┘
                       ▲
                       │ USB（烧录/日志，仅此用途）
        ┌──────────────┴───────────────┐
        │  Mac（指挥部 + 训练中心）       │  arduino-cli / esptool / PyTorch(MPS)
        └──────────────────────────────┘
```

可选外设（后续接入）：Action 5 Pro（磁吸车头，出片 + 高质量训练素材）、Xbox 手柄（连 iPhone，采数据用）、AirPods Pro 2（头部姿态遥控）、TP-Link 摄像头（全场上帝视角）。

## 3. 现在到哪一步（进度是真的，含未完成项）

| 环节 | 状态 | 说明 |
|---|---|---|
| 芯片识别 / 串口 | ✅ 完成 | ESP32-D0WD-V3，4MB，CH340 免驱 |
| 原厂固件备份 | ✅ 完成 | 4MB 完整镜像，可一条命令烧回卖家的 WiFi 网页遥控版 |
| OpenBot 固件适配 | ✅ 完成 | 引脚、死区、外设开关全部按本车改好，编译通过（1,128,017 B，占 app 分区 86%） |
| 烧录 + 校验 | ✅ 完成 | esptool 230400 波特率烧写，Hash verified |
| BLE 广播验证 | ✅ 完成 | iPhone nRF Connect 扫到 `OpenBotCar`，服务 UUID 正确 |
| **电机方向核对** | ✅ 完成 | 方向测试固件实车验证：四轮按预期顺序正/反转 |
| **首次 BLE 驾驶** | ✅ 完成 | Mac 遥控成功开车（途中揪出心跳解析 bug，见踩坑 #23） |
| **浏览器遥控** | ✅ 完成 | 摇杆 + WASD 组合键 + 手机 Safari 可用（`webdrive.py`） |
| iOS App 编译 | ⏳ 进行中 | Xcode 下载中（12GB+）；随后 CocoaPods + 自建 Firebase |
| 人物跟随 / 策略训练 | ⏳ 待做 | 依赖 iOS App |

## 4. 快速开始

### 4.1 装工具链（只需一次）

```bash
# 1) arduino-cli（官方二进制，不走 brew，避免被系统安全策略拦）
mkdir -p tools && cd tools
curl -fL -o arduino-cli.tar.gz https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_macOS_ARM64.tar.gz
tar xzf arduino-cli.tar.gz && cd ..

# 2) ESP32 核心（版本与 OpenBot 官方 CI 一致）
export ARDUINO_DIRECTORIES_DATA="$PWD/arduino-data" \
       ARDUINO_DIRECTORIES_DOWNLOADS="$PWD/arduino-dl" \
       ARDUINO_DIRECTORIES_USER="$PWD/arduino-user"
./tools/arduino-cli config init --overwrite
./tools/arduino-cli config set board_manager.additional_urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
./tools/arduino-cli core update-index
./tools/arduino-cli core install esp32:esp32@2.0.17

# 3) esptool（烧录/备份，用它替代 arduino-cli upload，原因见踩坑 #6）
brew install esptool
```

### 4.2 编译 + 烧录

```bash
./scripts/build.sh          # 编译，产物在 firmware/build/
./scripts/ob.sh flash       # 烧录（自动 230400 波特率）
./scripts/ob.sh monitor     # 串口实时日志，Ctrl+C 退出
./scripts/ob.sh status      # 芯片 / 串口 / 固件大小 / 引脚表 一屏看完
```

> ⚠️ **烧录铁律**：插 USB 前**关闭电池开关**。USB 的 5V 和板载电池 3.3V 同时供电会打架，轻则烧录失败，重则伤板。
> 拔 USB 后再开电池跑车。两者永不同时在线。

### 4.3 不编译 iOS App，先用 Mac / 手机遥控开车（过渡方案）

```bash
./remote-control/run-webdrive.sh    # 推荐：浏览器遥控
#   Mac 开 http://localhost:8765
#   iPhone 同 WiFi 开 http://<Mac的IP>:8765
#   摇杆（模拟量）+ W/A/S/D（真 keyup，可任意组合画弧线）

./remote-control/run-drive.sh       # 备选：终端遥控（单键，无组合）
# W/S/A/D 前进/后退/左右转（按住不放才持续，松手 0.5s 自动停）
# 空格刹车 · 1-4 速度档 · Q 退出（自动刹车）
```

首次运行 macOS 会弹「终端想使用蓝牙」→ 点**允许**（没弹就去
系统设置 → 隐私与安全性 → 蓝牙 手动勾上）。Python 直连 BLE 的
`OpenBotCar`，协议见 `remote-control/drive.py` 文件头注释。

### 4.4 恢复原厂固件（想玩回卖家的 WiFi 网页遥控）

```bash
./scripts/ob.sh backup      # 首次使用前先备份（读到 4MB 镜像，约 3 分钟）
./scripts/ob.sh restore     # 烧回整片镜像
```

## 5. 关键事实速查（最容易踩错的地方）

| 项 | 值 | 备注 |
|---|---|---|
| 左电机 | `IN1=GPIO19` `IN2=GPIO21` | 左前 + 左后并联 |
| 右电机 | `IN1=GPIO32` `IN2=GPIO33` | 右前 + 右后并联 |
| 停止语义 | **两脚同时高 = 刹车**；同时低 = 滑行 | 与 OpenBot 的 stop 逻辑一致，无需改协议 |
| 启动死区 | 占空比 **< 75% 电机完全不转** | 固件在 PWM 输出端补偿：`duty_from_ctrl()` 把控制量 0-255 映射到 191-255（不要做在控制量下限，见踩坑 #21） |
| 电池 | **4 节 5 号镍氢（1.2V）**，不要碱性、不要 3S 18650 | MX1508 上限 9.6V；板载升压固定 6V |
| 烧录波特率 | **230400**（921600 / 460800 必失败） | CH340 的通病 |
| 烧录偏移 | `0x1000` bootloader / `0x8000` partitions / `0x10000` app | flash mode `dio`, freq `40m`, size `4MB` |
| BLE 名称 | `OpenBotCar` | iOS「设置→蓝牙」**不会显示**，只能由 App 扫描 |
| 固件体积上限 | 1,310,720 B（1.25MB app 分区） | 当前 1,128,017 B，占 86%，剩 180KB 余量 |

## 6. 目录结构

```
esp32-openbot-car/
├── index.html                     # Pages 入口页（手机可直接打开的两个页面）
├── firmware/
│   ├── openbot/openbot.ino        # 适配本车的 OpenBot 固件（唯一改动版本）
│   └── moto-test/moto-test.ino    # 电机方向自动测试固件（无需控制端）
├── scripts/
│   ├── setup-toolchain.sh         # 一键装 arduino-cli + ESP32 核心
│   ├── build.sh                   # 编译
│   └── ob.sh                      # status / build / flash / monitor / backup / restore / pinmap
├── remote-control/
│   ├── drive.py                   # Mac 端 BLE 遥控（bleak，终端版，单键）
│   ├── webdrive.py                # 浏览器遥控服务器（WebSocket + 内嵌网页，摇杆 + 组合键，手机可用）
│   ├── run-drive.sh               # 终端遥控启动器
│   └── run-webdrive.sh            # 浏览器遥控启动器
├── docs/                          # 10 篇文档，见下节
└── web/                           # 两个可视化页面（浏览器直接打开）
    ├── OpenBot小车上手计划.html     # 四周计划 + 采购 + 坑清单
    └── OpenBot项目控制台.html       # 实时状态板（硬件核对/引脚/时间线）
```

## 7. 文档索引

| 文档 | 讲什么 |
|---|---|
| [docs/01-硬件清单与选型.md](docs/01-硬件清单与选型.md) | 买什么、花多少、**为什么否掉了 L298N / 18650 / Arduino Nano / 编码器** |
| [docs/02-引脚与接线.md](docs/02-引脚与接线.md) | GPIO 对照表、MX1508 的刹车语义、板载电源链路、怎么用万用表自己量出来 |
| [docs/03-刷机指南.md](docs/03-刷机指南.md) | 从零环境到烧录成功的完整命令，含全部报错的处理 |
| [docs/04-踩坑记录.md](docs/04-踩坑记录.md) | **23 个坑**：现象 / 根因 / 解法 / 怎么提前避开 |
| [docs/05-固件适配说明.md](docs/05-固件适配说明.md) | 改了哪 4 处、为什么改、怎么改成你自己车的引脚 |
| [docs/06-iOS-App编译指南.md](docs/06-iOS-App编译指南.md) | Firebase / CocoaPods / 签名 / 7 天证书，以及"为什么 App Store 没有" |
| [docs/07-技术路线图.md](docs/07-技术路线图.md) | 四层能力边界 + 五层视觉深度学习融合路线（含快慢双系统） |
| [docs/08-开发全过程记录.md](docs/08-开发全过程记录.md) | 每天的决策与理由，包括被推翻的方案 |
| [docs/09-项目结构与文件说明.md](docs/09-项目结构与文件说明.md) | 每个文件干什么，一次控制指令走过哪些代码 |
| [docs/10-代码与通信原理详解.md](docs/10-代码与通信原理详解.md) | **⭐ 最好读**：手机/电脑怎么连上车、指令怎么变成轮子转动，BLE/协议/PWM/混控全链路图解 |

## 8. 最值得看的六个坑（摘要）

1. **iOS 端只支持 BLE，不支持 USB 串口** → 主控必须是 ESP32（Arduino Nano 买来就是废的）。这一条决定了整份采购清单。
2. **GPIO19 冲突**：OpenBot 默认把 19 当左前 LED，正好是本车左电机 IN1。不处理就是"LED 代码和电机抢引脚"。
3. **75% 启动死区**：摇杆推一半车不动，不是坏，是没补偿。`VOLTAGE_MIN/MAX` 一改就顺。
4. **CH340 高速烧录必挂**：460800 读备份超时、921600 烧写失败，一律降到 230400。
5. **3S 18650 = 烧驱动**：MX1508 上限 9.6V，而这车用 4 节 5 号（板载升压 6V），18650 方案从根上就是错的。
6. **测试固件不广播蓝牙**：烧了方向测试程序后 nRF Connect 扫不到 `OpenBotCar` 是正常的，别以为板子坏了。
7. **心跳帧带冒号 = 车只嗡不转**：`h:400` 被固件 `atol` 解析成 0，控制量每圈都被清零——链路每环"看起来都正常"，只有数值是错的（踩坑 #23）。
8. **终端按键没法组合**：macOS 只给最后按下的键发重复信号、拿不到 keyup——想要 W+A 同时按住，用浏览器遥控（webdrive.py）。

完整版见 [docs/04-踩坑记录.md](docs/04-踩坑记录.md)。

## 9. 这个项目在教什么

它不是"又一个遥控车"。它把具身智能的每个环节压缩到一张桌子上，让每个抽象名词都变成能摸到的东西：

- **感知→决策→执行**：摄像头 30 FPS 输入，模型输出，BLE 下发，电机转动——延迟多少、卡在哪一环，你自己能量出来
- **数据决定上限**：同样 30 分钟，抖着开和稳着开，训出来的策略是两个东西
- **端侧算力是硬约束**：A18 跑满 15 分钟会热降频，帧率从 30 掉到 15，模型"突然变笨"——这是所有端侧 AI 的真实处境
- **开源硬件的不确定性**：卖家文档说舵机转向、实物是四轮差速；说支持开源、引脚表藏在源码里。**读源码比读商品页可靠**

## 10. 授权与致谢

- 本项目固件基于 [OpenBot](https://github.com/ob-f/OpenBot)（Intel Intelligent Systems Lab 发起，**MIT License**），已按其许可保留版权声明，改动部分在 [docs/05-固件适配说明.md](docs/05-固件适配说明.md) 中逐条标注。
- 底盘与原始固件来自淘宝商家（其 WiFi 网页遥控固件仅作本地备份，未收录进本仓库）。
- 本项目文档由「聪聪 + AI 结对」的方式产出：人负责决策与动手，AI 负责查源码、改固件、写脚本、排错。
