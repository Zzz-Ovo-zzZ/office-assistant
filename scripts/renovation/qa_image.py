#!/usr/bin/env python3
"""用视觉模型自检生成的图（平面图 / 效果图），把「我看不见」变成「可验证」。

两种检查模式：
- ``plan``   平面图：轮廓是否闭合、标注有没有被墙压住、家具位置对不对、比例是否自洽
- ``render`` 效果图：结构（飘窗/衣柜/门窗/地板）有没有被改坏、软装是否符合要求、AI 破绽

用法::

    python scripts/renovation/qa_image.py --kind plan   --image output/renovation/平面布局_主卧_20261104_v4.png
    python scripts/renovation/qa_image.py --kind render --image output/renovation/效果图/A_米杏原木/主卧_A方案_全景_01.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.console import force_utf8  # noqa: E402
from scripts.renovation.vlm import DEFAULT_MODEL, chat  # noqa: E402

force_utf8()

PROMPTS = {
    "plan": """这是一张程序自动生成的室内平面图。请检查可读性与正确性：

1. 房间轮廓是否闭合、四面有墙？墙上开口（门窗）是否合理？
2. 逐字读出图上所有文字标注（含尺寸、标题、图例）。
3. 每个图形块在房间里的位置对不对（床、柜、桌、飘窗、门、厕所等）？
4. 有没有明显问题：文字重叠/被墙压住/被裁切、图形跑出画布、大面积空白、比例失真？
5. 给可用性打分（1–10）并说明扣分点。

只看画面上真实存在的，看不清就说看不清。简体中文。""",
    "render": """这是一张「改造后」的卧室效果图。请对照设计要求逐条检查：

1. 结构是否保留：飘窗、通顶衣柜、书桌、门、地板——哪些还在、哪些被删掉或变形？
2. 墙面是什么颜色？是否偏暖米杏（奶茶色）？
3. 有没有双人床？床头什么材质？床品/抱枕/床尾毯什么颜色？
4. 有没有窗帘？什么颜色质地？
5. 有没有床头灯、地毯、飘窗台软装？
6. 有没有明显 AI 破绽：家具变形、物体融合、比例失真、涂抹感、奇怪反射？
7. 整体观感打分（1–10）并说一句最需要改的地方。

只说看到的，列点，简体中文。""",
}


def main() -> int:
    ap = argparse.ArgumentParser(description="用视觉模型自检平面图/效果图")
    ap.add_argument("--image", required=True, help="要检查的图片")
    ap.add_argument("--kind", default="plan", choices=sorted(PROMPTS), help="plan=平面图, render=效果图")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"视觉模型（默认 {DEFAULT_MODEL}）")
    ap.add_argument("--out", default=None, help="可选：把结论写入 Markdown")
    args = ap.parse_args()

    img = Path(args.image)
    if not img.exists():
        print(f"图片不存在：{img}")
        return 1

    text = chat(args.model, PROMPTS[args.kind], [img], max_tokens=2000)
    print(text)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(f"# 质检：{img.name}\n\n{text}\n", encoding="utf-8")
        print(f"\n✓ 已写入 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
