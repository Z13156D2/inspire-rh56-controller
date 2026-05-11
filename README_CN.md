# Inspire RH56 Dexterous Hand GUI Controller

> 因时机器人（Inspire Robots）RH56 灵巧手图形化上位机控制程序。  
> 本项目基于 Python + Tkinter + PySerial 实现，面向 RH56 灵巧手的串口调试、参数配置、状态回读和动作序列触发等场景。


## 1. 项目简介

`inspire-rh56-gui-controller` 是一个用于 **Inspire RH56 六自由度灵巧手** 的轻量级 GUI 上位机程序。它通过串口与灵巧手通信，提供直观的图形界面，用于控制手指角度、力控目标、运动速度、电流保护阈值、上电默认参数，以及读取角度、受力、电流、温度、状态码和故障码等实时信息。

该工具适合以下使用场景：

- RH56 灵巧手基础联调；
- 串口通信协议验证；
- 角度 / 力控 / 速度参数调试；
- 电流保护与默认参数配置；
- 状态回读与故障排查；
- 动作序列触发测试；
- 机器人遥操作、灵巧手控制、科研实验前的硬件检查。

## 2. 功能特性

### 2.1 串口连接管理

- 自动扫描可用串口；
- 支持自定义波特率；
- 支持设置 RH56 手部设备 ID；
- 支持连接与断开串口；
- 日志窗口实时显示操作信息。

### 2.2 六自由度控制

程序按照 RH56 的六路驱动通道进行控制，默认自由度顺序为：

| 序号 | 自由度名称 |
|---:|---|
| 0 | 小拇指 |
| 1 | 无名指 |
| 2 | 中指 |
| 3 | 食指 |
| 4 | 拇指弯曲 |
| 5 | 拇指旋转 |

支持写入和读取以下六路参数：

| 参数页 | 寄存器含义 | 典型范围 |
|---|---|---|
| `ANGLE_SET` | 目标角度 | `0~1000`，支持 `-1` 表示不设置 |
| `FORCE_SET` | 目标力控值 | `0~1000 g`，支持 `-1` 表示不设置 |
| `SPEED_SET` | 目标速度 | `0~1000`，支持 `-1` 表示不设置 |
| `CURRENT_LIMIT` | 电流保护阈值 | `0~1500 mA` |
| `DEFAULT_SPEED` | 上电默认速度 | `0~1000` |
| `DEFAULT_FORCE` | 上电默认力控值 | 前四路 `0~1000 g`，拇指两路 `0~1500 g` |

### 2.3 实时状态回读

支持自动或手动回读以下状态：

| 回读项 | 含义 |
|---|---|
| `ANGLE_ACT` | 六自由度实际角度 |
| `FORCE_ACT` | 六自由度实际受力 |
| `CURRENT` | 六路电缸电流值，单位 mA |
| `STATUS` | 六路状态码 |
| `TEMP` | 六路温度 |
| `ERROR` | 六路故障码 |

默认自动回读周期为 `300 ms`，可在代码中的 `CONFIG["poll_interval_ms"]` 修改。

### 2.4 参数管理

支持 RH56 参数管理相关操作：

- 清除可清除故障：`clearErr=1`；
- 力传感器校准：`forceClb=1`；
- 保存参数到 Flash：`SAVE=1`；
- 恢复出厂设置：`RESET_PARA=1`；
- 读取 / 写入 `reserve` 保留寄存器；
- 等待并解析保存到 Flash 后的结果帧。

### 2.5 动作序列控制

支持动作序列相关寄存器操作：

- 设置动作序列索引；
- 运行当前动作序列；
- 通过日志显示动作触发结果。

## 3. 安全提示

在运行本程序前，请务必注意以下事项：

1. **确保灵巧手周围没有人员手指、线缆或易损物体。**
2. 执行力传感器校准前，应确保手指处于空载状态，不接触任何物体。
3. 修改 `CURRENT_LIMIT`、`DEFAULT_FORCE`、`DEFAULT_SPEED` 等参数前，应确认数值范围符合设备手册要求。
4. 执行 `SAVE=1` 会将当前参数写入 Flash，断电后仍会保留。
5. 执行 `RESET_PARA=1` 会恢复出厂设置，可能覆盖当前调试参数。
6. 如果设备出现异常运动、堵转、过流或通信异常，应立即断电检查。

本程序仅提供软件层面的串口控制能力，使用者需要自行确认硬件接线、电源、电流限制、机械限位和实验安全。

## 4. 环境要求

推荐环境：

| 项目 | 建议版本 |
|---|---|
| 操作系统 | Windows 10/11，Linux 也可适配 |
| Python | Python 3.8 或更高 |
| GUI | Tkinter |
| 串口库 | PySerial |
| 设备 | Inspire RH56 灵巧手 |
| 通信方式 | USB 转串口 / RS485 转串口，视硬件连接方式而定 |

### 4.1 Python 依赖

本项目主要依赖：

```bash
pyserial
```

Tkinter 通常随 Python 一起安装。若在 Linux 上缺少 Tkinter，可安装：

```bash
sudo apt-get install python3-tk
```

## 5. 安装方法

### 5.1 克隆项目

```bash
git clone https://github.com/<your-username>/inspire-rh56-gui-controller.git
cd inspire-rh56-gui-controller
```

### 5.2 创建虚拟环境

Windows：

```bash
python -m venv .venv
.venv\Scripts\activate
```

Linux / macOS：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 5.3 安装依赖

```bash
pip install -r requirements.txt
```

如果暂时没有 `requirements.txt`，也可以直接安装：

```bash
pip install pyserial
```

建议新建一个 `requirements.txt`：

```txt
pyserial>=3.5
```

## 6. 运行方法

假设主程序文件名为 `rh56_gui_controller.py`，运行：

```bash
python rh56_gui_controller.py
```

程序启动后，按照以下步骤操作：

1. 选择串口，例如 Windows 下的 `COM3`，或 Linux 下的 `/dev/ttyUSB0`；
2. 设置波特率，默认 `115200`；
3. 设置手部 ID，默认 `1`；
4. 点击 **连接**；
5. 在不同标签页设置角度、力控、速度或默认参数；
6. 点击 **写入** 将参数发送到灵巧手；
7. 点击 **回读一次** 或开启自动回读查看状态；
8. 如需断电保存参数，点击 **保存到 Flash**。

## 7. GUI 页面说明

### 7.1 顶部连接栏

顶部栏包含：

- 串口选择；
- 刷新串口；
- 波特率输入；
- 手 ID 输入；
- 当前连接状态；
- 连接 / 断开按钮。

默认配置位于代码顶部：

```python
CONFIG = {
    "default_port": "COM3",
    "default_baud": 115200,
    "default_id": 1,
    "poll_interval_ms": 300,
    "serial_timeout": 0.15,
    "default_geometry": "1280x760",
}
```

可根据自己的设备修改默认串口、波特率、设备 ID 和窗口大小。

### 7.2 左侧控制区

左侧使用 `ttk.Notebook` 分页显示不同控制项：

- `ANGLE_SET`：设置目标角度；
- `FORCE_SET`：设置目标力；
- `SPEED_SET`：设置目标速度；
- `CURRENT_LIMIT`：设置电流保护值；
- `DEFAULT_SPEED`：设置上电默认速度；
- `DEFAULT_FORCE`：设置上电默认力控值。

前三类运动控制参数支持 `-1`，表示对应通道不设置。

### 7.3 右侧回读区

右侧表格实时显示六路通道的实际状态，包括：

- 实际角度；
- 实际受力；
- 电流；
- 状态码；
- 温度；
- 故障码。

状态码参考：

| 状态码 | 含义 |
|---:|---|
| 0 | 松开 |
| 1 | 抓取 |
| 2 | 位置到位停止 |
| 3 | 力控到位停止 |
| 5 | 电流保护停止 |
| 6 | 堵转停止 |
| 7 | 故障停止 |

### 7.4 日志区

底部日志区会显示：

- 串口连接状态；
- 参数写入记录；
- 参数读取记录；
- 保存 Flash 结果；
- 错误清除、力传感器校准和动作序列触发信息。

可以通过右侧的 **显示日志** 复选框隐藏或显示日志区域。

## 8. 寄存器说明

程序中使用的主要寄存器如下：

| 寄存器名 | 地址 | 类型 | 说明 |
|---|---:|---|---|
| `ID` | 1000 | 1 byte | 设备 ID |
| `baudrate` | 1001 | 1 byte | 波特率配置 |
| `clearErr` | 1004 | 1 byte | 清除错误 |
| `saveFlash` | 1005 | 1 byte | 保存数据到 Flash |
| `resetPara` | 1006 | 1 byte | 恢复出厂设置 |
| `reserve` | 1008 | 1 byte | 保留寄存器 |
| `forceClb` | 1009 | 1 byte | 力传感器校准 |
| `currentLimit` | 1020 | 6 short | 电流保护阈值 |
| `defaultSpeedSet` | 1032 | 6 short | 上电默认速度 |
| `defaultForceSet` | 1044 | 6 short | 上电默认力控 |
| `angleSet` | 1486 | 6 short | 目标角度 |
| `forceSet` | 1498 | 6 short | 目标力控 |
| `speedSet` | 1522 | 6 short | 目标速度 |
| `angleAct` | 1546 | 6 short | 实际角度 |
| `forceAct` | 1582 | 6 short | 实际受力 |
| `current` | 1594 | 6 unsigned short | 电流值 |
| `errCode` | 1606 | 6 byte | 故障码 |
| `statusCode` | 1612 | 6 byte | 状态码 |
| `temp` | 1618 | 6 byte | 温度 |
| `actionSeq` | 2320 | 1 byte | 动作序列索引 |
| `actionRun` | 2322 | 1 byte | 运行动作序列 |

## 9. 通信协议简述

### 9.1 写寄存器

写寄存器帧格式：

```text
0xEB 0x90 ID LEN 0x12 ADDR_L ADDR_H DATA... CHECKSUM
```

其中：

- `ID`：设备 ID；
- `LEN`：数据长度加 3；
- `0x12`：写寄存器命令；
- `ADDR_L / ADDR_H`：寄存器地址，低字节在前；
- `DATA`：待写入数据；
- `CHECKSUM`：从 `ID` 到最后一个数据字节求和后取低 8 位。

### 9.2 读寄存器

读寄存器帧格式：

```text
0xEB 0x90 ID 0x04 0x11 ADDR_L ADDR_H READ_LEN CHECKSUM
```

其中 `0x11` 表示读寄存器命令，`READ_LEN` 表示待读取的字节数。

### 9.3 回包解析

程序期望回包包头为：

```text
0x90 0xEB
```

并通过校验和验证回包完整性。若包头或校验和不正确，程序会丢弃该数据包。

## 10. 推荐项目结构

建议将仓库整理为以下结构：

```text
inspire-rh56-gui-controller/
├── README.md
├── README_EN.md
├── requirements.txt
├── rh56_gui_controller.py
├── docs/
│   └── screenshot.png
├── examples/
│   └── basic_usage.md
└── LICENSE
```

如果后续项目变复杂，也可以拆分为：

```text
inspire-rh56-gui-controller/
├── rh56/
│   ├── __init__.py
│   ├── controller.py
│   ├── gui.py
│   └── registers.py
├── main.py
├── README.md
├── README_EN.md
└── requirements.txt
```

## 11. 常见问题

### 11.1 找不到串口怎么办？

请检查：

- USB 转串口模块是否正确连接；
- 设备管理器中是否出现对应 COM 口；
- 串口是否被其他软件占用；
- Linux 下当前用户是否有串口权限。

Linux 下可尝试：

```bash
sudo usermod -aG dialout $USER
```

然后重新登录系统。

### 11.2 点击连接失败怎么办？

可能原因包括：

- 串口号错误；
- 波特率错误；
- 串口被其他程序占用；
- USB 转串口驱动未安装；
- 硬件连接异常；
- 设备未上电。

### 11.3 写入后灵巧手没有动作怎么办？

请检查：

- 是否已经连接串口；
- 手 ID 是否正确；
- 目标值是否在合法范围内；
- `ANGLE_SET`、`FORCE_SET`、`SPEED_SET` 是否写入正确；
- 是否存在故障码或电流保护状态；
- 设备供电是否满足要求。

### 11.4 自动回读失败怎么办？

自动回读失败通常与以下因素有关：

- 串口通信不稳定；
- 回读周期过短；
- 设备正在执行动作导致响应延迟；
- 手 ID 不正确；
- 线缆或转接器质量不佳。

可尝试增大：

```python
CONFIG["poll_interval_ms"] = 500
CONFIG["serial_timeout"] = 0.3
```

### 11.5 保存到 Flash 没有结果帧怎么办？

程序会等待设备返回保存结果帧。如果超时未收到，可能是：

- 固件版本回包格式不同；
- 通信链路丢包；
- 保存时间超过默认等待时间；
- 设备未正确响应。

可尝试重新保存，或增大 `save_to_flash()` 的 `wait_s` 参数。

## 12. 后续开发建议

可以进一步扩展以下功能：

- 增加配置文件，例如 `config.yaml`；
- 增加串口协议调试窗口，显示原始 TX/RX 数据；
- 增加预设手势管理；
- 增加动作序列编辑器；
- 增加 CSV 数据记录功能；
- 增加实时曲线显示角度、力、电流和温度；
- 支持 ROS2 topic 发布与订阅；
- 支持将 GUI 控制命令封装为 Python SDK；
- 支持多只 RH56 灵巧手同时控制；
- 增加打包脚本，生成 Windows `.exe` 程序。

## 13. 许可证

建议使用 MIT License 开源本项目。正式发布前，请在仓库中添加 `LICENSE` 文件。

## 14. 免责声明

本项目为 RH56 灵巧手的串口调试和科研实验辅助工具，并非官方软件。使用本项目控制真实硬件时，请务必遵守设备手册和实验室安全规范。因错误接线、错误参数、异常控制指令或不当使用造成的设备损坏或安全风险，需由使用者自行承担。
