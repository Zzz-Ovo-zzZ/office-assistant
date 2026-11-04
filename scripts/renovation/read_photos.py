#!/usr/bin/env python3
"""用视觉模型（默认 qwen3.8-max）逐张读房间现场照，输出结构化现状。

为什么需要它：贴墙衣柜、飘窗、灰蓝/杏米这类低饱和配色，通用读图容易糊成一片；
逐张 + 明确提问 + 允许「看不清」的回答，比一次性丢 6 张图可靠得多。

用法::

    python scripts/renovation/read_photos.py --dir output/renovation/照片/主卧
    python scripts/renovation/read_photos.py --dir ... --limit 1        # 只读第一张试水
    python scripts/renovation/read_photos.py --dir ... --model Qwen/Qwen3-VL-32B-Instruct
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

PROMPT = """这是一间主卧的第 {idx} 张现场照（拍摄位置：{label}）。请只报告你能确定的：

1. 【这一张能看到什么】一句话概括取景方向与可见墙面。
2. 【桌/台】画面上出现的每一件桌子、台面、柜子：位置（左/中/右）+ 主色（尽量具体：灰蓝/杏米/米白/纯白/原木/深灰/黑）+ 有无抽屉 + 桌腿还是柜体落地 + 台面颜色与柜体颜色是否不同。
3. 【飘窗】这一张是否出现飘窗？台面颜色、向室内凸出多深（目测）、下方是否有柜体。
4. 【窗】窗框颜色、几扇、窗台离地大约多高。
5. 【衣柜】是否出现？门板颜色、把手样式、是否通顶。
6. 【门】是否出现？门/门套颜色。
7. 【墙/地/踢脚线】各自颜色材质。
8. 【其他家具】凳子、椅子、床、其他杂物，逐件说颜色和位置。

看不清就写「看不清」，不确定就写「不确定」。用简体中文，列点。"""


def main() -> int:
    ap = argparse.ArgumentParser(description="逐张读房间照片，输出结构化现状")
    ap.add_argument("--dir", default=str(ROOT / "output" / "renovation" / "照片" / "主卧"),
                    help="照片目录（默认主卧）")
    ap.add_argument("--out", default=None, help="输出 Markdown（默认放到该目录上一级的 现状_照片解读_AI.md）")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"视觉模型（默认 {DEFAULT_MODEL}）")
    ap.add_argument("--limit", type=int, default=0, help="只读前 N 张（0=全部）")
    ap.add_argument("--labels", default="", help="自定义标签，形如 01_进门.jpg=站在门口;02_x.jpg=朝床头")
    args = ap.parse_args()

    photo_dir = Path(args.dir)
    if not photo_dir.exists():
        print(f"找不到照片目录：{photo_dir}")
        return 1
    files = sorted([p for p in photo_dir.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")])
    if args.limit:
        files = files[: args.limit]
    if not files:
        print(f"{photo_dir} 里没有 jpg/png")
        return 1

    labels = {}
    for pair in filter(None, args.labels.split(";")):
        if "=" in pair:
            k, v = pair.split("=", 1)
            labels[k.strip()] = v.strip()

    out_path = Path(args.out) if args.out else photo_dir.parent / "现状_照片解读_AI.md"
    parts = [f"# 照片解读 · {args.model} · {photo_dir.name}\n"]
    for i, f in enumerate(files, 1):
        label = labels.get(f.name, f.stem)
        print(f"[{i}/{len(files)}] {f.name} ...", flush=True)
        try:
            text = chat(args.model, PROMPT.format(idx=i, label=label), [f])
        except SystemExit as exc:
            text = f"[失败] {exc}"
        print(text[:160].replace("\n", " ") + " ...\n")
        parts.append(f"\n## {f.name}（{label}）\n\n{text}\n")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")
    print(f"✓ 已写入 {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
