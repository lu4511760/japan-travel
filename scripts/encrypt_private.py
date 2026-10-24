# -*- coding: utf-8 -*-
"""把私人行程加密成 private.enc（只有這個加密檔會進版控）。

用法：
    python scripts/encrypt_private.py
    （會提示輸入密碼；或先設環境變數 TRIP_PW）

來源 private-itinerary.json 已列入 .gitignore，明文永遠不會進 repo。
格式（陣列，每筆一個時間軸節點）：
[
  {"day": "d0121", "time": "19:00", "title": "🍶 居酒屋", "body": "<p>備註</p>"}
]
  day   對應日期標題 id：d0116 d0117 d0118 d0119 d0120 d0121 d0122 d0123
  time  HH:MM，會自動插進當天正確的時間順序
  title 節點標題（可用 emoji）
  body  選填，卡片內容的 HTML（可放 <a> 連結）
  cls   選填，標題樣式：meal（綠色，用餐）或 alert（紅色，重要）
"""
import base64
import getpass
import hashlib
import json
import os
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "private-itinerary.json")
OUT = os.path.join(BASE, "private.enc")
ITERATIONS = 200000


def main():
    if not os.path.exists(SRC):
        sys.exit("找不到 %s" % SRC)

    # 先驗證是合法 JSON，避免加密了壞資料
    with open(SRC, encoding="utf-8") as fh:
        items = json.load(fh)
    if not isinstance(items, list):
        sys.exit("private-itinerary.json 必須是陣列")

    pw = os.environ.get("TRIP_PW") or getpass.getpass("密碼：")
    if not pw:
        sys.exit("密碼不能空白")

    plaintext = json.dumps(items, ensure_ascii=False).encode("utf-8")
    salt = os.urandom(16)
    iv = os.urandom(12)
    key = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, ITERATIONS, 32)
    ct = AESGCM(key).encrypt(iv, plaintext, None)

    blob = {
        "v": 1,
        "it": ITERATIONS,
        "salt": base64.b64encode(salt).decode(),
        "iv": base64.b64encode(iv).decode(),
        "ct": base64.b64encode(ct).decode(),
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(blob, fh, indent=1)
    print("已加密 %d 筆私人行程 → %s" % (len(items), OUT))


if __name__ == "__main__":
    main()
