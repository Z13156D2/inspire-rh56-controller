"""
rh56_gui_controller_Linux.py

Created by Zhentao Zhou
Date: 2026-01-04
Version: 1.3
"""
import time
import threading
import errno
import os
import grp
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

import serial
from serial.tools import list_ports


CONFIG = {
    "default_port": "/dev/ttyUSB0",
    "default_baud": 115200,
    "default_id": 1,
    "poll_interval_ms": 300,
    "serial_timeout": 0.15,
    "default_geometry": "1280x760",
}

REG = {
    "ID": 1000,
    "baudrate": 1001,
    "clearErr": 1004,

    # ===== 手册新增寄存器 =====
    "saveFlash": 1005,     # SAVE 保存数据至Flash
    "resetPara": 1006,     # RESET_PARA 恢复出厂设置
    "reserve": 1008,       # 保留 reserve

    "forceClb": 1009,

    "currentLimit": 1020,       # CURRENT_LIMIT(m) 6short
    "defaultSpeedSet": 1032,    # DEFAULT_SPEED_SET(m) 6short
    "defaultForceSet": 1044,    # DEFAULT_FORCE_SET(m) 6short

    # ===== 运动/回读 =====
    "angleSet": 1486,
    "forceSet": 1498,
    "speedSet": 1522,

    "angleAct": 1546,
    "forceAct": 1582,
    "current": 1594,            # CURRENT(m) 六路电缸电流值（只读，mA）

    "errCode": 1606,
    "statusCode": 1612,
    "temp": 1618,

    # 动作序列
    "actionSeq": 2320,
    "actionRun": 2322,
}

DOF_NAMES = ["小拇指", "无名指", "中指", "食指", "拇指弯曲", "拇指旋转"]


class RH56Controller:
    def __init__(self, logger):
        self.ser = None
        self.lock = threading.Lock()
        self.logger = logger

    def is_open(self):
        return self.ser is not None and self.ser.is_open

    def open(self, port, baud):
        with self.lock:
            if self.is_open():
                return
            self.ser = serial.Serial(
                port=port,
                baudrate=int(baud),
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=CONFIG["serial_timeout"],
            )
        self.logger(f"✅ 串口已打开：{port} @ {baud}")

    def close(self):
        with self.lock:
            if self.ser is not None:
                try:
                    self.ser.close()
                except Exception:
                    pass
                self.ser = None
        self.logger("🛑 串口已关闭")

    def _write_frame(self, frame: bytes):
        if not self.is_open():
            raise RuntimeError("串口未打开")
        self.ser.write(frame)

    def _read_exact(self, n, timeout=0.25):
        if not self.is_open():
            return b""
        buf = b""
        t0 = time.time()
        while len(buf) < n and (time.time() - t0) < timeout:
            chunk = self.ser.read(n - len(buf))
            if chunk:
                buf += chunk
        return buf

    def _read_packet(self, timeout=0.25):
        hdr = self._read_exact(4, timeout=timeout)
        if len(hdr) < 4:
            return None
        # 回包包头：0x90 0xEB
        if hdr[0] != 0x90 or hdr[1] != 0xEB:
            try:
                self.ser.reset_input_buffer()
            except Exception:
                pass
            return None

        length = hdr[3]
        rest = self._read_exact(length + 1, timeout=timeout)
        if len(rest) < length + 1:
            return None

        pkt = hdr + rest
        chk = (sum(pkt[2:-1]) & 0xFF)
        if chk != pkt[-1]:
            return None
        return pkt

    def write_register(self, hand_id, addr, data_bytes):
        if not isinstance(data_bytes, (bytes, bytearray)):
            data_bytes = bytes(data_bytes)

        length = len(data_bytes) + 3
        frame = bytearray([0xEB, 0x90, hand_id, length, 0x12, addr & 0xFF, (addr >> 8) & 0xFF])
        frame.extend(data_bytes)
        frame.append(sum(frame[2:]) & 0xFF)

        with self.lock:
            self._write_frame(bytes(frame))
            time.sleep(0.01)
            _ = self._read_packet(timeout=0.20)

    def read_register(self, hand_id, addr, reg_len_bytes):
        frame = bytearray([0xEB, 0x90, hand_id, 0x04, 0x11, addr & 0xFF, (addr >> 8) & 0xFF, reg_len_bytes])
        frame.append(sum(frame[2:]) & 0xFF)

        with self.lock:
            try:
                self.ser.reset_input_buffer()
            except Exception:
                pass
            self._write_frame(bytes(frame))
            time.sleep(0.01)
            pkt = self._read_packet(timeout=0.25)

        if pkt is None:
            return None
        if pkt[4] != 0x11:
            return None

        data_start = 7
        data_end = 7 + reg_len_bytes
        if len(pkt) < data_end + 1:
            return None
        return pkt[data_start:data_end]

    # ---------- 1 byte ----------
    def write1_byte(self, hand_id, reg_key, value):
        if reg_key not in ("saveFlash", "resetPara", "reserve", "clearErr", "forceClb", "actionSeq", "actionRun"):
            raise ValueError("reg_key 不支持写 1byte")
        self.write_register(hand_id, REG[reg_key], bytes([int(value) & 0xFF]))

    def read1_byte(self, hand_id, reg_key):
        if reg_key not in ("saveFlash", "resetPara", "reserve", "clearErr", "forceClb", "actionSeq", "actionRun", "ID", "baudrate"):
            raise ValueError("reg_key 不支持读 1byte")
        raw = self.read_register(hand_id, REG[reg_key], 1)
        if raw is None or len(raw) != 1:
            return None
        return int(raw[0])

    # ---------- 6 shorts (12 bytes) ----------
    def write6_shorts(self, hand_id, reg_key, values6):
        if reg_key not in ("angleSet", "forceSet", "speedSet", "currentLimit", "defaultSpeedSet", "defaultForceSet"):
            raise ValueError("reg_key 不支持写6short")
        if len(values6) != 6:
            raise ValueError("values6 长度必须为6")

        data = bytearray()
        for v in values6:
            if v < -1 or v > 2000:
                raise ValueError("数值超范围：建议 -1 或 0~2000")
            vv = v & 0xFFFF
            data.append(vv & 0xFF)
            data.append((vv >> 8) & 0xFF)

        self.write_register(hand_id, REG[reg_key], data)

    def read6_shorts(self, hand_id, reg_key):
        if reg_key not in ("angleSet", "forceSet", "speedSet",
                           "currentLimit", "defaultSpeedSet", "defaultForceSet",
                           "angleAct", "forceAct"):
            raise ValueError("reg_key 不支持读6short")
        raw = self.read_register(hand_id, REG[reg_key], 12)
        if raw is None or len(raw) != 12:
            return None
        vals = []
        for i in range(6):
            v = int.from_bytes(raw[2 * i:2 * i + 2], byteorder="little", signed=True)
            vals.append(v)
        return vals

    def read6_ushorts(self, hand_id, reg_key):
        """读取 6 路 unsigned short（用于 CURRENT 这类只读非负量）"""
        if reg_key not in ("current",):
            raise ValueError("reg_key 不支持 read6_ushorts")
        raw = self.read_register(hand_id, REG[reg_key], 12)
        if raw is None or len(raw) != 12:
            return None
        vals = []
        for i in range(6):
            v = int.from_bytes(raw[2 * i:2 * i + 2], byteorder="little", signed=False)
            vals.append(v)
        return vals

    # ---------- 6 bytes ----------
    def read6_bytes(self, hand_id, reg_key):
        if reg_key not in ("errCode", "statusCode", "temp"):
            raise ValueError("reg_key 必须为 errCode/statusCode/temp")
        raw = self.read_register(hand_id, REG[reg_key], 6)
        if raw is None or len(raw) != 6:
            return None
        return list(raw)

    # ---------- higher-level ops ----------
    def clear_error(self, hand_id):
        self.write1_byte(hand_id, "clearErr", 1)

    def force_calibrate(self, hand_id):
        self.write1_byte(hand_id, "forceClb", 1)

    def set_action_seq(self, hand_id, idx):
        self.write1_byte(hand_id, "actionSeq", idx)

    def run_action_seq(self, hand_id):
        self.write1_byte(hand_id, "actionRun", 1)

    def save_to_flash(self, hand_id, wait_s=1.8):
        """
        SAVE=1 后，会返回“保存结果信息帧”，Data=0x00 成功 / 0xFF 失败（不同固件可能略有差异）
        这里做了兼容：cmd 字节允许 0x11 或 0x12
        """
        self.write1_byte(hand_id, "saveFlash", 1)

        addr = REG["saveFlash"]
        addr_l = addr & 0xFF
        addr_h = (addr >> 8) & 0xFF

        t0 = time.time()
        with self.lock:
            while (time.time() - t0) < wait_s:
                pkt = self._read_packet(timeout=min(0.35, wait_s - (time.time() - t0)))
                if pkt is None or len(pkt) < 9:
                    continue
                if pkt[2] != hand_id:
                    continue
                if pkt[4] not in (0x11, 0x12):
                    continue
                # 典型格式：len=4, addrL, addrH, data(1B)
                if pkt[3] == 4 and pkt[5] == addr_l and pkt[6] == addr_h:
                    return pkt[7]
        return None

    def factory_reset(self, hand_id):
        self.write1_byte(hand_id, "resetPara", 1)

    def write_reserve(self, hand_id, value):
        self.write1_byte(hand_id, "reserve", value)

    def read_reserve(self, hand_id):
        return self.read1_byte(hand_id, "reserve")


class RH56GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RH56 灵巧手调试 GUI（角度/力控/速度/状态回读）")
        self.root.geometry(CONFIG["default_geometry"])
        self.root.minsize(1100, 650)

        # 顶部栏
        self._build_topbar()
        self._build_pollbar()

        # 主区：Panedwindow（上：主内容，下：日志，可拉伸）
        self.vpaned = ttk.Panedwindow(self.root, orient=tk.VERTICAL)
        self.vpaned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.main_area = ttk.Frame(self.vpaned)
        self.log_area = ttk.Frame(self.vpaned)
        self.vpaned.add(self.main_area, weight=8)
        self.vpaned.add(self.log_area, weight=2)

        # 日志
        self.log = ScrolledText(self.log_area, height=8)
        self.log.pack(fill=tk.BOTH, expand=True)

        def logger(msg):
            ts = time.strftime("%H:%M:%S")
            self.log.insert(tk.END, f"[{ts}] {msg}\n")
            self.log.see(tk.END)

        self.logger = logger
        self.ctrl = RH56Controller(logger)

        # 主内容：左右分栏
        self._build_main_panels()

        self._refresh_ports()
        self._set_defaults()

        self._poll_loop()

    # ============ UI ============
    def _build_topbar(self):
        frm = ttk.Frame(self.root)
        frm.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(8, 4))

        ttk.Label(frm, text="串口:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(frm, textvariable=self.port_var, width=12, state="readonly")
        self.port_combo.pack(side=tk.LEFT, padx=6)
        ttk.Button(frm, text="刷新串口", command=self._refresh_ports).pack(side=tk.LEFT, padx=6)

        ttk.Label(frm, text="波特率:").pack(side=tk.LEFT)
        self.baud_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.baud_var, width=10).pack(side=tk.LEFT, padx=6)

        ttk.Label(frm, text="手 ID:").pack(side=tk.LEFT)
        self.id_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.id_var, width=6).pack(side=tk.LEFT, padx=6)

        self.conn_status = tk.StringVar(value="未连接")
        ttk.Label(frm, textvariable=self.conn_status, foreground="#444").pack(side=tk.LEFT, padx=10)

        ttk.Button(frm, text="连接", command=self.on_connect).pack(side=tk.LEFT, padx=6)
        ttk.Button(frm, text="断开", command=self.on_disconnect).pack(side=tk.LEFT, padx=6)

        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=(2, 6))

    def _build_pollbar(self):
        frm = ttk.Frame(self.root)
        frm.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(0, 6))

        self.polling_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="自动回读(角度/受力/电流/状态/温度/故障)", variable=self.polling_enabled).pack(side=tk.LEFT)

        ttk.Button(frm, text="回读一次", command=self.on_read_once).pack(side=tk.LEFT, padx=8)
        ttk.Button(frm, text="清除错误(clearErr)", command=self.on_clear_error).pack(side=tk.LEFT, padx=8)
        ttk.Button(frm, text="力传感器校准(forceClb)", command=self.on_force_calibrate).pack(side=tk.LEFT, padx=8)

        self.show_log = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="显示日志", variable=self.show_log, command=self._toggle_log).pack(side=tk.RIGHT)

        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=(6, 0))

    def _build_main_panels(self):
        hpaned = ttk.Panedwindow(self.main_area, orient=tk.HORIZONTAL)
        hpaned.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(hpaned)
        right = ttk.Frame(hpaned)
        hpaned.add(left, weight=3)
        hpaned.add(right, weight=4)

        # 左侧：Notebook
        nb = ttk.Notebook(left)
        nb.pack(fill=tk.BOTH, expand=True)

        tab_angle = ttk.Frame(nb)
        tab_force = ttk.Frame(nb)
        tab_speed = ttk.Frame(nb)
        tab_curr_lim = ttk.Frame(nb)
        tab_pwr_speed = ttk.Frame(nb)
        tab_pwr_force = ttk.Frame(nb)

        nb.add(tab_angle, text="ANGLE_SET")
        nb.add(tab_force, text="FORCE_SET")
        nb.add(tab_speed, text="SPEED_SET")
        nb.add(tab_curr_lim, text="CURRENT_LIMIT")
        nb.add(tab_pwr_speed, text="DEFAULT_SPEED")
        nb.add(tab_pwr_force, text="DEFAULT_FORCE")

        self._build_6dof_panel(
            tab_angle, title="ANGLE_SET (0~1000, -1不设置)", reg_key="angleSet",
            value_ranges=[(0, 1000)] * 6, allow_skip=True
        )
        self._build_6dof_panel(
            tab_force, title="FORCE_SET (0~1000 g, -1不设置)", reg_key="forceSet",
            value_ranges=[(0, 1000)] * 6, allow_skip=True
        )
        self._build_6dof_panel(
            tab_speed, title="SPEED_SET (0~1000, -1不设置)", reg_key="speedSet",
            value_ranges=[(0, 1000)] * 6, allow_skip=True
        )

        self._build_6dof_panel(
            tab_curr_lim, title="CURRENT_LIMIT(m) 电流保护值 (mA, 0~1500)", reg_key="currentLimit",
            value_ranges=[(0, 1500)] * 6, allow_skip=False
        )
        self._build_6dof_panel(
            tab_pwr_speed, title="DEFAULT_SPEED_SET(m) 上电初始速度 (0~1000)", reg_key="defaultSpeedSet",
            value_ranges=[(0, 1000)] * 6, allow_skip=False
        )
        self._build_6dof_panel(
            tab_pwr_force, title="DEFAULT_FORCE_SET(m) 上电初始力控 (g)", reg_key="defaultForceSet",
            value_ranges=[(0, 1000), (0, 1000), (0, 1000), (0, 1000), (0, 1500), (0, 1500)],
            allow_skip=False
        )

        # 右侧：回读 + 参数管理 + 动作
        self._build_readback_panel(right)
        self._build_param_mgmt_panel(right)
        self._build_action_panel(right)

    def _build_6dof_panel(self, parent, title, reg_key, value_ranges, allow_skip: bool):
        """
        value_ranges: list[(min,max)] 长度为 6
        allow_skip: 是否允许 -1 不设置（对应 GUI 的“不设置(-1)”）
        """
        card = ttk.LabelFrame(parent, text=title)
        card.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        vars_val, vars_skip = [], []
        scales, entries = [], []

        def set_widget_enabled(idx, enabled: bool):
            if enabled:
                try:
                    entries[idx].state(["!disabled"])
                except Exception:
                    entries[idx].configure(state="normal")
                try:
                    scales[idx].state(["!disabled"])
                except Exception:
                    pass
            else:
                try:
                    entries[idx].state(["disabled"])
                except Exception:
                    entries[idx].configure(state="disabled")
                try:
                    scales[idx].state(["disabled"])
                except Exception:
                    pass

        for i, name in enumerate(DOF_NAMES):
            row = ttk.Frame(card)
            row.pack(fill=tk.X, padx=8, pady=3)

            ttk.Label(row, text=f"{i}:{name}", width=10).pack(side=tk.LEFT)

            ent_var = tk.StringVar(value="0")
            skip_var = tk.BooleanVar(value=False)

            vmin, vmax = value_ranges[i]
            scale = ttk.Scale(row, from_=vmin, to=vmax, orient=tk.HORIZONTAL)
            scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)

            ent = ttk.Entry(row, textvariable=ent_var, width=7)
            ent.pack(side=tk.LEFT, padx=6)

            # 可选：不设置(-1)
            if allow_skip:
                def make_on_skip(idx):
                    def _on_skip():
                        if vars_skip[idx].get():
                            vars_val[idx].set("-1")
                            set_widget_enabled(idx, False)
                        else:
                            v0 = int(value_ranges[idx][0])
                            vars_val[idx].set(str(v0))
                            scales[idx].set(v0)
                            set_widget_enabled(idx, True)
                    return _on_skip

                cb = ttk.Checkbutton(row, text="不设置(-1)", variable=skip_var, command=make_on_skip(i))
                cb.pack(side=tk.LEFT, padx=6)

            def make_on_slide(scale_obj, entry_var, idx):
                def _on(_):
                    if allow_skip and vars_skip[idx].get():
                        return
                    entry_var.set(str(int(float(scale_obj.get()))))
                return _on

            scale.configure(command=make_on_slide(scale, ent_var, i))

            def make_apply_entry(scale_obj, entry_var, idx):
                def _apply(_=None):
                    if allow_skip and vars_skip[idx].get():
                        return
                    try:
                        v = int(entry_var.get())
                        vmin2, vmax2 = value_ranges[idx]
                        v = max(vmin2, min(vmax2, v))
                        scale_obj.set(v)
                        entry_var.set(str(v))
                    except Exception:
                        pass
                return _apply

            ent.bind("<Return>", make_apply_entry(scale, ent_var, i))
            ent.bind("<FocusOut>", make_apply_entry(scale, ent_var, i))

            vars_val.append(ent_var)
            vars_skip.append(skip_var)
            scales.append(scale)
            entries.append(ent)

        btn_row = ttk.Frame(card)
        btn_row.pack(fill=tk.X, padx=8, pady=(8, 6))

        ttk.Button(
            btn_row, text=f"写入 {reg_key}",
            command=lambda: self.on_apply_6dof(reg_key, vars_val, vars_skip, value_ranges, allow_skip)
        ).pack(side=tk.LEFT)

        ttk.Button(
            btn_row, text=f"读取 {reg_key}",
            command=lambda: self.on_load_6dof(reg_key, vars_val, vars_skip, scales, entries, value_ranges, allow_skip)
        ).pack(side=tk.LEFT, padx=8)

        ttk.Button(
            btn_row, text="全部设为 0",
            command=lambda: self._set_all(vars_val, vars_skip, value_ranges, allow_skip, mode="zero", scales=scales, entries=entries)
        ).pack(side=tk.LEFT, padx=8)

        ttk.Button(
            btn_row, text="全部设为 最大",
            command=lambda: self._set_all(vars_val, vars_skip, value_ranges, allow_skip, mode="max", scales=scales, entries=entries)
        ).pack(side=tk.LEFT, padx=8)

        if reg_key in ("currentLimit", "defaultSpeedSet", "defaultForceSet"):
            ttk.Label(
                card,
                text="提示：这些寄存器为“可断电保存参数”。通常修改后建议再点右侧“保存到Flash(SAVE=1)”。",
                foreground="#555",
                wraplength=520,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, padx=8, pady=(2, 6))

    def _build_readback_panel(self, parent):
        card = ttk.LabelFrame(parent, text="回读区（ANGLE_ACT / FORCE_ACT / CURRENT / STATUS / TEMP / ERROR）")
        card.pack(fill=tk.BOTH, expand=True, padx=6, pady=(6, 3))

        cols = ("dof", "angle_act", "force_act", "current", "status", "temp", "error")
        self.tree = ttk.Treeview(card, columns=cols, show="headings", height=10)

        for c, t, w in [
            ("dof", "自由度", 140),
            ("angle_act", "角度实际(0~1000)", 130),
            ("force_act", "受力(g)", 100),
            ("current", "电流(mA)", 95),
            ("status", "状态码", 80),
            ("temp", "温度(℃)", 80),
            ("error", "故障码", 90),
        ]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor=tk.CENTER)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        for i, name in enumerate(DOF_NAMES):
            self.tree.insert("", tk.END, iid=str(i), values=(f"{i}:{name}", "-", "-", "-", "-", "-", "-"))

        ttk.Label(
            card,
            text="状态码参考：0松开 1抓取 2位置到位停 3力控到位停 5电流保护停 6堵转停 7故障停（见手册 STATUS）",
            foreground="#555",
            wraplength=520,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=8, pady=(0, 8))

    def _build_param_mgmt_panel(self, parent):
        card = ttk.LabelFrame(parent, text="参数管理（SAVE / RESET_PARA / reserve）")
        card.pack(fill=tk.X, padx=6, pady=(3, 6))

        row1 = ttk.Frame(card)
        row1.pack(fill=tk.X, padx=8, pady=(8, 4))

        ttk.Button(row1, text="保存到Flash (SAVE=1)", command=self.on_save_flash).pack(side=tk.LEFT)
        ttk.Button(row1, text="恢复出厂设置 (RESET=1)", command=self.on_factory_reset).pack(side=tk.LEFT, padx=8)

        row2 = ttk.Frame(card)
        row2.pack(fill=tk.X, padx=8, pady=(4, 8))

        ttk.Label(row2, text="reserve(1008):").pack(side=tk.LEFT)
        self.reserve_var = tk.StringVar(value="0")
        ttk.Entry(row2, textvariable=self.reserve_var, width=8).pack(side=tk.LEFT, padx=6)
        ttk.Button(row2, text="读取", command=self.on_read_reserve).pack(side=tk.LEFT, padx=6)
        ttk.Button(row2, text="写入", command=self.on_write_reserve).pack(side=tk.LEFT, padx=6)

        ttk.Label(
            card,
            text="说明：reserve 为手册标注“保留”寄存器，仅建议用于调试/验证，不建议在业务逻辑依赖其含义。",
            foreground="#555",
            wraplength=620,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=8, pady=(0, 8))

    def _build_action_panel(self, parent):
        card = ttk.LabelFrame(parent, text="动作序列（ACTION_SEQ_INDEX / RUN）")
        card.pack(fill=tk.X, padx=6, pady=(3, 6))

        row = ttk.Frame(card)
        row.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(row, text="序列索引:").pack(side=tk.LEFT)
        self.action_idx_var = tk.StringVar(value="8")
        ttk.Entry(row, textvariable=self.action_idx_var, width=8).pack(side=tk.LEFT, padx=8)

        ttk.Button(row, text="设置索引", command=self.on_set_action_seq).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="运行序列", command=self.on_run_action_seq).pack(side=tk.LEFT, padx=6)

        ttk.Label(card, text="提示：运行结束后 RUN 寄存器会自动清零（手册说明）。", foreground="#555").pack(anchor=tk.W, padx=8, pady=(0, 8))

    # ============ helpers ============
    def _toggle_log(self):
        if self.show_log.get():
            panes = self.vpaned.panes()
            if str(self.log_area) not in panes:
                self.vpaned.add(self.log_area, weight=2)
        else:
            panes = self.vpaned.panes()
            if str(self.log_area) in panes:
                self.vpaned.forget(self.log_area)

    def _refresh_ports(self):
        ports = [p.device for p in list_ports.comports()]
        if not ports:
            ports = [CONFIG["default_port"]]
        self.port_combo["values"] = ports
        if self.port_var.get() not in ports:
            self.port_var.set(ports[0])

    def _set_defaults(self):
        # Linux 下端口号常变化（/dev/ttyUSB0, /dev/ttyUSB1, /dev/ttyACM0...），
        # 若当前列表中不存在默认端口，不要强制覆盖为默认值。
        ports = list(self.port_combo["values"])
        if self.port_var.get() and self.port_var.get() in ports:
            pass
        elif CONFIG["default_port"] in ports:
            self.port_var.set(CONFIG["default_port"])
        elif ports:
            self.port_var.set(ports[0])
        else:
            self.port_var.set(CONFIG["default_port"])
        self.baud_var.set(str(CONFIG["default_baud"]))
        self.id_var.set(str(CONFIG["default_id"]))

    def _set_all(self, vars_val, vars_skip, value_ranges, allow_skip, mode, scales=None, entries=None):
        for i, (ev, sv) in enumerate(zip(vars_val, vars_skip)):
            if allow_skip:
                sv.set(False)
                if entries is not None:
                    try:
                        entries[i].state(["!disabled"])
                    except Exception:
                        entries[i].configure(state="normal")
                if scales is not None:
                    try:
                        scales[i].state(["!disabled"])
                    except Exception:
                        pass

            if mode == "zero":
                v = int(value_ranges[i][0])
            elif mode == "max":
                v = int(value_ranges[i][1])
            else:
                v = int(value_ranges[i][0])

            ev.set(str(v))
            if scales is not None:
                scales[i].set(v)

    def _get_hand_id(self):
        try:
            hid = int(self.id_var.get())
            if hid < 1 or hid > 254:
                raise ValueError
            return hid
        except Exception:
            raise ValueError("手 ID 必须为 1~254")

    def _ensure_connected(self):
        if not self.ctrl.is_open():
            raise RuntimeError("请先连接串口")

    # ============ callbacks ============
    def on_connect(self):
        try:
            self._refresh_ports()
            port = self.port_var.get().strip()
            if not port:
                raise RuntimeError("未检测到可用串口，请先插好设备后点击“刷新串口”")

            # Linux 下先做设备存在/权限预检查，给出更明确提示
            if os.name == "posix" and port.startswith("/dev/"):
                if not os.path.exists(port):
                    raise RuntimeError(f"串口设备不存在：{port}")
                can_rw = os.access(port, os.R_OK | os.W_OK)
                if not can_rw:
                    st = os.stat(port)
                    try:
                        dev_group = grp.getgrgid(st.st_gid).gr_name
                    except Exception:
                        dev_group = str(st.st_gid)
                    my_groups = []
                    try:
                        my_groups = [grp.getgrgid(g).gr_name for g in os.getgroups()]
                    except Exception:
                        pass
                    raise PermissionError(
                        f"当前用户对 {port} 无读写权限。设备组={dev_group}，当前用户组={my_groups}"
                    )

            baud = int(self.baud_var.get().strip())
            self.ctrl.open(port, baud)
            self.conn_status.set(f"已连接：{port}@{baud}")
        except Exception as e:
            msg = str(e)
            lmsg = msg.lower()
            if ("permission" in lmsg) or ("denied" in lmsg) or (getattr(e, "errno", None) == errno.EACCES):
                msg = (
                    f"{msg}\n\n"
                    "Linux 串口权限不足。请执行：\n"
                    "1) sudo usermod -a -G dialout $USER\n"
                    "2) 重新登录系统（或重启）\n"
                    "3) 确认设备存在：ls /dev/ttyUSB* /dev/ttyACM*\n"
                )
            elif ("resource busy" in lmsg) or ("could not exclusively lock" in lmsg) or (getattr(e, "errno", None) == errno.EBUSY):
                msg = (
                    f"{msg}\n\n"
                    "串口被占用。请关闭其它串口工具（如 minicom/串口助手/其他Python进程）后重试。"
                )
            messagebox.showerror("连接失败", msg)

    def on_disconnect(self):
        self.ctrl.close()
        self.conn_status.set("未连接")

    def on_apply_6dof(self, reg_key, vars_val, vars_skip, value_ranges, allow_skip: bool):
        try:
            self._ensure_connected()
            hid = self._get_hand_id()

            vals = []
            for i, (ev, sv) in enumerate(zip(vars_val, vars_skip)):
                if allow_skip and sv.get():
                    vals.append(-1)
                    continue

                v = int(ev.get())
                vmin, vmax = value_ranges[i]
                if not (vmin <= v <= vmax):
                    raise ValueError(f"{reg_key} 第{i}路范围应为 {vmin}~{vmax}" + ("（或勾选不设置=-1）" if allow_skip else ""))
                vals.append(v)

            self.ctrl.write6_shorts(hid, reg_key, vals)
            self.logger(f"➡️ 写入 {reg_key}: {vals}")
        except Exception as e:
            messagebox.showerror("写入失败", str(e))

    def on_load_6dof(self, reg_key, vars_val, vars_skip, scales, entries, value_ranges, allow_skip: bool):
        try:
            self._ensure_connected()
            hid = self._get_hand_id()

            vals = self.ctrl.read6_shorts(hid, reg_key)
            if vals is None:
                raise RuntimeError(f"读取 {reg_key} 失败（无返回）")

            for i, v in enumerate(vals):
                if allow_skip and v == -1:
                    vars_skip[i].set(True)
                    vars_val[i].set("-1")
                    try:
                        entries[i].state(["disabled"])
                    except Exception:
                        entries[i].configure(state="disabled")
                    try:
                        scales[i].state(["disabled"])
                    except Exception:
                        pass
                else:
                    vars_skip[i].set(False)
                    vmin, vmax = value_ranges[i]
                    v = max(vmin, min(vmax, int(v)))
                    vars_val[i].set(str(v))
                    scales[i].set(v)
                    try:
                        entries[i].state(["!disabled"])
                    except Exception:
                        entries[i].configure(state="normal")
                    try:
                        scales[i].state(["!disabled"])
                    except Exception:
                        pass

            self.logger(f"⬅️ 读取 {reg_key}: {vals}")
        except Exception as e:
            messagebox.showerror("读取失败", str(e))

    def on_read_once(self):
        try:
            self._ensure_connected()
            hid = self._get_hand_id()

            angle = self.ctrl.read6_shorts(hid, "angleAct")
            force = self.ctrl.read6_shorts(hid, "forceAct")
            current = self.ctrl.read6_ushorts(hid, "current")
            status = self.ctrl.read6_bytes(hid, "statusCode")
            temp = self.ctrl.read6_bytes(hid, "temp")
            err = self.ctrl.read6_bytes(hid, "errCode")

            if angle is None: angle = ["-"] * 6
            if force is None: force = ["-"] * 6
            if current is None: current = ["-"] * 6
            if status is None: status = ["-"] * 6
            if temp is None: temp = ["-"] * 6
            if err is None: err = ["-"] * 6

            for i in range(6):
                self.tree.set(str(i), "angle_act", angle[i])
                self.tree.set(str(i), "force_act", force[i])
                self.tree.set(str(i), "current", current[i])
                self.tree.set(str(i), "status", status[i])
                self.tree.set(str(i), "temp", temp[i])
                self.tree.set(str(i), "error", f"0x{err[i]:02X}" if isinstance(err[i], int) else err[i])

        except Exception as e:
            messagebox.showerror("回读失败", str(e))

    def on_clear_error(self):
        try:
            self._ensure_connected()
            hid = self._get_hand_id()
            self.ctrl.clear_error(hid)
            self.logger("🧹 已发送 clearErr=1（清除可清除故障）")
        except Exception as e:
            messagebox.showerror("清错失败", str(e))

    def on_force_calibrate(self):
        if not messagebox.askyesno("确认校准", "力传感器校准需要空载（手指不接触任何物体）。\n确认开始？"):
            return
        try:
            self._ensure_connected()
            hid = self._get_hand_id()
            self.ctrl.force_calibrate(hid)
            self.logger("🧪 已发送 forceClb=1（开始力传感器校准）")
        except Exception as e:
            messagebox.showerror("校准失败", str(e))

    def on_save_flash(self):
        if not messagebox.askyesno("确认保存", "将当前参数保存到 Flash（断电不丢失）。\n确认执行 SAVE=1？"):
            return
        try:
            self._ensure_connected()
            hid = self._get_hand_id()
            self.logger("💾 正在保存到Flash...（等待结果帧）")
            code = self.ctrl.save_to_flash(hid, wait_s=1.8)
            if code is None:
                self.logger("⚠️ 未收到保存结果帧（可能超时/丢包），请查看串口连接或重试")
                messagebox.showwarning("保存可能未确认", "未收到保存结果帧（超时）。建议重试或检查串口链路。")
            elif code == 0x00:
                self.logger("✅ 保存成功（SAVE result=0x00）")
                messagebox.showinfo("保存成功", "保存成功（设备返回 0x00）")
            else:
                self.logger(f"❌ 保存失败（SAVE result=0x{code:02X}）")
                messagebox.showerror("保存失败", f"保存失败（设备返回 0x{code:02X}）")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def on_factory_reset(self):
        if not messagebox.askyesno("确认恢复出厂", "恢复出厂设置会覆盖当前参数。\n确认执行 RESET_PARA=1？"):
            return
        try:
            self._ensure_connected()
            hid = self._get_hand_id()
            self.ctrl.factory_reset(hid)
            self.logger("🧯 已发送 RESET_PARA=1（恢复出厂设置）")
            messagebox.showinfo("已发送", "已发送恢复出厂命令。必要时可重新读取各参数确认。")
        except Exception as e:
            messagebox.showerror("恢复失败", str(e))

    def on_read_reserve(self):
        try:
            self._ensure_connected()
            hid = self._get_hand_id()
            v = self.ctrl.read_reserve(hid)
            if v is None:
                raise RuntimeError("读取 reserve 失败（无返回）")
            self.reserve_var.set(str(int(v)))
            self.logger(f"⬅️ 读取 reserve= {v}")
        except Exception as e:
            messagebox.showerror("读取失败", str(e))

    def on_write_reserve(self):
        try:
            self._ensure_connected()
            hid = self._get_hand_id()
            v = int(self.reserve_var.get())
            if v < 0 or v > 255:
                raise ValueError("reserve 必须为 0~255")
            self.ctrl.write_reserve(hid, v)
            self.logger(f"➡️ 写入 reserve= {v}")
        except Exception as e:
            messagebox.showerror("写入失败", str(e))

    def on_set_action_seq(self):
        try:
            self._ensure_connected()
            hid = self._get_hand_id()
            idx = int(self.action_idx_var.get())
            if idx < 0 or idx > 255:
                raise ValueError("序列索引建议 0~255")
            self.ctrl.set_action_seq(hid, idx)
            self.logger(f"📌 已设置 actionSeq={idx}")
        except Exception as e:
            messagebox.showerror("设置失败", str(e))

    def on_run_action_seq(self):
        try:
            self._ensure_connected()
            hid = self._get_hand_id()
            self.ctrl.run_action_seq(hid)
            self.logger("▶️ 已发送 actionRun=1（运行当前动作序列）")
        except Exception as e:
            messagebox.showerror("运行失败", str(e))

    # ============ polling ============
    def _poll_loop(self):
        if self.polling_enabled.get() and self.ctrl.is_open():
            try:
                self.on_read_once()
            except Exception:
                pass
        self.root.after(CONFIG["poll_interval_ms"], self._poll_loop)


def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass
    RH56GUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
