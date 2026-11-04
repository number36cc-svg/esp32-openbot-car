# 06 · iOS App 编译指南（Week 2 的主要工作量）

> 现实先说清楚：**OpenBot iOS App 不在 App Store，也装不了别人的包**。
> 必须自己在 Mac 上从源码编译、用你自己的开发者证书签名，才能装进 iPhone。
> 这一步比接线麻烦得多，是整个项目里最"工程化"的环节。

## 1. 为什么必须自己编译

| 原因 | 说明 |
|---|---|
| 官方只发开发者构建 | 官方仓库 README 原文：目前唯一运行方式是通过下面的 developer build 流程 |
| 不签名的 App 装不进真机 | iOS 强制代码签名 |
| App 需要自己的 Firebase 项目 | 模型/项目数据存在 Google Firebase，你得有自己的 `GoogleService-Info.plist` 才能启动 |

## 2. 前置条件

- **Xcode**（iOS SDK 15.5+ 部署目标，当前工程要求 Xcode 较新版本）
- **CocoaPods**（依赖管理）
- **一个 Apple ID**（免费个人账号即可，但见 §5 的 7 天限制）
- iPhone 开启**开发者模式**（设置 → 隐私与安全性 → 开发者模式），并信任你的 Apple ID
- Mac 与 iPhone 用**数据线**相连（首次安装必须有线）

## 3. 步骤

```bash
# 1) 拿源码
git clone --depth 1 https://github.com/ob-f/OpenBot.git
cd OpenBot/robot/ios

# 2) 装依赖
sudo gem install cocoapods       # 若未安装
pod install                      # 生成 OpenBot.xcworkspace
```

```
# 3) 建 Firebase 项目（必须做，否则 App 起不来）
#    Firebase Console → 新建项目 → 添加 iOS App（Bundle ID 与 Xcode 工程一致）
#    → 下载 GoogleService-Info.plist → 拖进 Xcode 工程的 OpenBot target
#    详细步骤见：robot/ios/OpenBot/OpenBot/Authentication/README.md

# 4) 打开工程与签名
open OpenBot.xcworkspace
#    Xcode → Target OpenBot → Signing & Capabilities
#    Team 选你自己的 Apple ID（工程已配置 Automatically manage signing）
#    必要时改 Bundle Identifier（加个后缀避免冲突）
```

```
# 5) 选设备 → 跑 ▶️
#    首次运行：iPhone 设置 → 通用 → VPN与设备管理 → 信任你的开发者证书
```

## 4. 常见失败

| 现象 | 原因 | 处理 |
|---|---|---|
| `pod install` 卡住/失败 | 网络（CocoaPods 源） | 换源或用代理；重试 |
| App 启动即闪退 | 没放 `GoogleService-Info.plist` 或 Bundle ID 不匹配 | 核对 Bundle ID 与 Firebase 中一致 |
| `Untrusted Developer` | 证书未信任 | 设备管理里信任 |
| `Unable to install` | 设备未开开发者模式 | 设置里打开，重启手机 |
| 一周后 App 打不开 | **免费证书 7 天过期** | 重连 Mac 重编；或上付费账号 |

## 5. 免费证书的 7 天限制（一定要知道）

| 账号类型 | 有效期 | 影响 |
|---|---|---|
| 免费 Apple ID | **7 天** | 每周要连 Mac 重新编译安装一次，否则 App 图标点了没反应 |
| Apple Developer Program（¥688/年） | 1 年 | 装一次能用一年，还能 TestFlight 分发 |

**建议**：先免费跑通；确认这项目会长期玩下去，再考虑付费。

## 6. 装好 App 之后能干什么

| 功能 | 依赖 | 说明 |
|---|---|---|
| 遥控驾驶（虚拟摇杆） | 固件 BLE | 连上 `OpenBotCar` 即可 |
| 直播画面 + 实时检测 | 手机摄像头 | 目标检测在手机本地跑 |
| 人物跟随 / 物体追踪 | 上述 + 控制环 | 先用"人"这个类别试 |
| 数据采集 | 存储权限 | 画面 + 操作一起存，供 Mac 训练 |
| 加载自定义模型 | 重新编译 App | `.tflite` 换进工程资源目录，**必须重编** |

## 7. 在 App 编译完成之前，怎么先玩起来

三条过渡路径（按省事程度）：

1. **方向测试固件**：连 App 都不需要，通电自动跑（已实现，见 [05](05-固件适配说明.md)）
2. **Mac 端 BLE 遥控脚本**：用 Python + `bleak` 直连 `OpenBotCar`，键盘控制。需要在自己终端跑一次并允许蓝牙权限
3. **烧回卖家原厂固件**：手机浏览器进它的 WiFi 热点，网页摇杆驾驶（没有 AI，但立刻能开）

## 8. 关于"控制器 App"

官方仓库里还有 `controller/flutter`（另一台手机当遥控器 + 视频流），它连的是**跑在机器人上的 App**，不是直连 ESP32。也就是说：**机器上必须已经跑着 OpenBot App，控制器才有意义**。所以它不能替代主 App 的编译。
