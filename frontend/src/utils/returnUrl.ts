/**
 * 登入後回跳目標（returnUrl）解析 — SSOT
 *
 * 2026-07-29 建立。觸發：手機掃案件核銷 QR
 * （`/erp/expenses/create?case_code=CK2026_PM_01_005`）後無法進入該案件核銷頁。
 *
 * 根因：`ProtectedRoute` / `useAuthGuard` / `withAuth` **都有**把
 * `pathname + search` 存進 `?returnUrl=`，但 `EntryPage` 在登入/SSO 成功後
 * 一律 `navigate(ROUTES.DASHBOARD)`（5 處寫死）→ returnUrl 被丟棄，
 * 使用者落在儀表板、案號消失 ⇒ 所有「深連結 + 需登入」情境（QR、Email 連結、
 * LINE 分享連結）在公網一律失效。
 *
 * 此模組把「解析 + 防 open redirect」收斂為單一實作，避免各入口各寫一份
 * （LineCallbackPage 原本就有一份區域性的 isValidReturnUrl）。
 */

/**
 * 驗證 returnUrl 必須是站內相對路徑（防 open redirect）。
 * 允許：`/erp/expenses/create?case_code=X`
 * 拒絕：`//evil.com`、`https://evil.com`、`javascript:...`
 */
export const isValidReturnUrl = (url: string | null | undefined): boolean => {
  if (!url) return false;
  try {
    const decoded = decodeURIComponent(url);
    return decoded.startsWith('/') && !decoded.startsWith('//');
  } catch {
    return false;
  }
};

/**
 * 從 URLSearchParams 取出安全的回跳路徑；不合法或不存在時回傳 fallback。
 *
 * @example
 *   const target = resolveReturnUrl(searchParams, ROUTES.DASHBOARD);
 *   navigate(target, { replace: true });
 */
export const resolveReturnUrl = (
  params: URLSearchParams | null | undefined,
  fallback: string,
): string => {
  const raw = params?.get('returnUrl');
  return isValidReturnUrl(raw) ? decodeURIComponent(raw as string) : fallback;
};
