"""
办公记事本 — 入口文件
悬浮护眼多标签记事本应用
"""

import sys
import os

# 确保项目根目录在 path 中，方便模块导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from notepad_app.main_window import MainWindow
from notepad_app.create_shortcut import shortcut_exists, create_desktop_shortcut


def main():
    # 高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("办公记事本")
    app.setOrganizationName("OfficeAssistant")

    # 确保持续运行（窗口隐藏到托盘后应用不退出）
    app.setQuitOnLastWindowClosed(False)

    # ── 首次运行：创建桌面快捷方式 ──────
    if not shortcut_exists():
        result = create_desktop_shortcut()
        if result:
            print(f"桌面快捷方式已创建: {result}")

    # ── 启动主窗口 ──────────────────────
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
