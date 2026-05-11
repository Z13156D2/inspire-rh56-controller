# Inspire RH56 Dexterous Hand GUI Controller

> A lightweight graphical control and debugging tool for the Inspire Robots RH56 dexterous hand.  
> This project is implemented with Python, Tkinter, and PySerial, and is designed for serial communication, parameter tuning, real-time state readback, and action sequence triggering.


## 1. Overview

`inspire-rh56-gui-controller` is a Python-based GUI host program for the **Inspire RH56 six-DoF dexterous hand**. It communicates with the hand through a serial port and provides an easy-to-use interface for setting finger angles, target force, motion speed, current limits, power-on default parameters, and for reading back real-time status such as actual angle, force, current, temperature, status codes, and error codes.

This tool is useful for:

- RH56 hardware bring-up and debugging;
- serial communication protocol verification;
- angle, force, and speed tuning;
- current protection and default parameter configuration;
- status monitoring and fault diagnosis;
- action sequence testing;
- robotics, teleoperation, dexterous manipulation, and research experiments.

## 2. Features

### 2.1 Serial Port Management

- Automatically scans available serial ports;
- Supports custom baud rate settings;
- Supports configurable RH56 hand ID;
- Provides connect and disconnect controls;
- Displays real-time operation logs.

### 2.2 Six-DoF Control

The GUI controls the six actuator channels of the RH56 hand. The default DoF order is:

| Index | DoF Name |
|---:|---|
| 0 | Little finger |
| 1 | Ring finger |
| 2 | Middle finger |
| 3 | Index finger |
| 4 | Thumb flexion |
| 5 | Thumb rotation |

The following six-channel parameters can be written and read:

| Tab | Register Meaning | Typical Range |
|---|---|---|
| `ANGLE_SET` | Target angle | `0~1000`, supports `-1` to skip a channel |
| `FORCE_SET` | Target force | `0~1000 g`, supports `-1` to skip a channel |
| `SPEED_SET` | Target speed | `0~1000`, supports `-1` to skip a channel |
| `CURRENT_LIMIT` | Current protection threshold | `0~1500 mA` |
| `DEFAULT_SPEED` | Power-on default speed | `0~1000` |
| `DEFAULT_FORCE` | Power-on default force | first four channels `0~1000 g`, thumb channels `0~1500 g` |

### 2.3 Real-Time Readback

The GUI supports both automatic and manual readback of:

| Item | Description |
|---|---|
| `ANGLE_ACT` | Actual angle of each channel |
| `FORCE_ACT` | Actual force of each channel |
| `CURRENT` | Actuator current in mA |
| `STATUS` | Status code of each channel |
| `TEMP` | Temperature of each channel |
| `ERROR` | Error code of each channel |

The default polling interval is `300 ms`. You can modify it in:

```python
CONFIG["poll_interval_ms"] = 300
```

### 2.4 Parameter Management

The GUI supports the following parameter-management operations:

- Clear recoverable errors with `clearErr=1`;
- Calibrate force sensors with `forceClb=1`;
- Save parameters to Flash with `SAVE=1`;
- Restore factory parameters with `RESET_PARA=1`;
- Read and write the `reserve` register;
- Wait for and parse the Flash-save result frame.

### 2.5 Action Sequence Control

The GUI also supports basic action sequence operations:

- Set action sequence index;
- Run the selected action sequence;
- Log the execution request.

## 3. Safety Notice

Please read the following safety notes before running the GUI:

1. **Keep fingers, cables, and fragile objects away from the dexterous hand before sending motion commands.**
2. Force sensor calibration should be performed only when the fingers are unloaded and not touching any object.
3. Before modifying `CURRENT_LIMIT`, `DEFAULT_FORCE`, or `DEFAULT_SPEED`, make sure the values comply with the device manual.
4. `SAVE=1` writes the current parameters to Flash, so the settings remain after power cycling.
5. `RESET_PARA=1` restores factory parameters and may overwrite your current tuning results.
6. If abnormal movement, stall, over-current protection, or communication failure occurs, power off the device and inspect the hardware setup immediately.

This software only provides serial communication and GUI-level control. Users are responsible for verifying wiring, power supply, current limits, mechanical constraints, and experimental safety.

## 4. Requirements

Recommended environment:

| Item | Recommended Version |
|---|---|
| Operating system | Windows 10/11; Linux is also supported with minor adaptation |
| Python | Python 3.8 or later |
| GUI toolkit | Tkinter |
| Serial library | PySerial |
| Hardware | Inspire RH56 dexterous hand |
| Communication | USB-to-serial or RS485-to-serial adapter, depending on the hardware setup |

### 4.1 Python Dependencies

The main dependency is:

```bash
pyserial
```

Tkinter is usually bundled with Python. On Linux, if Tkinter is missing, install it with:

```bash
sudo apt-get install python3-tk
```

## 5. Installation

### 5.1 Clone the Repository

```bash
git clone https://github.com/<your-username>/inspire-rh56-gui-controller.git
cd inspire-rh56-gui-controller
```

### 5.2 Create a Virtual Environment

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 5.3 Install Dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` is not available yet, install PySerial directly:

```bash
pip install pyserial
```

A minimal `requirements.txt` can be:

```txt
pyserial>=3.5
```

## 6. Usage

Assuming the main script is named `rh56_gui_controller.py`, run:

```bash
python rh56_gui_controller.py
```

Typical workflow:

1. Select the serial port, such as `COM3` on Windows or `/dev/ttyUSB0` on Linux;
2. Set the baud rate, default `115200`;
3. Set the hand ID, default `1`;
4. Click **Connect**;
5. Set angle, force, speed, current limit, or default parameters in the corresponding tabs;
6. Click **Write** to send parameters to the RH56 hand;
7. Click **Read Once** or enable automatic polling to monitor real-time status;
8. Click **Save to Flash** if the parameters should remain after power cycling.

## 7. GUI Layout

### 7.1 Top Connection Bar

The top bar contains:

- Serial port selection;
- Refresh button;
- Baud rate input;
- Hand ID input;
- Connection status;
- Connect and disconnect buttons.

Default values are defined in:

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

You can modify the default port, baud rate, device ID, polling interval, serial timeout, and window size according to your setup.

### 7.2 Left Control Panel

The left panel uses a `ttk.Notebook` widget and contains multiple tabs:

- `ANGLE_SET`: target angle control;
- `FORCE_SET`: target force control;
- `SPEED_SET`: target speed control;
- `CURRENT_LIMIT`: current protection threshold;
- `DEFAULT_SPEED`: power-on default speed;
- `DEFAULT_FORCE`: power-on default force.

The first three motion-control tabs support `-1`, which means the selected channel will not be updated.

### 7.3 Right Readback Panel

The right panel displays real-time values for all six channels:

- Actual angle;
- Actual force;
- Current;
- Status code;
- Temperature;
- Error code.

Status code reference:

| Status Code | Meaning |
|---:|---|
| 0 | Released |
| 1 | Grasping |
| 2 | Stopped after reaching target position |
| 3 | Stopped after reaching target force |
| 5 | Stopped due to current protection |
| 6 | Stopped due to stall |
| 7 | Stopped due to fault |

### 7.4 Log Panel

The bottom log panel displays:

- Serial connection state;
- Parameter write records;
- Parameter readback records;
- Flash-save result;
- Clear-error, force calibration, and action sequence commands.

The log panel can be shown or hidden using the **Show Log** checkbox.

## 8. Register Map

The main registers used in this project are:

| Register Name | Address | Type | Description |
|---|---:|---|---|
| `ID` | 1000 | 1 byte | Device ID |
| `baudrate` | 1001 | 1 byte | Baud rate configuration |
| `clearErr` | 1004 | 1 byte | Clear error |
| `saveFlash` | 1005 | 1 byte | Save parameters to Flash |
| `resetPara` | 1006 | 1 byte | Restore factory parameters |
| `reserve` | 1008 | 1 byte | Reserved register |
| `forceClb` | 1009 | 1 byte | Force sensor calibration |
| `currentLimit` | 1020 | 6 short | Current protection threshold |
| `defaultSpeedSet` | 1032 | 6 short | Power-on default speed |
| `defaultForceSet` | 1044 | 6 short | Power-on default force |
| `angleSet` | 1486 | 6 short | Target angle |
| `forceSet` | 1498 | 6 short | Target force |
| `speedSet` | 1522 | 6 short | Target speed |
| `angleAct` | 1546 | 6 short | Actual angle |
| `forceAct` | 1582 | 6 short | Actual force |
| `current` | 1594 | 6 unsigned short | Current value |
| `errCode` | 1606 | 6 byte | Error code |
| `statusCode` | 1612 | 6 byte | Status code |
| `temp` | 1618 | 6 byte | Temperature |
| `actionSeq` | 2320 | 1 byte | Action sequence index |
| `actionRun` | 2322 | 1 byte | Run action sequence |

## 9. Communication Protocol

### 9.1 Write Register Frame

Write-register frame format:

```text
0xEB 0x90 ID LEN 0x12 ADDR_L ADDR_H DATA... CHECKSUM
```

where:

- `ID` is the hand device ID;
- `LEN` equals the data length plus 3;
- `0x12` is the write-register command;
- `ADDR_L / ADDR_H` are the low and high bytes of the register address;
- `DATA` is the payload to be written;
- `CHECKSUM` is the lower 8 bits of the sum from `ID` to the last data byte.

### 9.2 Read Register Frame

Read-register frame format:

```text
0xEB 0x90 ID 0x04 0x11 ADDR_L ADDR_H READ_LEN CHECKSUM
```

where `0x11` is the read-register command and `READ_LEN` is the number of bytes to read.

### 9.3 Response Packet

The expected response header is:

```text
0x90 0xEB
```

The program checks both the packet header and checksum. Invalid packets are discarded.


## 10. Troubleshooting

### 10.1 No Serial Port Found

Please check:

- Whether the USB-to-serial adapter is connected;
- Whether the correct COM port appears in Device Manager;
- Whether another program is using the serial port;
- Whether the user has permission to access the serial device on Linux.

On Linux, you may need:

```bash
sudo usermod -aG dialout $USER
```

Then log out and log back in.

### 10.2 Connection Failed

Possible causes include:

- Wrong serial port;
- Wrong baud rate;
- Serial port occupied by another program;
- Missing USB-to-serial driver;
- Incorrect wiring;
- Device not powered on.

### 10.3 The Hand Does Not Move After Writing Commands

Check the following:

- The serial port is connected;
- The hand ID is correct;
- The command values are within valid ranges;
- `ANGLE_SET`, `FORCE_SET`, and `SPEED_SET` are written correctly;
- No error code or current-protection status is active;
- The power supply is sufficient.

### 10.4 Readback Fails or Is Unstable

Readback instability may be caused by:

- Unstable serial communication;
- Polling interval too short;
- Device response delay during motion;
- Incorrect hand ID;
- Poor cable or adapter quality.

Try increasing:

```python
CONFIG["poll_interval_ms"] = 500
CONFIG["serial_timeout"] = 0.3
```

### 10.5 No Flash-Save Result Frame

The program waits for a save-result frame after `SAVE=1`. If no response is received, possible reasons include:

- Different firmware response format;
- Packet loss on the serial link;
- Save operation takes longer than expected;
- Device does not return a confirmation frame.

Try saving again or increasing the `wait_s` argument in `save_to_flash()`.

## 11. Future Improvements

Possible future extensions:

- Add a `config.yaml` configuration file;
- Add a raw TX/RX serial protocol debugging window;
- Add predefined gesture presets;
- Add an action sequence editor;
- Add CSV logging for angle, force, current, and temperature;
- Add real-time plotting;
- Add ROS2 topic support;
- Wrap the controller as a reusable Python SDK;
- Support multiple RH56 hands;
- Provide packaging scripts for generating a Windows `.exe`.

## 12. License

MIT License is recommended for open-source release. Please add a `LICENSE` file before publishing the repository.

## 13. Disclaimer

This project is a research and debugging tool for the RH56 dexterous hand and is not official software from Inspire Robots. When controlling real hardware, always follow the device manual and laboratory safety rules. The user is responsible for any hardware damage, safety risk, or unexpected behavior caused by incorrect wiring, inappropriate parameters, abnormal commands, or improper use.
