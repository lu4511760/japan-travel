# -*- coding: utf-8 -*-
"""依 行前清單.txt 重建網頁上的行前清單（分類 + 勾選狀態以項目名稱為鍵）。"""
import io, re, html

BASE = r"G:\My Drive\Riskval\claudeWorkspace\japanTravel"
TXT = BASE + r"\行前清單.txt"
P = BASE + r"\index.html"

LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

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

rows = []
total = 0
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
        rows.append('        <li><label><input type="checkbox" data-ck="%s"><span>%s</span></label></li>'
                    % (html.escape(key), label))

s = io.open(P, encoding="utf-8", newline="").read()
old = re.search(r'(      <ul class="check" id="cklist">\n)(.*?)(      </ul>\n)', s, re.S)
assert old, "找不到清單區塊"
s = s[:old.start(2)] + "\n".join(rows) + "\n" + s[old.end(2):]

# summary 加進度
old_sum = '    <summary>✅ 行前清單</summary>'
new_sum = '    <summary>✅ 行前清單 <span class="ck-count" id="ck-count"></span></summary>'
if old_sum in s:
    s = s.replace(old_sum, new_sum, 1)

# CSS：分類標題與進度
css_old = "ul.check{list-style:none; margin:0; padding:0}"
css_new = ("ul.check{list-style:none; margin:0; padding:0}\n"
           "ul.check li.ck-group{\n"
           "  margin:12px 0 2px; font-weight:700; font-size:13px; color:var(--accent);\n"
           "  letter-spacing:.5px;\n"
           "}\n"
           "ul.check li.ck-group:first-child{margin-top:4px}\n"
           ".ck-count{font-size:13px; font-weight:400; color:var(--muted)}")
if ".ck-group" not in s:
    assert css_old in s
    s = s.replace(css_old, css_new, 1)

# JS：改用項目名稱當鍵（換清單不會錯位），並更新進度
js_old = re.search(r"(// 行前清單勾選狀態存在瀏覽器本機（換裝置不會同步）\n)\(function\(\)\{.*?\n\}\)\(\);\n", s, re.S)
assert js_old, "找不到清單 JS"
js_new = """(function(){
  var KEY='japan2027-checklist-v2';      // v1 用索引存，清單改版後會錯位，故換鍵
  var boxes=document.querySelectorAll('#cklist input');
  var out=document.getElementById('ck-count');
  function store(){
    try{ return JSON.parse(localStorage.getItem(KEY)||'{}'); }catch(e){ return {}; }
  }
  function count(){
    var n=0;
    boxes.forEach(function(b){ if(b.checked) n++; });
    if(out) out.textContent='（'+n+' / '+boxes.length+'）';
  }
  var s=store();
  boxes.forEach(function(b){ b.checked=!!s[b.getAttribute('data-ck')]; });
  count();
  boxes.forEach(function(b){
    b.addEventListener('change', function(){
      var s=store();
      s[b.getAttribute('data-ck')]=b.checked;
      try{ localStorage.setItem(KEY, JSON.stringify(s)); }catch(e){}
      count();
    });
  });
  // 清單項目裡的連結要能正常點開，不要順便勾到 checkbox
  document.querySelectorAll('#cklist a').forEach(function(a){
    a.addEventListener('click', function(e){ e.stopPropagation(); });
  });
})();
"""
s = s[:js_old.start()] + js_old.group(1) + js_new + s[js_old.end():]

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("清單已更新：%d 類、%d 項" % (len(groups), total))
for name, items in groups:
    print("  %-10s %d 項" % (name, len(items)))
