# -*- coding: utf-8 -*-
"""
WPS 免关闭文件操作桥接
======================
通过 COM 连接「已经打开」的 WPS 表格/文字，直接读写内存中的数据，
从而不需要关闭文件即可分析和修改。适用于 WPS Office（个人版）。

依赖：pywin32（已安装 312）

模块用法：
    from scripts.utils.wps_bridge import get_et, get_wps, list_open, read_sheet

命令行用法：
    python scripts/utils/wps_bridge.py list           # 列出打开的表格和文档
    python scripts/utils/wps_bridge.py et             # 当前活动表格信息
    python scripts/utils/wps_bridge.py et --sheet 1   # 打印活动表格第1个工作表内容
    python scripts/utils/wps_bridge.py wps            # 当前活动文档信息
"""

import sys


def _force_utf8():
    """Windows 控制台默认 GBK，强制 UTF-8 避免中文/特殊字符乱码。"""
    for stream in (sys.stdout, sys.stderr):
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_force_utf8()

import win32com.client


# ── 连接 ──────────────────────────────────────────────
def get_et():
    """连接已打开的 WPS 表格（对应 Excel），不启动新进程。"""
    try:
        return win32com.client.GetActiveObject("KET.Application")
    except Exception as e:
        raise RuntimeError(
            "未检测到打开的 WPS 表格，请先在 WPS 中打开目标表格文件"
        ) from e


def get_wps():
    """连接已打开的 WPS 文字（对应 Word），不启动新进程。"""
    try:
        return win32com.client.GetActiveObject("KWPS.Application")
    except Exception as e:
        raise RuntimeError(
            "未检测到打开的 WPS 文字，请先在 WPS 中打开目标文档"
        ) from e


# ── 枚举 ──────────────────────────────────────────────
def list_open(app):
    """返回 (类型名, [打开的文件名列表])。"""
    if hasattr(app, "Workbooks"):
        return "工作簿", [wb.Name for wb in app.Workbooks]
    return "文档", [doc.Name for doc in app.Documents]


def active_name(app):
    """当前活动文件的名称。"""
    if hasattr(app, "Workbooks"):
        return app.ActiveWorkbook.Name
    return app.ActiveDocument.Name


# ── 读取 ──────────────────────────────────────────────
def read_sheet(app, name=None, sheet=None):
    """把表格某个工作表读成二维列表 list[list]。name=工作簿名, sheet=工作表名/序号。"""
    wb = app.Workbooks(name) if name else app.ActiveWorkbook
    ws = wb.Worksheets(sheet) if sheet else wb.ActiveSheet
    used = ws.UsedRange
    rows, cols = used.Rows.Count, used.Columns.Count
    if rows * cols > 500_000:
        raise RuntimeError(f"数据量过大({rows}×{cols})，请指定更小区域再读")
    raw = ws.Range(ws.Cells(1, 1), ws.Cells(rows, cols)).Value
    if rows == 1 and cols == 1:
        return [[raw]]
    return [list(r) for r in raw]


def read_document_text(app, name=None):
    """读取文档全文文本。"""
    doc = app.Documents(name) if name else app.ActiveDocument
    return doc.Content.Text


# ── 写入 ──────────────────────────────────────────────
def write_sheet(app, name=None, sheet=None):
    """返回可写的工作表对象，供 set_cell 等直接操作。"""
    wb = app.Workbooks(name) if name else app.ActiveWorkbook
    return wb.Worksheets(sheet) if sheet else wb.ActiveSheet


def set_cell(ws, row, col, value):
    """写单个单元格（1 基索引）。"""
    ws.Cells(row, col).Value = value


# ── 保存 ──────────────────────────────────────────────
def save(app, name=None):
    """让 WPS 自己保存指定/活动文件（绕开文件锁）。返回保存的文件名。"""
    if hasattr(app, "Workbooks"):
        wb = app.Workbooks(name) if name else app.ActiveWorkbook
        wb.Save()
        return wb.Name
    doc = app.Documents(name) if name else app.ActiveDocument
    doc.Save()
    return doc.Name


def save_as(app, path, name=None):
    """另存为指定路径（可用于生成副本，不必覆盖原文件）。"""
    if hasattr(app, "Workbooks"):
        wb = app.Workbooks(name) if name else app.ActiveWorkbook
        wb.SaveAs(path)
        return path
    doc = app.Documents(name) if name else app.ActiveDocument
    doc.SaveAs(path)
    return path


# ── 命令行 ────────────────────────────────────────────
def _main():
    import argparse

    p = argparse.ArgumentParser(description="WPS 免关闭文件操作桥接")
    p.add_argument(
        "target",
        nargs="?",
        choices=["list", "et", "wps"],
        help="list=列出打开文件; et=表格; wps=文字",
    )
    p.add_argument("--sheet", help="打印指定工作表（et 时用，序号或名称）")
    args = p.parse_args()

    if args.target == "list":
        for getter in (get_et, get_wps):
            try:
                app = getter()
            except RuntimeError as e:
                print(f"[跳过] {e}")
                continue
            kind, names = list_open(app)
            print(f"{kind}: {names if names else '(空)'}")
        return

    if args.target in ("et", "wps"):
        app = get_et() if args.target == "et" else get_wps()
        print(f"活动文件: {active_name(app)}")
        if args.target == "et" and args.sheet is not None:
            for row in read_sheet(app, sheet=args.sheet):
                print("\t".join("" if c is None else str(c) for c in row))


if __name__ == "__main__":
    _main()
