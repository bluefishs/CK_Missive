// Anonymous-load smoke test for SessionGate / EntryPage on public site.
// Verifies: app boots, does NOT stay on "驗證登入狀態中" loading, EntryPage renders,
// and collects console errors (classifying fatal vs noise).
const path = require('path');
const PW_DIR = 'C:/Users/User1/AppData/Roaming/npm/node_modules/@playwright/mcp/node_modules/playwright';
const fs = require('fs');
const { chromium } = require(PW_DIR);

// This playwright build wants headless_shell-1212 which isn't cached.
// Fall back to a nearby cached executable so we don't trigger a download.
const CACHE = 'C:/Users/User1/AppData/Local/ms-playwright';
const EXE_CANDIDATES = [
  CACHE + '/chromium_headless_shell-1217/chrome-headless-shell-win64/chrome-headless-shell.exe',
  CACHE + '/chromium_headless_shell-1223/chrome-headless-shell-win64/chrome-headless-shell.exe',
  CACHE + '/chromium_headless_shell-1208/chrome-headless-shell-win64/chrome-headless-shell.exe',
  CACHE + '/chromium-1161/chrome-win/chrome.exe',
];
const EXE = EXE_CANDIDATES.find((p) => fs.existsSync(p));

const TARGET = 'https://missive.cksurvey.tw/entry';
const LOADING_TEXT = '驗證登入狀態中';
const ENTRY_HINTS = ['乾坤', '公文系統入口', '公文系統', '星空', '進入系統', '訪客'];
const SHOT = path.resolve('D:/CKProject/CK_Missive/scripts/checks/sso_entry_smoke.png');

// Console-error noise filters (ignored): favicon, Google FedCM, network probes, third-party.
const NOISE_RE = [
  /favicon/i,
  /fedcm/i,
  /accounts\.google\.com/i,
  /gsi\/|identity\/|googleusercontent/i,
  /net::ERR_/i,
  /Failed to load resource.*(401|403|404)/i,
  /the server responded with a status of (401|403|404)/i,
  /ERR_BLOCKED_BY_CLIENT/i,
];

function isNoise(text) {
  return NOISE_RE.some((re) => re.test(text));
}

(async () => {
  const result = {
    resolved: false,
    entryRendered: false,
    stillLoading: null,
    matchedHint: null,
    fatalErrors: [],
    noiseErrors: [],
    screenshot: SHOT,
    titleSnippet: null,
  };

  const browser = await chromium.launch({ headless: true, executablePath: EXE });
  const context = await browser.newContext(); // fresh, no cookies = anonymous
  const page = await context.newPage();

  const consoleErrors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => {
    consoleErrors.push('[pageerror] ' + (err && err.message ? err.message : String(err)));
  });

  try {
    await page.goto(TARGET, { waitUntil: 'domcontentloaded', timeout: 30000 });
  } catch (e) {
    console.log(JSON.stringify({ ...result, gotoError: String(e) }, null, 2));
    await browser.close();
    process.exit(3);
  }

  // Wait up to 10s for the loading gate to disappear OR an entry hint to appear.
  const deadline = Date.now() + 10000;
  let stillLoading = true;
  while (Date.now() < deadline) {
    const bodyText = await page.evaluate(() => document.body ? document.body.innerText : '');
    stillLoading = bodyText.includes(LOADING_TEXT);
    const hint = ENTRY_HINTS.find((h) => bodyText.includes(h));
    if (!stillLoading && hint) { result.matchedHint = hint; break; }
    if (hint && !result.matchedHint) result.matchedHint = hint;
    await page.waitForTimeout(300);
  }

  const finalText = await page.evaluate(() => document.body ? document.body.innerText : '');
  result.stillLoading = finalText.includes(LOADING_TEXT);
  result.resolved = !result.stillLoading;
  const finalHint = ENTRY_HINTS.find((h) => finalText.includes(h));
  if (finalHint) result.matchedHint = finalHint;
  result.entryRendered = !!result.matchedHint;
  result.titleSnippet = finalText.replace(/\s+/g, ' ').slice(0, 200);

  for (const t of consoleErrors) {
    if (isNoise(t)) result.noiseErrors.push(t);
    else result.fatalErrors.push(t);
  }

  try {
    await page.screenshot({ path: SHOT, fullPage: true });
  } catch (e) {
    result.screenshotError = String(e);
  }

  console.log(JSON.stringify(result, null, 2));
  await browser.close();

  const pass = result.resolved && result.entryRendered && result.fatalErrors.length === 0;
  process.exit(pass ? 0 : 1);
})().catch((e) => {
  console.error('SCRIPT_FATAL', e);
  process.exit(2);
});
