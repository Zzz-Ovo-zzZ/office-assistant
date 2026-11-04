#!/usr/bin/env python3
"""照片客观取色（不依赖任何视觉模型）。

用途：视觉模型对「灰蓝 / 杏米 / 米白」这类低饱和近似色容易糊，这里用像素统计给出
硬数据——3×3 分区均色、主色占比、亮度与色温偏移，交叉验证 AI 的读图结论。

用法::

    python scripts/renovation/photo_palette.py --dir output/renovation/照片/主卧
    python scripts/renovation/photo_palette.py --dir ... --out temp/palette.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.console import force_utf8  # noqa: E402

force_utf8()


def hexc(rgb) -> str:
    return "#{:02X}{:02X}{:02X}".format(*[int(round(v)) for v in rgb])


def grid_means(img: Image.Image, n: int = 3):
    w, h = img.size
    out = []
    for gy in range(n):
        row = []
        for gx in range(n):
            box = (int(w * gx / n), int(h * gy / n), int(w * (gx + 1) / n), int(h * (gy + 1) / n))
            row.append(hexc(img.crop(box).resize((1, 1), Image.LANCZOS).getpixel((0, 0))))
        out.append(row)
    return out


def palette(img: Image.Image, k: int = 8):
    small = img.resize((240, max(1, int(240 * img.size[1] / img.size[0]))), Image.LANCZOS)
    q = small.convert("RGB").quantize(colors=k, method=Image.MEDIANCUT)
    pal = q.getpalette()
    counts = sorted(q.getcolors(), reverse=True)
    total = sum(c for c, _ in counts)
    return [
        {"hex": hexc(pal[i * 3: i * 3 + 3]), "share": round(c / total * 100, 1)}
        for c, i in counts[:k]
    ]


def stats(img: Image.Image):
    small = img.resize((120, max(1, int(120 * img.size[1] / img.size[0]))), Image.LANCZOS).convert("RGB")
    r, g, b = ImageStat.Stat(small).mean
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return {
        "mean_rgb": [round(r), round(g), round(b)],
        "luma": round(lum, 1),
        "warmth_r_minus_b": round(r - b, 1),
    }


def analyze(path: Path) -> dict:
    with Image.open(path) as im:
        im = im.convert("RGB")
        return {
            "file": path.name,
            "size": f"{im.size[0]}x{im.size[1]}",
            "grid_3x3": grid_means(im),
            "palette": palette(im),
            "stats": stats(im),
        }


def main() -> int:
    ap = argparse.ArgumentParser(description="照片客观取色（3×3 分区 + 主色 + 色温）")
    ap.add_argument("--dir", default=str(ROOT / "output" / "renovation" / "照片" / "主卧"))
    ap.add_argument("--out", default=None, help="输出 JSON（默认只打印摘要）")
    args = ap.parse_args()

    d = Path(args.dir)
    if not d.exists():
        print(f"目录不存在：{d}")
        return 1
    files = sorted(p for p in d.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    if not files:
        print(f"{d} 里没有图片")
        return 1

    report = [analyze(f) for f in files]
    for it in report:
        s = it["stats"]
        print(f"=== {it['file']}  {it['size']}")
        for row in it["grid_3x3"]:
            print("    " + " ".join(row))
        print("    主色: " + " | ".join(f"{p['hex']} {p['share']}%" for p in it["palette"][:5]))
        print(f"    亮度 {s['luma']}  色温偏移(R-B) {s['warmth_r_minus_b']}")
        print()

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"✓ 已写入 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
