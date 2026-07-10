"""
配置持久化管理模块
通过 QSettings 管理应用所有配置项
"""

import os
from PyQt6.QtCore import QSettings

# ═══════════════════════════════════════════════════════
# 常量
# ═══════════════════════════════════════════════════════

APP_NAME = "OfficeNotepad"
ORG_NAME = "OfficeAssistant"

# 数据存储目录：%APPDATA%/OfficeNotepad/
DATA_DIR = os.path.join(os.getenv("APPDATA"), APP_NAME)
NOTES_DIR = os.path.join(DATA_DIR, "notes")


def ensure_dirs():
    """确保数据目录存在"""
    os.makedirs(NOTES_DIR, exist_ok=True)


class SettingsManager:
    """应用配置管理器，封装 QSettings"""

    def __init__(self):
        self._settings = QSettings(ORG_NAME, APP_NAME)
        ensure_dirs()

    # ── 窗口状态 ──────────────────────────────

    def get_window_geometry(self):
        """获取窗口位置和大小，返回 (x, y, w, h) 或 None"""
        geo = self._settings.value("window/geometry")
        if geo is not None:
            return geo  # QByteArray
        return None

    def set_window_geometry(self, geometry):
        """保存窗口位置和大小"""
        self._settings.setValue("window/geometry", geometry)

    def get_window_maximized(self):
        """获取窗口是否最大化"""
        val = self._settings.value("window/maximized", False)
        return str(val).lower() == "true"

    def set_window_maximized(self, maximized):
        self._settings.setValue("window/maximized", maximized)

    # ── 置顶状态 ──────────────────────────────

    def get_always_on_top(self):
        val = self._settings.value("window/always_on_top", False)
        return str(val).lower() == "true"

    def set_always_on_top(self, on_top):
        self._settings.setValue("window/always_on_top", on_top)

    # ── 开机自启 ──────────────────────────────

    def get_auto_start(self):
        val = self._settings.value("system/auto_start", False)
        return str(val).lower() == "true"

    def set_auto_start(self, enabled):
        self._settings.setValue("system/auto_start", enabled)

    # ── 标签管理 ──────────────────────────────

    def get_tab_count(self):
        return int(self._settings.value("tabs/count", 1))

    def set_tab_count(self, count):
        self._settings.setValue("tabs/count", count)

    def get_tab_name(self, index):
        """获取标签名，默认"笔记 N" """
        default = f"笔记 {index + 1}"
        return self._settings.value(f"tabs/name_{index}", default)

    def set_tab_name(self, index, name):
        self._settings.setValue(f"tabs/name_{index}", name)

    def get_current_tab(self):
        return int(self._settings.value("tabs/current", 0))

    def set_current_tab(self, index):
        self._settings.setValue("tabs/current", index)

    def get_tab_file(self, index):
        """获取标签对应的文件路径"""
        default = os.path.join(NOTES_DIR, f"tab_{index + 1}.txt")
        return self._settings.value(f"tabs/file_{index}", default)

    def set_tab_file(self, index, filepath):
        self._settings.setValue(f"tabs/file_{index}", filepath)

    def remove_tab(self, index):
        """删除指定标签的配置"""
        self._settings.remove(f"tabs/name_{index}")
        self._settings.remove(f"tabs/file_{index}")

    def list_all_tabs(self):
        """返回所有标签的 (name, filepath) 列表"""
        count = self.get_tab_count()
        tabs = []
        for i in range(count):
            name = self.get_tab_name(i)
            path = self.get_tab_file(i)
            tabs.append((name, path))
        return tabs

    def sync(self):
        """同步写入磁盘"""
        self._settings.sync()
