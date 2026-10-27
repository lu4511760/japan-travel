# -*- coding: utf-8 -*-
"""依 行前清單.txt 重建網頁上的行前清單（只動 <ul id="cklist"> 這一塊）。

· 勾選狀態以「項目名稱」為鍵（data-ck），所以改名字等於換一個新項目，請小心。
· 每個項目前面的圖示在下面的 ICONS 查表，新增項目記得補一個；沒查到就不放圖示。
· 清單的 CSS 與 JS（勾選、長按取消檢核…）寫在 index.html 裡，這支程式不會動它們。
"""
import io
import re
import html

BASE = r"G:\My Drive\Riskval\claudeWorkspace\japanTravel"
TXT = BASE + r"\行前清單.txt"
P = BASE + r"\index.html"

LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

# 項目名稱 → 圖示（為了好記，同一類裡盡量不重複）
ICONS = {
    "eSIM / SIM卡": "📶", "旅平險(不便險)": "🛡️", "Visit Japan Web": "🌐",
    "護照": "🛂", "身分證": "🪪",
    "台幣現金": "💵", "日幣現金": "💴", "信用卡(JCB)": "💳", "西瓜卡(Suica)": "🍉",
    "手機": "📱", "耳機": "🎧", "充電線": "🔌", "充電器": "⚡", "行動電源": "🔋",
    "內衣褲": "🩲", "外衣褲": "👖", "襪子": "🧦", "外套": "🧥", "帽子(毛帽)": "🧢", "拖鞋": "🩴",
    "牙刷": "🪥", "牙膏": "🦷", "洗面乳": "🧼",
    "口罩": "😷", "濕紙巾": "🧽", "衛生紙": "🧻", "護手霜": "🧴", "護唇膏": "💄",
    "暖暖包": "♨️", "隱形眼鏡": "👁️", "非防風打火機": "🔥",
    "止痛藥": "💊", "腸胃藥": "🧪", "感冒藥": "🤧", "酸痛貼布": "🩹",
    "衣物真空袋": "🗜️", "購物袋": "🛍️", "行李秤": "⚖️", "行李束帶": "🔗",
    "雪衣": "⛷️", "雪褲": "🎿", "雪鏡": "🥽", "手套": "🧤",
    "頭套": "🥷", "貼身排汗衣褲": "👕", "內層手套": "🤲", "雪襪": "❄️",
    "安全帽": "⛑️", "護甲": "🦺", "護腕": "🤚", "護臀": "🍑", "護膝": "🦵",
}


def main():
    groups, cur = [], None
    for raw in io.open(TXT, encoding="utf-8"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("・"):
            cur = (line[1:].strip(), [])
            groups.append(cur)
        elif line.startswith("▢"):
            cur[1].append(line[1:].strip())

    rows, total, missing = [], 0, []
    for name, items in groups:
        rows.append('        <li class="ck-group">%s</li>' % html.escape(name))
        for it in items:
            total += 1
            key = LINK.sub(r"\1", it)                      # 勾選狀態的鍵：去掉連結語法的純文字
            label = LINK.sub(
                lambda m: '<a href="%s" target="_blank" rel="noopener">%s</a>'
                          % (html.escape(m.group(2)), html.escape(m.group(1))), it)
            if label == it:
                label = html.escape(it)
            icon = ICONS.get(key, "")
            if not icon:
                missing.append(key)
            ico = '<i class="ck-ico">%s</i>' % icon if icon else ""
            rows.append('        <li><label><input type="checkbox" data-ck="%s"><span>%s%s</span></label></li>'
                        % (html.escape(key), ico, label))

    s = io.open(P, encoding="utf-8", newline="").read()
    block = re.search(r'(      <ul class="check" id="cklist">\n)(.*?)(      </ul>\n)', s, re.S)
    assert block, "找不到清單區塊"
    s = s[:block.start(2)] + "\n".join(rows) + "\n" + s[block.end(2):]
    assert ".ck-ico" in s, "index.html 少了 .ck-ico 的樣式"
    io.open(P, "w", encoding="utf-8", newline="").write(s)

    print("清單已更新：%d 類、%d 項" % (len(groups), total))
    for name, items in groups:
        print("  %-10s %d 項" % (name, len(items)))
    if missing:
        print("！下列項目沒有圖示，請補進 ICONS：", "、".join(missing))


if __name__ == "__main__":
    main()
