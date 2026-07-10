"""
悬浮记事本主窗口
标签栏管理、菜单栏、系统托盘、置顶/自启控制
"""

import os
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QMenuBar, QMenu, QMessageBox,
    QInputDialog, QSystemTrayIcon, QApplication, QPushButton,
    QWidget, QHBoxLayout
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QAction, QKeySequence, QCloseEvent, QIcon, QPainter, QPixmap, QColor

from . import styles
from .text_edit import AutoSaveTextEdit
from .settings_manager import SettingsManager, NOTES_DIR
from .auto_start import is_auto_start_enabled, set_auto_start as reg_set_auto_start
from .resources.icon import get_icon


class MainWindow(QMainWindow):
    """记事本主窗口"""

    def __init__(self):
        super().__init__()

        self._settings = SettingsManager()

        # 窗口属性
        self.setWindowTitle("办公记事本")
        self.resize(720, 480)

        # ── 加载上次窗口位置 ──────────────
        geo = self._settings.get_window_geometry()
        if geo is not None:
            self.restoreGeometry(geo)
        if self._settings.get_window_maximized():
            self.showMaximized()

        # ── 应用全局样式 ──────────────────
        self.setStyleSheet(
            styles.MENUBAR_STYLE + "\n" + styles.WINDOW_STYLE
        )

        # ── 创建界面 ──────────────────────
        self._create_menu_bar()
        self._create_tab_widget()
        self._create_system_tray()

        # ── 恢复状态 ──────────────────────
        self._restore_tabs()
        self._apply_always_on_top()
        self._sync_auto_start_menu()

        # ── 窗口关闭检测 ──────────────────
        self._closing_to_tray = False

    # ═══════════════════════════════════════
    # 菜单栏
    # ═══════════════════════════════════════

    def _create_menu_bar(self):
        menubar = self.menuBar()

        # ── 文件菜单 ──────────────────────
        file_menu = menubar.addMenu("文件(&F)")

        new_tab_action = QAction("新建标签(&N)", self)
        new_tab_action.setShortcut(QKeySequence("Ctrl+T"))
        new_tab_action.triggered.connect(self._new_tab)
        file_menu.addAction(new_tab_action)

        rename_tab_action = QAction("重命名标签(&R)", self)
        rename_tab_action.setShortcut(QKeySequence("Ctrl+Shift+R"))
        rename_tab_action.triggered.connect(self._rename_current_tab)
        file_menu.addAction(rename_tab_action)

        close_tab_action = QAction("关闭标签(&W)", self)
        close_tab_action.setShortcut(QKeySequence("Ctrl+W"))
        close_tab_action.triggered.connect(self._close_current_tab)
        file_menu.addAction(close_tab_action)

        file_menu.addSeparator()

        open_dir_action = QAction("打开保存目录(&D)", self)
        open_dir_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        open_dir_action.triggered.connect(self._open_save_directory)
        file_menu.addAction(open_dir_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self._real_exit)
        file_menu.addAction(exit_action)

        # ── 视图菜单 ──────────────────────
        view_menu = menubar.addMenu("视图(&V)")

        self._always_on_top_action = QAction("窗口置顶(&T)", self)
        self._always_on_top_action.setCheckable(True)
        self._always_on_top_action.setChecked(self._settings.get_always_on_top())
        self._always_on_top_action.toggled.connect(self._toggle_always_on_top)
        view_menu.addAction(self._always_on_top_action)

        view_menu.addSeparator()

        self._auto_start_action = QAction("开机自启(&A)", self)
        self._auto_start_action.setCheckable(True)
        self._auto_start_action.toggled.connect(self._toggle_auto_start)
        view_menu.addAction(self._auto_start_action)

    # ═══════════════════════════════════════
    # 标签页管理
    # ═══════════════════════════════════════

    def _create_tab_widget(self):
        self._tab_widget = QTabWidget(self)
        self._tab_widget.setTabsClosable(True)
        self._tab_widget.setMovable(True)
        self._tab_widget.setStyleSheet(styles.TAB_WIDGET_STYLE)
        self._tab_widget.tabCloseRequested.connect(self._on_tab_close_requested)
        self._tab_widget.currentChanged.connect(self._on_tab_changed)
        self._tab_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tab_widget.customContextMenuRequested.connect(self._on_tab_context_menu)

        # ── 右侧 + 新建标签按钮 ──────────
        self._add_tab_btn = QPushButton("+")
        self._add_tab_btn.setFixedSize(28, 26)
        self._add_tab_btn.setToolTip("新建标签 (Ctrl+T)")
        self._add_tab_btn.clicked.connect(self._new_tab)
        self._add_tab_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.TAB_BG};
                color: {styles.TAB_TEXT};
                border: 1px solid {styles.TAB_BORDER};
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
                font-family: "{styles.FONT_FAMILY}";
                margin-right: 4px;
            }}
            QPushButton:hover {{
                background-color: {styles.TAB_HOVER_BG};
                color: {styles.TAB_TEXT_ACTIVE};
            }}
            QPushButton:pressed {{
                background-color: {styles.TAB_BORDER};
            }}
        """)
        # 放在标签栏右侧
        self._tab_widget.setCornerWidget(self._add_tab_btn, Qt.Corner.TopRightCorner)

        self.setCentralWidget(self._tab_widget)

    def _new_tab(self, name=None, file_path=None, select=True):
        """创建新标签页"""
        idx = self._tab_widget.count()
        if name is None:
            name = f"笔记 {idx + 1}"
        if file_path is None:
            file_path = os.path.join(NOTES_DIR, f"tab_{idx + 1}.txt")

        editor = AutoSaveTextEdit(file_path)
        self._tab_widget.addTab(editor, name)

        if select:
            self._tab_widget.setCurrentWidget(editor)

        self._save_tabs_config()
        return editor

    def _close_current_tab(self):
        """关闭当前标签"""
        idx = self._tab_widget.currentIndex()
        if idx >= 0:
            self._close_tab(idx)

    def _on_tab_close_requested(self, idx):
        """用户点击标签关闭按钮"""
        self._close_tab(idx)

    def _close_tab(self, idx):
        """关闭指定标签（保存内容、清理文件）"""
        # 至少保留一个标签
        if self._tab_widget.count() <= 1:
            return

        editor = self._tab_widget.widget(idx)
        if isinstance(editor, AutoSaveTextEdit):
            editor.save_now()

        self._tab_widget.removeTab(idx)

        # 重新编号：更新配置
        self._save_tabs_config()

    def _on_tab_changed(self, idx):
        """标签切换"""
        if idx >= 0:
            self._settings.set_current_tab(idx)

    def _on_tab_context_menu(self, pos):
        """标签右键菜单"""
        tab_idx = self._tab_widget.tabBar().tabAt(pos)
        if tab_idx < 0:
            return

        menu = QMenu(self)
        menu.setStyleSheet(styles.MENUBAR_STYLE)

        rename_action = menu.addAction("重命名")
        close_action = menu.addAction("关闭标签")
        menu.addSeparator()
        new_action = menu.addAction("新建标签")

        action = menu.exec(self._tab_widget.tabBar().mapToGlobal(pos))

        if action == rename_action:
            self._rename_tab(tab_idx)
        elif action == close_action:
            self._close_tab(tab_idx)
        elif action == new_action:
            self._new_tab()

    def _rename_current_tab(self):
        """重命名当前标签"""
        idx = self._tab_widget.currentIndex()
        if idx >= 0:
            self._rename_tab(idx)

    def _rename_tab(self, idx):
        """弹出对话框重命名指定标签"""
        old_name = self._tab_widget.tabText(idx)
        new_name, ok = QInputDialog.getText(
            self, "重命名标签", "请输入新名称：",
            text=old_name
        )
        if ok and new_name.strip():
            self._tab_widget.setTabText(idx, new_name.strip())
            self._save_tabs_config()

    # ═══════════════════════════════════════
    # 标签配置持久化
    # ═══════════════════════════════════════

    def _save_tabs_config(self):
        """保存所有标签配置到 QSettings"""
        count = self._tab_widget.count()
        self._settings.set_tab_count(count)
        for i in range(count):
            name = self._tab_widget.tabText(i)
            self._settings.set_tab_name(i, name)
            editor = self._tab_widget.widget(i)
            if isinstance(editor, AutoSaveTextEdit):
                self._settings.set_tab_file(i, editor.file_path())
        # 清理多余的旧配置
        old_count = self._settings.get_tab_count()
        for i in range(count, old_count + 5):
            self._settings.remove_tab(i)

    def _restore_tabs(self):
        """从配置恢复标签页"""
        count = self._settings.get_tab_count()
        if count <= 0:
            # 首次运行，创建默认标签
            self._new_tab("笔记 1")
            return

        for i in range(count):
            name = self._settings.get_tab_name(i)
            file_path = self._settings.get_tab_file(i)
            self._new_tab(name, file_path, select=False)

        # 恢复上次活跃标签
        current = self._settings.get_current_tab()
        if 0 <= current < self._tab_widget.count():
            self._tab_widget.setCurrentIndex(current)

    # ═══════════════════════════════════════
    # 打开保存目录
    # ═══════════════════════════════════════

    def _open_save_directory(self):
        """在资源管理器中打开笔记保存目录"""
        import subprocess
        subprocess.Popen(["explorer", NOTES_DIR])

    # ═══════════════════════════════════════
    # 系统托盘
    # ═══════════════════════════════════════

    def _create_system_tray(self):
        """创建系统托盘图标和菜单"""
        self._tray_icon = QSystemTrayIcon(self)
        self._tray_icon.setIcon(get_icon())
        self._tray_icon.setToolTip("办公记事本")

        # 托盘菜单
        tray_menu = QMenu(self)
        tray_menu.setStyleSheet(styles.MENUBAR_STYLE)

        show_action = tray_menu.addAction("显示窗口")
        show_action.triggered.connect(self._show_from_tray)

        new_action = tray_menu.addAction("新建标签")
        new_action.triggered.connect(self._new_tab)

        tray_menu.addSeparator()

        # 置顶开关
        top_action = QAction("窗口置顶", tray_menu)
        top_action.setCheckable(True)
        top_action.setChecked(self._settings.get_always_on_top())
        top_action.toggled.connect(self._toggle_always_on_top)
        # 同步菜单栏
        top_action.toggled.connect(self._always_on_top_action.setChecked)
        tray_menu.addAction(top_action)

        tray_menu.addSeparator()

        exit_action = tray_menu.addAction("退出")
        exit_action.triggered.connect(self._real_exit)

        self._tray_icon.setContextMenu(tray_menu)

        # 双击托盘图标恢复窗口
        self._tray_icon.activated.connect(self._on_tray_activated)

        self._tray_icon.show()

    def _on_tray_activated(self, reason):
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def _show_from_tray(self):
        """从托盘恢复窗口"""
        self.showNormal()
        self.activateWindow()
        self.raise_()

    # ═══════════════════════════════════════
    # 置顶控制
    # ═══════════════════════════════════════

    def _toggle_always_on_top(self, checked):
        """切换窗口置顶"""
        self._settings.set_always_on_top(checked)
        self._apply_always_on_top()

    def _apply_always_on_top(self):
        """应用置顶设置"""
        on_top = self._settings.get_always_on_top()
        if on_top:
            self.setWindowFlags(
                self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
            )
        else:
            self.setWindowFlags(
                self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint
            )
        # 窗口标志变更后需要重新显示
        self.show()

    # ═══════════════════════════════════════
    # 开机自启控制
    # ═══════════════════════════════════════

    def _toggle_auto_start(self, checked):
        """切换开机自启"""
        success = reg_set_auto_start(checked)
        if success:
            self._settings.set_auto_start(checked)
        else:
            # 操作失败，恢复勾选状态
            self._auto_start_action.setChecked(not checked)

    def _sync_auto_start_menu(self):
        """同步自启菜单与实际注册表状态"""
        enabled = is_auto_start_enabled()
        self._auto_start_action.setChecked(enabled)
        self._settings.set_auto_start(enabled)

    # ═══════════════════════════════════════
    # 窗口事件
    # ═══════════════════════════════════════

    def closeEvent(self, event: QCloseEvent):
        """关闭窗口 → 隐藏到托盘（不退出）"""
        # 保存所有标签内容
        for i in range(self._tab_widget.count()):
            editor = self._tab_widget.widget(i)
            if isinstance(editor, AutoSaveTextEdit):
                editor.save_now()

        # 保存窗口状态
        self._settings.set_window_geometry(self.saveGeometry())
        self._settings.set_window_maximized(self.isMaximized())
        self._save_tabs_config()
        self._settings.sync()

        # 隐藏到托盘
        self.hide()
        self._tray_icon.showMessage(
            "办公记事本",
            "已最小化到系统托盘，双击图标恢复窗口。",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
        event.ignore()

    def _real_exit(self):
        """真正退出应用"""
        # 保存所有内容
        for i in range(self._tab_widget.count()):
            editor = self._tab_widget.widget(i)
            if isinstance(editor, AutoSaveTextEdit):
                editor.save_now()

        # 保存配置
        self._settings.set_window_geometry(self.saveGeometry())
        self._settings.set_window_maximized(self.isMaximized())
        self._save_tabs_config()
        self._settings.sync()

        # 隐藏托盘
        self._tray_icon.hide()

        QApplication.quit()
