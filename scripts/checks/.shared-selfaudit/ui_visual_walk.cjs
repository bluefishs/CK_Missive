/**
 * 視覺走查（Visual Walk）— 2026-08-05
 *
 * ## 為什麼需要這一支
 *
 * 既有兩支引擎都是**斷言式**：元素在不在、數量夠不夠、文字有沒有出現。
 * 它們抓不到「斷言全過但畫面是錯的」——而那正是使用者實際會抱怨的那一類：
 *
 *   · 2026-08-04 我們自己踩過：表格外溢修好了，但姓名被截成兩字。
 *     textContent 完整、元素數量正確、**每一條斷言都會過**，只是人看不懂。
 *   · CK_FacilityDev 2026-07-31 首輪走查抓到的三個缺陷同一類：
 *     欄位寬度使長標籤截字／錯誤標註只寫欄位名無法對回明細／面層不透明遮蔽底圖。
 *     三者都會通過任何合理的斷言。
 *
 * 更關鍵的是：本引擎的截圖**只在 FAIL 時拍**，所以通過的頁面零視覺覆蓋。
 * 全綠的時候，我們手上一張圖都沒有。
 *
 * ## 這支不是自動判定器（重要）
 *
 * 借自 CK_FacilityDev 的做法是「程式驅動 → 逐步截圖 → **AI/人逐張判讀**」。
 * 判讀那一步沒有辦法放進 cron —— cron 裡沒有人在看。
 * 所以本引擎只負責**把圖拍齊、拍對、拍成好讀的樣子**，判讀由 session 內進行。
 *
 * 這是第三種模式，不取代任何一種：
 *   每日斷言走查（無人值守）→ 已知會壞的東西壞了
 *   視覺走查（本支，週期性）→ 沒人想到要斷言的東西
 *   真人                    → 手感、字級舒適度
 *
 * ## 紀律（否則就是一次性勞動）
 *
 * **每發現一個缺陷，必須轉成 flow 斷言**。CK_FacilityDev 的 run_tests.py 裡
 * 有三處明寫「走查修正之回歸鎖定」——走查是發現器，回歸鎖才是機制。
 *
 * 用法：
 *   node ui_visual_walk.cjs                  # 依 config 的 visual_walk 設定
 *   node ui_visual_walk.cjs --routes=/a,/b   # 臨時指定
 * 退出碼：0 拍完 / 2 未拍完（設定錯、playwright 缺、0 張）
 */
const fs = require('fs');
const path = require('path');

const boot = require('./_bootstrap.cjs');

const { CONFIG, ROOT } = boot.loadConfig('sweep', __dirname);
const PW = boot.resolvePlaywright(ROOT);
const BASE = process.env.SMOKE_BASE || CONFIG.base_url;

const VW = CONFIG.visual_walk || {};
// 預設兩個寬度：桌面與手機。單一寬度看不出 RWD 問題，而 RWD 正是視覺缺陷的大宗。
const VIEWPORTS = VW.viewports || [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
];

function todayStamp() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}`;
}

function resolveRoutes() {
  // 2026-08-07：原本用 `.split('=')[1]`，於是**任何帶 query string 的路由都會在第二個
  // `=` 被截斷** —— `/taoyuan/dispatch/2?tab=correspondence` 變成 `/taoyuan/dispatch/2?tab`，
  // 然後靜靜拍下預設分頁的截圖。看圖的人會以為自己驗過那一頁了，其實根本沒去到。
  // 這種「拍到了、但拍錯地方」比拍不到更危險。
  const prefix = '--routes=';
  const found = process.argv.find((a) => a.startsWith(prefix));
  const arg = found ? found.slice(prefix.length) : '';
  if (arg) {
    // 允許不帶前導斜線（documents,kunge）—— Git Bash 會把 `/documents` 當成
    // POSIX 路徑轉成 `C:/Program Files/Git/documents`，而 MSYS_NO_PATHCONV=1
    // 又會反過來讓入口腳本算不出 ROOT。兩邊都繞不過，不如讓參數本身不觸發轉換。
    return arg.split(',').map((x) => x.trim()).filter(Boolean)
      .map((x) => (x.startsWith('/') ? x : '/' + x));
  }
  if (Array.isArray(VW.routes) && VW.routes.length) return VW.routes;
  // 沒有專屬清單時退回廣度掃描的路由 —— 但**不是全部**：
  // 視覺走查是給人讀的，一次幾十張沒有人會看完。取樣要在 config 明講。
  const sweepRoutes = (CONFIG.page_sweep && CONFIG.page_sweep.routes) || [];
  return sweepRoutes.slice(0, VW.max_routes || 12);
}

async function main() {
  if (!PW || !PW.exe) boot.fail(boot.playwrightMissingMessage());

  const routes = resolveRoutes();
  boot.assertNonEmpty(
    routes.length, '視覺走查路由',
    '請在 selfaudit.config.json 設 visual_walk.routes，或以 --routes= 指定',
  );

  const outRoot = path.resolve(
    ROOT, VW.out_dir || path.join('docs', 'health', 'visual'), todayStamp(),
  );
  fs.mkdirSync(outRoot, { recursive: true });

  const browser = await PW.chromium.launch({ executablePath: PW.exe, headless: true });
  const shots = [];

  for (const vp of VIEWPORTS) {
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
    });
    await boot.applyAuth(context, CONFIG, BASE);

    for (const route of routes) {
      const page = await context.newPage();
      let note = '';
      try {
        await page.goto(BASE + route, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForTimeout(VW.settle_ms || 2500);
        if (/\/entry|\/login/.test(page.url())) note = '被導回入口頁（未驗）';
      } catch (e) {
        note = `載入失敗：${String(e).slice(0, 80)}`;
      }
      const safe = route.replace(/[^a-z0-9]/gi, '_') || 'root';
      const file = `${safe}__${vp.name}.png`;
      // fullPage：視覺缺陷常在摺線以下（表格尾端、footer 按鈕），
      // 只拍可視範圍會漏掉一半。
      await page.screenshot({ path: path.join(outRoot, file), fullPage: true }).catch(() => {});
      shots.push({ route, viewport: vp.name, file, note });
      await page.close();
      await new Promise((r) => setTimeout(r, VW.throttle_ms || 700));
    }
    await context.close();
  }
  await browser.close();

  // 索引：讓讀的人知道**要看什麼**，而不是拿到一堆檔名
  const idx = [
    `# 視覺走查 ${todayStamp()}`,
    '',
    `站台：${BASE}｜路由 ${routes.length} 條 × 視窗 ${VIEWPORTS.length} 種 = ${shots.length} 張`,
    '',
    '## 這批圖要看什麼',
    '',
    '斷言式檢核**看不到**以下這些，所以才需要人／AI 逐張看：',
    '',
    '- 文字有沒有被截斷（存在 ≠ 看得懂，例：姓名被截成兩字）',
    '- 版面有沒有錯位、元素有沒有被遮蔽（存在 ≠ 看得到）',
    '- 顏色語意對不對（紅＝錯誤、綠＝正常）',
    '- 數字在畫面上是否合理（不只是「有數字」）',
    '- 手機寬度下是否仍可操作',
    '',
    '> ⚠️ **看完務必把發現轉成 flow 斷言**，否則下次還要再看一遍。',
    '> 視覺走查是發現器，回歸鎖才是機制。',
    '',
    '## 清單',
    '',
    '| 路由 | 視窗 | 檔案 | 備註 |',
    '|---|---|---|---|',
    ...shots.map((s) => `| ${s.route} | ${s.viewport} | ${s.file} | ${s.note || ''} |`),
    '',
  ].join('\n');
  fs.writeFileSync(path.join(outRoot, 'index.md'), idx, 'utf-8');

  console.log('='.repeat(70));
  console.log(`視覺走查完成：${shots.length} 張 → ${outRoot}`);
  console.log('='.repeat(70));
  const blocked = shots.filter((s) => s.note);
  if (blocked.length) {
    console.log(`⚪ ${blocked.length} 張有備註（未驗完）：`);
    for (const b of blocked.slice(0, 8)) console.log(`    ${b.route} [${b.viewport}] — ${b.note}`);
  }
  console.log('');
  console.log('下一步：讀 index.md，逐張看版面／截字／配色／遮蔽。');
  console.log('每發現一個缺陷 → 轉成 flow 斷言，否則這輪就是一次性勞動。');

  process.exit(shots.length ? 0 : 2);
}

main().catch((e) => { console.error(e); process.exit(2); });
