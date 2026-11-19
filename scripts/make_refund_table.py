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
# 商家寫法「名稱|手續費」：手續費(店家的退稅手續費，以未稅價計；¥ 是每筆定額)畫成灰小字接在名稱後面
#   名稱結尾加 * ＝已宣告免退稅手續費（畫成綠字，* 不會印出來）；機場領現金的手續費另計
#   名稱太長可用 \n 斷行，手續費接在最後一行後面
#   名稱是「其他」＝其餘合作店家的手續費範圍，整行灰字當補述
# 手續費來源：林氏璧 2026/11/15 整理(linshibi.com/?p=53059)、PIE VAT 官方說明(help.pievat.com)
PLATFORMS = [
    # 名稱, 主要配合商家, 設定方式, 信用卡, 現金, GLORY, Cash Japan
    ('J-TaxRefund', ['唐吉訶德*|0%', 'Bic Camera*|0%', '多慶屋*|0%', '山田電機*|0%', '鶴羽藥妝*|0%',
                     'Sundrug*|0%', '大國藥妝*|0%', 'Sapporo Drug*|0%', 'Kojima*|0%', 'Sofmap*|0%',
                     '松本清|0~0.33%', 'Cocokara|0.33%', 'UNIQLO|1%', 'GU|1%', '東武百貨|1%',
                     'MUJI|1.3%', '松屋銀座|1~1.5%', '寶可夢中心|1.5%', '其他|1.5~4%'],
     ['網站'], True, True, True, True),
    ('JPrefund', ['3COINS|¥320', '思夢樂|1~2.5%', 'LOFT|1.55~2%', 'HANDS|1.55~2%', 'PARCO|1.5~2%',
                  'Fancl|3.5%', '其他|0.4~3%'], ['網站'], True, True, True, True),
    ('Global Blue', ['高島屋|2.3%', '大丸松坂屋|2.3%', '伊勢丹三越|2.3%', '阪急阪神|2.3%', '京王百貨|1.5~1.65%',
                     '近鐵百貨|1.55~2.3%', '小田急百貨|2.3%', '西武Sogo',
                     'Yodobashi|2.3%', 'Sugi藥局|¥160', 'EDION|¥210', '其他|1.6~3%'],
     ['App', '網站'], True, True, False, True),
    ('PIE VAT', ['澀谷109|1.55%', '三井Outlet|1.5%', 'LaLaport|1.5%', 'mont-bell|2~3%', 'MURASAKI\nSPORTS|2~3%', '其他|1.5~3%'],
     ['App'], True, False, False, False),
    ('Ocean\nTax Refund', ['Yamada電機*|0%', 'animate|2.1%', 'ADASTRIA|2~2.5%'], ['LINE', 'WeChat', '網站'], True, False, False, False),
    ('Planet', ['AEON Mall|1.5%', '沖繩商場|2.5%'], ['網站'], True, True, True, False),
    ('IntaSect', ['未公開'], ['依收據'], None, True, True, False),
]
# 打勾格子底下要加的小字：(平台名稱, 列索引) → (文字, 顏色)。列索引對照 ROWS（2＝信用卡、3＝現金退稅）
# JPrefund 要領現金，得在海關確認前就上網把退款方式選成「機場領現金」，之後不能改（jptaxrefund.com/blog/jprefund-guide）
C_NOTE_GRAY = (120, 120, 120)
C_NOTE_ORANGE = (220, 150, 30)
MARK_NOTES = {
    ('J-TaxRefund', 2): ('可能有匯款費\n約0.33~0.5%', C_NOTE_GRAY),
    ('JPrefund', 2): ('可能另扣匯款費', C_NOTE_GRAY),
    ('Global Blue', 2): ('換匯加價2~4%\n建議JCB/雙幣卡', C_NOTE_GRAY),
    ('PIE VAT', 2): ('另扣提領費\n0.28~0.36%', C_NOTE_GRAY),
    ('Ocean\nTax Refund', 2): ('無額外費用', C_NOTE_GRAY),
    ('JPrefund', 3): ('(需先線上設定)', C_NOTE_ORANGE),
    # 友都八喜 11 間分店的市區現金退稅(只收 Global Blue)
    ('Global Blue', 3): ('友都八喜市區可領\n退稅額5%(約未稅0.5%)\n最低¥150、最高¥500', C_NOTE_GRAY),
}
ROWS = ['主要配合商家', '設定方式', '信用卡退稅', '現金退稅', 'GLORY\nSelf Tax Refund', 'Cash Japan']
# 列名底下的灰小字(機場現金退稅機的手續費，另外加在店家手續費上)
ROW_NOTES = {
    4: '約未稅價1.1%\n最低/最高: 未公開\n未滿¥100捨去',
    5: '約未稅價1%\n最低¥100、最高¥500\n以¥50四捨五入',
}

S = 2                      # 整張放大倍率（手機點開放大仍清楚）
HEAD_W = 170 * S           # 左側列名欄寬
COL_W = 178 * S
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
f_fee = ImageFont.truetype(FONT, 15 * S)          # 商家後面的手續費
f_small = ImageFont.truetype(FONT, 13 * S)        # 勾勾、列名底下的灰小字
SMALL_LH = 18 * S                                 # 灰小字行高
MARK_BOX = 34 * S                                 # 勾勾本身佔的高度


def lines_of(r, ci):
    """某列某平台要印的文字行（打勾列回傳 None）。"""
    p = PLATFORMS[ci]
    if r == 0:
        return p[1]
    if r == 1:
        return p[2]
    return None


def nlines(t):
    return len(t.split('\n')) if t else 0


def row_height(r):
    # 列名(含底下灰小字)要的高度
    head = nlines(ROWS[r]) * LINE_H + (nlines(ROW_NOTES.get(r)) * SMALL_LH + 4 * S if r in ROW_NOTES else 0) + 2 * PAD
    if r >= 2:
        notes = [MARK_NOTES.get((p[0], r)) for p in PLATFORMS]
        n = max([nlines(x[0]) for x in notes if x] or [0])
        cell = MARK_BOX + (n * SMALL_LH + 6 * S if n else 0) + 2 * PAD
        return max(64 * S, cell, head)
    n = max(sum(nlines(it.partition('|')[0]) for it in lines_of(r, ci)) for ci in range(len(PLATFORMS)))
    return max(n * LINE_H + 2 * PAD, 64 * S, head)


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
NOTE_H = 106 * S
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


def small_lines(text, cx, y, fill):
    """從 y 開始往下畫置中的灰小字(可多行)。"""
    for ln in text.split('\n'):
        w = d.textlength(ln, font=f_small)
        d.text((cx - w / 2, y + (SMALL_LH - f_small.size) / 2 - S), ln, font=f_small, fill=fill)
        y += SMALL_LH


def merchant_lines(box, items):
    """主要配合商家：名稱(綠字＝免手續費) + 灰色小字手續費；「其他」整行灰字。"""
    x0, y0, x1, y1 = box
    # 名稱有 \n 的拆成多行：前面幾行只有名稱，手續費接在最後一行
    flat = []
    for it in items:
        name, bar, fee = it.partition('|')
        star = '*' if name.endswith('*') else ''
        parts = name.rstrip('*').split('\n')
        flat += [x + star for x in parts[:-1]] + [parts[-1] + star + bar + fee]
    items = flat
    y = (y0 + y1 - len(items) * LINE_H) / 2
    gap = 4 * S
    for it in items:
        name, _, fee = it.partition('|')
        col = C_TX
        if name.endswith('*'):
            name, col = name[:-1], C_FREE
        if name == '其他' or name in ('未公開', '依收據'):
            col = C_SUB
        fee_t = '(%s)' % fee if fee else ''
        wn = d.textlength(name, font=f_tx)
        wf = d.textlength(fee_t, font=f_fee) if fee_t else 0
        total = wn + (gap + wf if fee_t else 0)
        if total > (x1 - x0) - 6 * S:
            print('  ⚠ 太寬會超出格子:', name, fee_t)
        x = (x0 + x1 - total) / 2
        ty = y + (LINE_H - f_tx.size) / 2 - 2 * S
        d.text((x, ty), name, font=f_tx, fill=col)
        if fee_t:
            # 手續費字比較小，底線對齊名稱
            d.text((x + wn + gap, ty + (f_tx.size - f_fee.size) - S), fee_t, font=f_fee,
                   fill=C_FREE if col == C_FREE else C_SUB)
        y += LINE_H


def draw_mark(box, v, note=None):
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    r = 15 * S
    if note:                      # 有小字就把記號往上移，小字放下面，整塊垂直置中
        text, ncol = note
        block = MARK_BOX + 6 * S + nlines(text) * SMALL_LH
        top = cy - block / 2
        cy = top + MARK_BOX / 2
        small_lines(text, cx, top + MARK_BOX + 6 * S, ncol)
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
    if r in ROW_NOTES:              # 列名＋底下灰小字，整塊垂直置中
        nh = nlines(name) * LINE_H
        block = nh + 4 * S + nlines(ROW_NOTES[r]) * SMALL_LH
        top = y + (h - block) / 2
        center_text((0, top, HEAD_W, top + nh), name, f_b, C_TX)
        small_lines(ROW_NOTES[r], HEAD_W / 2, top + nh + 4 * S, C_SUB)
    else:
        center_text((0, y, HEAD_W, y + h), name, f_b, C_TX)
    for ci, p in enumerate(PLATFORMS):
        x = HEAD_W + ci * COL_W
        box = (x, y, x + COL_W, y + h)
        ls = lines_of(r, ci)
        if ls is None:
            draw_mark(box, p[r + 1], MARK_NOTES.get((p[0], r)))
        elif r == 0:
            merchant_lines(box, ls)
        else:
            col = C_SUB if ls == ['未公開'] or ls == ['依收據'] else C_TX
            center_text(box, '\n'.join(ls), f_tx, col)
    d.line([0, y, W, y], fill=C_GRID, width=S)
    y += h
d.line([0, y, W, y], fill=C_GRID, width=S)
for ci in range(len(PLATFORMS) + 1):
    x = HEAD_W + ci * COL_W
    d.line([x, TITLE_H, x, y], fill=C_GRID, width=S)
# 表頭上下的深藍粗線最後再畫一次，蓋過直格線，線才是連續的
d.rectangle([HEAD_W, TITLE_H, W, TITLE_H + 3 * S], fill=C_HEAD)
d.rectangle([HEAD_W, TITLE_H + HEADER_H - 3 * S, W, TITLE_H + HEADER_H], fill=C_HEAD)

# 註腳
notes = ['店家後面括號＝店家的退稅手續費(以未稅價計，¥＝每筆定額)；綠字＝店家宣告免手續費。？＝查不到官方資訊。',
         '機場領現金另扣機台手續費(見左欄)，店家免手續費也不會吸收；現金支付日圓。手續費為 2026/11 網友實測整理，以店頭標示為準。',
         '如開在百貨商場之"店中店"(高島屋、大丸、PARCO、AEON)，退稅平台與手續費一律跟著該百貨商場走。']
ny = y + 14 * S
for n in notes:
    d.text((PAD, ny), n, font=f_note, fill=C_SUB)
    ny += 26 * S

im.save(OUT, 'WEBP', quality=88, method=6)
print('已產生', OUT, im.size, os.path.getsize(OUT) // 1024, 'KB')
