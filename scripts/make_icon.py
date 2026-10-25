# -*- coding: utf-8 -*-
"""網站 icon：單板滑手。SVG 與 PNG 共用同一組座標。"""
import io, math
from PIL import Image, ImageDraw

BASE = r"G:\My Drive\Riskval\claudeWorkspace\japanTravel"
BG, RIDER, BOARD = "#16202b", "#e58a4e", "#eef4f8"

HEAD = (33, 18, 4.8)                    # cx, cy, r
LIMBS = [                               # 身體與四肢的折線（蹲低前傾的單板姿勢）
    [(32, 24), (29.5, 32.5)],           # 軀幹
    [(31.5, 26), (20.5, 29)],           # 後手（往後下）
    [(31.8, 25.5), (42, 21.5)],         # 前手（往前上）
    [(29.5, 32.5), (23.5, 36), (23.5, 42)],   # 後腳：膝蓋外開、小腿垂直
    [(29.5, 32.5), (37, 36.5), (38.5, 42)],   # 前腳
]
LIMB_W = 4.6
BOARD_RECT = (11, 42.5, 53, 49.5)       # x0,y0,x1,y1（旋轉前）
BOARD_ROT = -11                         # 度，正值為順時針（SVG rotate 的方向）
BOARD_PIVOT = (32, 46)
SLOPE = "M0 64 V55 C16 49 34 53 48 58 C54 60 59 62 64 63 V64 Z"


def svg():
    limbs = "\n".join(
        '    <path d="M%s"/>' % " L".join("%g %g" % p for p in seg) for seg in LIMBS)
    x0, y0, x1, y1 = BOARD_RECT
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="斑尾單板滑雪 × 東京">
  <rect width="64" height="64" rx="14" fill="%s"/>
  <path d="%s" fill="%s"/>
  <rect x="%g" y="%g" width="%g" height="%g" rx="%g" fill="%s"
        transform="rotate(%g %g %g)"/>
  <g fill="none" stroke="%s" stroke-width="%g" stroke-linecap="round" stroke-linejoin="round">
%s
  </g>
  <circle cx="%g" cy="%g" r="%g" fill="%s"/>
</svg>
""" % (BG, SLOPE, BOARD, x0, y0, x1 - x0, y1 - y0, (y1 - y0) / 2, BOARD,
       BOARD_ROT, BOARD_PIVOT[0], BOARD_PIVOT[1],
       RIDER, LIMB_W, limbs, HEAD[0], HEAD[1], HEAD[2], RIDER)


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def png(size):
    SS = 4
    W = size * SS

    def px(v):
        return v * W / 64.0

    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, W - 1, W - 1], radius=px(14), fill=rgb(BG))

    # 雪坡（與 SVG 的貝茲曲線同樣取樣）
    pts = [(0, 64), (0, 55)]
    for t in range(101):
        u = t / 100.0
        pts.append((2 * (1 - u) * u * 22 + u * u * 48,
                    (1 - u) ** 2 * 55 + 2 * (1 - u) * u * 49 + u * u * 58))
    pts += [(54, 60), (59, 62), (64, 63), (64, 64)]
    d.polygon([(px(x), px(y)) for x, y in pts], fill=rgb(BOARD))

    # 單板：畫在獨立圖層再旋轉（PIL 的 rotate 是逆時針）
    layer = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = BOARD_RECT
    dl.rounded_rectangle([px(x0), px(y0), px(x1), px(y1)],
                         radius=px((y1 - y0) / 2), fill=rgb(BOARD))
    layer = layer.rotate(-BOARD_ROT, resample=Image.BICUBIC,
                         center=(px(BOARD_PIVOT[0]), px(BOARD_PIVOT[1])))
    im = Image.alpha_composite(im, layer)

    # 滑手：粗線條＋關節補圓，模擬 stroke-linecap:round
    d = ImageDraw.Draw(im)
    w = px(LIMB_W)
    for seg in LIMBS:
        for (ax, ay), (bx, by) in zip(seg, seg[1:]):
            d.line([px(ax), px(ay), px(bx), px(by)], fill=rgb(RIDER), width=int(round(w)))
        for x, y in seg:
            d.ellipse([px(x) - w / 2, px(y) - w / 2, px(x) + w / 2, px(y) + w / 2], fill=rgb(RIDER))
    hx, hy, hr = HEAD
    d.ellipse([px(hx - hr), px(hy - hr), px(hx + hr), px(hy + hr)], fill=rgb(RIDER))
    return im.resize((size, size), Image.LANCZOS)


io.open(BASE + r"\icon.svg", "w", encoding="utf-8", newline="\n").write(svg())
png(180).save(BASE + r"\apple-touch-icon.png")
png(192).save(BASE + r"\icon-192.png")
png(48).resize((192, 192), Image.NEAREST).save(
    r"C:\Users\twdev\AppData\Local\Temp\claude\G--My-Drive-Riskval-claudeWorkspace-japanTravel\29916330-70f2-4cac-9ff8-496bd065ec22\scratchpad\icon48_big.png")
print("icon 已產生")
