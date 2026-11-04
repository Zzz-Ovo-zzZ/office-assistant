# -*- coding: utf-8 -*-
"""在桌面创建「前进吧zzz」快捷方式（无控制台窗口 + 高颜值番茄图标）。

用法：
    python scripts/focus/make_shortcut.py
"""

import base64
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.join(HERE, "pomodoro.py")
ICON_PATH = os.path.join(HERE, "focus.ico")
SHORTCUT_NAME = "前进吧zzz"


def pythonw_path():
    """返回无控制台窗口的 pythonw.exe 路径。"""
    base = os.path.dirname(sys.executable)
    for name in ("pythonw.exe", "pythonw3.exe"):
        p = os.path.join(base, name)
        if os.path.exists(p):
            return p
    return sys.executable


def ensure_icon():
    if os.path.exists(ICON_PATH):
        return
    import make_icon
    make_icon.main()


def create_shortcut():
    target = pythonw_path()
    # 用 -EncodedCommand（UTF-16LE base64）传递命令，规避 .ps1 文件的中文编码问题
    ps = f"""
$desktop = [Environment]::GetFolderPath('Desktop')
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut((Join-Path $desktop '{SHORTCUT_NAME}.lnk'))
$sc.TargetPath = '{target}'
$sc.Arguments = '"{SCRIPT_PATH}"'
$sc.WorkingDirectory = '{HERE}'
$sc.IconLocation = '{ICON_PATH},0'
$sc.Description = '前进吧zzz - 置顶监督番茄钟'
$sc.Save()
Write-Output (Join-Path $desktop '{SHORTCUT_NAME}.lnk')
"""
    enc = base64.b64encode(ps.encode("utf-16-le")).decode("ascii")
    out = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", enc],
        capture_output=True, text=True)
    if out.returncode != 0:
        print("创建失败:\n", out.stderr)
        return None
    return out.stdout.strip()


if __name__ == "__main__":
    ensure_icon()
    path = create_shortcut()
    if path and os.path.exists(path):
        print("✅ 快捷方式已创建:", path)
    else:
        print("❌ 快捷方式创建失败")
        sys.exit(1)
