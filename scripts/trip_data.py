# -*- coding: utf-8 -*-
"""讀寫 index.html 裡內嵌的行程資料（<script id="trip-data">）。

這是行程的唯一來源，請勿另外建立 itinerary.json 以免兩邊不同步。

    from scripts.trip_data import load, save
    d = load(); d['items'].append({...}); save(d)
"""
import io, json, os, re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(BASE, "index.html")
PAT = re.compile(r'(<script id="trip-data" type="application/json">)(.*?)(</script>)', re.S)


def load():
    s = io.open(P, encoding="utf-8", newline="").read()
    m = PAT.search(s)
    if not m:
        raise SystemExit("index.html 找不到 trip-data")
    return json.loads(m.group(2).replace(r"<\/", "</"))


def save(data):
    s = io.open(P, encoding="utf-8", newline="").read()
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", r"<\/")
    s = PAT.sub(lambda m: m.group(1) + payload + m.group(3), s, count=1)
    io.open(P, "w", encoding="utf-8", newline="").write(s)
    return len(data["items"])
