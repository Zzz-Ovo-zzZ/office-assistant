"""
悬浮记事本 v2.0
- 米色温暖主题
- 始终置顶于所有窗口之上
- 全局热键 显示/隐藏（可自定义）
- 自动保存（失焦 + 30秒定时）
- 系统托盘常驻（右键菜单：显示/设置/关于/退出）
- 开机自启（设置界面一键开关）
- 桌面快捷方式（设置界面一键创建/移除）
- 记忆窗口位置和大小
- 设置界面：快捷键配置 + 自启动开关 + 桌面快捷方式
"""
import sys
import os
import json
import threading
import subprocess
import ctypes
from datetime import datetime
from pathlib import Path

# ═══ 路径 ═══
PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_DIR / "output"
TEMP_DIR = PROJECT_DIR / "temp"
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

NOTE_FILE = OUTPUT_DIR / "float_notepad.txt"
CONFIG_FILE = TEMP_DIR / "float_notepad_config.json"

DESKTOP_DIR = Path.home() / "Desktop"

# ═══ tkinter ═══
import tkinter as tk
from tkinter import ttk, font, messagebox

# ═══ 米色主题配色 ═══
THEME = {
    "bg_main":      "#FFF8E7",   # 主背景 — 温暖米色
    "bg_text":      "#FFFDF5",   # 编辑区背景 — 浅米白
    "bg_title":     "#E8D5A0",   # 标题栏 — 深米色
    "bg_status":    "#E0CDA0",   # 状态栏 — 中间米色
    "fg_text":      "#3D2B1F",   # 文字 — 深棕色
    "fg_status":    "#6B5B3A",   # 状态栏文字 — 中棕色
    "fg_hint":      "#A09070",   # 提示文字 — 浅棕色
    "accent":       "#8B6914",   # 强调色 — 金棕色
    "accent_hover": "#A67C00",   # 悬停 — 亮金棕
    "border":       "#C4A96A",   # 边框 — 暖金
    "scroll_bg":    "#D4C098",   # 滚动条背景
    "scroll_trough": "#F0E4C8",  # 滚动条轨道
    "btn_bg":       "#E8D5A0",   # 按钮背景
    "btn_fg":       "#3D2B1F",   # 按钮文字
    "entry_bg":     "#FFFDF5",   # 输入框背景
    "pin_active":   "#8B6914",   # 置顶激活
    "pin_inactive": "#B8A080",   # 置顶未激活
    "cursor":       "#3D2B1F",   # 光标颜色
}

# ═══ 默认快捷键选项 ═══
HOTKEY_PRESETS = [
    ("Ctrl + Alt + N",  ["ctrl", "alt"], "n"),
    ("Ctrl + Alt + M",  ["ctrl", "alt"], "m"),
    ("Ctrl + Shift + N", ["ctrl", "shift"], "n"),
    ("Ctrl + Win + N",  ["ctrl", "cmd"], "n"),
    ("Alt + Shift + N", ["alt", "shift"], "n"),
    ("Ctrl + Alt + V",  ["ctrl", "alt"], "v"),
    ("Ctrl + Alt + Space", ["ctrl", "alt"], "<space>"),
    ("Ctrl + Alt + .",  ["ctrl", "alt"], "."),
]


class FloatNotepad:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("悬浮记事本")
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        # 加载配置
        self.config = self.load_config()

        # 设置窗口
        self.setup_window()

        # 构建界面
        self.setup_ui()

        # 加载上次内容
        self.load_content()

        # 自动保存定时器
        self.setup_autosave()

        # 窗口事件绑定
        self.root.bind("<FocusOut>", self.on_focus_out)
        self.root.bind("<Control-s>", self.on_manual_save)
        self.root.bind("<Control-S>", self.on_manual_save)
        self.root.bind("<Escape>", lambda e: self.hide_window())
        self.root.bind("<Destroy>", self.on_destroy)

        # 启动全局热键
        self.hotkey_listener = None
        self.start_hotkey()

        # 启动系统托盘
        self.tray_icon = None
        self.tray_thread = None
        self.start_tray()

        # 更新状态栏
        self.update_status("就绪")

        # 窗口就绪后保存位置
        self.root.after(500, self.save_config)

    # ═══ 窗口设置 ═══
    def setup_window(self):
        w = self.config.get("width", 380)
        h = self.config.get("height", 280)
        x = self.config.get("x", 100)
        y = self.config.get("y", 100)

        # 确保窗口在屏幕范围内
        try:
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            if x + w > screen_w:
                x = screen_w - w - 20
            if y + h > screen_h:
                y = screen_h - h - 40
            if x < 0:
                x = 20
            if y < 0:
                y = 20
        except Exception:
            pass

        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.minsize(260, 160)

        # 置顶
        self.root.attributes("-topmost", self.config.get("topmost", True))

        # 窗口底色
        self.root.configure(bg=THEME["bg_main"])

        # 任务栏图标（Windows）
        try:
            if sys.platform == "win32":
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "float.notepad.v2"
                )
        except Exception:
            pass

    # ═══ 界面构建 ═══
    def setup_ui(self):
        # ── 标题栏 ──
        self.title_bar = tk.Frame(
            self.root, bg=THEME["bg_title"], height=32,
            highlightbackground=THEME["border"], highlightthickness=1
        )
        self.title_bar.pack(side=tk.TOP, fill=tk.X)
        self.title_bar.pack_propagate(False)

        # 应用图标 + 标题
        title_label = tk.Label(
            self.title_bar, text=" 📝 悬浮记事本",
            bg=THEME["bg_title"], fg=THEME["fg_text"],
            font=("Microsoft YaHei UI", 9, "bold")
        )
        title_label.pack(side=tk.LEFT, pady=4, padx=(8, 0))
        title_label.bind("<Button-1>", self.start_drag)
        title_label.bind("<B1-Motion>", self.do_drag)
        self.title_bar.bind("<Button-1>", self.start_drag)
        self.title_bar.bind("<B1-Motion>", self.do_drag)

        # 右侧按钮区
        btn_frame = tk.Frame(self.title_bar, bg=THEME["bg_title"])
        btn_frame.pack(side=tk.RIGHT, padx=4)

        # 设置按钮
        settings_btn = tk.Label(
            btn_frame, text="⚙", bg=THEME["bg_title"], fg=THEME["fg_text"],
            font=("Segoe UI", 11), cursor="hand2"
        )
        settings_btn.pack(side=tk.RIGHT, padx=3)
        settings_btn.bind("<Button-1>", lambda e: self.open_settings())

        # 置顶按钮
        pin_char = "📌" if self.config.get("topmost", True) else "📍"
        pin_color = THEME["pin_active"] if self.config.get("topmost", True) else THEME["pin_inactive"]
        self.pin_btn = tk.Label(
            btn_frame, text=pin_char, bg=THEME["bg_title"], fg=pin_color,
            font=("Segoe UI", 10), cursor="hand2"
        )
        self.pin_btn.pack(side=tk.RIGHT, padx=3)
        self.pin_btn.bind("<Button-1>", self.toggle_topmost)

        # 隐藏按钮
        hide_btn = tk.Label(
            btn_frame, text="─", bg=THEME["bg_title"], fg=THEME["fg_text"],
            font=("Segoe UI", 10, "bold"), cursor="hand2"
        )
        hide_btn.pack(side=tk.RIGHT, padx=3)
        hide_btn.bind("<Button-1>", lambda e: self.hide_window())

        # ── 编辑区 ──
        text_frame = tk.Frame(
            self.root, bg=THEME["bg_main"],
            highlightbackground=THEME["border"], highlightthickness=0
        )
        text_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=4, pady=(2, 0))

        self.text_area = tk.Text(
            text_frame,
            bg=THEME["bg_text"], fg=THEME["fg_text"],
            insertbackground=THEME["cursor"],
            font=("Microsoft YaHei UI", 10),
            wrap=tk.WORD,
            relief=tk.FLAT,
            borderwidth=0,
            padx=10, pady=10,
            undo=True,
            maxundo=50,
            selectbackground="#C4A96A",
            selectforeground="#3D2B1F",
        )
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 滚动条
        scrollbar = tk.Scrollbar(
            text_frame, bg=THEME["scroll_bg"],
            troughcolor=THEME["scroll_trough"], width=8
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.text_area.yview)

        # 绑定文本变更
        self.text_modified = False
        self.text_area.bind("<<Modified>>", self.on_text_modified)

        # ── 状态栏 ──
        self.status_bar = tk.Frame(
            self.root, bg=THEME["bg_status"], height=24,
            highlightbackground=THEME["border"], highlightthickness=1
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar.pack_propagate(False)

        self.status_label = tk.Label(
            self.status_bar, text=" 就绪",
            bg=THEME["bg_status"], fg=THEME["fg_status"],
            font=("Microsoft YaHei UI", 8),
            anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, padx=8, pady=2)

        # 热键提示
        hk = self.get_hotkey_display()
        self.hint_label = tk.Label(
            self.status_bar,
            text=f"{hk} 显隐 | Ctrl+S 保存 | Esc 隐藏",
            bg=THEME["bg_status"], fg=THEME["fg_hint"],
            font=("Microsoft YaHei UI", 8),
            anchor=tk.E
        )
        self.hint_label.pack(side=tk.RIGHT, padx=8, pady=2)

    # ═══ 窗口拖动 ═══
    def start_drag(self, event):
        self._drag_x = event.x_root
        self._drag_y = event.y_root

    def do_drag(self, event):
        dx = event.x_root - self._drag_x
        dy = event.y_root - self._drag_y
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")
        self._drag_x = event.x_root
        self._drag_y = event.y_root
        self.root.after(300, self.save_config)

    # ═══ 置顶切换 ═══
    def toggle_topmost(self, event=None):
        current = self.root.attributes("-topmost")
        new_state = not current
        self.root.attributes("-topmost", new_state)
        self.config["topmost"] = new_state
        icon = "📌" if new_state else "📍"
        color = THEME["pin_active"] if new_state else THEME["pin_inactive"]
        self.pin_btn.config(text=icon, fg=color)
        self.save_config()
        self.update_status("已置顶" if new_state else "取消置顶")

    # ═══ 显示/隐藏 ═══
    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.text_area.focus_set()

    def hide_window(self):
        self.save_content()
        self.root.withdraw()

    def toggle_window(self):
        """被热键调用 — 从非主线程，用 after 调度"""
        self.root.after(0, self._toggle_window)

    def _toggle_window(self):
        if self.root.state() == "withdrawn":
            self.show_window()
        else:
            self.hide_window()

    # ═══ 内容管理 ═══
    def load_content(self):
        try:
            if NOTE_FILE.exists():
                content = NOTE_FILE.read_text(encoding="utf-8")
                self.text_area.insert("1.0", content)
                self.text_area.edit_modified(False)
                self.text_modified = False
        except Exception as e:
            print(f"[FloatNotepad] 加载失败: {e}")

    def save_content(self):
        try:
            content = self.text_area.get("1.0", "end-1c")
            NOTE_FILE.write_text(content, encoding="utf-8")
            self.text_area.edit_modified(False)
            self.text_modified = False
            self.update_status(f"已保存 {datetime.now().strftime('%H:%M:%S')}")
            return True
        except Exception as e:
            self.update_status(f"保存失败: {e}")
            return False

    def on_text_modified(self, event=None):
        if self.text_area.edit_modified():
            self.text_modified = True
            self.text_area.edit_modified(False)

    def on_focus_out(self, event=None):
        if self.text_modified:
            self.save_content()

    def on_manual_save(self, event=None):
        if self.save_content():
            self.update_status(f"已保存 {datetime.now().strftime('%H:%M:%S')}")
        return "break"

    # ═══ 自动保存 ═══
    def setup_autosave(self):
        def autosave_loop():
            if self.text_modified and self.root.state() != "withdrawn":
                self.save_content()
            self.root.after(30000, autosave_loop)

        self.root.after(30000, autosave_loop)

    def update_status(self, msg, duration=3000):
        self.status_label.config(text=f"  {msg}")
        if duration > 0:
            def restore():
                self.status_label.config(text=" 就绪")
            self.root.after(duration, restore)

    # ═══ 配置管理 ═══
    def load_config(self):
        defaults = {
            "width": 380, "height": 280, "x": 100, "y": 100,
            "topmost": True,
            "hotkey_modifiers": ["ctrl", "alt"],
            "hotkey_key": "n",
            "auto_start": False,
            "desktop_shortcut": False,
        }
        try:
            if CONFIG_FILE.exists():
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                defaults.update(data)
        except Exception:
            pass
        return defaults

    def save_config(self):
        try:
            if self.root.state() != "withdrawn":
                self.config["x"] = self.root.winfo_x()
                self.config["y"] = self.root.winfo_y()
                self.config["width"] = self.root.winfo_width()
                self.config["height"] = self.root.winfo_height()
            CONFIG_FILE.write_text(
                json.dumps(self.config, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

    def on_destroy(self, event=None):
        self.save_config()
        self.save_content()

    def get_hotkey_display(self):
        """获取热键的显示文本"""
        mods = self.config.get("hotkey_modifiers", ["ctrl", "alt"])
        key = self.config.get("hotkey_key", "n")
        mod_map = {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "cmd": "Win"}
        parts = [mod_map.get(m, m) for m in mods]
        key_display = key.replace("<", "").replace(">", "").capitalize()
        if key_display == "Space":
            key_display = "Space"
        parts.append(key_display)
        return " + ".join(parts)

    def build_hotkey_string(self, mods=None, key=None):
        """构建 pynput 格式的热键字符串"""
        if mods is None:
            mods = self.config.get("hotkey_modifiers", ["ctrl", "alt"])
        if key is None:
            key = self.config.get("hotkey_key", "n")
        mod_part = "+".join(f"<{m}>" for m in mods)
        key_part = key if key.startswith("<") else key
        return f"{mod_part}+{key_part}"

    # ═══ 全局热键 ═══
    def start_hotkey(self):
        try:
            from pynput import keyboard

            def on_activate():
                self.toggle_window()

            hotkey_str = self.build_hotkey_string()
            self.hotkey_listener = keyboard.GlobalHotKeys({
                hotkey_str: on_activate,
            })

            hotkey_thread = threading.Thread(
                target=self.hotkey_listener.run,
                daemon=True
            )
            hotkey_thread.start()
            print(f"[FloatNotepad] 全局热键已注册: {hotkey_str}")
        except Exception as e:
            print(f"[FloatNotepad] 热键注册失败: {e}")
            self.update_status(f"热键失败: {e}", duration=5000)

    def restart_hotkey(self):
        """重新注册热键（设置变更时调用）"""
        try:
            if self.hotkey_listener:
                self.hotkey_listener.stop()
        except Exception:
            pass
        self.start_hotkey()
        # 更新状态栏提示
        hk = self.get_hotkey_display()
        self.hint_label.config(
            text=f"{hk} 显隐 | Ctrl+S 保存 | Esc 隐藏"
        )

    # ═══ 系统托盘 ═══
    def start_tray(self):
        try:
            from PIL import Image, ImageDraw
            import pystray

            # 生成托盘图标（米色主题）
            icon_img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(icon_img)

            # 圆角矩形背景 — 金棕色
            draw.rounded_rectangle([4, 4, 60, 60], radius=12, fill="#8B6914")
            # 内层浅色区域（记事本纸页）
            draw.rounded_rectangle([14, 10, 50, 52], radius=6, fill="#FFFDF5")
            # 横线模拟文字
            for i, y in enumerate([20, 28, 36, 44]):
                line_w = [38, 34, 30, 26][i]
                x1 = (64 - line_w) // 2
                draw.line([x1, y, x1 + line_w, y], fill="#C4A96A", width=2)

            def on_show(icon):
                self.root.after(0, self.show_window)

            def on_settings(icon):
                self.root.after(0, self.open_settings)

            def on_quit(icon):
                icon.stop()
                self.root.after(0, self.quit_app)

            menu = pystray.Menu(
                pystray.MenuItem("📝 显示", on_show, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("⚙ 设置", on_settings),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("❌ 退出", on_quit),
            )

            self.tray_icon = pystray.Icon(
                "float_notepad_v2",
                icon_img,
                "悬浮记事本",
                menu
            )

            self.tray_thread = threading.Thread(
                target=self.tray_icon.run,
                daemon=True
            )
            self.tray_thread.start()
            print("[FloatNotepad] 系统托盘已启动")
        except Exception as e:
            print(f"[FloatNotepad] 托盘启动失败: {e}")

    def quit_app(self):
        self.save_content()
        self.save_config()
        try:
            if self.hotkey_listener:
                self.hotkey_listener.stop()
        except Exception:
            pass
        try:
            if self.tray_icon:
                self.tray_icon.stop()
        except Exception:
            pass
        self.root.destroy()

    # ═══ 设置窗口 ═══
    def open_settings(self):
        """打开设置对话框"""
        win = tk.Toplevel(self.root)
        win.title("悬浮记事本 — 设置")
        win.geometry("420x380")
        win.resizable(False, False)
        win.configure(bg=THEME["bg_main"])
        win.transient(self.root)

        # 居中于父窗口
        win.update_idletasks()
        px = self.root.winfo_x() + (self.root.winfo_width() - 420) // 2
        py = self.root.winfo_y() + (self.root.winfo_height() - 380) // 2
        win.geometry(f"+{px}+{py}")

        # 确保置顶
        win.attributes("-topmost", True)
        win.focus_force()

        # 标题栏
        title_bar = tk.Frame(
            win, bg=THEME["bg_title"], height=36,
            highlightbackground=THEME["border"], highlightthickness=1
        )
        title_bar.pack(side=tk.TOP, fill=tk.X)
        title_bar.pack_propagate(False)

        tk.Label(
            title_bar, text=" ⚙ 设置",
            bg=THEME["bg_title"], fg=THEME["fg_text"],
            font=("Microsoft YaHei UI", 10, "bold")
        ).pack(side=tk.LEFT, padx=10, pady=8)

        # ── 内容区 ──
        content = tk.Frame(win, bg=THEME["bg_main"], padx=20, pady=16)
        content.pack(fill=tk.BOTH, expand=True)

        # ── 快捷键设置 ──
        section_font = ("Microsoft YaHei UI", 9, "bold")
        label_font = ("Microsoft YaHei UI", 9)
        small_font = ("Microsoft YaHei UI", 8)

        tk.Label(
            content, text="全局快捷键", font=section_font,
            bg=THEME["bg_main"], fg=THEME["fg_text"]
        ).pack(anchor=tk.W)

        # 预设选择
        hk_frame = tk.Frame(content, bg=THEME["bg_main"])
        hk_frame.pack(fill=tk.X, pady=(6, 12))

        current_hk = self._get_current_preset_index()
        self.hk_var = tk.StringVar(value=HOTKEY_PRESETS[current_hk][0] if current_hk >= 0 else "自定义")

        hk_combo = ttk.Combobox(
            hk_frame, textvariable=self.hk_var,
            values=[p[0] for p in HOTKEY_PRESETS],
            state="readonly", width=24,
            font=("Microsoft YaHei UI", 9)
        )
        hk_combo.pack(side=tk.LEFT, padx=(0, 8))

        def on_hk_change(*args):
            """快捷键预设变更时即时生效"""
            selected = self.hk_var.get()
            for label, mods, key in HOTKEY_PRESETS:
                if label == selected:
                    self.config["hotkey_modifiers"] = mods
                    self.config["hotkey_key"] = key
                    self.save_config()
                    self.restart_hotkey()
                    break

        self.hk_var.trace_add("write", on_hk_change)

        tk.Label(
            hk_frame, text="Ctrl+Alt+N 推荐", font=small_font,
            bg=THEME["bg_main"], fg=THEME["fg_hint"]
        ).pack(side=tk.LEFT)

        # ── 开机自启 ──
        sep1 = tk.Frame(content, bg=THEME["border"], height=1)
        sep1.pack(fill=tk.X, pady=(4, 8))

        tk.Label(
            content, text="开机自启动", font=section_font,
            bg=THEME["bg_main"], fg=THEME["fg_text"]
        ).pack(anchor=tk.W)

        auto_frame = tk.Frame(content, bg=THEME["bg_main"])
        auto_frame.pack(fill=tk.X, pady=(6, 12))

        self.auto_var = tk.BooleanVar(value=check_auto_start())
        auto_cb = tk.Checkbutton(
            auto_frame, text="开机时自动启动悬浮记事本",
            variable=self.auto_var,
            bg=THEME["bg_main"], fg=THEME["fg_text"],
            font=label_font,
            activebackground=THEME["bg_main"],
            selectcolor=THEME["bg_text"],
            command=self.toggle_auto_start
        )
        auto_cb.pack(side=tk.LEFT)

        # ── 桌面快捷方式 ──
        sep2 = tk.Frame(content, bg=THEME["border"], height=1)
        sep2.pack(fill=tk.X, pady=(4, 8))

        tk.Label(
            content, text="桌面快捷方式", font=section_font,
            bg=THEME["bg_main"], fg=THEME["fg_text"]
        ).pack(anchor=tk.W)

        dskt_frame = tk.Frame(content, bg=THEME["bg_main"])
        dskt_frame.pack(fill=tk.X, pady=(6, 12))

        has_shortcut = check_desktop_shortcut()
        dskt_status = "✅ 已创建" if has_shortcut else "未创建"
        self.dskt_status_label = tk.Label(
            dskt_frame, text=dskt_status, font=label_font,
            bg=THEME["bg_main"], fg=THEME["fg_status"] if has_shortcut else THEME["fg_hint"]
        )
        self.dskt_status_label.pack(side=tk.LEFT, padx=(0, 12))

        dskt_btn_text = "移除快捷方式" if has_shortcut else "创建桌面快捷方式"
        dskt_btn = tk.Button(
            dskt_frame, text=dskt_btn_text,
            bg=THEME["btn_bg"], fg=THEME["btn_fg"],
            font=label_font, relief=tk.FLAT,
            padx=10, pady=2,
            activebackground=THEME["accent"],
            activeforeground="#FFFFFF",
            cursor="hand2",
            command=lambda: self.toggle_desktop_shortcut(dskt_btn)
        )
        dskt_btn.pack(side=tk.LEFT)

        # ── 底部按钮 ──
        sep3 = tk.Frame(content, bg=THEME["border"], height=1)
        sep3.pack(fill=tk.X, pady=(12, 12))

        btn_bar = tk.Frame(content, bg=THEME["bg_main"])
        btn_bar.pack(fill=tk.X)

        # 关于信息
        tk.Label(
            btn_bar, text="悬浮记事本 v2.0", font=small_font,
            bg=THEME["bg_main"], fg=THEME["fg_hint"]
        ).pack(side=tk.LEFT)

        close_btn = tk.Button(
            btn_bar, text="关闭", width=8,
            bg=THEME["bg_title"], fg=THEME["fg_text"],
            font=label_font, relief=tk.FLAT,
            activebackground=THEME["accent"],
            activeforeground="#FFFFFF",
            cursor="hand2",
            command=win.destroy
        )
        close_btn.pack(side=tk.RIGHT)

        # 模态等待
        win.grab_set()
        self.root.wait_window(win)

    def _get_current_preset_index(self):
        """获取当前热键配置对应的预设索引"""
        mods = self.config.get("hotkey_modifiers", ["ctrl", "alt"])
        key = self.config.get("hotkey_key", "n")
        for i, (_, pmods, pkey) in enumerate(HOTKEY_PRESETS):
            if sorted(pmods) == sorted(mods) and pkey == key:
                return i
        return -1

    def toggle_auto_start(self):
        """切换开机自启状态"""
        if self.auto_var.get():
            success = install_auto_start()
            if success:
                self.config["auto_start"] = True
                self.save_config()
                self.update_status("已启用开机自启")
            else:
                self.auto_var.set(False)
                messagebox.showwarning("提示", "开机自启设置失败，请重试。")
        else:
            success = remove_auto_start()
            if success:
                self.config["auto_start"] = False
                self.save_config()
                self.update_status("已关闭开机自启")
            else:
                self.auto_var.set(True)
                messagebox.showwarning("提示", "移除开机自启失败，请重试。")

    def toggle_desktop_shortcut(self, btn_widget):
        """创建或移除桌面快捷方式"""
        has_it = check_desktop_shortcut()
        if has_it:
            success = remove_desktop_shortcut()
            if success:
                self.dskt_status_label.config(text="未创建", fg=THEME["fg_hint"])
                btn_widget.config(text="创建桌面快捷方式")
                self.config["desktop_shortcut"] = False
                self.save_config()
                self.update_status("已移除桌面快捷方式")
        else:
            success = create_desktop_shortcut()
            if success:
                self.dskt_status_label.config(text="✅ 已创建", fg=THEME["fg_status"])
                btn_widget.config(text="移除快捷方式")
                self.config["desktop_shortcut"] = True
                self.save_config()
                self.update_status("已创建桌面快捷方式")
            else:
                messagebox.showwarning("提示", "桌面快捷方式创建失败，请重试。")

    # ═══ 入口 ═══
    def run(self):
        self.root.mainloop()


# ═══════════════════════════════════════════════════════════
# 工具函数：开机自启 + 桌面快捷方式
# ═══════════════════════════════════════════════════════════

def get_startup_dir():
    """获取 Windows 启动文件夹路径"""
    return Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Startup"


def get_shortcut_path():
    """获取启动文件夹中快捷方式的路径"""
    return get_startup_dir() / "悬浮记事本.lnk"


def get_desktop_shortcut_path():
    """获取桌面快捷方式路径"""
    return DESKTOP_DIR / "悬浮记事本.lnk"


def get_script_path():
    return Path(__file__).resolve()


def get_pythonw_path():
    """获取 pythonw.exe 路径（无控制台窗口）"""
    return sys.executable.replace("python.exe", "pythonw.exe")


def check_auto_start():
    """检查是否已设置开机自启"""
    return get_shortcut_path().exists()


def check_desktop_shortcut():
    """检查桌面快捷方式是否存在"""
    return get_desktop_shortcut_path().exists()


def install_auto_start():
    """安装开机自启 — 在启动文件夹创建快捷方式"""
    try:
        script_path = get_script_path()
        pythonw = get_pythonw_path()
        shortcut_path = get_shortcut_path()

        ps_cmd = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{pythonw}"
$Shortcut.Arguments = '"{script_path}"'
$Shortcut.Description = "悬浮记事本 — 开机自启"
$Shortcut.WorkingDirectory = "{script_path.parent}"
$Shortcut.WindowStyle = 7
$Shortcut.Save()
'''
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=10
        )
        if shortcut_path.exists():
            print("[FloatNotepad] 已安装开机自启")
            return True
        else:
            print(f"[FloatNotepad] 开机自启安装失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"[FloatNotepad] 开机自启安装异常: {e}")
        return False


def remove_auto_start():
    """移除开机自启"""
    try:
        shortcut_path = get_shortcut_path()
        if shortcut_path.exists():
            shortcut_path.unlink()
            print("[FloatNotepad] 已移除开机自启")
        return True
    except Exception as e:
        print(f"[FloatNotepad] 移除开机自启失败: {e}")
        return False


def create_desktop_shortcut():
    """创建桌面快捷方式"""
    try:
        script_path = get_script_path()
        pythonw = get_pythonw_path()
        shortcut_path = get_desktop_shortcut_path()

        ps_cmd = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{pythonw}"
$Shortcut.Arguments = '"{script_path}"'
$Shortcut.Description = "悬浮记事本 — 桌面便签"
$Shortcut.WorkingDirectory = "{script_path.parent}"
$Shortcut.WindowStyle = 7
$Shortcut.Save()
'''
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=10
        )
        if shortcut_path.exists():
            print(f"[FloatNotepad] 已创建桌面快捷方式: {shortcut_path}")
            return True
        return False
    except Exception as e:
        print(f"[FloatNotepad] 创建桌面快捷方式失败: {e}")
        return False


def remove_desktop_shortcut():
    """移除桌面快捷方式"""
    try:
        shortcut_path = get_desktop_shortcut_path()
        if shortcut_path.exists():
            shortcut_path.unlink()
            print("[FloatNotepad] 已移除桌面快捷方式")
        return True
    except Exception as e:
        print(f"[FloatNotepad] 移除桌面快捷方式失败: {e}")
        return False


# ═══════════════════════════════════════════════════════════
# 命令行接口
# ═══════════════════════════════════════════════════════════

def main():
    if "--install-startup" in sys.argv:
        if install_auto_start():
            print("[OK] 已安装开机自启")
        else:
            print("[FAIL] 安装开机自启失败")
        return

    if "--uninstall-startup" in sys.argv:
        if remove_auto_start():
            print("[OK] 已移除开机自启")
        else:
            print("[FAIL] 移除开机自启失败")
        return

    if "--install-desktop" in sys.argv:
        if create_desktop_shortcut():
            print("[OK] 已创建桌面快捷方式")
        else:
            print("[FAIL] 桌面快捷方式创建失败")
        return

    if "--uninstall-desktop" in sys.argv:
        if remove_desktop_shortcut():
            print("[OK] 已移除桌面快捷方式")
        else:
            print("[FAIL] 桌面快捷方式移除失败")
        return

    if "--setup" in sys.argv:
        # 一键安装：开机自启 + 桌面快捷方式
        ok1 = install_auto_start()
        ok2 = create_desktop_shortcut()
        print(f"开机自启: {'[OK]' if ok1 else '[FAIL]'}")
        print(f"桌面快捷方式: {'[OK]' if ok2 else '[FAIL]'}")
        return

    if "--help" in sys.argv or "-h" in sys.argv:
        print("悬浮记事本 v2.0")
        print("用法: python float_notepad.py [选项]")
        print("  --setup              一键安装（开机自启 + 桌面快捷方式）")
        print("  --install-startup    仅安装开机自启")
        print("  --uninstall-startup  仅移除开机自启")
        print("  --install-desktop    仅创建桌面快捷方式")
        print("  --uninstall-desktop  仅移除桌面快捷方式")
        print("  无参数               启动悬浮记事本")
        return

    app = FloatNotepad()
    app.run()


if __name__ == "__main__":
    main()
