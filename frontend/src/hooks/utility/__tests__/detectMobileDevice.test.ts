/**
 * 行動裝置偵測的判準鎖 —— 2026-09-09 owner「不同行動裝置有時仍會誤判為桌機」。
 *
 * 守的是這一條：**`userAgentData.mobile === false` 不是「不是行動裝置」的證據。**
 * 規格上那個旗標指的是「手機形態」，Android 平板與部分廠商瀏覽器都會回 false，
 * 而舊版把它當成排他性答案，回 false 就直接判桌機、完全不看 UA。
 *
 * 失敗方向刻意偏向「當成行動裝置」：手機拿到桌面版是看不完的表格，
 * 桌機拿到手機版只是卡片比較大，而且使用者可以一鍵切回去。
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';

async function detectWith(env: {
  uaDataMobile?: boolean;
  ua?: string;
  coarse?: boolean;
  noHover?: boolean;
  maxTouchPoints?: number;
  screenWidth?: number;
}): Promise<boolean> {
  vi.resetModules();
  const nav: Record<string, unknown> = {
    userAgent: env.ua ?? '',
    maxTouchPoints: env.maxTouchPoints ?? 0,
  };
  if (env.uaDataMobile !== undefined) nav.userAgentData = { mobile: env.uaDataMobile };
  vi.stubGlobal('navigator', nav);
  vi.stubGlobal('window', {
    matchMedia: (q: string) => ({
      matches: q.includes('pointer: coarse') ? !!env.coarse : q.includes('hover: none') ? !!env.noHover : false,
    }),
    screen: { width: env.screenWidth ?? 1920 },
    addEventListener: () => {},
    removeEventListener: () => {},
    localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
  });
  const mod = await import('../useResponsive');
  return mod.detectMobileDevice();
}

const ANDROID_TABLET = 'Mozilla/5.0 (Linux; Android 14; SM-X200) AppleWebKit/537.36 Chrome/126 Safari/537.36';
const ANDROID_PHONE = 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/126 Mobile Safari/537.36';
const IPADOS = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605 Version/17 Safari/605';
const DESKTOP = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36';

describe('detectMobileDevice', () => {
  beforeEach(() => { vi.unstubAllGlobals(); });

  it('⭐ Android 平板：UA-CH 說 false，但 UA 說 Android ⇒ 仍判行動裝置（舊版在這裡誤判成桌機）', async () => {
    expect(await detectWith({
      uaDataMobile: false, ua: ANDROID_TABLET,
      coarse: true, noHover: true, maxTouchPoints: 5, screenWidth: 1024,
    })).toBe(true);
  });

  it('Android 手機：UA-CH 說 true ⇒ 行動裝置', async () => {
    expect(await detectWith({ uaDataMobile: true, ua: ANDROID_PHONE, coarse: true, maxTouchPoints: 5, screenWidth: 412 })).toBe(true);
  });

  it('iPadOS 自稱 Macintosh：靠觸控點數認出來', async () => {
    expect(await detectWith({ ua: IPADOS, coarse: true, noHover: true, maxTouchPoints: 5, screenWidth: 1024 })).toBe(true);
  });

  it('沒有 UA-CH 的舊版行動瀏覽器：UA 有 Mobile ⇒ 行動裝置', async () => {
    expect(await detectWith({ ua: ANDROID_PHONE, coarse: true, maxTouchPoints: 5, screenWidth: 412 })).toBe(true);
  });

  it('一般桌機：每一項證據都不指向 ⇒ 桌機', async () => {
    expect(await detectWith({ uaDataMobile: false, ua: DESKTOP, coarse: false, noHover: false, maxTouchPoints: 0, screenWidth: 1920 })).toBe(false);
  });

  it('觸控筆電：有觸控但有 hover、螢幕寬 ⇒ 桌機（不能因為有觸控就當手機）', async () => {
    expect(await detectWith({
      uaDataMobile: false, ua: DESKTOP,
      coarse: false, noHover: false, maxTouchPoints: 10, screenWidth: 1920,
    })).toBe(false);
  });

  it('外接觸控大螢幕：粗指標＋無 hover 但螢幕 ≥1024 ⇒ 桌機（最弱的證據要加螢幕條件）', async () => {
    expect(await detectWith({
      uaDataMobile: false, ua: DESKTOP,
      coarse: true, noHover: true, maxTouchPoints: 10, screenWidth: 1920,
    })).toBe(false);
  });

  it('navigator 取不到時不得拋錯（隱私模式／非瀏覽器環境）', async () => {
    vi.resetModules();
    vi.stubGlobal('navigator', undefined);
    vi.stubGlobal('window', {});
    const mod = await import('../useResponsive');
    expect(mod.detectMobileDevice()).toBe(false);
  });
});
