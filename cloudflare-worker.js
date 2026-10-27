// 日本行程網站的後端 Worker（Cloudflare）
//
// 兩個用途：
//   1. 成田機場航班資料代理 —— 成田官網不開放跨域（CORS），由這支代抓並只回傳需要的 JSON
//        GET /?type=arr&id=20270116-JX0802
//        GET /?type=dep&id=20270123-JX0803
//        GET /?type=imm                      ← 入境審查各查驗處等待時間
//   2. 行程修改的雲端儲存 —— 讓手機在解鎖後可以改行程，存在 Workers KV
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
    return handleNarita(url);
  },
};
