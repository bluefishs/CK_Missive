/**
 * returnUrl 解析 Regression（2026-07-29）
 *
 * 事故：owner 用手機掃案件核銷 QR
 * （`/erp/expenses/create?case_code=CK2026_PM_01_005`）→ 無法進入該案件核銷頁。
 *
 * 根因：ProtectedRoute / useAuthGuard / withAuth 都正確把 `pathname + search`
 * 存成 `?returnUrl=`，但 EntryPage 登入/SSO 成功後 **5 處寫死 navigate(DASHBOARD)**
 * → returnUrl 丟棄 → 所有「深連結 + 需登入」情境（QR / Email / LINE 分享）在公網全失效。
 */
import { describe, expect, it } from 'vitest';

import { isValidReturnUrl, resolveReturnUrl } from '../returnUrl';

const FALLBACK = '/dashboard';

describe('isValidReturnUrl', () => {
  it('接受站內相對路徑', () => {
    expect(isValidReturnUrl('/erp/expenses/create?case_code=CK2026_PM_01_005')).toBe(true);
    expect(isValidReturnUrl('/dashboard')).toBe(true);
  });

  it('接受已編碼的站內路徑（ProtectedRoute 存進去的形式）', () => {
    expect(isValidReturnUrl('%2Ferp%2Fexpenses%2Fcreate%3Fcase_code%3DCK2026_PM_01_005')).toBe(true);
  });

  it('拒絕 open redirect', () => {
    expect(isValidReturnUrl('//evil.com')).toBe(false);
    expect(isValidReturnUrl('https://evil.com')).toBe(false);
    expect(isValidReturnUrl('javascript:alert(1)')).toBe(false);
  });

  it('空值安全', () => {
    expect(isValidReturnUrl(null)).toBe(false);
    expect(isValidReturnUrl(undefined)).toBe(false);
    expect(isValidReturnUrl('')).toBe(false);
  });
});

describe('resolveReturnUrl', () => {
  it('掃 QR 深連結：登入後必須回到帶 case_code 的核銷頁（本次事故情境）', () => {
    const target = '/erp/expenses/create?case_code=CK2026_PM_01_005';
    const params = new URLSearchParams({ returnUrl: encodeURIComponent(target) });
    expect(resolveReturnUrl(params, FALLBACK)).toBe(target);
  });

  it('沒有 returnUrl 時回退 dashboard（原行為不變）', () => {
    expect(resolveReturnUrl(new URLSearchParams(), FALLBACK)).toBe(FALLBACK);
    expect(resolveReturnUrl(null, FALLBACK)).toBe(FALLBACK);
  });

  it('惡意 returnUrl 一律回退，不得跳出站外', () => {
    const params = new URLSearchParams({ returnUrl: 'https://evil.com' });
    expect(resolveReturnUrl(params, FALLBACK)).toBe(FALLBACK);
  });
});
