# -*- coding: utf-8 -*-
"""從桃園機場室內地圖的設施資料，產生「登機門／到達門／行李轉盤／報到櫃台 → 地圖 POI ID」對照表，
寫進 index.html 的 <script id="tpe-poi" type="application/json">。

用法：python scripts/build_tpe_poi.py
      （機場改了地圖、連結打不開時重跑一次即可）

資料來源：map.taoyuan-airport.com 背後的 poi-data.json（公開、約 2MB、不開放跨網域，
所以不讓手機直接抓，改成在這裡先挑出需要的幾百筆，內嵌進網頁）。
地圖網址只要帶 ?poi=ID 就會自己切到對的航廈與樓層。

對照表的鍵：
  dep|D1      出發登機門（mapId 樓層 3F／region 出發區）
  arr|D1      抵達到達門（mapId 樓層 2F／region 抵達區）
  belt|T1|3A  行李轉盤（同號碼兩個航廈都有，要帶航廈）
  ck|T1|6     報到櫃台（同號碼兩個航廈都有，要帶航廈）
"""
import io
import json
import os
import re
import urllib.request

SRC = 'https://pub-7f923ce89a404c968d730f74a111e765.r2.dev/poi-data.json'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'index.html')
PAT = re.compile(r'(<script id="tpe-poi" type="application/json">)(.*?)(</script>)', re.S)


def main():
    req = urllib.request.Request(SRC, headers={'User-Agent': 'Mozilla/5.0 (travel-site personal use)'})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode('utf-8'))
    am = d['amenities'] if isinstance(d['amenities'], list) else list(d['amenities'].values())

    out = {}
    skipped = []
    for x in am:
        p = x.get('properties') or {}
        cat = p.get('category')
        name = p.get('name') or {}
        mid = p.get('mapId') or ''
        term = mid.split('-')[0] if mid else ''
        if cat == 'boardinggate.aircraft':
            g = (name.get('en') or '').strip().upper()
            if not g:
                continue
            floor = mid.split('-')[1] if mid.count('-') >= 2 else ''
            region = p.get('region') or ''
            kind = 'arr' if (floor == '2F' or region == '抵達區') else 'dep'
            k = kind + '|' + g
        elif cat == 'baggagecarousel':
            m = re.match(r'^(\d+[A-Z]?)', name.get('zh-Hant') or '')
            if not (m and term):
                skipped.append(x['id'])
                continue
            k = 'belt|' + term + '|' + m.group(1)
        elif cat == 'checkin.desk':
            m = re.match(r'^(\d+)號', name.get('zh-Hant') or '')
            if not (m and term):
                skipped.append(x['id'])
                continue
            k = 'ck|' + term + '|' + m.group(1)
        else:
            continue
        if k in out and out[k] != x['id']:
            # 同一個鍵有兩筆：留有 mapId 的那筆（比較完整）
            if not mid:
                continue
        out[k] = x['id']

    payload = json.dumps(dict(sorted(out.items())), ensure_ascii=False, separators=(',', ':'))
    s = io.open(P, encoding='utf-8', newline='').read()
    if not PAT.search(s):
        raise SystemExit('index.html 找不到 <script id="tpe-poi">')
    s = PAT.sub(lambda m: m.group(1) + payload + m.group(3), s, count=1)
    io.open(P, 'w', encoding='utf-8', newline='').write(s)
    kinds = {}
    for k in out:
        kinds[k.split('|')[0]] = kinds.get(k.split('|')[0], 0) + 1
    print('已寫入 tpe-poi 對照表：', kinds, '，略過', len(skipped), '筆，大小', len(payload), 'bytes')


if __name__ == '__main__':
    main()
