// 成田機場航班資料代理（Cloudflare Worker）
// 用途：成田官網不開放跨域（CORS），由這支 Worker 代抓航班頁並只回傳需要的 JSON。
// 部署：Cloudflare Dashboard → Workers → 貼上本檔 → Deploy
// 呼叫方式：GET https://<worker網址>/?type=arr&id=20270116-JX0802
//           GET https://<worker網址>/?type=dep&id=20270123-JX0803

// 只允許這個網站呼叫
const ALLOWED_ORIGIN = "https://lu4511760.github.io";

export default {
  async fetch(request) {
    const cors = {
      "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
      "Cache-Control": "no-store",
    };

    const url = new URL(request.url);
    const type = url.searchParams.get("type"); // arr（到達）或 dep（出發）
    const id = url.searchParams.get("id");     // 例：20270116-JX0802

    // 嚴格驗證參數，避免被當成萬用代理濫用
    if (!/^(arr|dep)$/.test(type || "") || !/^\d{8}-[A-Z]{2}\d{4}$/.test(id || "")) {
      return new Response(JSON.stringify({ error: "bad params" }), {
        status: 400,
        headers: { ...cors, "Content-Type": "application/json" },
      });
    }

    const target = `https://www.narita-airport.jp/zh-tc/flight/${type}-search/${id}/`;

    // cacheTtl 30 秒：多人/多次重整共用快取，對成田官網禮貌一點
    const resp = await fetch(target, {
      cf: { cacheTtl: 30, cacheEverything: true },
      headers: { "User-Agent": "Mozilla/5.0 (travel-site personal use)" },
    });

    if (!resp.ok) {
      return new Response(JSON.stringify({ error: "narita " + resp.status }), {
        status: 502,
        headers: { ...cors, "Content-Type": "application/json" },
      });
    }

    const html = await resp.text();
    // 成田官網是 Next.js，航班資料都在 __NEXT_DATA__ 這段 JSON 裡
    const m = html.match(/__NEXT_DATA__" type="application\/json">(.+?)<\/script>/s);
    if (!m) {
      return new Response(JSON.stringify({ error: "parse fail" }), {
        status: 502,
        headers: { ...cors, "Content-Type": "application/json" },
      });
    }

    const data = JSON.parse(m[1]);
    const p = (data.props && data.props.pageProps) || {};
    // 只回傳航班本體與安檢/入境擁擠度，其餘（翻譯字串、商店推薦等）全部丟掉
    const out = { flight: p.flight || null, flightSecurity: p.flightSecurity || [] };

    return new Response(JSON.stringify(out), {
      headers: { ...cors, "Content-Type": "application/json; charset=utf-8" },
    });
  },
};
