/**
 * 路由 API 成本探針（2026-09-05，lvrland 跨 session 知會後建）
 *
 * 量每條路由「載入時打了哪些 API、各花多久、有沒有同體重複」。兩種模式：
 *   冷載入（預設）：page.goto 整頁重載——含 layout 級查詢（nav／csrf／auth／unread…）
 *   暖切換（WARM=1）：pushState＋popstate 讓 react-router 換頁——React Query 快取生效後真正每頁要付的
 *
 * 登入態沿用 selfaudit adapter（COOKIE／USER_INFO 由呼叫端放進 env，同 rwd_mobile_quality_gate._mint_credential）。
 * 09-05 基準：colo=SJC，每支 API 固定多 ~0.55s 往返；冷 8–15 支、暖 0–7 支；後端真實耗時多在 15–75ms，
 * 唯一慢的是 ai/digital-twin/dashboard 冷 4.2s（已加 60s 快取）。
 *
 * 用法：node scripts/perf/route_cost_probe.cjs "/documents,/contract-cases"   （輸出一行 JSON）
 *       WARM=1 node scripts/perf/route_cost_probe.cjs "/documents,/erp/quotations"
 * 量測口徑（與平台數字對照時要先對齊）：每支 API 的 ms 是瀏覽器 request→response 事件的 wall，連線復用、
 * 幾乎不含 TLS 握手、含回應體；平台 §72 的 0.40s 是 curl TTFB、我另報的 0.56s 是新連線 curl time_total（含握手）。
 * 三把尺量的不是同一段，相減沒有意義。
 * 這不是閘門（沒有退出碼判準）——是給人看數字的量測；要做成閘門先定基線。
 */
const boot = require('../checks/.shared-selfaudit/_bootstrap.cjs');
const { CONFIG, ROOT } = boot.loadConfig('sweep', require('path').join(__dirname, '..', 'checks', '.shared-selfaudit'));
const PW = boot.resolvePlaywright(ROOT);
const routes = process.argv[2].split(',');
(async () => {
  const b = await PW.chromium.launch({ executablePath: PW.exe, headless: true });
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  await boot.applyAuth(ctx, CONFIG, CONFIG.base_url);
  const p = await ctx.newPage();
  await p.goto(CONFIG.base_url + '/dashboard', { waitUntil: 'networkidle' }).catch(() => {});
  const out = {};
  for (const route of routes) {
    const reqs = [];
    const onReq = (r) => { if (r.url().includes('/api/')) reqs.push({ url: r.url().replace(CONFIG.base_url, ''), method: r.method(), t0: Date.now(), body: (r.postData() || '').slice(0, 80) }); };
    const onRes = (res) => { const q = reqs.find((x) => !x.done && x.url === res.url().replace(CONFIG.base_url, '') && x.method === res.request().method()); if (q) { q.done = true; q.ms = Date.now() - q.t0; q.status = res.status(); } };
    p.on('request', onReq); p.on('response', onRes);
    const t = Date.now();
    if (process.env.WARM === '1') {
      // SPA 暖切換：pushState + popstate 讓 react-router 換頁，不重載整頁（layout 級的查詢若有快取就不會再打）
      await p.evaluate((r) => { window.history.pushState(null, '', r); window.dispatchEvent(new PopStateEvent('popstate')); }, route);
      await p.waitForLoadState('networkidle', { timeout: 45000 }).catch(() => {});
      await p.waitForTimeout(800);
    } else {
      await p.goto(CONFIG.base_url + route, { waitUntil: 'networkidle', timeout: 45000 }).catch((e) => { reqs.push({ url: 'ERR ' + String(e).slice(0, 60) }); });
    }
    const wall = Date.now() - t;
    p.off('request', onReq); p.off('response', onRes);
    const byUrl = {};
    for (const r of reqs) { const k = `${r.method} ${r.url.split('?')[0]}`; byUrl[k] = byUrl[k] || { n: 0, ms: 0, max: 0, bodies: new Set() }; byUrl[k].n++; byUrl[k].ms += r.ms || 0; byUrl[k].max = Math.max(byUrl[k].max, r.ms || 0); byUrl[k].bodies.add(r.body || ''); }
    const rows = Object.entries(byUrl).map(([k, v]) => ({ k, n: v.n, dupSameBody: v.n - v.bodies.size, max: v.max })).sort((a, b) => b.max - a.max);
    out[route] = { wall, calls: reqs.length, distinct: rows.length, dupSameBody: rows.reduce((a, r) => a + r.dupSameBody, 0), slow: rows.slice(0, 4), multi: rows.filter((r) => r.n > 1).map((r) => `${r.k}×${r.n}`) };
  }
  await b.close();
  console.log(JSON.stringify(out));
})();
