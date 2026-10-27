# -*- coding: utf-8 -*-
"""網站 icon：卡通風格的單板滑手（粗黑描邊、黃帽藍衣白褲棕板）。"""
import math
from PIL import Image, ImageDraw

BASE = r"G:\My Drive\Riskval\claudeWorkspace\japanTravel"
SKY, SNOW = (159, 212, 239), (248, 252, 255)
INK = (26, 26, 26)
COAT, PANTS, SKIN, HAT, GLOVE, BOARD = (41, 155, 213), (252, 252, 252), (248, 208, 172), (248, 196, 48), (90, 96, 104), (139, 91, 54)

SS = 6                       # 先畫 6 倍再縮，描邊才平滑
GRID = 64.0


def px(v, W):
    return v * W / GRID


def limb(d, W, pts, color, w, ink=True):
    """粗線條肢體：先鋪黑描邊，再疊顏色。"""
    for col, ww in (((INK,), w + 2.2), ((color,), w)) if ink else (((color,), w),):
        wpx = max(1, int(round(px(ww, W))))
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            d.line([px(ax, W), px(ay, W), px(bx, W), px(by, W)], fill=col[0], width=wpx)
        for x, y in pts:
            r = wpx / 2
            d.ellipse([px(x, W) - r, px(y, W) - r, px(x, W) + r, px(y, W) + r], fill=col[0])


def blob(d, W, box, color, grow=1.1, kind="ellipse", radius=0):
    """橢圓／圓角矩形：先畫放大的黑底，再畫本體。"""
    x0, y0, x1, y1 = box
    for col, g in ((INK, grow), (color, 0)):
        b = [px(x0 - g, W), px(y0 - g, W), px(x1 + g, W), px(y1 + g, W)]
        if kind == "ellipse":
            d.ellipse(b, fill=col)
        else:
            d.rounded_rectangle(b, radius=px(radius + g, W), fill=col)


def build(size):
    W = size * SS
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, W - 1, W - 1], radius=px(14, W), fill=SKY)

    # 雪坡
    pts = [(0, 64), (0, 54)]
    for t in range(101):
        u = t / 100.0
        pts.append((2 * (1 - u) * u * 20 + u * u * 40,
                    (1 - u) ** 2 * 54 + 2 * (1 - u) * u * 60 + u * u * 57))
    pts += [(52, 60), (64, 58), (64, 64)]
    d.polygon([(px(x, W), px(y, W)) for x, y in pts], fill=SNOW)

    # 單板：獨立圖層畫好再旋轉
    layer = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    blob(dl, W, (9, 42.5, 55, 49.5), BOARD, grow=1.3, kind="rect", radius=3.5)
    layer = layer.rotate(25, resample=Image.BICUBIC, center=(px(32, W), px(46, W)))
    im = Image.alpha_composite(im, layer)
    d = ImageDraw.Draw(im)

    # 腿（白褲）
    limb(d, W, [(31, 29.5), (24, 38), (22.3, 47.2)], PANTS, 7)
    limb(d, W, [(34.5, 30.5), (41, 36), (42.6, 41.2)], PANTS, 7)
    # 手臂（藍外套袖）
    limb(d, W, [(30, 22), (22, 23.5), (16.5, 26)], COAT, 5.6)
    limb(d, W, [(37, 22.5), (45, 26), (50, 29.5)], COAT, 5.6)
    # 軀幹
    blob(d, W, (27, 17.5, 39, 32), COAT, grow=1.3, kind="rect", radius=5)
    # 手套
    blob(d, W, (13.3, 23.4, 18.7, 28.6), GLOVE, grow=1.2)
    blob(d, W, (47.6, 27.2, 53, 32.4), GLOVE, grow=1.2)
    # 頭與帽
    blob(d, W, (30.5, 8.2, 42.2, 20.4), SKIN, grow=1.3)
    blob(d, W, (30.2, 5.8, 42.5, 13.2), HAT, grow=1.3, kind="rect", radius=5.4)
    blob(d, W, (29.6, 11.4, 43.1, 14.6), HAT, grow=1.3, kind="rect", radius=1.6)

    return im.resize((size, size), Image.LANCZOS)


build(180).save(BASE + "/apple-touch-icon.png")
build(192).save(BASE + "/icon-192.png")
build(512).save(BASE + "/icon-512.png")   # 加到主畫面（PWA）用的大圖
build(32).save(BASE + "/favicon-32.png")
build(48).resize((192, 192), Image.NEAREST).save("icon48_big.png")
print("icon 已產生")
