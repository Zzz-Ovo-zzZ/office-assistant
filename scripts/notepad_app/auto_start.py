r"""
Windows 注册表开机自启管理
通过 HKCU\Software\Microsoft\Windows\CurrentVersion\Run 注册/注销
"""

import os
import sys
import winreg


# 注册表路径
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "OfficeNotepad"


def _get_target_command():
    """
    获取开机启动要执行的命令
    使用 pythonw.exe 以无控制台窗口方式运行
    """
    main_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(main_dir, "main.py")

    # 查找 pythonw.exe（与 python.exe 同目录）
    python_exe = sys.executable
    python_dir = os.path.dirname(python_exe)
    pythonw = os.path.join(python_dir, "pythonw.exe")

    if not os.path.exists(pythonw):
        # 备选：尝试用 python.exe
        pythonw = python_exe

    return f'"{pythonw}" "{main_py}"'


def is_auto_start_enabled():
    """检查是否已注册开机自启"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ
        )
        try:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return value == _get_target_command()
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except OSError:
        return False


def set_auto_start(enable):
    """
    设置或取消开机自启
    enable=True → 注册
    enable=False → 注销
    返回是否操作成功
    """
    try:
        if enable:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
            )
            command = _get_target_command()
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
            winreg.CloseKey(key)
        else:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
            )
            try:
                winreg.QueryValueEx(key, APP_NAME)
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass  # 本来就没注册，无需删除
            winreg.CloseKey(key)
        return True
    except OSError as e:
        print(f"注册表操作失败: {e}")
        return False
