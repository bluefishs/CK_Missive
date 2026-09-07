/**
 * weekly 111 `crushedCol` 判準的正負向控制（2026-09-07）。
 *
 * ## 為什麼需要這一支
 *
 * 09-07 補上「欄位被壓扁」判準後，全站跑出來是 0 —— 而 **0 有兩種意思**：
 * 「沒有這個問題」或「這個判準永遠不會紅」。本 repo 對這件事付過學費
 * （`fitness_self_false_green`：它從來沒紅過，還是從來沒綠過？）。
 *
 * 這一支用**判準自己的實作**（`require` 探針的 `measure`，不另抄一份）跑三張造出來的表：
 *
 * | 控制 | 表格 | 應該 |
 * |---|---|---|
 * | 正向 | 名稱欄被固定欄寬擠到 ~30px、內容是長公司名 | **抓到 1 欄** |
 * | 負向 A | 兩字數值欄 60px、內容是「2」 | 不抓（窄但讀得完，首版就是在這裡誤報 7 筆） |
 * | 負向 B | 名稱欄 220px、內容同一個長公司名 | 不抓（夠寬） |
 *
 * 用法：`node scripts/checks/rwd_crushed_column_control.cjs`
 * 退出碼 0＝三個控制都符合預期；2＝判準行為與預期不符（**判準壞了，不是頁面壞了**）。
 */
const path = require('path');
const boot = require('./.shared-selfaudit/_bootstrap.cjs');
const { measure } = require('./rwd_mobile_quality_probe.cjs');

// playwright 走 vendored bootstrap 的解析（與探針同一條路）——
// 直接 `require('playwright')` 在本 repo 解不到（它不在根 node_modules）。
const { ROOT } = boot.loadConfig('sweep', path.join(__dirname, '.shared-selfaudit'));
const PW = boot.resolvePlaywright(ROOT);
if (!PW || !PW.exe) boot.fail(boot.playwrightMissingMessage());

/** 造一張 AntD 形狀的表：`table-layout: fixed` + 固定欄寬總和超過容器 */
function html({ nameWidth, containerWidth }) {
  const nameStyle = nameWidth ? `width:${nameWidth}px` : '';
  return `<!doctype html><html><head><meta charset="utf-8"><style>
    body { margin: 0; font: 14px sans-serif; }
    .wrap { width: ${containerWidth}px; overflow-x: auto; }
    table { table-layout: fixed; width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid #eee; padding: 4px; text-align: left;
             overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  </style></head><body>
  <div class="wrap"><table>
    <thead><tr>
      <th class="ant-table-cell" ${nameStyle ? `style="${nameStyle}"` : ''}>廠商名稱</th>
      <th class="ant-table-cell" style="width:140px">統一編號</th>
      <th class="ant-table-cell" style="width:150px">計畫類別</th>
      <th class="ant-table-cell" style="width:170px">案件狀態</th>
      <th class="ant-table-cell" style="width:60px">案數</th>
      <th class="ant-table-cell" style="width:130px">應付總額</th>
      <th class="ant-table-cell" style="width:130px">已付總額</th>
    </tr></thead>
    <tbody><tr>
      <td>政威資訊顧問有限公司</td><td>29158583</td><td>委辦招標</td>
      <td>執行中 2</td><td>2</td><td>3,000,000</td><td>0</td>
    </tr></tbody>
  </table></div></body></html>`;
}

(async () => {
  const browser = await PW.chromium.launch({ executablePath: PW.exe, headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const fails = [];

  // 正向：名稱欄不給寬度，固定欄寬總和 780 > 容器 900 之後它被擠扁
  // （容器 820 讓剩餘空間只有 ~40px）
  await page.setContent(html({ nameWidth: 0, containerWidth: 820 }));
  let m = await page.evaluate(measure, 1440);
  const hitNames = (m.crushedTop || []).map((c) => c.text);
  if (!hitNames.includes('廠商名稱')) {
    fails.push(`正向控制沒有抓到被擠扁的名稱欄（crushedCol=${m.crushedCol}、命中=${JSON.stringify(hitNames)}）`);
  }
  if (hitNames.includes('案數')) {
    fails.push('正向控制把 60px 的「案數」也算進去了——窄而讀得完不是缺陷');
  }

  // 負向 A：同一張表，名稱欄給足寬度 ⇒ 一欄都不該中
  await page.setContent(html({ nameWidth: 220, containerWidth: 1400 }));
  m = await page.evaluate(measure, 1440);
  if ((m.crushedCol || 0) !== 0) {
    fails.push(`負向控制 A 誤報 ${m.crushedCol} 欄：${JSON.stringify(m.crushedTop)}`);
  }

  await browser.close();

  if (fails.length) {
    console.log('[RED] crushedCol 判準的行為與預期不符：');
    fails.forEach((f) => console.log('  - ' + f));
    process.exit(2);
  }
  console.log('[GREEN] crushedCol 判準：正向會紅、兩個負向不紅');
})().catch((e) => { console.error(e); process.exit(2); });
