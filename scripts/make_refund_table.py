# -*- coding: utf-8 -*-
"""產生「退稅平台比較表」圖片（退稅平台比較.webp），給 1/23 退稅那則連結用。

用法：python scripts/make_refund_table.py
資料寫在下面的 PLATFORMS / ROWS，平台或商家有變動就改這裡再重跑。
調查日期 2026/11/18，來源見 變動紀錄.md。
"""
import io
import os
import re

from PIL import Image, ImageChops, ImageDraw, ImageFont
import pymupdf   # 用來把 SVG logo 轉成點陣圖

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, '退稅平台比較.webp')
LOGO_DIR = os.path.join(ROOT, 'scripts', 'refund_logos')   # 來源見該資料夾的 README.md

# 表頭 logo：平台名稱 → (檔名, 是否在 logo 下面再寫名字, SVG 顏色替換)
# logo 本身就有名字的只放 logo；J-TaxRefund 只有圖案，所以下面再寫名字
LOGOS = {
    'J-TaxRefund': ('jtaxrefund.svg', True, None),
    'JPrefund': ('jprefund.svg', False, None),
    'Global Blue': ('globalblue.svg', False, None),
    'PIE VAT': ('pievat.svg', False, None),
    'Ocean\nTax Refund': ('ocean_og.png', False, None),
    'Planet': ('planet.svg', False, [('#FFFFFF', '#1B2A41')]),   # 官網是白字，白底表格要改深色
    'IntaSect': ('intaxfree.png', False, None),
}

FONT = 'C:/Windows/Fonts/msjh.ttc'
FONT_B = 'C:/Windows/Fonts/msjhbd.ttc'

# 打勾欄位：True=有、False=沒有、None=查不到（畫問號）
# 商家名稱結尾加 * ＝已宣告免退稅手續費（畫成綠字，* 不會印出來）；機場領現金的手續費另計
PLATFORMS = [
    # 名稱, 主要配合商家, 設定方式, 信用卡, 現金, GLORY, Cash Japan
    ('J-TaxRefund', ['唐吉訶德*', 'Bic Camera*', 'UNIQLO', 'GU', 'MUJI', '松本清', 'Cocokara',
                     '大國藥妝*', 'Sundrug*', '鶴羽藥妝*'],
     ['網站'], True, True, True, True),
    ('JPrefund', ['3COINS', 'Shimamura'], ['網站'], True, True, True, True),
    ('Global Blue', ['高島屋', '大丸松坂屋', '伊勢丹三越', '阪急阪神', '西武Sogo', 'Yodobashi', 'Sugi藥局'],
     ['App', '網站'], True, True, False, True),
    ('PIE VAT', ['SHIBUYA109', '三井Outlet', 'LaLaport', 'mont-bell'], ['App'], True, False, False, False),
    ('Ocean\nTax Refund', ['Yamada電機*', 'animate'], ['LINE', 'WeChat', '網站'], True, False, False, False),
    ('Planet', ['未公開'], ['網站'], True, True, True, False),
    ('IntaSect', ['未公開'], ['依收據'], None, True, True, False),
]
# 打勾格子底下要加的小字：(平台名稱, 列索引) → 文字。列索引對照 ROWS（3＝現金退稅）
# JPrefund 要領現金，得在海關確認前就上網把退款方式選成「機場領現金」，之後不能改（jptaxrefund.com/blog/jprefund-guide）
MARK_NOTES = {('JPrefund', 3): '(需先線上設定)'}
ROWS = ['主要配合商家', '設定方式', '信用卡退稅', '現金退稅', 'GLORY\nSelf Tax Refund', 'Cash Japan']

S = 2                      # 整張放大倍率（手機點開放大仍清楚）
HEAD_W = 170 * S           # 左側列名欄寬
COL_W = 150 * S
LINE_H = 30 * S
PAD = 14 * S

C_BG = (255, 255, 255)
C_HEAD = (32, 64, 112)
C_HEAD_TX = (255, 255, 255)
C_ROWHEAD = (232, 238, 247)
C_STRIPE = (247, 249, 252)
C_GRID = (200, 208, 220)
C_TX = (30, 30, 30)
C_SUB = (120, 120, 120)
C_YES = (34, 150, 70)
C_NO = (200, 200, 200)
C_UNK = (220, 150, 30)
C_FREE = (34, 150, 70)        # 免手續費的商家

f_tx = ImageFont.truetype(FONT, 20 * S)
f_b = ImageFont.truetype(FONT_B, 20 * S)
f_title = ImageFont.truetype(FONT_B, 30 * S)
f_note = ImageFont.truetype(FONT, 16 * S)
f_mark_note = ImageFont.truetype(FONT, 14 * S)


def lines_of(r, ci):
    """某列某平台要印的文字行（打勾列回傳 None）。"""
    p = PLATFORMS[ci]
    if r == 0:
        return p[1]
    if r == 1:
        return p[2]
    return None


def row_height(r):
    if r >= 2:
        return 64 * S
    n = max(len(lines_of(r, ci)) for ci in range(len(PLATFORMS)))
    return max(n * LINE_H + 2 * PAD, 64 * S)


TITLE_H = 70 * S
HEADER_H = 118 * S                 # 表頭放 logo，比原本兩行字高
LOGO_W = COL_W - 26 * S            # logo 最大寬度
LOGO_H = 62 * S                    # 只有 logo 時的最大高度
LOGO_H_NAMED = 50 * S              # logo 下面還有名字時的最大高度


def load_logo(fn, recolor):
    """讀 logo（SVG 先轉點陣圖），裁掉四周空白，回傳 RGBA。"""
    path = os.path.join(LOGO_DIR, fn)
    if fn.endswith('.svg'):
        t = io.open(path, encoding='utf-8').read()
        # MuPDF 不認 <style> 裡的 class 上色：改成直接寫在元素上
        for cls, col in re.findall(r'\.([\w-]+)\s*\{\s*fill:\s*([^;}\s]+)', t):
            t = t.replace('class="%s"' % cls, 'fill="%s"' % col)
        # 漸層畫不出來(會變黑)：改成漸層的主色
        t = re.sub(r'fill="url\(#[^)]*\)"', 'fill="#D50000"', t)
        for a, b in (recolor or []):
            t = t.replace('fill="%s"' % a, 'fill="%s"' % b).replace('fill="%s"' % a.lower(), 'fill="%s"' % b)
        doc = pymupdf.open(stream=t.encode('utf-8'), filetype='svg')
        pg = doc[0]
        z = 900 / max(pg.rect.width, pg.rect.height)
        lg = Image.open(io.BytesIO(pg.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=True).tobytes('png'))).convert('RGBA')
    else:
        lg = Image.open(path).convert('RGBA')
    a = lg.getchannel('A')
    if a.getextrema()[0] == 255:   # 不透明的圖(白底)：依跟白色的差異裁，並把白底變透明
        diff = ImageChops.difference(lg.convert('RGB'), Image.new('RGB', lg.size, (255, 255, 255))).convert('L')
        mask = diff.point(lambda v: 255 if v > 24 else 0)
        lg.putalpha(diff.point(lambda v: min(255, v * 6)))
        bb = mask.getbbox()
    else:
        bb = a.point(lambda v: 255 if v > 10 else 0).getbbox()
    return lg.crop(bb)


def paste_logo(lg, cx, cy, max_w, max_h):
    k = min(max_w / lg.width, max_h / lg.height)
    lg = lg.resize((max(1, round(lg.width * k)), max(1, round(lg.height * k))), Image.LANCZOS)
    im.paste(lg, (round(cx - lg.width / 2), round(cy - lg.height / 2)), lg)
NOTE_H = 56 * S
W = HEAD_W + COL_W * len(PLATFORMS)
H = TITLE_H + HEADER_H + sum(row_height(r) for r in range(len(ROWS))) + NOTE_H

im = Image.new('RGB', (W, H), C_BG)
d = ImageDraw.Draw(im)


def center_text(box, text, font, fill):
    x0, y0, x1, y1 = box
    ls = text.split('\n')
    total = len(ls) * LINE_H
    y = (y0 + y1 - total) / 2
    for ln in ls:
        col = fill
        if ln.endswith('*'):          # 免手續費的商家畫綠字
            ln, col = ln[:-1], C_FREE
        w = d.textlength(ln, font=font)
        d.text(((x0 + x1 - w) / 2, y + (LINE_H - font.size) / 2 - 2 * S), ln, font=font, fill=col)
        y += LINE_H


def draw_mark(box, v, note=None):
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    r = 15 * S
    if note:                      # 有小字就把記號往上移，小字放下面
        cy -= 11 * S
        w = d.textlength(note, font=f_mark_note)
        d.text((cx - w / 2, cy + r + 4 * S), note, font=f_mark_note, fill=C_UNK)
    if v is True:
        d.line([(cx - r, cy), (cx - r / 3, cy + r * 0.7), (cx + r, cy - r * 0.7)], fill=C_YES, width=5 * S, joint='curve')
    elif v is False:
        d.line([(cx - r * 0.6, cy), (cx + r * 0.6, cy)], fill=C_NO, width=4 * S)
    else:
        w = d.textlength('?', font=f_title)
        d.text((cx - w / 2, cy - f_title.size * 0.65), '?', font=f_title, fill=C_UNK)


# 標題
d.text((PAD, (TITLE_H - f_title.size) / 2 - 4 * S), '日本退稅平台比較(2026/11 新制)', font=f_title, fill=C_HEAD)

# 表頭：「平台」格維持深藍，各平台格白底放 logo(深色 logo 在深藍底上看不到)
y = TITLE_H
d.rectangle([0, y, HEAD_W, y + HEADER_H], fill=C_HEAD)
center_text((0, y, HEAD_W, y + HEADER_H), '平台', f_b, C_HEAD_TX)
for ci, p in enumerate(PLATFORMS):
    x = HEAD_W + ci * COL_W
    cx = x + COL_W / 2
    spec = LOGOS.get(p[0])
    if not spec:
        center_text((x, y, x + COL_W, y + HEADER_H), p[0], f_b, C_HEAD)
        continue
    lg = load_logo(spec[0], spec[2])
    if spec[1]:                     # logo＋名字
        paste_logo(lg, cx, y + PAD + LOGO_H_NAMED / 2, LOGO_W, LOGO_H_NAMED)
        center_text((x, y + PAD + LOGO_H_NAMED, x + COL_W, y + HEADER_H - PAD / 2), p[0], f_b, C_HEAD)
    else:                           # 只有 logo
        paste_logo(lg, cx, y + HEADER_H / 2, LOGO_W, LOGO_H)
d.line([HEAD_W, y + HEADER_H - S, W, y + HEADER_H - S], fill=C_HEAD, width=3 * S)
y += HEADER_H

# 內容
for r, name in enumerate(ROWS):
    h = row_height(r)
    if r % 2:
        d.rectangle([HEAD_W, y, W, y + h], fill=C_STRIPE)
    d.rectangle([0, y, HEAD_W, y + h], fill=C_ROWHEAD)
    center_text((0, y, HEAD_W, y + h), name, f_b, C_TX)
    for ci, p in enumerate(PLATFORMS):
        x = HEAD_W + ci * COL_W
        box = (x, y, x + COL_W, y + h)
        ls = lines_of(r, ci)
        if ls is None:
            draw_mark(box, p[r + 1], MARK_NOTES.get((p[0], r)))
        else:
            col = C_SUB if ls == ['未公開'] or ls == ['依收據'] else C_TX
            center_text(box, '\n'.join(ls), f_tx, col)
    d.line([0, y, W, y], fill=C_GRID, width=S)
    y += h
d.line([0, y, W, y], fill=C_GRID, width=S)
for ci in range(len(PLATFORMS) + 1):
    x = HEAD_W + ci * COL_W
    d.line([x, TITLE_H, x, y], fill=C_GRID, width=S)

# 註腳
notes = ['綠字＝店家宣告免退稅手續費(機場領現金仍會扣)。？＝查不到官方資訊。現金支付日圓，會取整數，且會另扣手續費。']
ny = y + 14 * S
for n in notes:
    d.text((PAD, ny), n, font=f_note, fill=C_SUB)
    ny += 26 * S

im.save(OUT, 'WEBP', quality=88, method=6)
print('已產生', OUT, im.size, os.path.getsize(OUT) // 1024, 'KB')
