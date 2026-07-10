"""
桌面快捷方式创建模块
使用 PowerShell 在用户桌面生成 .lnk 文件
"""

import os
import subprocess


LNK_NAME = "办公记事本.lnk"


def _get_desktop_path():
    """获取用户桌面路径"""
    return os.path.join(os.path.expanduser("~"), "Desktop")


def shortcut_exists():
    """检查桌面是否已有快捷方式"""
    desktop = _get_desktop_path()
    lnk_path = os.path.join(desktop, LNK_NAME)
    return os.path.exists(lnk_path)


def create_desktop_shortcut():
    """
    在桌面创建快捷方式
    使用 PowerShell 创建 .lnk，指向 pythonw.exe 运行 main.py
    返回快捷方式路径，失败返回 None
    """
    desktop = _get_desktop_path()
    lnk_path = os.path.join(desktop, LNK_NAME)

    # 目标脚本路径
    main_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(main_dir, "main.py")

    # pythonw.exe 路径（无控制台窗口）
    import sys
    python_exe = sys.executable
    python_dir = os.path.dirname(python_exe)
    pythonw = os.path.join(python_dir, "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = python_exe

    # 工作目录
    working_dir = main_dir

    # 使用 PowerShell 创建快捷方式
    ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{lnk_path}")
$Shortcut.TargetPath = "{pythonw}"
$Shortcut.Arguments = '"{main_py}"'
$Shortcut.WorkingDirectory = "{working_dir}"
$Shortcut.Description = "办公记事本 - 悬浮护眼多标签记事本"
$Shortcut.Save()
Write-Output "OK"
'''

    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=10
        )
        if "OK" in result.stdout:
            return lnk_path
        else:
            print(f"创建快捷方式失败: {result.stderr}")
            return None
    except Exception as e:
        print(f"创建快捷方式异常: {e}")
        return None
