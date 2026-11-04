' 悬浮记事本 v2.0 静默启动（无控制台窗口，路径相对脚本自身）
Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "pythonw """ & base & "\scripts\float_notepad.py""", 0, False
