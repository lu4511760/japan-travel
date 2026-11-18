// 日本行程網站的後端 Worker（Cloudflare）
//
// 用途：
//   1. 成田機場航班資料代理 —— 成田官網不開放跨域（CORS），由這支代抓並只回傳需要的 JSON
//        GET /?type=arr&id=20270116-JX0802
//        GET /?type=dep&id=20270123-JX0803
//        GET /?type=imm                      ← 入境審查各查驗處等待時間
//   2. 斑尾雪場即時雪況代理 —— tangram.jp 同樣不開放跨域，由這支代抓並解析官網那塊面板
//        GET /snow                           ← 天氣、氣溫、雪質、積雪、纜車運行
//   3. 斑尾雪場直播代理 —— 官方會不定期重開直播、影片 ID 跟著變，由這支去查現在正在播的那兩支
//        GET /live                           ← 野尻湖テラス、ホテルタングラム 的現役影片 ID
//   4. 公路客運即時動態代理 —— taiwanbus.tw 不開放跨域，由這支代抓某條路線某個方向的各站動態
//        GET /bus?key=196801                 ← key 是 路線編號＋方向（6 位數字，見 handleBus 說明）
//   5. 行程修改的雲端儲存 —— 讓手機在解鎖後可以改行程，存在 Workers KV
//        GET  /data                          ← 任何人都可讀（朋友才看得到你的更新）
//        GET  /data?prev=1                   ← 上一版備份（寫入前自動留的，還原用）
//        POST /data  + X-Edit-Token          ← 只有帶正確權杖才能寫
//
// 部署前需在 Cloudflare 後台設定：
//   · KV 命名空間，變數名稱綁定為  TRIP
//   · Secret（機密變數）           EDIT_TOKEN
// 兩者都設好後，把本檔貼上 Worker 編輯器 → Deploy。

const ALLOWED_ORIGIN = "https://lu4511760.github.io";
const KV_KEY = "trip-edits";
const KV_PREV = "trip-edits-prev";   // 上一版備份：誤刪或蓋掉時可以還原

const cors = (extra = {}) => ({
  "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
  "Cache-Control": "no-store",
  ...extra,
});

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: cors({ "Content-Type": "application/json; charset=utf-8" }),
  });

// 比對權杖時不要因為長度/提早不符而洩漏資訊
function tokenMatches(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

// ── 行程修改的讀寫 ────────────────────────────────────────
async function handleData(request, env) {
  if (!env.TRIP) return json({ error: "KV 未綁定（請在 Cloudflare 綁定 TRIP）" }, 500);

  if (request.method === "GET") {
    // /data?prev=1 讀上一版備份（手動還原用）
    const key = new URL(request.url).searchParams.get("prev") ? KV_PREV : KV_KEY;
    const saved = await env.TRIP.get(key);
    return json(saved ? JSON.parse(saved) : { pub: null, priv: null, at: null });
  }

  if (request.method === "POST") {
    if (!env.EDIT_TOKEN) return json({ error: "EDIT_TOKEN 未設定" }, 500);
    if (!tokenMatches(request.headers.get("X-Edit-Token") || "", env.EDIT_TOKEN)) {
      return json({ error: "unauthorized" }, 401);
    }
    let body;
    try {
      body = await request.json();
    } catch (e) {
      return json({ error: "bad json" }, 400);
    }
    // pub：公開行程的修改（明文）；priv：私人行程（瀏覽器端已先加密，這裡看不到內容）
    const doc = {
      pub: body.pub ?? null,
      priv: body.priv ?? null,
      at: new Date().toISOString(),
    };
    const text = JSON.stringify(doc);
    if (text.length > 512 * 1024) return json({ error: "too large" }, 413);
    // 覆寫之前先把目前這版留一份，改壞了還有得救
    const before = await env.TRIP.get(KV_KEY);
    if (before) await env.TRIP.put(KV_PREV, before);
    await env.TRIP.put(KV_KEY, text);
    return json({ ok: true, at: doc.at });
  }

  return json({ error: "method not allowed" }, 405);
}

// ── 成田官網代理 ─────────────────────────────────────────
async function handleNarita(url) {
  const type = url.searchParams.get("type");
  const id = url.searchParams.get("id");
  const isImm = type === "imm";

  // 嚴格驗證參數，避免被當成萬用代理濫用
  if (!isImm && (!/^(arr|dep)$/.test(type || "") || !/^\d{8}-[A-Z]{2}\d{4}$/.test(id || ""))) {
    return json({ error: "bad params" }, 400);
  }

  const target = isImm
    ? "https://www.narita-airport.jp/zh-tc/airportguide/inter-arr/immigration/"
    : `https://www.narita-airport.jp/zh-tc/flight/${type}-search/${id}/`;

  // cacheTtl 30 秒：多次重整共用快取，對成田官網禮貌一點
  const resp = await fetch(target, {
    cf: { cacheTtl: 30, cacheEverything: true },
    headers: { "User-Agent": "Mozilla/5.0 (travel-site personal use)" },
  });
  if (!resp.ok) return json({ error: "narita " + resp.status }, 502);

  const html = await resp.text();
  // 成田官網是 Next.js，航班資料都在 __NEXT_DATA__ 這段 JSON 裡
  const m = html.match(/__NEXT_DATA__" type="application\/json">(.+?)<\/script>/s);
  if (!m) return json({ error: "parse fail" }, 502);

  const p = (JSON.parse(m[1]).props || {}).pageProps || {};
  if (isImm) {
    // 入境審查各查驗處：名稱、營運時間、日本人通道/外國旅客通道的等待時間
    return json({
      immigration: ((p.pfmDetail && p.pfmDetail.securityDetails) || []).map((s) => ({
        name: s.fullName || s.name,
        terminal: s.location && s.location.terminalKey,
        hours: s.businessHour,
        jp: s.congestion && s.congestion.text,
        abroad: s.congestionAbroad && s.congestionAbroad.text,
      })),
    });
  }
  return json({ flight: p.flight || null, flightSecurity: p.flightSecurity || [] });
}

// ── 斑尾雪場雪況代理 ───────────────────────────────────────
// tangram.jp 的雪況是伺服器直接印在 HTML 裡的（沒有 JSON API），所以只能照著版型撈。
// 官網改版就會撈不到，因此每個欄位各自判斷，撈不到的就回 null，前端顯示「—」，不會整塊掛掉。
async function handleSnow() {
  // cacheTtl 300 秒：官網那塊一天也才更新幾次，不需要每個人每次都去敲它
  const resp = await fetch("https://www.tangram.jp/ski/", {
    cf: { cacheTtl: 300, cacheEverything: true },
    headers: { "User-Agent": "Mozilla/5.0 (travel-site personal use)" },
  });
  if (!resp.ok) return json({ error: "tangram " + resp.status }, 502);
  const html = await resp.text();

  const pick = (re, i = 1) => {
    const m = html.match(re);
    return m ? m[i].trim() : null;
  };
  // 表格列：<th>気温</th> <td><strong>7</strong>℃</td>
  // 注意這裡是用字串組正則（欄位名是變數），字串裡的反斜線要寫兩個，寫一個會被 JS 吃掉。
  const cell = (label) =>
    pick(new RegExp(label + "\\s*</th>\\s*<td[^>]*>\\s*(?:<strong>)?([^<]*)", "i"));

  const liftM = html.match(/class="cdLift"[\s\S]{0,200}?<strong>(\d+)<\/strong>\s*\/\s*(\d+)/i);

  return json({
    // 官網自己標的更新時刻（日本時間），例如 "2026.03.29 18:57"
    at: pick(/CONDITION_<span>([\d.]+\s+[\d:]+)\s*現在/),
    // 天氣用圖示的 alt 取，比抓 <p> 穩（<p> 在那塊裡有好幾個）
    weather: pick(/icon_weather_\w+\.png"\s+alt="([^"]+)"/),
    temp: cell("気温"),      // 攝氏，字串（可能是負數）
    quality: cell("雪質"),   // 日文雪質，前端自己對照成中文
    depth: cell("積雪"),     // 公分
    lift: liftM ? { open: Number(liftM[1]), total: Number(liftM[2]) } : null,
  });
}

// ── 斑尾雪場直播代理 ───────────────────────────────────────
// 官方（@TangramMadarao）會不定期把 24 小時直播重開，一重開影片 ID 就換、舊的嵌入畫面變黑。
// 這支去頻道的直播清單抓現在正在播的那兩支，前端照它回的 ID 嵌入，就不必每次手改。
//
// 怎麼判斷「正在播」：清單頁同時列著已結束的場次，而且頁面上沒有可靠的直播標記。
// 但 oEmbed 的回應分得很乾淨 —— 正在播的會回完整欄位（title、author_name、thumbnail_url…），
// 已結束的只回 html/provider/type/version 這幾個。所以用「有沒有 title」來篩。
// 這是觀察出來的行為、不是官方文件保證，所以查不到時一律回 null，
// 前端會留著網頁裡原本寫死的那組 ID（也就是退回到人工維護的狀態），不會變成空白。
async function handleLive() {
  const resp = await fetch("https://www.youtube.com/@TangramMadarao/streams", {
    cf: { cacheTtl: 1800, cacheEverything: true },   // 直播 ID 幾天才換一次，半小時問一次夠了
    headers: { "User-Agent": "Mozilla/5.0 (travel-site personal use)" },
  });
  if (!resp.ok) return json({ error: "youtube " + resp.status }, 502);
  const html = await resp.text();

  // 清單頁裡同一支會出現很多次，去重；只看前幾支，避免頻道哪天影片變多時打太多次 oEmbed
  const ids = [...new Set((html.match(/"videoId":"[\w-]{11}"/g) || []).map((m) => m.slice(11, -1)))].slice(0, 6);

  const infos = await Promise.all(
    ids.map(async (id) => {
      try {
        const r = await fetch(
          "https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=" + id + "&format=json",
          { cf: { cacheTtl: 1800, cacheEverything: true } }
        );
        if (!r.ok) return null;
        const d = await r.json();
        return d && d.title ? { id, title: d.title } : null;   // 沒有 title 就是已經不播了
      } catch (e) {
        return null;
      }
    })
  );

  const live = infos.filter(Boolean);
  const pick = (kw) => live.find((v) => v.title.includes(kw)) || null;
  return json({
    nojiri: pick("野尻湖"),              // 野尻湖テラス LIVE
    hotel: pick("ホテルタングラム"),      // ホテルタングラム LIVE
    checked: ids.length,
  });
}

// ── 公路客運即時動態代理 ─────────────────────────────────────
// 公路客運的「動態資訊」頁（taiwanbus.tw/eBUSPage/Query/QueryResult.aspx?rno=…）背後
// 是用 getRData.ashx?type=4&key=… 拿 JSON。key 是頁面裡 _ROUTES 的值：路線編號（含支線碼）＋方向，
// 例如 rno=19680 的頁面 _ROUTES 是 '196801,196802'，01 是去程、02 是返程。
// 這是從官網頁面原始碼看來的、不是公開 API，官網改版就可能失效；失效時前端會顯示讀不到。
//
// 回傳只留前端要的：各站（依行駛順序）站名、狀態文字（「8分」「進站中」「21:18」「05:40發車」…）、
// 正開往該站的車牌（沒有就是空字串）。
async function handleBus(url) {
  const key = url.searchParams.get("key") || "";
  if (!/^\d{6}$/.test(key)) return json({ error: "bad params" }, 400);   // 只接受 6 位數字，不當萬用代理

  const resp = await fetch(
    "https://www.taiwanbus.tw/eBUSPage/Query/ws/getRData.ashx?type=4&key=" + key,
    {
      cf: { cacheTtl: 15, cacheEverything: true },   // 官網大約 20～30 秒更新一次，15 秒內共用
      headers: { "User-Agent": "Mozilla/5.0 (travel-site personal use)" },
    }
  );
  if (!resp.ok) return json({ error: "taiwanbus " + resp.status }, 502);
  let d;
  try {
    d = JSON.parse((await resp.text()).replace(/^﻿/, ""));
  } catch (e) {
    return json({ error: "parse fail" }, 502);
  }
  if (!d || !Array.isArray(d.data)) return json({ error: "parse fail" }, 502);

  return json({
    time: d.time || null,            // 官網資料時間（台灣時間 HH:MM:SS）
    stops: d.data.map((r) => ({ na: r.na || "", ptime: r.ptime || "", car: r.car || "" })),
  });
}

export default {
  async fetch(request, env) {
    // 瀏覽器寫入前會先送出 preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: cors({
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type, X-Edit-Token",
          "Access-Control-Max-Age": "86400",
        }),
      });
    }

    const url = new URL(request.url);
    if (url.pathname === "/data") return handleData(request, env);
    if (url.pathname === "/snow") return handleSnow();
    if (url.pathname === "/live") return handleLive();
    if (url.pathname === "/bus") return handleBus(url);
    return handleNarita(url);
  },
};
