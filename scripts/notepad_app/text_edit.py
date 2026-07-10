"""
自定义编辑器控件
继承 QPlainTextEdit，实现防抖自动保存
"""

import os
from PyQt6.QtWidgets import QPlainTextEdit
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import (
    QFont, QTextCursor, QColor, QPalette, QTextDocument
)

from . import styles


# 自动保存延迟（毫秒）
AUTO_SAVE_DELAY = 2000


class AutoSaveTextEdit(QPlainTextEdit):
    """
    支持自动保存的文本编辑器
    - textChanged 后 2 秒自动写入磁盘
    - 绑定一个 .txt 文件路径
    - 护眼配色 + 舒适行距
    """

    def __init__(self, file_path, parent=None):
        super().__init__(parent)

        self._file_path = file_path
        self._modified = False

        # ── 视觉配置 ──────────────────────
        self._setup_appearance()

        # ── 自动换行 ──────────────────────
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)

        # ── 自动保存定时器 ────────────────
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(AUTO_SAVE_DELAY)
        self._save_timer.timeout.connect(self._do_save)

        # 连接信号
        self.textChanged.connect(self._on_text_changed)

        # ── 加载文件内容 ──────────────────
        self._load_file()

    # ═══════════════════════════════════════
    # 视觉设置
    # ═══════════════════════════════════════

    def _setup_appearance(self):
        """配置护眼配色、字体、行距"""
        # ── 字体（Microsoft YaHei UI 更清晰）──
        font = QFont(styles.FONT_FAMILY, styles.FONT_SIZE)
        font.setStyleHint(QFont.StyleHint.System)
        font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
        self.setFont(font)

        # ── 调色板 ────────────────────────
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(styles.BG_COLOR))
        palette.setColor(QPalette.ColorRole.Text, QColor(styles.TEXT_COLOR))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(styles.SELECTION_BG))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(styles.SELECTION_FG))
        self.setPalette(palette)

        # ── 文档级 CSS 行距 ───────────────
        # QTextDocument 原生支持 CSS2 的 line-height
        self.document().setDefaultStyleSheet(f"""
            body {{
                line-height: 160%;
            }}
        """)

        # ── 控件级样式表 ──────────────────
        self.setStyleSheet(styles.EDITOR_STYLE)

        # ── 光标 ──────────────────────────
        self.setCursorWidth(2)

    # ═══════════════════════════════════════
    # 公共接口
    # ═══════════════════════════════════════

    def file_path(self):
        """返回绑定的文件路径"""
        return self._file_path

    def set_file_path(self, path):
        """更换绑定的文件路径"""
        self._file_path = path

    def is_modified(self):
        """检查是否有未保存的修改"""
        return self._modified

    def save_now(self):
        """立即保存（关闭标签/退出时调用）"""
        if self._modified:
            self._save_timer.stop()
            self._do_save()

    # ═══════════════════════════════════════
    # 内部方法
    # ═══════════════════════════════════════

    def _on_text_changed(self):
        """文本变更 → 重置定时器"""
        self._modified = True
        self._save_timer.start()

    def _do_save(self):
        """执行写入磁盘"""
        try:
            os.makedirs(os.path.dirname(self._file_path), exist_ok=True)
            with open(self._file_path, "w", encoding="utf-8") as f:
                f.write(self.toPlainText())
            self._modified = False
        except OSError as e:
            print(f"自动保存失败 ({self._file_path}): {e}")

    def _load_file(self):
        """从磁盘加载文件内容"""
        if os.path.exists(self._file_path):
            try:
                with open(self._file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.setPlainText(content)
                # 移动光标到末尾
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.setTextCursor(cursor)
            except OSError as e:
                print(f"加载文件失败 ({self._file_path}): {e}")
