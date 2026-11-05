#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把测量 JSON 导出为 DXF（R12 ASCII）—— 给会 CAD 的人打开/编辑的底图。

不含标注尺寸（DXF 标注实体复杂），只画：墙体轮廓、门窗洞、柜/桌/固定件/新家具矩形、文字标签。
用法:
    python scripts/renovation/to_dxf.py --data <json> [--out xxx.dxf]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.console import force_utf8  # noqa: E402

force_utf8()

WALL_T = 120


def _line(x1, y1, x2, y2, layer="WALL"):
    return ("0\nLINE\n8\n%s\n10\n%.1f\n20\n%.1f\n11\n%.1f\n21\n%.1f\n" % (layer, x1, y1, x2, y2))


def _rect(x, y, w, d, layer):
    return (_line(x, y, x + w, y, layer) + _line(x + w, y, x + w, y + d, layer)
            + _line(x + w, y + d, x, y + d, layer) + _line(x, y + d, x, y, layer))


def _text(x, y, h, s, layer="TEXT"):
    s = str(s).replace("\n", " ")
    return ("0\nTEXT\n8\n%s\n10\n%.1f\n20\n%.1f\n40\n%.1f\n1\n%s\n" % (layer, x, y, h, s))


def build_dxf(data: dict) -> str:
    out = ["0\nSECTION\n2\nENTITIES\n"]
    for room in data["rooms"]:
        W, D = room["inner"]["w"], room["inner"]["d"]
        t = WALL_T
        # 墙：内外两圈，中间填充墙厚
        out.append(_rect(-t, -t, W + 2 * t, D + 2 * t, "WALL"))
        out.append(_rect(0, 0, W, D, "ROOM"))
        # 门窗（洞口用两条短线表示）
        for op in room.get("openings", []):
            wall, off, wid = op.get("wall"), op.get("offset", 0), op.get("width", 0)
            if wall in ("north", "south"):
                y = -t if wall == "north" else D
                out.append(_line(off, y, off, y + t, "OPEN"))
                out.append(_line(off + wid, y, off + wid, y + t, "OPEN"))
                out.append(_text(off + wid / 2, y - 150, 120, "M" if op.get("type") == "door" else "C"))
            else:
                x = -t if wall == "west" else W
                out.append(_line(x, off, x + t, off, "OPEN"))
                out.append(_line(x, off + wid, x + t, off + wid, "OPEN"))
                out.append(_text(x, off + wid / 2, 120, "M" if op.get("type") == "door" else "C"))
        # 物件
        for key, layer in (("cabinets", "CABINET"), ("tables", "TABLE"),
                           ("fixed", "FIXED"), ("proposed", "NEW")):
            for it in room.get(key, []):
                d = it.get("depth", it.get("d", 0))
                out.append(_rect(it["x"], it["y"], it["w"], d, layer))
                out.append(_text(it["x"] + 60, it["y"] + d / 2, 110, it.get("name", "")))
        # 房间名 + 面积
        out.append(_text(0, D + 200, 180, f'{room["name"]} {int(W)}x{int(D)}'))
    out.append("0\nENDSEC\n0\nEOF\n")
    return "".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="测量 JSON → DXF 底图（R12）")
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    p = Path(args.data)
    data = json.loads(p.read_text(encoding="utf-8-sig"))
    out = Path(args.out) if args.out else (
        ROOT / "output" / "renovation" / f"底图_{p.stem}_{dt.date.today():%Y%m%d}.dxf")
    out.write_text(build_dxf(data), encoding="utf-8")
    print(f"✓ {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
