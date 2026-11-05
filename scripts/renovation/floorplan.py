#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""婚房翻新 · 平面布局图生成 / 动线自检 / 尺寸总表

纯标准库，数据驱动：所有尺寸来自 measurements JSON，图面不手写任何数字。

用法:
    python scripts/renovation/floorplan.py draw  --data <json> [--out DIR] [--layer all|lighting]
    python scripts/renovation/floorplan.py check --data <json>
    python scripts/renovation/floorplan.py table --data <json> --out <md>
    python scripts/renovation/floorplan.py selftest

坐标约定: 单位 mm；每间房以内墙西北角为原点，x 向东、y 向南。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.console import force_utf8  # noqa: E402

force_utf8()

DEFAULT_OUT = ROOT / "output" / "renovation"

# ── 视觉参数（模型单位 = mm）────────────────────────────────
WALL_T = 120          # 墙厚
MARGIN = 900          # 图面留白（模型单位），容纳尺寸线与图例
FONT = "Microsoft YaHei, PingFang SC, Source Han Sans SC, sans-serif"

CABINET_FILL = {
    "暖白": "#F1ECE3", "米杏": "#E8DCC8", "奶白": "#F5F1E8",
    "原木": "#D8BE96", "木色": "#D8BE96", "胡桃": "#8A6A4A", "深色": "#6E6257",
    "灰": "#B9B9B4", "灰色": "#B9B9B4", "白": "#FAFAF7", "黑": "#3A3A38",
}
TABLE_FILL = "#D9E2EA"
NEW_FILL = "#EDF1F4"
FIXED_FILL = "#CFCFCB"


# ══════════════════════════════════════════════════════════
# 数据与几何
# ══════════════════════════════════════════════════════════

def load_data(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"找不到数据文件：{p}")
    data = json.loads(p.read_text(encoding="utf-8-sig"))
    if data.get("unit") != "mm":
        raise SystemExit('数据里 "unit" 必须是 "mm"（毫米），当前为：' + str(data.get("unit")))
    if not data.get("rooms"):
        raise SystemExit("数据里没有 rooms，至少需要一间房。")
    for r in data["rooms"]:
        for key in ("id", "name", "inner"):
            if key not in r:
                raise SystemExit(f"房间缺少字段 {key}：{r}")
        for key in ("w", "d"):
            if not isinstance(r["inner"].get(key), (int, float)):
                raise SystemExit(f"房间 {r['name']} 的 inner.{key} 必须是数字")
    return data


def items_of(room: dict) -> list[dict]:
    """把四类物件合并成一个列表，统一带 kind 标记，并把 d/depth 归一为 depth。"""
    out = []

    def norm(o: dict) -> dict:
        o = dict(o)
        o["depth"] = o.get("depth", o.get("d", 0))
        return o

    for c in room.get("cabinets", []):
        o = norm(c)
        o.update(kind="cabinet", role=c.get("role", "wardrobe" if "衣柜" in c.get("name", "") else "cabinet"))
        out.append(o)
    for t in room.get("tables", []):
        o = norm(t)
        o.update(kind="table", role=t.get("role", "desk"))
        out.append(o)
    for f in room.get("fixed", []):
        o = norm(f)
        o.update(kind="fixed", role="fixed")
        out.append(o)
    for p in room.get("proposed", []):
        o = norm(p)
        o.update(kind="proposed", role=p.get("role", "other"))
        out.append(o)
    return out


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return min(a1, b1) - max(a0, b0)


def clearance(room: dict, item: dict, side: str, items: list[dict] | None = None) -> float:
    """item 某一侧到最近障碍/墙的距离（mm）。side: N/E/S/W（图面方向）。"""
    W, D = room["inner"]["w"], room["inner"]["d"]
    items = items if items is not None else items_of(room)
    x, y, w, d = item["x"], item["y"], item["w"], item.get("depth", 0)

    def others():
        for o in items:
            if o is item:
                continue
            if o.get("ignore_clearance"):   # 床头柜等贴身小件不参与净空计算
                continue
            if o.get("x") == x and o.get("y") == y and o.get("name") == item.get("name") and o.get("kind") == item.get("kind"):
                continue
            yield o

    if side == "E":
        best = W - (x + w)
        for o in others():
            if o["x"] >= x + w - 1 and _overlap(y, y + d, o["y"], o["y"] + o.get("depth", 0)) > 1:
                best = min(best, o["x"] - (x + w))
    elif side == "W":
        best = x
        for o in others():
            if o["x"] + o["w"] <= x + 1 and _overlap(y, y + d, o["y"], o["y"] + o.get("depth", 0)) > 1:
                best = min(best, x - (o["x"] + o["w"]))
    elif side == "N":
        best = y
        for o in others():
            od = o.get("depth", 0)
            if o["y"] + od <= y + 1 and _overlap(x, x + w, o["x"], o["x"] + o["w"]) > 1:
                best = min(best, y - (o["y"] + od))
    else:  # S
        best = D - (y + d)
        for o in others():
            if o["y"] >= y + d - 1 and _overlap(x, x + w, o["x"], o["x"] + o["w"]) > 1:
                best = min(best, o["y"] - (y + d))
    return round(best)


def check_room(room: dict) -> list[dict]:
    """按空间规则检查一间房，返回问题列表。level: hard / soft。"""
    problems = []
    items = items_of(room)
    for it in items:
        if it.get("kind") == "fixed":
            continue
        name = it.get("name", "未命名")
        role = it.get("role", "other")
        sides = {s: clearance(room, it, s, items) for s in "NESW"}
        best = max(sides.values())

        def add(side, need, level, msg):
            problems.append({"room": room["name"], "item": name, "side": side,
                             "gap": sides[side], "need": need, "level": level, "msg": msg})

        if role == "wardrobe":          # 衣柜前净空 ≥750
            if best < 450:
                add(max(sides, key=sides.get), 750, "hard", "衣柜前操作空间不足 450mm")
            elif best < 750:
                add(max(sides, key=sides.get), 750, "soft", "衣柜前建议 ≥750mm")
        elif role == "desk":           # 桌后活动区 ≥900
            if best < 600:
                add(max(sides, key=sides.get), 900, "hard", "书桌活动区不足 600mm")
            elif best < 900:
                add(max(sides, key=sides.get), 900, "soft", "书桌活动区建议 ≥900mm")
        elif role == "dining":         # 餐椅后退 ≥900（极限 750）
            if best < 750:
                add(max(sides, key=sides.get), 900, "hard", "餐椅后退不足 750mm")
            elif best < 900:
                add(max(sides, key=sides.get), 900, "soft", "餐椅后退建议 ≥900mm")
        elif role == "bed":            # 双人床：至少一侧可通行；两侧都窄才算硬伤
            w, d = it.get("w", 0), it.get("depth", 0)
            lateral = ("E", "W") if d >= w else ("N", "S")
            lat = [sides[s] for s in lateral]
            if max(lat) < 450:
                add(lateral[lat.index(max(lat))], 600, "hard", "床两侧通行均不足 450mm")
            elif max(lat) < 600:
                add(lateral[lat.index(max(lat))], 600, "soft", "床侧建议 ≥600mm（贴墙可 500）")
            elif min(lat) < 300:
                add(lateral[lat.index(min(lat))], 500, "soft", "床一侧贴墙/过窄，另一侧需 ≥600mm")
    return problems


def room_free_gap(room: dict) -> int:
    """房间内所有物件的最小侧向净空，用于总览。"""
    items = items_of(room)
    gaps = [min(clearance(room, it, s, items) for s in "NESW") for it in items if it.get("kind") != "fixed"]
    return min(gaps) if gaps else 0


# ══════════════════════════════════════════════════════════
# SVG 绘制
# ══════════════════════════════════════════════════════════

def pick_scale(w: float, d: float) -> int:
    """按 A3 横向可绘制区域挑选比例分母（1:N），优先更大比例。"""
    area_w, area_h = 380.0, 250.0
    for s in (20, 25, 30, 40, 50, 60, 75, 100):
        if (w + 2 * MARGIN) / s <= area_w and (d + 2 * MARGIN) / s <= area_h:
            return s
    return 100


def _dim_h(x1: float, x2: float, y: float, text: str, s: int, color: str = "#444") -> str:
    f = 2.8 * s
    return (
        f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{color}" stroke-width="{s*0.2}"/>'
        f'<line x1="{x1}" y1="{y-s*1.8}" x2="{x1}" y2="{y+s*1.8}" stroke="{color}" stroke-width="{s*0.2}"/>'
        f'<line x1="{x2}" y1="{y-s*1.8}" x2="{x2}" y2="{y+s*1.8}" stroke="{color}" stroke-width="{s*0.2}"/>'
        f'<text x="{(x1+x2)/2}" y="{y - s*1.2}" font-size="{f}" text-anchor="middle" fill="{color}" font-family="{FONT}">{text}</text>'
    )


def _dim_v(y1: float, y2: float, x: float, text: str, s: int, color: str = "#444") -> str:
    f = 2.8 * s
    cx = x - s * 1.2
    cy = (y1 + y2) / 2
    return (
        f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke="{color}" stroke-width="{s*0.2}"/>'
        f'<line x1="{x-s*1.8}" y1="{y1}" x2="{x+s*1.8}" y2="{y1}" stroke="{color}" stroke-width="{s*0.2}"/>'
        f'<line x1="{x-s*1.8}" y1="{y2}" x2="{x+s*1.8}" y2="{y2}" stroke="{color}" stroke-width="{s*0.2}"/>'
        f'<text x="{cx}" y="{cy}" font-size="{f}" text-anchor="middle" fill="{color}" font-family="{FONT}" transform="rotate(-90 {cx} {cy})">{text}</text>'
    )


def draw_room(room: dict, s: int, layer: str = "plan") -> str:
    W, D = room["inner"]["w"], room["inner"]["d"]
    M = MARGIN
    # 纸张尺寸按 A3 横向 420×297mm；图面用「模型 mm」绘制，外层 g 统一缩放到 1:s 并按内容包围盒居中
    L, R = -M * 0.62, W + M * 0.62
    T, B = -M * 0.62, D + M * 1.05
    cw, ch = (R - L) / s, (B - T) / s
    tx = (420 - cw) / 2 - L / s
    ty = (297 - ch) / 2 - T / s
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 420 297">',
           '<rect x="0" y="0" width="420" height="297" fill="#FFFFFF"/>',
           f'<g transform="translate({tx:.2f} {ty:.2f}) scale({1/s:.6f})">']

    # 墙体
    t = WALL_T
    out.append(f'<rect x="{-t}" y="{-t}" width="{W+2*t}" height="{D+2*t}" fill="#4A4A48"/>')
    out.append(f'<rect x="0" y="0" width="{W}" height="{D}" fill="#FBFAF6"/>')

    # 门窗：先挖白，再画符号
    for op in room.get("openings", []):
        wall = op.get("wall", "north")
        off, width = op.get("offset", 0), op.get("width", 900)
        if wall in ("south", "north"):
            y0 = D if wall == "south" else -t
            out.append(f'<rect x="{off}" y="{y0}" width="{width}" height="{t}" fill="#FBFAF6"/>')
            if op.get("type") == "window":
                for k in (0.2, 0.5, 0.8):
                    out.append(f'<line x1="{off}" y1="{y0 + t*k}" x2="{off+width}" y2="{y0 + t*k}" stroke="#5B7C99" stroke-width="{s*0.18}"/>')
            else:
                hinge = off if op.get("swing", "in-left").endswith("left") else off + width
                out.append(f'<path d="M {hinge} {y0} A {width} {width} 0 0 {1 if wall=="south" else 0} {hinge + (width if hinge==off else -width)} {y0}" fill="none" stroke="#8A8A85" stroke-width="{s*0.2}" stroke-dasharray="{s*25},{s*20}"/>')
        else:
            x0 = -t if wall == "west" else W
            out.append(f'<rect x="{x0}" y="{off}" width="{t}" height="{width}" fill="#FBFAF6"/>')
            if op.get("type") == "window":
                for k in (0.2, 0.5, 0.8):
                    out.append(f'<line x1="{x0 + t*k}" y1="{off}" x2="{x0 + t*k}" y2="{off+width}" stroke="#5B7C99" stroke-width="{s*0.18}"/>')
            else:
                hinge = off if op.get("swing", "in-left").endswith("left") else off + width
                out.append(f'<path d="M {x0} {hinge} A {width} {width} 0 0 {1 if wall=="east" else 0} {x0} {hinge + (width if hinge==off else -width)}" fill="none" stroke="#8A8A85" stroke-width="{s*0.2}" stroke-dasharray="{s*25},{s*20}"/>')

    # 物件
    for it in items_of(room):
        x, y, w = it["x"], it["y"], it["w"]
        d = it.get("depth", it.get("d", 0))
        kind = it["kind"]
        if kind == "cabinet":
            fill = CABINET_FILL.get(str(it.get("color", "")), "#E6E1D8")
            stroke, dash = "#6B6257", ""
        elif kind == "table":
            fill, stroke, dash = TABLE_FILL, "#4F6D85", ""
        elif kind == "proposed":
            fill, stroke, dash = NEW_FILL, "#7E93A8", f'stroke-dasharray="{s*12},{s*7}"'
        else:
            fill, stroke, dash = FIXED_FILL, "#8A8A85", ""
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{d}" fill="{fill}" stroke="{stroke}" '
                   f'stroke-width="{s*0.3}" {dash}/>')

        label = it.get("name", "")
        dims = f'{int(w)}×{int(d)}'
        if it.get("h"):
            dims += f'×{int(it["h"])}'
        if kind == "proposed":
            label = "+" + label
        fs1, fs2 = 2.9 * s, 2.5 * s
        text = f'{label} {dims}'
        if w / s > 22 and d / s > 10:
            out.append(f'<text x="{x + w/2}" y="{y + d/2 - s*0.4}" font-size="{fs1}" text-anchor="middle" '
                       f'fill="#2F2F2C" font-family="{FONT}" font-weight="600">{label}</text>')
            out.append(f'<text x="{x + w/2}" y="{y + d/2 + s*3.4}" font-size="{fs2}" text-anchor="middle" '
                       f'fill="#4A4A46" font-family="{FONT}">{dims}</text>')
        elif w / s <= 22 and d / s <= 16:
            # 小件（床头柜/边几）：只写名称，尺寸看尺寸总表，避免竖向文字压墙
            out.append(f'<text x="{x + w + s*1.2}" y="{y + d/2 + s*0.7}" font-size="{2.1*s}" '
                       f'fill="#4A4A46" font-family="{FONT}">{label}</text>')
        elif w / s <= 22 and d / s > 10:
            # 窄而高（如贴墙衣柜）：文字竖排放在块内，避免被墙线压住
            cx, cy = x + w / 2, y + d / 2
            out.append(f'<text x="{cx}" y="{cy}" font-size="{fs2:.2f}" text-anchor="middle" '
                       f'fill="#2F2F2C" font-family="{FONT}" transform="rotate(-90 {cx} {cy})">{text}</text>')
        elif x + w + s * 2 + len(text) * fs2 * 0.95 > W:
            # 右侧放不下：翻到左侧右对齐
            out.append(f'<text x="{x - s*2}" y="{y + d/2}" font-size="{fs2}" text-anchor="end" '
                       f'fill="#4A4A46" font-family="{FONT}">{text}</text>')
        else:
            out.append(f'<text x="{x + w + s*2}" y="{y + d/2}" font-size="{fs2}" fill="#4A4A46" font-family="{FONT}">{text}</text>')

    # 尺寸线
    out.append(_dim_h(0, W, -MARGIN * 0.55, f"{int(W)}", s))
    out.append(_dim_h(0, W, D + MARGIN * 0.55, f"{int(W)}", s))
    out.append(_dim_v(0, D, -MARGIN * 0.55, f"{int(D)}", s))
    out.append(_dim_v(0, D, W + MARGIN * 0.55, f"{int(D)}", s))

    # 灯光层（仅 --layer lighting 时绘制，单独出「灯光点位图」）
    if layer == "lighting":
        for lt in room.get("lighting", []):
            lx, ly = lt.get("x", W / 2), lt.get("y", D / 2)
            r = s * 1.0
            out.append(f'<circle cx="{lx}" cy="{ly}" r="{r}" fill="#FFF" stroke="#C98A2E" stroke-width="{s*0.18}"/>')
            out.append(f'<line x1="{lx-r}" y1="{ly}" x2="{lx+r}" y2="{ly}" stroke="#C98A2E" stroke-width="{s*0.14}"/>')
            out.append(f'<line x1="{lx}" y1="{ly-r}" x2="{lx}" y2="{ly+r}" stroke="#C98A2E" stroke-width="{s*0.14}"/>')
            out.append(f'<text x="{lx + r*1.1}" y="{ly + r + s*2.4}" font-size="{2.1*s}" fill="#8A5A12" '
                       f'font-family="{FONT}" style="paint-order:stroke" stroke="#FFFFFF" stroke-width="{s*0.8}">{lt.get("label","灯")}</text>')

    # 指北针 + 标题
    nx, ny = W + M * 0.55, -M * 0.62
    out.append(f'<path d="M {nx} {ny} l {-s*3} {s*7} l {s*3} {-s*2.2} l {s*3} {s*2.2} z" fill="#3A3A38"/>')
    out.append(f'<text x="{nx}" y="{ny - s*1.5}" font-size="{2.4*s}" text-anchor="middle" fill="#3A3A38" font-family="{FONT}">N</text>')

    area = W * D / 1_000_000
    title = f'{room["name"]}　{int(W)}×{int(D)}mm　{area:.1f}㎡　1:{s}'
    out.append(f'<text x="0" y="{D + M*0.95}" font-size="{3.4*s}" fill="#2F2F2C" font-family="{FONT}" font-weight="700">{title}</text>')
    out.append(f'<text x="0" y="{D + M*0.75}" font-size="{2.2*s}" fill="#7A7A74" font-family="{FONT}">实线=现有柜/桌　虚线=新增家具　灰色=固定构件（柱/梁）</text>')
    out.append("</g></svg>")
    return "\n".join(out)


def build_html(svgs: list[tuple[str, str]], title: str) -> str:
    pages = []
    for name, svg in svgs:
        pages.append(f'<section class="page">{svg}<div class="cap">{name}</div></section>')
    return f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{title}</title>
<style>
  @page {{ size: A3 landscape; margin: 0; }}
  html,body {{ margin:0; padding:0; background:#fff; }}
  .page {{ width:420mm; height:297mm; page-break-after:always; overflow:hidden; }}
  .page:last-child {{ page-break-after:auto; }}
  svg {{ display:block; }}
  .cap {{ display:none; }}
</style></head><body>
{''.join(pages)}
</body></html>'''


def find_edge() -> str | None:
    cands = [shutil.which("msedge"),
             r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
             r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
    return next((c for c in cands if c and Path(c).exists()), None)


def export_html(html_path: Path, png_path: Path, pdf_path: Path, pages: int) -> None:
    edge = find_edge()
    if not edge:
        print("⚠ 未找到 Edge，跳过 PNG/PDF 导出（HTML 可直接用浏览器打印）")
        return
    from urllib.parse import quote

    html_path = html_path.resolve()
    png_path = png_path.resolve()
    pdf_path = pdf_path.resolve()
    url = "file:///" + quote(html_path.as_posix())
    profile_dir = Path(tempfile.mkdtemp(prefix="edge_headless_"))

    # 先删旧文件：Edge 在目标已存在时可能静默失败，留着旧文件会造成"看起来成功"
    for p in (pdf_path, png_path):
        p.unlink(missing_ok=True)

    def run(args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run([edge, "--headless=new", "--disable-gpu", "--no-first-run",
                               f"--user-data-dir={profile_dir}", *args],
                              capture_output=True, timeout=240)

    r = run(["--no-pdf-header-footer", f"--print-to-pdf={pdf_path}", url])
    if not pdf_path.exists():
        print(f"⚠ PDF 导出失败：{(r.stderr or b'').decode('utf-8', 'ignore')[:200]}")

    r = run(["--hide-scrollbars", "--window-size=1587,1123", "--force-device-scale-factor=2",
             f"--screenshot={png_path}", url])
    if not png_path.exists():
        print(f"⚠ PNG 导出失败：{(r.stderr or b'').decode('utf-8', 'ignore')[:200]}")

    shutil.rmtree(profile_dir, ignore_errors=True)
    for p in (pdf_path, png_path):
        print(f"{'✓' if p.exists() else '✗'} {p.name}")


# ══════════════════════════════════════════════════════════
# 尺寸总表
# ══════════════════════════════════════════════════════════

def build_table(data: dict) -> str:
    lines = [f'# 尺寸总表 · {data.get("project", "")}', "",
             f'> 生成于 {_dt.date.today()}｜单位 mm｜坐标原点=各房内墙西北角（x 向东、y 向南）', ""]
    for room in data["rooms"]:
        W, D = room["inner"]["w"], room["inner"]["d"]
        lines += [f'## {room["name"]}（{int(W)}×{int(D)}，{W*D/1e6:.1f}㎡，层高 {room["inner"].get("h","—")}）', "",
                  "| 物件 | 类型 | 宽×深×高 | 位置(x,y) | 距西墙 | 距北墙 | 说明 |",
                  "|------|------|----------|-----------|--------|--------|------|"]
        for it in items_of(room):
            kind = {"cabinet": "现有柜", "table": "现有桌", "fixed": "固定", "proposed": "新增"}[it["kind"]]
            d = it.get("depth", it.get("d", 0))
            note = []
            if it.get("h"):
                note.append(f'H{int(it["h"])}')
            if it.get("color"):
                note.append(str(it["color"]))
            if it.get("keep") == "optional":
                note.append("可保留/可调")
            if it.get("keep") is True:
                note.append("保留")
            lines.append(f'| {it.get("name","")} | {kind} | {int(it["w"])}×{int(d)}×{int(it.get("h",0))} | '
                         f'({int(it["x"])},{int(it["y"])}) | {int(it["x"])} | {int(it["y"])} | {"，".join(note)} |')
        lines.append("")
        lines.append(f'门窗：' + "；".join(
            f'{o.get("type")}·{o.get("wall")}·距角{int(o.get("offset",0))}·宽{int(o.get("width",0))}' for o in room.get("openings", [])))
        lines.append("")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════
# 命令
# ══════════════════════════════════════════════════════════

def cmd_draw(args) -> int:
    data = load_data(args.data)
    out_dir = Path(args.out or DEFAULT_OUT)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _dt.date.today().strftime("%Y%m%d")
    base = args.name or f'平面布局_婚房翻新_{stamp}_v1'
    if args.layer == "lighting" and not base.endswith("灯光"):
        base += "_灯光"

    svgs = []
    for room in data["rooms"]:
        s = pick_scale(room["inner"]["w"], room["inner"]["d"])
        svg = draw_room(room, s, layer=args.layer)
        svgs.append((room["name"], svg))
        (out_dir / f'{base}_{room["id"]}.svg').write_text(svg, encoding="utf-8")
        print(f'✓ {base}_{room["id"]}.svg  (1:{s})')

    html_path = out_dir / f"{base}.html"
    html_path.write_text(build_html(svgs, data.get("project", "平面布局")), encoding="utf-8")
    print(f"✓ {html_path.name}")

    export_html(html_path, out_dir / f"{base}.png", out_dir / f"{base}.pdf", len(svgs))

    if not args.no_table:
        table_path = out_dir / f"尺寸总表_{stamp}.md"
        table_path.write_text(build_table(data), encoding="utf-8")
        print(f"✓ {table_path.name}")

    problems = []
    for room in data["rooms"]:
        problems += check_room(room)
    hard = [p for p in problems if p["level"] == "hard"]
    if hard:
        print(f"\n⚠ 动线检查有 {len(hard)} 条硬违规，建议先跑 check 看详情")
    return 0


def cmd_check(args) -> int:
    data = load_data(args.data)
    problems = []
    for room in data["rooms"]:
        problems += check_room(room)
    if not problems:
        for room in data["rooms"]:
            print(f'✓ {room["name"]}：最小净空 {room_free_gap(room)}mm，无规则违规')
        return 0
    print(f'{"房间":<6}{"物件":<10}{"侧":<3}{"实测":>6}{"要求":>6}  说明')
    print("-" * 62)
    for p in sorted(problems, key=lambda x: x["level"] != "hard"):
        flag = "✗" if p["level"] == "hard" else "!"
        print(f'{flag} {p["room"]:<5}{p["item"]:<10}{p["side"]:<3}{p["gap"]:>6}{p["need"]:>6}  {p["msg"]}')
    hard = sum(1 for p in problems if p["level"] == "hard")
    print(f"\n硬违规 {hard} 条，建议 {len(problems)-hard} 条")
    return 1 if hard else 0


def cmd_table(args) -> int:
    data = load_data(args.data)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_table(data), encoding="utf-8")
    print(f"✓ {out}")
    return 0


def cmd_selftest(_args) -> int:
    sample = {
        "project": "自测样例", "unit": "mm",
        "rooms": [
            {"id": "master", "name": "主卧", "inner": {"w": 3600, "d": 4200, "h": 2800},
             "openings": [{"type": "door", "wall": "south", "offset": 300, "width": 900},
                          {"type": "window", "wall": "north", "offset": 600, "width": 1800}],
             "cabinets": [{"name": "衣柜", "x": 0, "y": 0, "w": 1800, "depth": 600, "h": 2400, "color": "暖白", "keep": True, "role": "wardrobe"}],
             "tables": [{"name": "书桌", "x": 2000, "y": 500, "w": 1200, "depth": 600, "h": 750, "keep": "optional", "role": "desk"}],
             "fixed": [{"name": "柱", "x": 3400, "y": 3600, "w": 200, "depth": 200}],
             "proposed": [{"name": "床1.8m", "x": 700, "y": 1800, "w": 1800, "depth": 2000, "h": 450, "role": "bed"}],
             "lighting": [{"type": "pendant", "x": 1800, "y": 2100, "label": "吸顶 3000K"}]},
            {"id": "dining", "name": "餐厅", "inner": {"w": 3000, "d": 3200, "h": 2800},
             "openings": [{"type": "window", "wall": "east", "offset": 600, "width": 1500}],
             "cabinets": [{"name": "餐边柜", "x": 0, "y": 0, "w": 1200, "depth": 400, "h": 900, "color": "原木", "role": "cabinet"}],
             "tables": [{"name": "餐桌", "x": 900, "y": 1200, "w": 1400, "depth": 800, "h": 750, "role": "dining"}],
             "proposed": []},
            {"id": "study", "name": "书房", "inner": {"w": 2700, "d": 3000, "h": 2800},
             "cabinets": [{"name": "书柜", "x": 0, "y": 0, "w": 1800, "depth": 350, "h": 2100, "color": "胡桃", "role": "cabinet"}],
             "tables": [{"name": "书桌", "x": 1800, "y": 400, "w": 900, "depth": 600, "h": 750, "role": "desk"}],
             "proposed": []},
        ],
    }
    tmp = Path(tempfile.mkdtemp(prefix="floorplan_selftest_"))
    data_path = tmp / "sample.json"
    data_path.write_text(json.dumps(sample, ensure_ascii=False), encoding="utf-8")

    data = load_data(data_path)
    ok = True
    for room in data["rooms"]:
        s = pick_scale(room["inner"]["w"], room["inner"]["d"])
        svg = draw_room(room, s)
        assert "<svg" in svg and "衣柜" in svg or room["id"] != "master", "SVG 生成异常"
        (tmp / f'{room["id"]}.svg').write_text(svg, encoding="utf-8")
    print("✓ SVG 生成")

    # 故意制造一处硬违规：加一间 1.5m 小房塞 1.4m 床，两侧只剩 50
    broken = json.loads(json.dumps(sample))
    broken["rooms"].append({
        "id": "tiny", "name": "测试小间", "inner": {"w": 1500, "d": 1500, "h": 2600},
        "proposed": [{"name": "超大床", "x": 50, "y": 50, "w": 1400, "depth": 1400, "role": "bed"}],
    })
    probs = []
    for room in broken["rooms"]:
        probs += check_room(room)
    hard = [p for p in probs if p["level"] == "hard"]
    if hard:
        print(f"✓ 检查器捕获硬违规 {len(hard)} 条（预期）")
    else:
        ok = False
        print("✗ 检查器未捕获故意设置的违规")

    probs_ok = []
    for room in sample["rooms"]:
        probs_ok += check_room(room)
    print(f"✓ 样例违规 {len(probs_ok)} 条（硬 {sum(1 for p in probs_ok if p['level']=='hard')}）")
    table = build_table(sample)
    assert "尺寸总表" in table and "衣柜" in table
    print("✓ 尺寸总表生成")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="婚房翻新 · 平面布局工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("draw", help="生成 SVG/HTML/PNG/PDF")
    d.add_argument("--data", required=True)
    d.add_argument("--out", default=None)
    d.add_argument("--name", default=None)
    d.add_argument("--layer", default="plan", choices=["plan", "lighting"])
    d.add_argument("--no-table", action="store_true")
    d.set_defaults(func=cmd_draw)

    c = sub.add_parser("check", help="动线/间隙自检")
    c.add_argument("--data", required=True)
    c.set_defaults(func=cmd_check)

    t = sub.add_parser("table", help="生成尺寸总表 Markdown")
    t.add_argument("--data", required=True)
    t.add_argument("--out", required=True)
    t.set_defaults(func=cmd_table)

    st = sub.add_parser("selftest", help="内置样例自测")
    st.set_defaults(func=cmd_selftest)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
