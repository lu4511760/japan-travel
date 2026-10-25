# -*- coding: utf-8 -*-
"""黑銀鮪屋：中文直接疊在菜單海報的品名／價格位置上。"""
import sys
from PIL import Image, ImageDraw, ImageFont

BASE = r"G:\My Drive\Riskval\claudeWorkspace\japanTravel"
SRC = BASE + r"\黑銀鮪屋 Menu.png"
OUT = BASE + r"\黑銀鮪屋 Menu ZH.png"
FONT = r"C:\Windows\Fonts\msjhbd.ttc"
SCALE = 3

# (x0, y0, x1, y1, [(文字, 顏色), ...])   k=黑 r=紅 b=藍
CELLS = [
    # ── 上排：套餐 ──
    (2, 112, 226, 154, [("No.1 極上 鮪魚三種握壽司", "k"), ("頰腹肉・大腹・中腹　¥4,600", "r")]),
    (228, 116, 502, 162, [("No.2 本鮪 黑銀壽司組", "k"), ("大腹・中腹・赤身　¥4,100", "r")]),
    # ── 右上：刺身（不配飯）──
    (628, 6, 1069, 40, [("刺身　不配飯", "k")]),
    (626, 106, 834, 184, [("頂・四種刺身拼盤", "k"), ("頰腹肉（カマトロ）", "k"),
                          ("大腹（大トロ）・中腹（中トロ）", "k"), ("赤身　　¥8,000", "r")]),
    (836, 34, 1069, 96, [("頰腹肉刺身", "k"), ("カマトロ・限定品", "k"), ("¥5,000", "r")]),
    (636, 262, 834, 356, [("鮪魚三種刺身拼盤", "k"), ("頰腹肉（カマトロ）", "k"),
                          ("大腹（大トロ）", "k"), ("中腹（中トロ）　¥7,500", "r")]),
    (836, 224, 1016, 274, [("中腹刺身拼盤", "k"), ("中トロ　¥4,500", "r")]),
    # ── 左下：單品握壽司（2 貫）──
    (52, 476, 242, 522, [("頰腹肉握壽司", "k"), ("カマトロ　¥2,000", "r")]),
    (272, 476, 448, 522, [("大腹握壽司", "k"), ("大トロ　¥1,800", "r")]),
    (84, 560, 242, 606, [("中腹握壽司", "k"), ("中トロ　¥1,400", "r")]),
    (292, 560, 438, 606, [("赤身握壽司", "k"), ("赤身　¥1,000", "r")]),
    (26, 606, 142, 652, [("本鮪 頰腹肉", "k"), ("4 貫組", "k")]),
    (148, 606, 256, 652, [("本鮪 大腹", "k"), ("4 貫組", "k")]),
    (264, 612, 506, 748, [("可自由搭配組合！", "r"), ("不接受單貫（1 貫）點餐", "r")]),
    # ── 右下：丼飯 ──
    (528, 420, 1069, 452, [("丼飯　白飯鋪上鮪魚刺身", "k")]),
    (545, 664, 757, 724, [("頂・黑銀丼　¥8,500", "r"),
                          ("頰腹・大腹・中腹・赤身・蔥花鮪魚泥", "k")]),
    (788, 664, 1002, 724, [("鮪魚三種丼　¥5,600", "r"),
                          ("頰腹・大腹・中腹・蔥花鮪魚泥", "k")]),
    (528, 728, 1060, 750, [("白飯大碗 ＋100円", "k")]),
]

COLORS = {"k": (20, 18, 15), "r": (170, 28, 28), "b": (30, 60, 150)}


def main():
    preview = "--preview" in sys.argv
    im = Image.open(SRC).convert("RGB")
    im = im.resize((im.width * SCALE, im.height * SCALE), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    for x0, y0, x1, y1, lines in CELLS:
        X0, Y0, X1, Y1 = x0 * SCALE, y0 * SCALE, x1 * SCALE, y1 * SCALE
        if preview:
            d.rectangle([X0, Y0, X1, Y1], outline=(255, 0, 0), width=3)
            continue
        d.rectangle([X0, Y0, X1, Y1], fill=(252, 250, 245))
        d.rectangle([X0, Y0, X1, Y1], outline=(120, 110, 95), width=2)
        w, h = X1 - X0, Y1 - Y0
        n = len(lines)
        pad = h * 0.06
        slot = (h - pad * 2) / n
        for i, (text, ck) in enumerate(lines):
            size = max(8, int(slot * 0.80))
            while size > 8:
                f = ImageFont.truetype(FONT, size)
                l, t, r, b = d.textbbox((0, 0), text, font=f)
                if r - l <= w - 10:
                    break
                size -= 1
            l, t, r, b = d.textbbox((0, 0), text, font=f)
            cy = Y0 + pad + slot * i + (slot - (b - t)) / 2
            d.text((X0 + (w - (r - l)) / 2 - l, cy - t), text, font=f, fill=COLORS[ck])
    out = "preview.png" if preview else OUT
    if not preview:
        im = im.resize((int(im.width * 0.75), int(im.height * 0.75)), Image.LANCZOS)
    im.save(out, optimize=True)
    print("saved", out, im.size, "格數", len(CELLS))


if __name__ == "__main__":
    main()
