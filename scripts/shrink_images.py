# -*- coding: utf-8 -*-
"""把網頁會連到的菜單／地圖圖片轉成 WebP，手機點開才不用等。

用法：python scripts/shrink_images.py
  · 長邊超過 MAX_SIDE 的先縮小（菜單文字放大仍清楚）
  · 轉成 WebP（quality 82），原 PNG 留在原地，確認沒問題後再手動刪
  · index.html 內的連結（URL-encoded 檔名）同步改成 .webp
"""
import glob, os, urllib.parse, io

from PIL import Image

MAX_SIDE = 2000
QUALITY = 82
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def targets():
    os.chdir(ROOT)
    return sorted(glob.glob('*Menu ZH.png')) + ['Madarao Map & Guide.png', 'iiyama-express2025.png']


def convert(src):
    im = Image.open(src)
    if max(im.size) > MAX_SIDE:
        r = MAX_SIDE / max(im.size)
        im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    if im.mode not in ('RGB', 'RGBA'):
        im = im.convert('RGB')
    dst = os.path.splitext(src)[0] + '.webp'
    im.save(dst, 'WEBP', quality=QUALITY, method=6)
    return dst


def main():
    html_path = os.path.join(ROOT, 'index.html')
    html = io.open(html_path, encoding='utf-8').read()
    total_before = total_after = 0
    for src in targets():
        if not os.path.exists(src):
            print('  略過（找不到）:', src)
            continue
        dst = convert(src)
        a, b = os.path.getsize(src), os.path.getsize(dst)
        total_before += a
        total_after += b
        print('  %-48s %6.2f MB -> %6.2f MB  (%d%%)' % (src, a / 1048576, b / 1048576, 100 * b // a))
        old = urllib.parse.quote(src, safe='')
        new = urllib.parse.quote(dst, safe='')
        if old in html:
            html = html.replace(old, new)
        else:
            print('    ！index.html 找不到這張圖的連結:', old)
    io.open(html_path, 'w', encoding='utf-8', newline='').write(html)
    print('合計 %.2f MB -> %.2f MB' % (total_before / 1048576, total_after / 1048576))


if __name__ == '__main__':
    main()
