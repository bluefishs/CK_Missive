/**
 * RWD 手機品質探針（weekly 111 的量測端；判定在 rwd_mobile_quality_gate.py）
 *
 * owner 2026-09-05：「加強視覺檢核機制，確保 RWD 設計正確性」。
 * 既有的 mobile_probe 只量「整頁有沒有被撐寬」；視覺走查拍圖但要人看。
 * 中間缺的是「人看圖會抱怨、而斷言量得出來」的那幾件事——這支就量那幾件：
 *
 *   clipped     文字被硬截（scrollWidth > clientWidth 且不是刻意的 ellipsis）——存在 ≠ 看得懂
 *   tinyFont    可見文字 font-size < 11px——手機上讀不了
 *   smallTap    可點元素高或寬 < 28px——手指點不到（WCAG 建議 44，AntD small 是 24，先抓 < 28）
 *   covered     position:fixed 的浮動元件（坤哥鈕、倒數徽章）壓在可點元素上 ≥ 40% 面積——「功能遮蔽」
 *   loneCard    統計卡（含 .ant-statistic 的 .ant-col）寬度 ≥ 70% 視窗且同頁有 ≥ 2 張——§2.6 ① 手機兩張一列
 *
 * 不動 `.shared-selfaudit/`（vendored，改了 sync-vendored 會 DRIFT）；登入態沿用它的 _bootstrap.applyAuth
 * （COOKIE／USER_INFO 由閘門用 adapter 簽好放進 env，不印值）。
 *
 * 用法：node rwd_mobile_quality_probe.cjs [--routes=a,b] [--width=390] [--out=path.json]
 * 輸出：JSON（預設 wiki/memory/integration-health/rwd-quality.json）
 */
const fs = require('fs');
const path = require('path');
const boot = require('./.shared-selfaudit/_bootstrap.cjs');

const { CONFIG, ROOT } = boot.loadConfig('sweep', path.join(__dirname, '.shared-selfaudit'));
const PW = boot.resolvePlaywright(ROOT);
const BASE = process.env.SMOKE_BASE || CONFIG.base_url;

function arg(name, dflt) {
  const p = `--${name}=`;
  const f = process.argv.find((a) => a.startsWith(p));
  return f ? f.slice(p.length) : dflt;
}

function resolveRoutes() {
  const a = arg('routes', '');
  if (a) return a.split(',').map((x) => x.trim()).filter(Boolean).map((x) => (x.startsWith('/') ? x : '/' + x));
  const MP = (CONFIG.page_sweep && CONFIG.page_sweep.mobile_probe) || {};
  return [...(MP.routes || []), ...(MP.detail_routes || [])].filter((r) => !/^\/(entry|login)$/.test(r));
}

const WIDTH = Number(arg('width', 390));
const OUT = path.resolve(ROOT, arg('out', path.join('wiki', 'memory', 'integration-health', 'rwd-quality.json')));

// 在頁面裡跑的量測：只回傳數字與前幾個定位，不回傳整棵 DOM
function measure(vw) {
  const vis = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return false;
    const cs = getComputedStyle(el);
    return cs.visibility !== 'hidden' && cs.display !== 'none' && Number(cs.opacity) !== 0;
  };
  const sel = (el) => el.tagName.toLowerCase()
    + (el.id ? '#' + el.id : '')
    + (typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : '');
  const txt = (el) => (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 24);
  const all = [...document.querySelectorAll('body *')];

  // clipped：有自己的文字、被 overflow hidden 硬截、而且不是 ellipsis（ellipsis 是設計，另計）
  const clipped = []; let ellipsis = 0;
  for (const el of all) {
    if (!vis(el)) continue;
    const ownText = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
    if (!ownText) continue;
    if (el.scrollWidth <= el.clientWidth + 2) continue;
    const cs = getComputedStyle(el);
    if (cs.overflowX !== 'hidden' && cs.overflow !== 'hidden') continue;
    if (cs.textOverflow === 'ellipsis') { ellipsis += 1; continue; }
    if (el.closest('.ant-table-cell, .ant-select-selection-item')) continue;   // 表格格與 Select 值本來就會截
    clipped.push({ sel: sel(el), text: txt(el), over: el.scrollWidth - el.clientWidth });
  }

  // tinyFont
  const tiny = [];
  for (const el of all) {
    if (!vis(el)) continue;
    const ownText = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
    if (!ownText) continue;
    const fs = parseFloat(getComputedStyle(el).fontSize);
    if (fs && fs < 11) tiny.push({ sel: sel(el), text: txt(el), px: Math.round(fs * 10) / 10 });
  }

  // smallTap：可點元素（排除隱形 input 與圖示本體）
  const ctrlSel = 'a[href], button, [role="button"], input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]), select, textarea, .ant-select, .ant-switch, .ant-tabs-tab, .ant-pagination-item';
  const ctrls = [...document.querySelectorAll(ctrlSel)].filter(vis);
  const small = [];
  for (const el of ctrls) {
    if (el.closest('.ant-table-thead')) continue;                  // 表頭漏斗／排序圖示本來就小
    if (el.matches('.ant-checkbox-input, .ant-radio-input')) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 28 || r.height < 28) small.push({ sel: sel(el), text: txt(el), w: Math.round(r.width), h: Math.round(r.height) });
  }

  // covered：fixed 元件壓住可點元素
  const fixed = all.filter((el) => vis(el) && getComputedStyle(el).position === 'fixed' && !el.closest('.ant-layout-header, .ant-drawer, .ant-modal, .ant-message, .ant-notification'));
  const covered = [];
  for (const f of fixed) {
    const fr = f.getBoundingClientRect();
    if (fr.width > vw * 0.9) continue;                              // 整幅的 fixed（遮罩、底欄）不算
    for (const el of ctrls) {
      if (f.contains(el) || el.contains(f)) continue;
      const r = el.getBoundingClientRect();
      const ix = Math.max(0, Math.min(fr.right, r.right) - Math.max(fr.left, r.left));
      const iy = Math.max(0, Math.min(fr.bottom, r.bottom) - Math.max(fr.top, r.top));
      const cover = (ix * iy) / Math.max(1, r.width * r.height);
      if (cover < 0.4) continue;
      // 任何 fixed 鈕在任何捲動位置都會壓到「某個東西」；真正的遮蔽是**捲動也躲不開**的那種：
      // 把目標捲到視窗中央後仍與 fixed 元件重疊（頁面太短捲不動、或目標本身在底部貼邊）。
      // 09-05 第二跑：/erp/operational 的分頁鈕在初始捲動位置被坤哥鈕壓 75%，但往下捲 300px 就分開——那不算遮蔽。
      const maxScroll = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
      const wantY = window.scrollY + r.top - window.innerHeight / 2;
      const reachY = Math.min(maxScroll, Math.max(0, wantY));
      const topAfter = r.top - (reachY - window.scrollY);
      const iyAfter = Math.max(0, Math.min(fr.bottom, topAfter + r.height) - Math.max(fr.top, topAfter));
      const coverAfter = (ix * iyAfter) / Math.max(1, r.width * r.height);
      if (coverAfter >= 0.4) covered.push({ fixed: sel(f), target: sel(el), text: txt(el), cover: Math.round(cover * 100), afterScroll: Math.round(coverAfter * 100) });
    }
  }

  // loneCard：統計卡獨佔一列
  // 只看**最內層**的 col：外層容器 col 也含統計卡，會把「兩張一列」的頁面誤判成獨列（09-05 首跑行事曆就是這樣）
  const statSel = '.ant-statistic, .ck-stat-card, [class*="StatCard"]';
  const statCols = [...document.querySelectorAll('.ant-col')].filter((c) => vis(c) && c.querySelector(statSel)
    && ![...c.querySelectorAll('.ant-col')].some((inner) => inner.querySelector(statSel)));
  const lone = statCols.filter((c) => c.getBoundingClientRect().width >= vw * 0.7).map((c) => ({ sel: sel(c), text: txt(c.querySelector('.ant-statistic-title') || c) }));

  return {
    clipped: clipped.length, clippedTop: clipped.slice(0, 5), ellipsis,
    tinyFont: tiny.length, tinyTop: tiny.slice(0, 5),
    smallTap: small.length, smallTop: small.slice(0, 5),
    covered: covered.length, coveredTop: covered.slice(0, 5),
    loneCard: statCols.length >= 2 ? lone.length : 0, loneTop: lone.slice(0, 4), statCards: statCols.length,
    controls: ctrls.length,
  };
}

async function main() {
  if (!PW || !PW.exe) boot.fail(boot.playwrightMissingMessage());
  const routes = resolveRoutes();
  boot.assertNonEmpty(routes.length, '手機品質探針路由', '請在 selfaudit.config.json 設 page_sweep.mobile_probe.routes，或以 --routes= 指定');
  const browser = await PW.chromium.launch({ executablePath: PW.exe, headless: true });
  // 純 viewport、不設 isMobile（同 mobile_probe 的理由：isMobile 會 shrink-to-fit 把量測變假綠）
  const ctx = await browser.newContext({ viewport: { width: WIDTH, height: 844 }, hasTouch: true });
  await boot.applyAuth(ctx, CONFIG, BASE);
  const rows = [];
  let blocked = 0;
  for (const route of routes) {
    const page = await ctx.newPage();
    try {
      await page.goto(BASE + route, { waitUntil: 'domcontentloaded', timeout: 30000 });
      // 等資料進來再量（與 mobile_probe 刻意量 2.2 秒不同：這裡要的是穩定後的畫面，跳版由那支負責）
      await page.waitForTimeout(4000);
      if (/\/entry|\/login/.test(page.url())) { blocked += 1; rows.push({ route, blocked: true }); await page.close(); continue; }
      const m = await page.evaluate(measure, WIDTH);
      rows.push({ route, width: WIDTH, ...m });
    } catch (e) {
      rows.push({ route, error: String(e).slice(0, 100) });
    }
    await page.close();
  }
  await ctx.close();
  await browser.close();
  const out = { checked_at: new Date().toISOString(), base: BASE, width: WIDTH, routes: routes.length, blocked, rows };
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(out, null, 2));
  const sum = (k) => rows.reduce((a, r) => a + (r[k] || 0), 0);
  console.log(`RWD 手機品質探針：${routes.length} 頁 @${WIDTH}px（被導回登入 ${blocked}）`);
  console.log(`  截字 ${sum('clipped')}／字級<11px ${sum('tinyFont')}／點擊目標<28px ${sum('smallTap')}／被浮動元件遮住 ${sum('covered')}／統計卡獨佔一列 ${sum('loneCard')}`);
  console.log(`  結果 → ${OUT}`);
}

main().catch((e) => { console.error(e); process.exit(2); });
