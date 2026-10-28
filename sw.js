// 離線支援：把行程頁與圖片存在手機上，到日本沒網路也打得開
//
// · 網頁本身與加密的私人行程：先連網，連不到才用存下來的版本（內容才會是最新的）
// · 圖片：直接用存下來的，省流量也快
// · 航班 API、雲端修改（跨網域）：完全不攔，沒網路時由頁面自己處理
//
// 這支檔案由 scripts/build_sw.py 產生，不要直接改；新增圖片後重跑它。

const CACHE = 'japan2027-v1';

// 安裝時就先抓好的檔案（第一次開頁、有網路時完成）
const PRECACHE = [
  './',
  'index.html',
  'private.enc',
  'manifest.webmanifest',
  'favicon-32.png',
  'icon-192.png',
  'icon-512.png',
  'apple-touch-icon.png',
  'Madarao Map & Guide.webp',
  'Manriki Spice Ramen Akihabara Menu ZH.webp',
  'iiyama-express2025.webp',
  'めし処 ぶたや Menu ZH.webp',
  '姫豚丼＆カレー 姫軒 Menu ZH.webp',
  '拉麵 潮 Menu ZH.webp',
  '東池袋大勝軒 本店 Menu ZH.webp',
  '焼肉力丸 池袋東口店 Menu ZH.webp',
  '狐狸屋牛丼 Menu ZH.webp',
  '若葉拉麵 Menu ZH.webp',
  '蔵仕込みらーめん KURA Menu ZH.webp',
  '退稅步驟.webp',
  '麦さと屋 Menu ZH.webp',
  '麵屋海神 Menu ZH.webp',
  '黑銀鮪屋 Menu ZH.webp'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE)
      // 單一檔案失敗不要讓整批安裝失敗
      .then((c) => Promise.allSettled(PRECACHE.map((u) => c.add(u))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function save(req, res) {
  if (res && res.ok && res.type === 'basic') {
    const copy = res.clone();
    caches.open(CACHE).then((c) => c.put(req, copy));
  }
  return res;
}

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;     // 跨網域的即時資料不經過這裡

  // 圖片：存下來的優先
  if (/\.(webp|png|jpg|jpeg|pdf)$/i.test(url.pathname)) {
    e.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => save(req, res)))
    );
    return;
  }

  // 其他（網頁、private.enc…）：先連網，失敗才用存下來的
  e.respondWith(
    fetch(req)
      .then((res) => save(req, res))
      .catch(() => caches.match(req).then((hit) => hit || caches.match('index.html')))
  );
});
