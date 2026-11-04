# -*- coding: utf-8 -*-
"""控制台编码修正 —— Windows 默认 GBK，打印中文/emoji 会报 UnicodeEncodeError。

任何需要打印中文或符号的 CLI，在入口处调用 ``force_utf8()`` 即可。
"""
from __future__ import annotations

import sys


def force_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
