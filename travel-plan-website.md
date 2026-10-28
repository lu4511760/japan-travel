# 旅遊行程網站 建置指南

> 這份文件是寫給 **AI 助手** 看的實作規格。照著做就能生出一個「手機優先、離線可用、會跟著時間自己變化」的旅遊行程網站。
>
> 範例取自一趟 8 天 7 夜的日本滑雪行程（2027/01/16–01/23，斑尾高原＋東京）。把資料換成自己的行程即可。

---

## 0. 成品長什麼樣

- 一條**垂直時間軸**，由上到下就是整趟行程；每天一個大標題，底下是一個個時間節點。
- 頂端一排**日期快速跳轉鈕**（Day 1 ~ Day 8），黏在畫面上方。
- **時間到了會自己變化**：已結束的行程變灰、今天的日期標成橘色、出發前顯示行前清單。
- 可**加到手機主畫面**當 App 用，**沒網路也打得開**（到了國外訊號不好照樣看行程）。
- 全部只有 **一個 `index.html`**，沒有框架、沒有 build，丟到 GitHub Pages 就是網站。

---

## 1. 技術選擇與原則

| 項目 | 選擇 | 理由 |
|---|---|---|
| 框架 | **不用**。純 HTML + CSS + 原生 JS | 行程網站生命週期短，不值得背一套 build 工具；單檔最好維護 |
| 檔案 | 全部 inline 在 `index.html`（CSS 在 `<style>`、JS 在 `<script>`） | 一個檔案就是整個網站，離線快取也最單純 |
| 資料 | 內嵌 JSON（`<script id="trip-data" type="application/json">`） | 跟程式分離，但不用多一個 HTTP request |
| 部署 | GitHub Pages | 免費、免伺服器、push 完 1~3 分鐘生效 |
| 離線 | Service Worker + manifest | 出國沒網路時最有感的功能 |

**核心原則：資料驅動**。畫面完全由 JSON 產生，不要把行程寫死在 HTML 裡——否則每改一個時間都要改版面。

---

## 2. 檔案結構

```
index.html                  ← 整個網站（HTML + CSS + JS + 行程資料）
sw.js                       ← Service Worker（離線快取）
manifest.webmanifest        ← PWA 設定（加到主畫面）
favicon-32.png
icon-192.png
icon-512.png
apple-touch-icon.png
*.webp                      ← 菜單、地圖等圖片
scripts/
  trip_data.py              ← 讀寫 index.html 裡的 JSON（給 AI／自己改資料用）
  build_sw.py               ← 產生 sw.js（自動掃圖片清單）
  shrink_images.py          ← 圖片轉 WebP
```

---

## 3. 資料格式（最重要的一節）

```html
<script id="trip-data" type="application/json">{"days":[...],"items":[...]}</script>
```

> ⚠️ JSON 內容若含 `</`（例如 `</a>`、`</p>`）**必須逸出成 `<\/`**，否則瀏覽器會提早結束 `<script>` 標籤。

### days（每一天）

```json
{ "id": "d0116", "label": "第1天・01/16", "dow": "週六" }
```

- `id`：當天的錨點，節點靠它歸屬到某一天，也是 `#d0116` 的跳轉目標。
- `label` / `dow`：顯示用文字。**不要**在這裡放真正的年月日，日期另外用一張對照表管（見 5.3）。

### items（每一個行程節點）

```json
{
  "id": "n015",
  "day": "d0117",
  "time": "12:00",
  "end": "13:00",
  "title": "🍛 中餐: 雪場餐廳",
  "cls": "meal",
  "body": "<p>卡片內容，可放 HTML</p>",
  "below": "卡片外的補充行"
}
```

| 欄位 | 必要 | 說明 |
|---|---|---|
| `id` | ✅ | 唯一代號，分享連結、編輯都靠它 |
| `day` | ✅ | 對應 `days[].id` |
| `time` | | `HH:MM`，開始時間。沒有就是「不綁時間的資訊卡」 |
| `end` | | `HH:MM`，結束時間。沒填＝做到下一個節點開始為止 |
| `title` | | 標題，**emoji 開頭辨識度最好** |
| `cls` | | `meal`（綠色，用餐）或 `alert`（紅色，重要） |
| `body` | | 卡片內容，字串或字串陣列（陣列＝多張卡片） |
| `below` | | 卡片外的補充行，字串或陣列 |

**真實範例**（交通節點，含 Google Maps 連結與路線標記）：

```json
{
  "id": "n046",
  "day": "d0120",
  "time": "13:46",
  "end": "14:00",
  "body": "<p><a href=\"https://www.google.com/maps?cid=7820979510707196484\" target=\"_blank\" rel=\"noopener\">📍 上野</a> → <a href=\"https://www.google.com/maps?cid=1553519931154601905\" target=\"_blank\" rel=\"noopener\">📍 秋葉原</a> <span class=\"note\">(5分鐘)</span></p><p class=\"jr-row\">① <span class=\"jr-code jy\">JY</span><span class=\"jr-line jy\">山手線</span> <span class=\"chip\">普通</span>東京/品川方面(外環線)、3號月台</p>"
}
```

### 地點連結的建議寫法

用 **Google Maps CID 連結**，比搜尋字串精準，不會點進去跑到別家分店：

```
https://www.google.com/maps?cid=<十進位 CID>
```

取得方式：在 Google Maps 找到店家 → 分享 → 取得的短網址展開後可找到 CID（或用 Places API）。

---

## 4. 畫面結構與樣式

### HTML 骨架

```html
<body>
<div class="wrap">
  <h1>行程標題</h1>
  <p class="sub">2027/01/16 ~ 01/23・8 天 7 夜</p>

  <nav id="daynav">                      <!-- 日期快速跳轉，sticky 置頂 -->
    <a href="#d0116" data-d="2027-01-16"><span class="dn">Day 1</span>01/16</a>
    ...
  </nav>

  <details class="block" id="checklist">  <!-- 行前清單（可收合） -->
    <summary>✅ 行前清單 <span class="ck-count"></span></summary>
    <div class="info"><ul class="check" id="cklist">...</ul></div>
  </details>

  <script id="trip-data" type="application/json">{...}</script>

  <div class="tl"></div>                  <!-- 時間軸，由 JS 填滿 -->

  <footer>...</footer>
</div>
<script> /* 全部邏輯 */ </script>
</body>
```

### CSS 要點

```css
:root{
  --bg:#fcfbf7; --fg:#231f1a; --muted:#8a8379; --line:#e8e3d8;
  --accent:#b3541e; --link:#1667d9; --meal:#0e7a52; --day:#c2185b; --alert:#d32f2f;
  --card:#ffffff;
}
@media (prefers-color-scheme: dark){
  :root{ --bg:#1a1814; --fg:#ece7de; --card:#232019; /* … */ }
}
.wrap{max-width:640px; margin:0 auto; padding:26px 16px 64px}   /* 手機優先 */

/* 時間軸的那條線 */
.tl{position:relative; padding-left:30px}
.tl::before{content:""; position:absolute; left:9px; top:6px; bottom:6px; width:2px; background:var(--rail)}
/* 每個節點左邊的圓點 */
.ev{position:relative; margin-bottom:24px; scroll-margin-top:58px}
.ev::before{content:""; position:absolute; left:-29px; top:5px; width:12px; height:12px;
            border-radius:50%; background:var(--bg); border:3px solid var(--accent)}

/* 已過去的行程：變灰 */
.ev.past > *{opacity:.4; filter:grayscale(1)}
.ev.past::before{border-color:var(--rail)}
```

**一定要做深色模式**，手機晚上看行程才不刺眼，用 CSS 變數成本極低。

---

## 5. 功能清單與實作要點

### 5.1 由資料產生時間軸

```js
(function(){
  var data = JSON.parse(document.getElementById('trip-data').textContent);
  window.__tripData = data;

  function fill(ev, it){
    var h = '';
    if(it.time){
      h += '<div class="when" data-t="'+it.time+'"'+(it.end?' data-e="'+it.end+'"':'')+'>'
         + it.time + (it.end ? '<span class="when-end"> ~ '+it.end+'</span>' : '') + '</div>';
    }
    if(it.title) h += '<h2'+(it.cls?' class="'+it.cls+'"':'')+'>'+it.title+'</h2>';
    if(it.body) (Array.isArray(it.body)?it.body:[it.body]).forEach(function(b){
      h += '<div class="body">'+b+'</div>';
    });
    if(it.below) (Array.isArray(it.below)?it.below:[it.below]).forEach(function(b){
      h += '<p class="jr-row">'+b+'</p>';
    });
    ev.innerHTML = h;
    ev.dataset.id = it.id;
  }

  function render(){
    var tl = document.querySelector('.tl');
    tl.textContent = '';
    data.days.forEach(function(d){
      var head = document.createElement('div');
      head.className = 'day-head'; head.id = d.id;
      head.innerHTML = d.label + '<span class="dow">'+d.dow+'</span>';
      tl.appendChild(head);
      data.items.forEach(function(it){
        if(it.day !== d.id) return;
        var ev = document.createElement('div');
        ev.className = 'ev';
        fill(ev, it);
        tl.appendChild(ev);
      });
    });
  }
  render();
})();
```

> **時刻一定要同時寫進 `data-t` / `data-e` 屬性**。畫面文字之後可能變成「12:00 ~ 13:00」甚至被隱藏，程式不該去 parse 顯示文字。

### 5.2 日期快速跳轉列

`nav` 用 `position:sticky; top:0`，水平可捲、隱藏捲軸。開頁時若今天在行程期間，把今天那顆捲到最左邊：

```js
var nav = link.parentNode;
var toFront = function(){
  nav.scrollLeft += link.getBoundingClientRect().left - nav.getBoundingClientRect().left - 12;
};
toFront();
setTimeout(toFront, 400);   // 字型載入後位置會位移，再校一次
```

### 5.3 時間狀態：進行中 / 已結束（核心邏輯）

先有一張 **「天 id → 真實日期」** 對照表，`days[].label` 只是顯示文字：

```js
var DAY_DATES = {d0116:'2027-01-16', d0117:'2027-01-17', /* … */ d0123:'2027-01-23'};
```

每個節點的**有效結束時間**規則：

1. 有填 `end` → 用它
2. 沒填 → 做到**同一天下一個節點的開始時間**
3. 當天最後一個 → 算到午夜

```js
function scan(now){
  var curDate=null, items=[];
  document.querySelectorAll('.tl > *').forEach(function(el){
    if(el.classList.contains('day-head')){
      curDate = DAY_DATES[el.id] || curDate;
      items.push({el:el, date:curDate, head:true});
    }else if(el.classList.contains('ev')){
      var w = el.querySelector('.when');
      items.push({el:el, date:curDate, head:false,
                  t: w && w.getAttribute('data-t'),
                  e: w && w.getAttribute('data-e')});
    }
  });
  // 由後往前，才知道「同一天的下一個是幾點」
  var nextStart = {};
  for(var i=items.length-1; i>=0; i--){
    var x = items[i];
    if(x.head || !x.t) continue;
    x.end = x.e || nextStart[x.date] || '24:00';
    nextStart[x.date] = x.t;
  }
  var cur=null, next=null;
  items.forEach(function(x){
    if(x.head || !x.t || !x.date) return;
    x.start = new Date(x.date+'T'+x.t+':00');
    x.stop  = new Date(x.date+'T'+(x.end==='24:00' ? '23:59:59' : x.end+':00'));
    if(x.end!=='24:00' && x.end < x.t) x.stop.setDate(x.stop.getDate()+1);  // 跨午夜
    if(x.start<=now && now<x.stop) cur = x;      // 重疊時以較晚開始的為準
    if(x.start>now && !next) next = x;
  });
  return {items:items, cur:cur, next:next};
}

function grayPast(now){
  var today = dateStr(now), sc = scan(now);
  document.querySelectorAll('#daynav a[data-d]').forEach(function(a){
    var d = a.getAttribute('data-d');
    a.classList.toggle('past', d < today);
    a.classList.toggle('today', d === today);
  });
  sc.items.forEach(function(x){
    var past = (x.head || !x.t || !x.date) ? (!!x.date && x.date < today) : (now >= x.stop);
    x.el.classList.toggle('past', !!past);
  });
}
```

**時間點型事件**（發車、起飛、到站）直接填 `end = 開始 + 10 分鐘`，不要做特例邏輯——規則越少越好維護。

### 5.4 讓畫面「準時」更新（容易踩坑）

手機會把背景分頁的計時器**凍結**，只靠 `setInterval` 會發現「頁面開著卻沒更新」：

```js
var lastAt = 0;
function wake(){ lastAt = Date.now(); tick(new Date()); }
wake();
setInterval(wake, 30000);
document.addEventListener('visibilitychange', function(){ if(!document.hidden) wake(); });
window.addEventListener('pageshow', wake);     // iOS 從背景回來常常只有這個
window.addEventListener('focus', wake);
(function loop(){                               // 最後一道保險
  requestAnimationFrame(loop);
  if(Date.now()-lastAt > 20000) wake();         // rAF 在背景不會跑，所以不耗電
})();
```

### 5.5 行前清單（勾選狀態存本機）

- 以**項目名稱**當 key 存 `localStorage`（用索引存，清單一改版就全錯位）。
- 每個人的清單各自獨立，不要同步到雲端。
- 進階：**長按某項目 → 標成「這趟不用準備」**，用 checkbox 的 `indeterminate`（顯示成「－」）加刪除線，並從分母扣掉。

```js
// 長按 600ms 切換；手指移動超過 10px 就取消
var timer=null, sx=0, sy=0, longed=false;
document.addEventListener('pointerdown', function(e){
  var b = boxOf(e); if(!b) return;
  sx=e.clientX; sy=e.clientY; longed=false;
  timer = setTimeout(function(){
    timer=null; longed=true;
    setNa(b, !naOn(b));
    if(navigator.vibrate) try{ navigator.vibrate(30); }catch(e2){}
  }, 600);
});
document.addEventListener('pointermove', function(e){
  if(timer && (Math.abs(e.clientX-sx)>10 || Math.abs(e.clientY-sy)>10)){ clearTimeout(timer); timer=null; }
});
```

> ⚠️ **坑**：點 `indeterminate` 的 checkbox 時，瀏覽器會**先**把 `indeterminate` 清掉再派發事件，`preventDefault()` 只還原得了 `checked`、還原不了 `indeterminate`。所以要在 **`change` 事件**裡重設狀態，不要在 `click` 攔截。
>
> 另外長按的元素要加 `user-select:none; -webkit-touch-callout:none`，否則手機會跳出系統的複製選單。

### 5.6 擇一行程（同一時段有兩個方案）

同一個節點裡放兩套內容，用膠囊標籤切換，選擇存 `localStorage`：

```html
<div class="opts" data-opt="d0121-2000">
  <button class="opt-tab on" data-opt-i="0">路線一</button>
  <button class="opt-tab" data-opt-i="1">路線二</button>
</div>
<div class="opt-pane" data-opt="d0121-2000" data-opt-i="0">…</div>
<div class="opt-pane" data-opt="d0121-2000" data-opt-i="1" hidden>…</div>
```

用**事件委派**處理點擊，因為節點隨時可能被重新渲染。

### 5.7 一鍵複製

任何帶 `data-copy` 的元素點了就複製，適合放飯店地址、訂位代碼：

```js
document.addEventListener('click', function(e){
  var b = e.target.closest && e.target.closest('[data-copy]');
  if(!b) return;
  e.preventDefault();
  var text = b.getAttribute('data-copy');
  if(navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text)['catch'](fallback);
  else fallback(text);
  b.textContent = '✓ 已複製';
  setTimeout(function(){ b.textContent = '複製'; }, 1500);
});
// fallback：建立隱藏 textarea + document.execCommand('copy')
```

### 5.8 節點連結（長按複製、開啟自動定位）

長按某個行程 → 複製 `https://…/#n=n046` → 朋友點開會自動捲到那一段並閃五下。

```js
// 開頁最早期就把 hash 記下來，之後清掉網址才不會重整又跳一次
window.__nodeLink = (function(){
  var m = (location.hash||'').match(/^#n=([A-Za-z0-9_-]+)$/);
  return m ? m[1] : null;
})();
// 定位後清掉 hash
history.replaceState(null, '', location.pathname + location.search);
```

重點：**所有「自動捲到今天」的程式都要檢查 `window.__nodeLink`**，否則使用者會被硬拉走。

閃爍用 CSS animation：

```css
.flash{animation:evflash .5s ease-in-out 5; border-radius:12px}
@keyframes evflash{
  0%,100%{background:transparent; box-shadow:none}
  50%{background:rgba(230,126,34,.16); box-shadow:0 0 0 6px rgba(230,126,34,.16)}
}
```

重播動畫要先移除 class、強制重繪（`void el.offsetWidth`）再加回去。

### 5.9 「目前行程」浮動按鈕

右下角圓鈕，按了捲到正在進行的那一段、**到位之後**才閃五下：

```js
function afterScroll(el, cb){          // 等捲動真的停下來，而且目標已經出現在畫面上
  var done=false, last=null, same=0, deadline=Date.now()+2600;
  var t = setInterval(function(){
    if(done) return;
    var y = Math.round(window.scrollY);
    if(y===last) same++; else { last=y; same=0; }
    var r = el.getBoundingClientRect(), shown = r.top<innerHeight && r.bottom>0;
    if((same>=3 && shown) || Date.now()>deadline){ done=true; clearInterval(t); cb(); }
  }, 80);
}
```

> 不要用固定的 `setTimeout` 等捲動完成——smooth 捲動的時間跟距離有關，短的 300ms、長的 1.5 秒。

### 5.10 行程結束後的畫面

最後一天過了就整頁換成「旅程已結束」＋一顆「回顧行程」按鈕；按下去用**回顧模式**重新顯示，時間一律當成出發當天，所以不會有任何一段是灰的。

```js
function tick(now){
  var ended = isEnded(now) && !REVIEW;
  document.body.classList.toggle('ended', ended);
  if(ended) return;
  if(REVIEW) now = new Date(DAY_DATES.d0116 + 'T00:00:00');   // 回到出發前
  grayPast(now);
}
```

### 5.11 即時航班資訊（選配，台灣出發適用）

- **桃園機場**有公開 API，可直接在前端 `fetch`：
  `POST https://www.taoyuan-airport.com/api/api/flight/a_flight/airlines`
  body：`{"id":"20270116_D_JX802","language":"ch"}`（日期_出發D或抵達A_航班號）
- **日本的機場官網**多半沒開 CORS，需要一支 **Cloudflare Worker** 當代理（免費額度很夠），在 Worker 裡抓 HTML、解析出 JSON 再回傳，並限制 `Access-Control-Allow-Origin` 只給自己的網域。
- 把**最後一次抓到的結果存進 `localStorage`**，開頁先顯示上次的內容，新資料回來再換掉——沒網路時也不會整片空白。
- **只在用得到的日子才打 API**：出發當天過了就不用再查去程，整趟結束後完全停掉。

### 5.12 測試用的日期切換面板

行程在幾個月後，但「今天是第幾天」的邏輯現在就要測。做一個小面板（平常隱藏，需要時才打開），選一個日期當第一天，其餘天數依序往後推：

```js
function shiftDays(first){
  var base = new Date(first+'T00:00:00');
  DAY_IDS.forEach(function(id, i){
    var d = new Date(base.getTime());
    d.setDate(d.getDate() + i);
    DAY_DATES[id] = dateStr(d);
    var a = document.querySelector('#daynav a[href="#'+id+'"]');
    if(a) a.setAttribute('data-d', DAY_DATES[id]);
  });
}
```

設定存 `localStorage`，只影響自己這台裝置。**程式裡的日期永遠放正式值**，測試不要改程式。

---

## 6. 離線支援（PWA）

### manifest.webmanifest

```json
{
  "name": "斑尾滑雪 × 東京",
  "short_name": "斑尾滑雪",
  "start_url": "./",
  "scope": "./",
  "display": "standalone",
  "background_color": "#fcfbf7",
  "theme_color": "#fcfbf7",
  "icons": [
    { "src": "icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}
```

`index.html` 的 `<head>` 要加：

```html
<link rel="manifest" href="manifest.webmanifest">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="斑尾滑雪">
```

### sw.js 的快取策略

| 資源 | 策略 | 理由 |
|---|---|---|
| 網頁本身 | **先連網，失敗才用快取** | 內容永遠是最新的，離線時還有得看 |
| 圖片 | **快取優先** | 菜單、地圖不會變，省流量又快 |
| 跨網域 API | **完全不攔** | 即時資料本來就該失敗就失敗 |

```js
const CACHE = 'trip-v1';
const PRECACHE = ['./', 'index.html', 'manifest.webmanifest', 'icon-192.png', /* 所有 *.webp */];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE)
    .then((c) => Promise.allSettled(PRECACHE.map((u) => c.add(u))))   // 單一檔案失敗不要整批掛掉
    .then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys()
    .then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if(req.method !== 'GET') return;
  const url = new URL(req.url);
  if(url.origin !== location.origin) return;                 // 跨網域不攔

  if(/\.(webp|png|jpg|pdf)$/i.test(url.pathname)){           // 圖片：快取優先
    e.respondWith(caches.match(req).then((hit) => hit || fetch(req).then((res) => save(req, res))));
    return;
  }
  e.respondWith(fetch(req).then((res) => save(req, res))      // 其他：先連網
    .catch(() => caches.match(req).then((hit) => hit || caches.match('index.html'))));
});
```

註冊：

```js
if('serviceWorker' in navigator){
  window.addEventListener('load', function(){
    navigator.serviceWorker.register('sw.js')['catch'](function(){});
  });
}
```

### 圖片一定要壓

手機在國外用行動網路點開 2MB 的菜單照片是災難。用 Python + Pillow 批次轉 WebP（長邊上限 2000、quality 82），實測 **24MB → 3MB**，文字清晰度看不出差別：

```python
from PIL import Image
im = Image.open(src)
if max(im.size) > 2000:
    r = 2000 / max(im.size)
    im = im.resize((round(im.width*r), round(im.height*r)), Image.LANCZOS)
im.save(dst, 'WEBP', quality=82, method=6)
```

---

## 7. 部署到 GitHub Pages

1. 建一個 repo（公開或私有都可以，Pages 需要公開或付費方案）。
2. 把檔案放在根目錄，push 到 `main`。
3. Settings → Pages → Source 選 `Deploy from a branch` → `main` / `(root)`。
4. 網址是 `https://<帳號>.github.io/<repo>/`。
5. push 之後大約 **1~3 分鐘**生效。

**驗證部署有沒有生效的小技巧**：用這次改動才有的獨特字串輪詢，比盲等可靠：

```bash
for i in $(seq 1 40); do
  if curl -s https://你的網址/ | grep -q "這次新增的字串"; then echo "deployed"; exit 0; fi
  sleep 10
done
```

---

## 8. 踩過的坑（請務必注意）

1. **`</` 要逸出**：內嵌 JSON 裡的 `</a>` 會提早關掉 `<script>`，一律寫成 `<\/a>`。
2. **別去 parse 畫面文字**：時刻放在 `data-t` / `data-e`，顯示文字之後一定會改。
3. **手機會凍結背景分頁的計時器**：見 5.4，要多路喚醒。
4. **`indeterminate` 不能用 `preventDefault()` 還原**：見 5.5，改在 `change` 處理。
5. **全站 `scroll-behavior:smooth` 會影響程式捲動**：程式要「瞬間」捲回原位時，明確指定 `behavior:'instant'`。
6. **重新渲染會洗掉狀態**：灰階、選項、快取內容都要在 `MutationObserver`（監聽 `.tl` 的 `childList`）後重新套用。
7. **自動捲動要留逃生門**：使用者從分享連結進來、或正在看別天時，不要硬把畫面拉走。
8. **深色模式下「半透明疊色」要實測**：卡片本身有底色時，閃爍動畫改背景色幾乎看不出來，改閃外框或提高不透明度。
9. **GitHub Pages 的檔名**：中文、空格的檔名可以用，但連結要 URL-encode。

---

## 9. 建議的開發順序

1. 先把**資料結構**定好，塞 2~3 天的真實行程。
2. 做**渲染 + 樣式**，手機寬度（375px）優先看。
3. 加**日期列**與**灰階邏輯**（最有感的功能）。
4. 加**行前清單**。
5. 丟上 **GitHub Pages**，用手機實際看一次。
6. 再加 **PWA 離線**、分享連結、即時資訊等加分項。

> 一個建議：**行程資料用腳本改，不要手改 HTML**。寫一支小 Python（讀出 `trip-data` 的 JSON → 改 → 寫回），之後請 AI 幫你調整行程時會穩定非常多。
