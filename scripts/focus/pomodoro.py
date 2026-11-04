# -*- coding: utf-8 -*-
"""
前进吧zzz —— 置顶监督 + 番茄钟 + 游戏化激励（增强版）

一个帮助你对抗低自制力的悬浮番茄钟：
  · 窗口始终置顶，盖在其它窗口之上，时刻提醒你专注
  · 制定任务计划 + 预计完成时间（番茄数）
  · 番茄工作法：25 分钟专注 / 5 分钟短休 / 15 分钟长休（每 4 个番茄一轮），时长可自定义
  · 完成任务 / 番茄后：合成欢快旋律音效 + 彩带特效 + 鼓励语
  · 游戏化：XP、等级称号、连击天数、今日番茄与专注时长统计
  · 增强：自定义时长、系统托盘、任务栏进度条、专注热力图、开机自启

纯标准库实现（tkinter + winsound + ctypes + winreg），托盘可选依赖 pystray+Pillow。

运行方式：
    python scripts/focus/pomodoro.py
"""

import ctypes
import json
import math
import os
import queue
import random
import struct
import sys
import threading
import tkinter as tk
import uuid
import wave
from ctypes import wintypes
from datetime import date, datetime, timedelta
from tkinter import ttk

try:
    import winsound
except ImportError:  # 非 Windows 环境降级处理
    winsound = None

try:
    import winreg
except ImportError:
    winreg = None

try:
    import pystray
except ImportError:
    pystray = None

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = ImageDraw = None


# ============================ 常量与配色 ============================
APP_TITLE = "前进吧zzz"
SCRIPT_PATH = os.path.abspath(__file__)
BASE_DIR = os.path.dirname(SCRIPT_PATH)
DATA_PATH = os.path.join(BASE_DIR, "focus_data.json")
SOUND_DIR = os.path.join(BASE_DIR, "sounds")

# 温暖、多巴胺向配色
BG = "#fff7ed"            # 暖米白背景
CARD = "#ffffff"          # 卡片
TEXT = "#2d2a26"          # 主文字
MUTED = "#8a857e"         # 次要文字
WORK_COLOR = "#f25c4d"    # 工作红（番茄）
BREAK_COLOR = "#3fbf8f"   # 休息绿
GOLD = "#f5a623"          # 奖励金
RING_TRACK = "#f0e6dc"    # 进度环底轨

CONFETTI_COLORS = ["#f25c4d", "#f5a623", "#3fbf8f", "#4a90d9",
                   "#9b6dd6", "#f274a8", "#ffd166", "#57c7c2"]

# 等级称号（等级 = 累计 XP // 100）
TITLES = ["番茄种子", "破土新芽", "嫩绿幼苗", "茁壮小苗", "专注新星",
          "专注学徒", "专注达人", "时间管理师", "自律高手", "效率传奇",
          "专注大师", "番茄之神"]

XP_PER_POMODORO = 25      # 每完成一个番茄获得的经验
XP_PER_TASK = 30          # 每完成一个任务获得的额外经验

DEFAULT_SETTINGS = {
    "work_min": 25,
    "short_break_min": 5,
    "long_break_min": 15,
    "long_every": 4,
    "tray_enabled": True,
}

# 开机自启注册表
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_RUN_NAME = "FocusTomato"

# 鼓励语库
ENCOURAGE_START = [
    "开始专注啦，就 25 分钟，你一定行 💪",
    "深呼吸，开始进入心流状态 🌊",
    "把手机放远点，我们一起搞定它 🔒",
    "专注 25 分钟，然后就能理直气壮休息啦 🎯",
    "现在开始，比什么都重要 ✨",
]

ENCOURAGE_WORK = [
    "太棒了！又拿下了一颗番茄 🍅",
    "专注的你，闪闪发光 ✨",
    "坚持就是胜利，你已经很棒了！",
    "每一颗番茄，都是成长的印记 💪",
    "好样的！继续保持这个节奏！",
    "你比昨天的自己又强了一点 🚀",
    "又完成一个，离目标更近了 🎯",
    "太厉害了，奖励自己休息一下吧 🎉",
    "自律给你自由，继续加油 🔥",
    "专注是最稀缺的能力，而你正在拥有它 ⭐",
    "厉害！这个番茄被你稳稳拿捏 🍅",
    "看着进度一点点涨，是不是很爽 😎",
]

ENCOURAGE_TASK = [
    "🎉 任务完成！你就是传说中的行动派！",
    "🏆 又清掉一件待办，轻松感拉满！",
    "🌟 说干就干，干完就爽，太优秀了！",
    "🥳 任务清零，成就感爆棚！",
    "💯 完美收工！给自己点个大大的赞！",
    "🎊 完成的感觉，就是这么上瘾！",
]

ENCOURAGE_BREAK = [
    "休息一下，喝口水，你值得的 🍵",
    "起来伸个懒腰，看看远方 👀",
    "让大脑歇一歇，等下状态会更好 🌿",
    "短暂休息是为了更高效地出发 ⛽",
]


# ============================ 音效（合成 WAV） ============================
SAMPLE_RATE = 22050
C5, E5, G5, C6, E6 = 523.25, 659.25, 783.99, 1046.50, 1318.50

# 音效规格：音符 (频率, 起始秒, 时长秒, 振幅)
SOUND_SPECS = {
    "success": [(C5, 0.00, 0.16, 0.9), (E5, 0.14, 0.16, 0.9),
                (G5, 0.28, 0.16, 0.9), (C6, 0.42, 0.55, 0.9)],
    "fanfare": [(C5, 0.00, 0.13, 0.9), (E5, 0.11, 0.13, 0.9),
                (G5, 0.22, 0.13, 0.9), (C6, 0.33, 0.20, 0.95),
                (G5, 0.52, 0.13, 0.9), (C6, 0.63, 0.20, 0.95),
                (E6, 0.82, 0.55, 0.95)],
    "soft": [(E5, 0.0, 0.30, 0.6)],
}

# Beep 旋律兜底（winsound 合成失败时使用）
FALLBACK_MELODY = {
    "success": [(523, 120), (659, 120), (784, 120), (1047, 320)],
    "fanfare": [(523, 110), (659, 110), (784, 110), (1047, 160),
                (784, 110), (1047, 160), (1319, 360)],
    "soft": [(659, 90), (784, 140)],
}


def _synthesize(path, tones):
    """把音符序列合成一段带衰减包络的铃声，写入 WAV。"""
    total = max((s + d for _, s, d, _ in tones), default=0.0) + 0.15
    n = int(SAMPLE_RATE * total)
    buf = [0.0] * n
    for freq, start, dur, amp in tones:
        i0 = int(start * SAMPLE_RATE)
        i1 = min(n, i0 + int(dur * SAMPLE_RATE))
        for i in range(i0, i1):
            t = (i - i0) / SAMPLE_RATE
            attack = min(1.0, t / 0.012)
            decay = math.exp(-4.0 * t / dur)
            env = attack * decay
            v = (math.sin(2 * math.pi * freq * t) * 0.6 +
                 math.sin(2 * math.pi * freq * 2 * t) * 0.25 +
                 math.sin(2 * math.pi * freq * 3 * t) * 0.15)
            buf[i] += v * env * amp
    peak = max(1.0, max(abs(x) for x in buf))
    frames = b"".join(struct.pack("<h", int(x / peak * 32000)) for x in buf)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(frames)


def ensure_sounds():
    """首次运行时生成音效文件，失败则返回 False。"""
    try:
        os.makedirs(SOUND_DIR, exist_ok=True)
        for name, tones in SOUND_SPECS.items():
            path = os.path.join(SOUND_DIR, name + ".wav")
            if not os.path.exists(path):
                _synthesize(path, tones)
        return True
    except Exception:
        return False


def _play_notes(notes):
    if winsound is None:
        return
    for freq, ms in notes:
        winsound.Beep(freq, ms)


def play_sound(name):
    """播放音效：优先合成 WAV（异步，不阻塞），失败则退回 Beep 旋律。"""
    if winsound is None:
        return
    path = os.path.join(SOUND_DIR, name + ".wav")
    if os.path.exists(path):
        try:
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return
        except Exception:
            pass
    beep = FALLBACK_MELODY.get(name)
    if beep:
        threading.Thread(target=_play_notes, args=(beep,), daemon=True).start()


def play_system_sound():
    if winsound is None:
        return
    try:
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except Exception:
        pass


# ============================ 任务栏进度条（ctypes） ============================
class _GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", wintypes.BYTE * 8)]


def _make_guid(s):
    u = uuid.UUID(s)
    return _GUID(u.time_low, u.time_mid, u.time_hi_version,
                 (wintypes.BYTE * 8)(*u.bytes_le[8:16]))


_SetProgressValue = ctypes.WINFUNCTYPE(
    ctypes.HRESULT, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulonglong, ctypes.c_ulonglong)
_SetProgressState = ctypes.WINFUNCTYPE(
    ctypes.HRESULT, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int)
_Release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)

TBPF_NOPROGRESS = 0
TBPF_NORMAL = 2
TBPF_PAUSED = 8


class TaskbarProgress:
    """通过 ITaskbarList3 COM 接口在任务栏按钮上显示进度。"""

    def __init__(self):
        self.hwnd = None
        self.obj = None
        self._set_value = None
        self._set_state = None
        self._release = None

    def bind(self, hwnd):
        self.hwnd = hwnd
        try:
            ctypes.oledll.ole32.CoInitialize(None)
        except Exception:
            pass
        clsid = _make_guid("{56FDF344-FD6D-11d0-958A-006097C9A090}")
        iid = _make_guid("{EA1AFB91-9E28-4B86-90E9-9E9F8A5EEFAF}")
        ptr = ctypes.c_void_p()
        hres = ctypes.oledll.ole32.CoCreateInstance(
            ctypes.byref(clsid), None, 1, ctypes.byref(iid), ctypes.byref(ptr))
        if hres != 0 or not ptr.value:
            return False
        self.obj = ptr
        vtbl_addr = ctypes.cast(ptr.value, ctypes.POINTER(ctypes.c_void_p))[0]
        vtbl = ctypes.cast(vtbl_addr, ctypes.POINTER(ctypes.c_void_p))
        # ITaskbarList3 方法表：SetProgressValue=9, SetProgressState=10, Release=2
        self._set_value = _SetProgressValue(int(vtbl[9]))
        self._set_state = _SetProgressState(int(vtbl[10]))
        self._release = _Release(int(vtbl[2]))
        return True

    def _hw(self):
        return ctypes.c_void_p(self.hwnd)

    def set_progress(self, frac):
        if not self._set_value:
            return
        try:
            self._set_state(self.obj, self._hw(), TBPF_NORMAL)
            self._set_value(self.obj, self._hw(),
                            ctypes.c_ulonglong(int(frac * 1000)), ctypes.c_ulonglong(1000))
        except Exception:
            pass

    def set_paused(self, frac):
        if not self._set_state:
            return
        try:
            self._set_state(self.obj, self._hw(), TBPF_PAUSED)
            if self._set_value:
                self._set_value(self.obj, self._hw(),
                                ctypes.c_ulonglong(int(frac * 1000)), ctypes.c_ulonglong(1000))
        except Exception:
            pass

    def clear(self):
        if not self._set_state:
            return
        try:
            self._set_state(self.obj, self._hw(), TBPF_NOPROGRESS)
        except Exception:
            pass

    def release(self):
        if self._release and self.obj:
            try:
                self._release(self.obj)
            except Exception:
                pass
        self.obj = None


# ============================ 开机自启（winreg） ============================
def _pythonw_path():
    """返回无控制台窗口的 pythonw.exe 路径。"""
    base = os.path.dirname(sys.executable)
    for name in ("pythonw.exe", "pythonw3.exe"):
        p = os.path.join(base, name)
        if os.path.exists(p):
            return p
    return sys.executable


def get_autostart():
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as k:
            winreg.QueryValueEx(k, APP_RUN_NAME)
            return True
    except OSError:
        return False


def set_autostart(enable, script_path, extra_args=""):
    if winreg is None:
        return
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
    except OSError:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY)
    try:
        if enable:
            cmd = f'"{_pythonw_path()}" "{script_path}" {extra_args}'.strip()
            winreg.SetValueEx(key, APP_RUN_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, APP_RUN_NAME)
            except OSError:
                pass
    finally:
        winreg.CloseKey(key)


# ============================ 数据持久化 ============================
def load_data():
    default = {
        "tasks": [],
        "xp": 0,
        "total_pomodoros": 0,
        "streak": 0,
        "last_active_date": None,
        "history": {},  # {"2026-10-21": {"pomodoros": 3, "minutes": 75}}
        "settings": dict(DEFAULT_SETTINGS),
    }
    if not os.path.exists(DATA_PATH):
        return default
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, val in default.items():
            data.setdefault(key, val)
        data["settings"] = {**DEFAULT_SETTINGS, **data.get("settings", {})}
        return data
    except Exception:
        return default


def save_data(data):
    try:
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ============================ 彩带特效 ============================
class Confetti:
    """在画布上撒彩带的粒子动画。"""

    def __init__(self, canvas, width, height):
        self.canvas = canvas
        self.w = width
        self.h = height
        self.particles = []
        self.running = False

    def burst(self, count=90):
        for _ in range(count):
            x = random.uniform(0, self.w)
            y = random.uniform(-self.h * 0.3, self.h * 0.2)
            vx = random.uniform(-2.2, 2.2)
            vy = random.uniform(2.5, 6.0)
            size = random.randint(4, 9)
            color = random.choice(CONFETTI_COLORS)
            pid = self.canvas.create_oval(x, y, x + size, y + size * 0.6,
                                          fill=color, outline="")
            self.particles.append([pid, x, y, vx, vy, size])
        if not self.running:
            self.running = True
            self._animate()

    def _animate(self):
        alive = []
        for p in self.particles:
            pid, x, y, vx, vy, size = p
            x += vx
            y += vy
            vy += 0.16      # 重力
            vx *= 0.99      # 水平阻尼
            self.canvas.coords(pid, x, y, x + size, y + size * 0.6)
            if y < self.h + 30:
                alive.append([pid, x, y, vx, vy, size])
            else:
                self.canvas.delete(pid)
        self.particles = alive
        if self.particles:
            self.canvas.after(16, self._animate)
        else:
            self.running = False


# ============================ 托盘图标 ============================
def _make_tray_image():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([10, 20, 54, 60], fill="#f25c4d")                      # 番茄身
    d.polygon([(32, 22), (22, 6), (32, 10), (42, 6)], fill="#3fbf8f")  # 叶子
    return img


# ============================ 主应用 ============================
class FocusTomatoApp:
    def __init__(self, root):
        self.root = root
        self.data = load_data()
        self.settings = self.data["settings"]

        self.tray_cmds = queue.Queue()
        self.tray_icon = None
        self.taskbar = TaskbarProgress()
        self.tray_enabled = bool(self.settings.get("tray_enabled", True)) and pystray is not None

        # 番茄钟状态
        self.mode = "work"          # work / short / long
        self.state = "idle"         # idle / running / paused
        self.remaining = self._mode_seconds("work")
        self.total = self.remaining
        self.cycle_count = 0        # 本轮已完成的番茄数

        ensure_sounds()
        self._build_ui()
        self._apply_mode_visual()
        self.refresh_tasks()
        self.refresh_stats()

        if self.tray_enabled:
            self._setup_tray()
        self.root.after(300, self._init_taskbar)
        self._tick_loop()

    # ---------- 工具 ----------
    def _mode_seconds(self, mode):
        if mode == "work":
            return int(self.settings["work_min"]) * 60
        if mode == "long":
            return int(self.settings["long_break_min"]) * 60
        return int(self.settings["short_break_min"]) * 60

    def _mode_label(self, mode):
        return {"work": "专注中", "short": "短休息", "long": "长休息"}[mode]

    def _fmt(self, seconds):
        m, s = divmod(max(0, int(seconds)), 60)
        return f"{m:02d}:{s:02d}"

    def current_task(self):
        """返回第一个未完成的任务（作为自动关联的当前任务）。"""
        for t in self.data["tasks"]:
            if not t.get("done"):
                return t
        return None

    # ---------- UI 构建 ----------
    def _build_ui(self):
        self.root.title(APP_TITLE)
        self.root.geometry("360x700")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.mini = False       # 迷你模式（专注时只保留计时 + 鼓励）
        # 窗口始终置顶
        self.topmost = tk.BooleanVar(value=True)
        self.root.attributes("-topmost", True)

        # ---- 顶部容器（迷你模式下隐藏）----
        self.top_bar = tk.Frame(self.root, bg=BG)
        self.top_bar.pack(fill="x")

        header = tk.Frame(self.top_bar, bg=BG)
        header.pack(fill="x", padx=14, pady=(12, 0))
        tk.Label(header, text=APP_TITLE, font=("Microsoft YaHei UI", 15, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        tk.Checkbutton(header, text="置顶", variable=self.topmost,
                       command=self._toggle_topmost, bg=BG, fg=MUTED,
                       activebackground=BG, font=("Microsoft YaHei UI", 9)).pack(side="right")

        toolbar = tk.Frame(self.top_bar, bg=BG)
        toolbar.pack(fill="x", padx=14, pady=(2, 0))
        self._link_btn(toolbar, "⚙ 设置", self.open_settings).pack(side="left", padx=(0, 10))
        self._link_btn(toolbar, "📊 统计", self.open_stats).pack(side="left")

        self.mode_label = tk.Label(self.top_bar, text="", font=("Microsoft YaHei UI", 13, "bold"),
                                   bg=BG, fg=WORK_COLOR)
        self.mode_label.pack(pady=(6, 0))

        # 计时画布（进度环 + 时间 + 彩带）
        self.canvas = tk.Canvas(self.root, width=300, height=300, bg=BG,
                                highlightthickness=0)
        self.canvas.pack(pady=(2, 0))
        cx, cy, r = 150, 150, 108
        self.ring_track = self.canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r, start=90, extent=-359.9,
            style="arc", width=14, outline=RING_TRACK)
        self.ring = self.canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r, start=90, extent=0,
            style="arc", width=14, outline=WORK_COLOR)
        self.time_text = self.canvas.create_text(
            cx, cy - 8, text=self._fmt(self.remaining),
            font=("Consolas", 40, "bold"), fill=TEXT)
        self.sub_text = self.canvas.create_text(
            cx, cy + 34, text="点击「开始」进入专注", font=("Microsoft YaHei UI", 11),
            fill=MUTED)
        self.confetti = Confetti(self.canvas, 300, 300)

        # 鼓励语
        self.msg_label = tk.Label(self.root, text="设定计划，开始你的第一颗番茄吧 🍅",
                                  font=("Microsoft YaHei UI", 11), bg=BG, fg=MUTED,
                                  wraplength=320, justify="center")
        self.msg_label.pack(padx=14, pady=(6, 2))

        # 控制按钮
        self.ctrl = tk.Frame(self.root, bg=BG)
        self.ctrl.pack(pady=6)
        self.start_btn = self._button(self.ctrl, "▶ 开始", WORK_COLOR, self.on_start)
        self.start_btn.pack(side="left", padx=4)
        self.skip_btn = self._button(self.ctrl, "⏭ 跳过", MUTED, self.on_skip)
        self.skip_btn.pack(side="left", padx=4)
        self.reset_btn = self._button(self.ctrl, "↺ 重置", MUTED, self.on_reset)
        self.reset_btn.pack(side="left", padx=4)
        self.back_btn = self._button(self.ctrl, "↩ 返回", GOLD, self._exit_mini)

        # ---- 底部容器（迷你模式下隐藏）----
        self.bottom_bar = tk.Frame(self.root, bg=BG)
        self.bottom_bar.pack(fill="both", expand=True)

        task_title = tk.Frame(self.bottom_bar, bg=BG)
        task_title.pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(task_title, text="📋 任务计划", font=("Microsoft YaHei UI", 12, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        tk.Label(task_title, text="自动关联第一项未完成", font=("Microsoft YaHei UI", 8),
                 bg=BG, fg=MUTED).pack(side="right")

        add = tk.Frame(self.bottom_bar, bg=CARD)
        add.pack(fill="x", padx=14, pady=6)
        self.task_entry = tk.Entry(add, font=("Microsoft YaHei UI", 10), relief="flat",
                                   bg="#f5efe9", fg=TEXT)
        self.task_entry.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=8)
        self.task_entry.bind("<Return>", lambda e: self.add_task())
        tk.Label(add, text="番茄", font=("Microsoft YaHei UI", 9), bg=CARD,
                 fg=MUTED).pack(side="left")
        self.est_var = tk.StringVar(value="2")
        tk.Spinbox(add, from_=1, to=20, textvariable=self.est_var, width=3,
                   font=("Microsoft YaHei UI", 10), relief="flat", bg="#f5efe9",
                   fg=TEXT, buttonbackground="#e9dfd4").pack(side="left", padx=4, pady=8)
        self._button(add, "添加", GOLD, self.add_task).pack(side="right", padx=(0, 8))

        list_wrap = tk.Frame(self.bottom_bar, bg=CARD)
        list_wrap.pack(fill="both", expand=True, padx=14, pady=(0, 6))
        self.task_canvas = tk.Canvas(list_wrap, bg=CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_wrap, orient="vertical",
                                  command=self.task_canvas.yview)
        self.task_inner = tk.Frame(self.task_canvas, bg=CARD)
        self.task_inner.bind("<Configure>",
                             lambda e: self.task_canvas.configure(
                                 scrollregion=self.task_canvas.bbox("all")))
        self.task_canvas.create_window((0, 0), window=self.task_inner, anchor="nw")
        self.task_canvas.configure(yscrollcommand=scrollbar.set)
        self.task_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        footer = tk.Frame(self.bottom_bar, bg=BG)
        footer.pack(fill="x", padx=14, pady=(4, 12))
        self.stat_label = tk.Label(footer, text="", font=("Microsoft YaHei UI", 9),
                                   bg=BG, fg=MUTED, justify="left")
        self.stat_label.pack(anchor="w")

        # 键盘快捷键：空格 开始/暂停
        self.root.bind("<space>", lambda e: self.on_start())
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _button(self, parent, text, color, command):
        return tk.Button(parent, text=text, command=command, font=("Microsoft YaHei UI", 10, "bold"),
                         bg=color, fg="white", activebackground=color, activeforeground="white",
                         relief="flat", bd=0, cursor="hand2", padx=12, pady=5)

    def _link_btn(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, font=("Microsoft YaHei UI", 9),
                         bg=BG, fg=MUTED, activebackground=BG, relief="flat", bd=0,
                         cursor="hand2", padx=4)

    def _toggle_topmost(self):
        self.root.attributes("-topmost", self.topmost.get())

    # ---------- 迷你模式（专注时只保留计时 + 鼓励） ----------
    def _enter_mini(self):
        if self.mini:
            return
        self.mini = True
        self.top_bar.pack_forget()
        self.bottom_bar.pack_forget()
        self.skip_btn.pack_forget()
        self.reset_btn.pack_forget()
        self.back_btn.pack(side="left", padx=4)
        self.canvas.itemconfig(self.sub_text, text=self._mode_label(self.mode),
                               fill=WORK_COLOR if self.mode == "work" else BREAK_COLOR)
        self.root.geometry("360x440")
        self.root.title(f"{APP_TITLE} · {self._mode_label(self.mode)}")

    def _exit_mini(self):
        if not self.mini:
            return
        self.mini = False
        self.back_btn.pack_forget()
        self.skip_btn.pack(side="left", padx=4)
        self.reset_btn.pack(side="left", padx=4)
        self.top_bar.pack(fill="x", before=self.canvas)
        self.bottom_bar.pack(fill="both", expand=True, after=self.ctrl)
        self.root.geometry("360x700")
        self.root.title(APP_TITLE)

    # ---------- 番茄钟控制 ----------
    def on_start(self):
        if self.state == "running":
            self._pause()
            return
        if self.state == "idle":
            if self.mode == "work":
                self._enter_mini()
                self._set_encourage(random.choice(ENCOURAGE_START), WORK_COLOR)
            else:
                self._set_encourage(random.choice(ENCOURAGE_BREAK), BREAK_COLOR)
        self.state = "running"
        self.start_btn.config(text="⏸ 暂停")
        self._update_taskbar()

    def _pause(self):
        self.state = "paused"
        self.start_btn.config(text="▶ 继续")
        self._update_taskbar()

    def on_reset(self):
        self.state = "idle"
        self.remaining = self.total
        self.start_btn.config(text="▶ 开始")
        self.canvas.itemconfig(self.sub_text, text="已重置", fill=MUTED)
        self._update_ring()
        self._update_taskbar()

    def on_skip(self):
        """跳过当前阶段（不发放奖励）。"""
        self._advance_mode(reward=False)

    def _advance_mode(self, reward=True):
        """结束当前阶段并进入下一阶段。reward=False 时不发放奖励。"""
        self.state = "idle"
        self.start_btn.config(text="▶ 开始")
        if self.mode == "work":
            self._exit_mini()
            if reward:
                self._reward_work()
                self.cycle_count += 1
                if self.cycle_count % int(self.settings["long_every"]) == 0:
                    self._switch_mode("long")
                else:
                    self._switch_mode("short")
            else:
                self._switch_mode("short")
        else:
            if reward:
                play_sound("soft")
            self._set_encourage(random.choice(ENCOURAGE_START), WORK_COLOR)
            self._switch_mode("work")

    def _tick_loop(self):
        if self.state == "running":
            self.remaining -= 1
            if self.remaining <= 0:
                self._complete()
            else:
                self._update_ring()
        self._update_taskbar()
        self.root.after(1000, self._tick_loop)

    def _update_ring(self):
        progress = 1 - self.remaining / self.total
        self.canvas.itemconfig(self.ring, extent=-360 * max(0.0, min(1.0, progress)))
        self.canvas.itemconfig(self.time_text, text=self._fmt(self.remaining))

    def _complete(self):
        self._advance_mode(reward=True)

    def _reward_work(self):
        """完成一个番茄：音效 + 特效 + 鼓励 + 统计 + 游戏化。"""
        play_sound("success")
        play_system_sound()
        self.confetti.burst()
        self._flash_text("+1 🍅")

        # 统计与经验
        self.data["total_pomodoros"] += 1
        self.data["xp"] += XP_PER_POMODORO
        self._record_day(int(self.settings["work_min"]))

        # 关联当前任务
        task = self.current_task()
        if task:
            task["pomodoros"] = task.get("pomodoros", 0) + 1
            if task.get("estimate", 0) > 0 and task["pomodoros"] >= task["estimate"]:
                self._complete_task(task)

        self._set_encourage(random.choice(ENCOURAGE_WORK), GOLD)
        self.refresh_tasks()
        self.refresh_stats()
        self.save()

    def _complete_task(self, task):
        """标记任务完成并发放额外奖励（仅一次）。"""
        if task.get("done"):
            return
        task["done"] = True
        self.data["xp"] += XP_PER_TASK
        play_sound("fanfare")
        self.confetti.burst(120)
        self._flash_text("🎉 任务完成")
        self._set_encourage(random.choice(ENCOURAGE_TASK), GOLD)

    def _switch_mode(self, mode):
        self.mode = mode
        self.total = self._mode_seconds(mode)
        self.remaining = self.total
        self._apply_mode_visual()
        self._update_ring()
        self._update_taskbar()
        if mode in ("short", "long"):
            self._set_encourage(random.choice(ENCOURAGE_BREAK), BREAK_COLOR)

    def _apply_mode_visual(self):
        color = WORK_COLOR if self.mode == "work" else BREAK_COLOR
        self.mode_label.config(text=self._mode_label(self.mode), fg=color)
        self.canvas.itemconfig(self.ring, outline=color)
        self.canvas.itemconfig(self.sub_text, text="点击「开始」进入" + self._mode_label(self.mode))

    def _set_encourage(self, text, color):
        self.msg_label.config(text=text, fg=color)

    def _flash_text(self, text):
        """在计时环中央短暂弹出成就文字。"""
        self.canvas.itemconfig(self.sub_text, text=text, fill=GOLD)
        self.root.after(1800, lambda: self.canvas.itemconfig(
            self.sub_text, text="点击「开始」进入" + self._mode_label(self.mode),
            fill=MUTED))

    # ---------- 任务栏进度 ----------
    def _init_taskbar(self):
        try:
            hwnd = self.root.winfo_id()
            hwnd = ctypes.windll.user32.GetAncestor(hwnd, 2)  # GA_ROOT
            if not self.taskbar.bind(hwnd):
                self.taskbar = None
        except Exception:
            self.taskbar = None

    def _update_taskbar(self):
        if self.taskbar is None:
            return
        frac = 1 - self.remaining / self.total
        if self.state == "running":
            self.taskbar.set_progress(frac)
        elif self.state == "paused":
            self.taskbar.set_paused(frac)
        else:
            self.taskbar.clear()

    # ---------- 统计与游戏化 ----------
    def _record_day(self, minutes):
        today = date.today().isoformat()
        hist = self.data["history"].setdefault(today, {"pomodoros": 0, "minutes": 0})
        hist["pomodoros"] += 1
        hist["minutes"] += minutes

        # 连击（连续打卡天数）
        if self.data["last_active_date"] != today:
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            if self.data["last_active_date"] == yesterday:
                self.data["streak"] += 1
            else:
                self.data["streak"] = 1
            self.data["last_active_date"] = today

    def _level_info(self):
        level = self.data["xp"] // 100
        title = TITLES[min(level, len(TITLES) - 1)]
        progress = (self.data["xp"] % 100) / 100.0
        return level, title, progress

    def _longest_streak(self):
        dates = sorted(d for d, h in self.data["history"].items() if h.get("pomodoros", 0) > 0)
        if not dates:
            return 0
        best = cur = 1
        prev = None
        for ds in dates:
            d = datetime.strptime(ds, "%Y-%m-%d").date()
            if prev and (d - prev).days == 1:
                cur += 1
            else:
                cur = 1
            best = max(best, cur)
            prev = d
        return best

    def refresh_stats(self):
        level, title, _ = self._level_info()
        today = date.today().isoformat()
        today_hist = self.data["history"].get(today, {"pomodoros": 0, "minutes": 0})
        self.stat_label.config(
            text=(f"🍅 今日 {today_hist['pomodoros']} 颗 · 累计 {self.data['total_pomodoros']} 颗\n"
                  f"⏱ 今日专注 {today_hist['minutes']} 分钟 · 🔥 连击 {self.data['streak']} 天\n"
                  f"⭐ Lv.{level} {title}  ({self.data['xp']} XP)"))

    # ---------- 设置面板 ----------
    def open_settings(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("⚙ 设置")
        dlg.configure(bg=BG)
        dlg.geometry("330x340")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        vars_ = {
            "work": tk.IntVar(value=int(self.settings["work_min"])),
            "short": tk.IntVar(value=int(self.settings["short_break_min"])),
            "long": tk.IntVar(value=int(self.settings["long_break_min"])),
            "every": tk.IntVar(value=int(self.settings["long_every"])),
        }
        rows = [("专注时长（分钟）", "work", 120), ("短休息（分钟）", "short", 60),
                ("长休息（分钟）", "long", 60), ("几个番茄后长休", "every", 12)]

        frame = tk.Frame(dlg, bg=BG)
        frame.pack(fill="x", padx=20, pady=16)
        for i, (label, key, upper) in enumerate(rows):
            tk.Label(frame, text=label, font=("Microsoft YaHei UI", 10), bg=BG, fg=TEXT).grid(
                row=i, column=0, sticky="w", pady=6)
            tk.Spinbox(frame, from_=1, to=upper, textvariable=vars_[key], width=6,
                       font=("Microsoft YaHei UI", 10), relief="flat", bg="#f5efe9",
                       fg=TEXT, buttonbackground="#e9dfd4").grid(row=i, column=1, sticky="e", pady=6)
        frame.columnconfigure(0, weight=1)

        self.autostart_var = tk.BooleanVar(value=get_autostart())
        tk.Checkbutton(dlg, text="开机自动启动", variable=self.autostart_var, bg=BG, fg=TEXT,
                       activebackground=BG, font=("Microsoft YaHei UI", 10)).pack(
            anchor="w", padx=20, pady=(0, 2))

        if pystray is not None:
            self.tray_var = tk.BooleanVar(value=self.tray_enabled)
            tk.Checkbutton(dlg, text="最小化到系统托盘", variable=self.tray_var, bg=BG, fg=TEXT,
                           activebackground=BG, font=("Microsoft YaHei UI", 10)).pack(
                anchor="w", padx=20)

        btns = tk.Frame(dlg, bg=BG)
        btns.pack(pady=14)
        tk.Button(btns, text="取消", command=dlg.destroy, font=("Microsoft YaHei UI", 10),
                  bg="#f0e6dc", fg=TEXT, relief="flat", padx=18, pady=5,
                  cursor="hand2").pack(side="left", padx=6)
        tk.Button(btns, text="保存", command=lambda: self._save_settings(dlg, vars_),
                  font=("Microsoft YaHei UI", 10, "bold"), bg=WORK_COLOR, fg="white",
                  relief="flat", padx=18, pady=5, cursor="hand2").pack(side="left", padx=6)

    def _save_settings(self, dlg, vars_):
        self.settings["work_min"] = int(vars_["work"].get())
        self.settings["short_break_min"] = int(vars_["short"].get())
        self.settings["long_break_min"] = int(vars_["long"].get())
        self.settings["long_every"] = int(vars_["every"].get())
        self.settings["tray_enabled"] = bool(self.tray_var.get()) if pystray is not None else False

        set_autostart(self.autostart_var.get(), SCRIPT_PATH, "--minimized")

        # 托盘开关即时生效
        if pystray is not None:
            want_tray = bool(self.tray_var.get())
            if want_tray != self.tray_enabled:
                self.tray_enabled = want_tray
                if want_tray:
                    self._setup_tray()
                elif self.tray_icon:
                    try:
                        self.tray_icon.stop()
                    except Exception:
                        pass
                    self.tray_icon = None

        # 若尚未开始，刷新当前模式时长
        if self.state == "idle":
            self.total = self._mode_seconds(self.mode)
            self.remaining = self.total
            self._update_ring()
            self._update_taskbar()

        self.save()
        dlg.destroy()
        self._set_encourage("设置已保存 ✅", TEXT)

    # ---------- 统计面板（专注热力图） ----------
    def open_stats(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("📊 专注统计")
        dlg.configure(bg=BG)
        dlg.geometry("440x430")
        dlg.resizable(False, False)
        dlg.transient(self.root)

        total = self.data["total_pomodoros"]
        total_min = sum(h.get("minutes", 0) for h in self.data["history"].values())
        longest = self._longest_streak()
        today = date.today().isoformat()
        today_p = self.data["history"].get(today, {}).get("pomodoros", 0)

        # 汇总卡片
        summary = tk.Frame(dlg, bg=CARD)
        summary.pack(fill="x", padx=16, pady=(14, 6))
        cards = [
            ("累计番茄", f"{total} 🍅"),
            ("累计专注", f"{total_min // 60} 时 {total_min % 60} 分"),
            ("最长连击", f"{longest} 天 🔥"),
            ("今日", f"{today_p} 🍅"),
        ]
        for i, (k, v) in enumerate(cards):
            col = tk.Frame(summary, bg=CARD)
            col.pack(side="left", expand=True, pady=8)
            tk.Label(col, text=k, font=("Microsoft YaHei UI", 8), bg=CARD, fg=MUTED).pack()
            tk.Label(col, text=v, font=("Microsoft YaHei UI", 11, "bold"), bg=CARD,
                     fg=TEXT).pack()

        tk.Label(dlg, text="近 14 天专注热力", font=("Microsoft YaHei UI", 10, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", padx=18, pady=(8, 2))

        # 柱状热力图
        W, H = 400, 180
        c = tk.Canvas(dlg, width=W, height=H, bg=CARD, highlightthickness=0)
        c.pack(padx=16, pady=(0, 14))
        days = []
        for i in range(13, -1, -1):
            d = date.today() - timedelta(days=i)
            hist = self.data["history"].get(d.isoformat(), {})
            days.append((d, hist.get("pomodoros", 0)))
        max_p = max([p for _, p in days] + [1])
        n = len(days)
        bar_w = W / n
        for i, (d, p) in enumerate(days):
            x0 = i * bar_w + 4
            x1 = (i + 1) * bar_w - 4
            h = (p / max_p) * (H - 44) if p else 2
            y0 = H - 20 - h
            y1 = H - 20
            c.create_rectangle(x0, y0, x1, y1, fill=self._heat_color(p, max_p), outline="")
            if p:
                c.create_text((x0 + x1) / 2, y0 - 8, text=str(p),
                              font=("Microsoft YaHei UI", 7), fill=TEXT)
            if i % 2 == 0 or i == n - 1:
                c.create_text((x0 + x1) / 2, H - 8, text=d.strftime("%m-%d"),
                              font=("Microsoft YaHei UI", 7), fill=MUTED)

        tk.Button(dlg, text="关闭", command=dlg.destroy, font=("Microsoft YaHei UI", 10),
                  bg="#f0e6dc", fg=TEXT, relief="flat", padx=18, pady=5,
                  cursor="hand2").pack(pady=(0, 12))

    def _heat_color(self, p, max_p):
        if p == 0:
            return "#f0e6dc"
        ratio = p / max_p
        r1, g1, b1 = 0xfd, 0xe2, 0xdc
        r2, g2, b2 = 0xc0, 0x39, 0x2b
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        return f"#{r:02x}{g:02x}{b:02x}"

    # ---------- 任务管理 ----------
    def add_task(self):
        name = self.task_entry.get().strip()
        if not name:
            return
        try:
            estimate = int(self.est_var.get())
        except ValueError:
            estimate = 1
        estimate = max(1, estimate)
        self.data["tasks"].append({
            "name": name, "estimate": estimate,
            "done": False, "pomodoros": 0,
        })
        self.task_entry.delete(0, "end")
        self.refresh_tasks()
        self.save()
        self._set_encourage(f"已添加任务「{name}」，预计 {estimate} 个番茄 🍅", TEXT)

    def _toggle_task_done(self, task):
        if task.get("done"):
            task["done"] = False
        else:
            self._complete_task(task)
        self.refresh_tasks()
        self.refresh_stats()
        self.save()

    def _delete_task(self, task):
        if task in self.data["tasks"]:
            self.data["tasks"].remove(task)
        self.refresh_tasks()
        self.save()

    def refresh_tasks(self):
        for child in self.task_inner.winfo_children():
            child.destroy()
        if not self.data["tasks"]:
            tk.Label(self.task_inner, text="暂无任务，点击上方「添加」制定计划",
                     font=("Microsoft YaHei UI", 9), bg=CARD, fg=MUTED,
                     pady=14).pack()
            return
        for task in self.data["tasks"]:
            row = tk.Frame(self.task_inner, bg=CARD)
            row.pack(fill="x", padx=8, pady=3)
            done = task.get("done")
            name = "✓ " + task["name"] if done else task["name"]
            btn_done = tk.Button(row, text="✓" if done else "○", width=2, relief="flat", bd=0,
                                 font=("Microsoft YaHei UI", 12),
                                 bg="#3fbf8f" if done else "#f0e6dc",
                                 fg="white" if done else MUTED, cursor="hand2",
                                 command=lambda t=task: self._toggle_task_done(t))
            btn_done.pack(side="left")
            name_label = tk.Label(row, text=name, font=("Microsoft YaHei UI", 10),
                                  bg=CARD, fg=MUTED if done else TEXT, anchor="w")
            name_label.pack(side="left", fill="x", expand=True, padx=4)
            progress = f"🍅 {task.get('pomodoros', 0)}/{task.get('estimate', 1)}"
            tk.Label(row, text=progress, font=("Microsoft YaHei UI", 9),
                     bg=CARD, fg=GOLD).pack(side="left", padx=2)
            btn_del = tk.Button(row, text="✕", relief="flat", bd=0, font=("Microsoft YaHei UI", 9),
                                bg=CARD, fg="#d9c7bc", cursor="hand2",
                                command=lambda t=task: self._delete_task(t))
            btn_del.pack(side="left", padx=(2, 0))

    # ---------- 系统托盘 ----------
    def _setup_tray(self):
        if pystray is None or Image is None:
            return
        try:
            menu = pystray.Menu(
                pystray.MenuItem("显示窗口", self._tray_show, default=True),
                pystray.MenuItem("开始/暂停", self._tray_toggle),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", self._tray_quit),
            )
            self.tray_icon = pystray.Icon("FocusTomato", _make_tray_image(), APP_TITLE, menu)
            self.tray_icon.run_detached()
            self._poll_tray()
        except Exception:
            self.tray_icon = None

    def _tray_show(self, icon, item):
        self.tray_cmds.put("show")

    def _tray_toggle(self, icon, item):
        self.tray_cmds.put("toggle")

    def _tray_quit(self, icon, item):
        self.tray_cmds.put("quit")

    def _poll_tray(self):
        try:
            while True:
                cmd = self.tray_cmds.get_nowait()
                if cmd == "show":
                    self.show_window()
                elif cmd == "toggle":
                    self.on_start()
                elif cmd == "quit":
                    self.quit_app()
                    return
        except queue.Empty:
            pass
        self.root.after(150, self._poll_tray)

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", self.topmost.get())

    # ---------- 收尾 ----------
    def save(self):
        self.data["settings"] = self.settings
        save_data(self.data)

    def on_close(self):
        if self.tray_enabled and self.tray_icon is not None:
            self.root.withdraw()
            try:
                self.tray_icon.notify("已最小化到托盘，继续为你计时", APP_TITLE)
            except Exception:
                pass
            return
        self.quit_app()

    def quit_app(self):
        self.save()
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        try:
            self.taskbar.release()
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = FocusTomatoApp(root)
    if "--minimized" in sys.argv:
        if app.tray_enabled and app.tray_icon is not None:
            root.withdraw()       # 启动即隐藏到托盘
        else:
            root.iconify()        # 无托盘时最小化到任务栏
    root.mainloop()


if __name__ == "__main__":
    main()
