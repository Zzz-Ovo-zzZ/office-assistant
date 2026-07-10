"""
内嵌图标资源
使用 QPainter 程序绘制图标，避免外部文件依赖
生成一个淡黄色笔记本风格图标
"""

from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtCore import Qt, QRect, QPoint


def get_icon():
    """
    用 QPainter 绘制一个简单的记事本图标 (32x32)
    返回 QIcon 供托盘和窗口使用
    """
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # ── 背景矩形（米黄色纸张） ─────────
    painter.setPen(QPen(QColor("#BFA77A"), 1))
    painter.setBrush(QBrush(QColor("#F5E6C8")))
    painter.drawRoundedRect(2, 1, 28, 29, 3, 3)

    # ── 横线（模拟文字行） ─────────────
    painter.setPen(QPen(QColor("#D7CCC8"), 1))
    for y in (8, 13, 18):
        painter.drawLine(7, y, 25, y)

    # ── 装订环（顶部两个小圈） ─────────
    painter.setPen(QPen(QColor("#8D6E63"), 1.5))
    painter.setBrush(QBrush(QColor("#BCAAA4")))
    painter.drawEllipse(QPoint(10, 2), 2, 2)
    painter.drawEllipse(QPoint(22, 2), 2, 2)

    # ── 红色书签带 ────────────────────
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor("#E57373")))
    painter.drawRect(25, 7, 2, 8)

    painter.end()

    return QIcon(pixmap)
