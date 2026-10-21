# -*- coding: utf-8 -*-
"""生成「前进吧zzz」高颜值图标（预览 PNG + 多尺寸 ICO）。

用法：
    python scripts/focus/make_icon.py
"""

import math
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ICO_PATH = os.path.join(HERE, "focus.ico")
PNG_PATH = os.path.join(HERE, "focus_preview.png")

S = 1024  # 高分辨率绘制，最后缩放抗锯齿

RED = (255, 97, 85, 255)         # 亮番茄红
RED_DARK = (214, 60, 50, 255)    # 底部暗部
RED_DEEPER = (196, 48, 40, 255)  # 描边
GREEN = (63, 191, 143, 255)      # 叶
GREEN_DARK = (46, 158, 107, 255)  # 茎
DARK = (58, 38, 32, 255)         # 五官
BLUSH = (255, 170, 170, 200)     # 腮红
GOLD = (255, 209, 102, 255)      # 金色
GOLD_DARK = (168, 120, 30, 255)  # 金色描边
WHITE = (255, 255, 255, 255)


def _star(d, cx, cy, r, color):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.52
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    d.polygon(pts, fill=color)


def _sparkle(d, cx, cy, r, color):
    pts = [(cx, cy - r), (cx + r * 0.2, cy - r * 0.2), (cx + r, cy),
           (cx + r * 0.2, cy + r * 0.2), (cx, cy + r),
           (cx - r * 0.2, cy + r * 0.2), (cx - r, cy),
           (cx - r * 0.2, cy - r * 0.2)]
    d.polygon(pts, fill=color)


def _bolt(d, ox, oy, s):
    pts = [(50, 0), (18, 78), (42, 78), (24, 150),
           (78, 52), (50, 52), (68, 0)]
    poly = [(ox + int(x * s), oy + int(y * s)) for x, y in pts]
    d.polygon(poly, fill=GOLD, outline=GOLD_DARK)


def draw_icon():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # ---- 番茄身体（带明暗与高光的球体） ----
    body = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bd = ImageDraw.Draw(body)
    cx, cy, rx, ry = 512, 600, 360, 335
    bbox = (cx - rx, cy - ry, cx + rx, cy + ry)
    bd.ellipse(bbox, fill=RED)

    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse(bbox, fill=255)

    shade = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    sd.ellipse((cx - rx, cy + ry * 0.35, cx + rx, cy + ry + 30), fill=RED_DARK)          # 底部暗部
    sd.ellipse((cx - rx * 0.75, cy - ry * 0.85, cx + rx * 0.15, cy - ry * 0.15),
               fill=(255, 255, 255, 110))                                                # 柔光
    sd.ellipse((cx - rx * 0.55, cy - ry * 0.7, cx - rx * 0.05, cy - ry * 0.35),
               fill=(255, 255, 255, 170))                                                # 亮高光
    body.paste(shade, (0, 0), mask)

    ImageDraw.Draw(body).ellipse(bbox, outline=RED_DEEPER, width=10)  # 描边
    img.alpha_composite(body)

    d = ImageDraw.Draw(img)

    # ---- 顶部叶（花萼）与茎 ----
    _star(d, cx, cy - ry + 30, 150, GREEN)
    _star(d, cx, cy - ry + 30, 100, GREEN_DARK)
    d.rounded_rectangle((cx - 16, cy - ry - 55, cx + 16, cy - ry + 70),
                        radius=16, fill=GREEN_DARK)

    # ---- 脸：坚定又可爱 ----
    for ex in (378, 646):
        d.ellipse((ex - 40, 535, ex + 40, 615), fill=DARK)      # 眼睛
        d.ellipse((ex - 15, 552, ex + 9, 576), fill=WHITE)       # 眼神光
    d.line((336, 495, 420, 516), fill=DARK, width=18)            # 眉（内倾，坚定）
    d.line((688, 495, 604, 516), fill=DARK, width=18)
    d.ellipse((296, 632, 410, 692), fill=BLUSH)                  # 腮红
    d.ellipse((614, 632, 728, 692), fill=BLUSH)
    d.arc((452, 618, 572, 722), start=20, end=160, fill=DARK, width=22)  # 自信微笑

    # ---- 金色闪电徽章（干劲/前进） ----
    _bolt(d, 700, 730, 1.6)

    # ---- 点缀小星星 ----
    _sparkle(d, 150, 290, 44, GOLD)
    _sparkle(d, 880, 200, 32, WHITE)
    _sparkle(d, 175, 760, 28, WHITE)
    _sparkle(d, 660, 130, 22, GOLD)

    return img


def main():
    img = draw_icon()
    img.resize((512, 512), Image.LANCZOS).save(PNG_PATH)
    img.resize((256, 256), Image.LANCZOS).save(
        ICO_PATH, format="ICO", sizes=[(256, 256), (64, 64), (48, 48), (32, 32), (16, 16)])
    print("✅ 图标已生成:", ICO_PATH)
    print("✅ 预览图:", PNG_PATH)


if __name__ == "__main__":
    main()
