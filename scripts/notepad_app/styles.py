"""
护眼主题样式模块
定义颜色常量、字体配置和 QSS 样式表
"""

# ═══════════════════════════════════════════════════════
# 颜色常量
# ═══════════════════════════════════════════════════════

# 编辑器背景色 — 浅米黄护眼色
BG_COLOR = "#F5E6C8"

# 编辑器文字色 — 深棕，柔和不刺眼
TEXT_COLOR = "#3E2723"

# 光标颜色
CURSOR_COLOR = "#5D4037"

# 选中文字背景色
SELECTION_BG = "#C8B89A"

# 选中文字颜色
SELECTION_FG = "#3E2723"

# 标签栏颜色
TAB_BG = "#E8DCC8"
TAB_ACTIVE_BG = "#F5E6C8"
TAB_HOVER_BG = "#F0E4D0"
TAB_BORDER = "#C8B89A"
TAB_TEXT = "#5D4E37"
TAB_TEXT_ACTIVE = "#3E2723"

# 菜单栏颜色
MENU_BG = "#F0E8D5"
MENU_HOVER = "#D7CCC8"
MENU_BORDER = "#C8B89A"

# ═══════════════════════════════════════════════════════
# 字体配置
# ═══════════════════════════════════════════════════════

# 编辑区域字体 — 使用系统 UI 字体，更清晰
FONT_FAMILY = "Microsoft YaHei UI"
FONT_SIZE = 12

# 标签栏字体
FONT_SIZE_TAB = 10

# ═══════════════════════════════════════════════════════
# 编辑器 QSS 样式表
# ═══════════════════════════════════════════════════════

EDITOR_STYLE = f"""
QPlainTextEdit {{
    background-color: {BG_COLOR};
    color: {TEXT_COLOR};
    font-family: "{FONT_FAMILY}";
    font-size: {FONT_SIZE}pt;
    border: none;
    selection-background-color: {SELECTION_BG};
    selection-color: {SELECTION_FG};
    padding: 10px 14px;
}}
"""

# ═══════════════════════════════════════════════════════
# 标签栏样式（彻底美化）
# ═══════════════════════════════════════════════════════

TAB_WIDGET_STYLE = f"""
QTabWidget::pane {{
    background-color: {BG_COLOR};
    border: none;
    top: -1px;
}}

QTabBar {{
    background-color: {TAB_BG};
    border-bottom: 1px solid {TAB_BORDER};
    qproperty-drawBase: 0;
}}

QTabBar::tab {{
    background-color: #DDD0B8;
    color: {TAB_TEXT};
    font-family: "{FONT_FAMILY}";
    font-size: {FONT_SIZE_TAB}pt;
    padding: 7px 20px;
    margin-right: 1px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid {TAB_BORDER};
    border-bottom: none;
    min-width: 60px;
}}

QTabBar::tab:selected {{
    background-color: {TAB_ACTIVE_BG};
    color: {TAB_TEXT_ACTIVE};
    font-weight: bold;
    border-bottom: 2px solid {TAB_ACTIVE_BG};
    padding-top: 8px;
    padding-bottom: 8px;
}}

QTabBar::tab:hover:!selected {{
    background-color: {TAB_HOVER_BG};
}}

QTabBar::tab:first {{
    margin-left: 4px;
}}

/* ── 关闭按钮美化 ── */
QTabBar::close-button {{
    subcontrol-position: right;
    subcontrol-origin: padding;
    margin-left: 10px;
    margin-right: 2px;
    padding: 0px;
    border-radius: 8px;
    background-color: transparent;
}}

QTabBar::close-button:hover {{
    background-color: #D7CCC8;
}}

/* ── 新建标签按钮（+）在标签栏右侧 ── */
QTabBar::scroller {{
    width: 0px;
}}

QTabWidget::right-corner {{
    background-color: {TAB_BG};
    border-bottom: 1px solid {TAB_BORDER};
}}
"""

# ═══════════════════════════════════════════════════════
# 菜单栏样式
# ═══════════════════════════════════════════════════════

MENUBAR_STYLE = f"""
QMenuBar {{
    background-color: {MENU_BG};
    color: {TEXT_COLOR};
    font-family: "{FONT_FAMILY}";
    font-size: 11pt;
    border-bottom: 1px solid {MENU_BORDER};
    padding: 6px 8px;
}}

QMenuBar::item {{
    padding: 4px 10px;
    margin: 2px 2px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {MENU_HOVER};
}}

QMenu {{
    background-color: {MENU_BG};
    color: {TEXT_COLOR};
    font-family: "{FONT_FAMILY}";
    font-size: 11pt;
    border: 1px solid {MENU_BORDER};
    border-radius: 6px;
    padding: 8px 4px;
}}

QMenu::item {{
    padding: 10px 40px 10px 20px;
    margin: 2px 4px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {MENU_HOVER};
}}

QMenu::separator {{
    height: 1px;
    background: {MENU_BORDER};
    margin: 6px 16px;
}}
"""

# ═══════════════════════════════════════════════════════
# 全局窗口样式
# ═══════════════════════════════════════════════════════

WINDOW_STYLE = f"""
QMainWindow {{
    background-color: {BG_COLOR};
}}
"""
