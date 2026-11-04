@echo off
:: 悬浮记事本 v2.0 启动脚本（相对路径，项目放哪都能用）
cd /d "%~dp0"
where pythonw >nul 2>nul && (start "" pythonw "scripts\float_notepad.py") || (start "" python "scripts\float_notepad.py")
