/**
 * RequestThrottler 單元測試
 *
 * 測試請求熔斷器的三層防護機制：
 * 1. 同 URL 去重（MIN_INTERVAL_MS 內返回快取）
 * 2. 單 URL 滑動窗口限流（MAX_PER_URL）
 * 3. 全域熔斷器（GLOBAL_MAX + COOLDOWN_MS）
 *
 * @version 1.0.0
 * @date 2026-02-06
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock logger 必須在 import 前宣告
vi.mock('../../services/logger', () => ({
  logger: {
    error: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
    log: vi.fn(),
    debug: vi.fn(),
  },
}));

// Mock config/env
vi.mock('../../config/env', () => ({
  isInternalIPAddress: vi.fn(() => false),
}));

// Mock endpoints
vi.mock('../../api/endpoints', () => ({
  AUTH_ENDPOINTS: { REFRESH: '/auth/refresh' },
}));

import { RequestThrottler, THROTTLE_CONFIG } from '../../api/client';

describe('RequestThrottler', () => {
  let throttler: RequestThrottler;

  beforeEach(() => {
    vi.useFakeTimers();
    throttler = new RequestThrottler();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // ===========================================================================
  // 基本放行測試
  // ===========================================================================

  describe('基本放行', () => {
    it('首次請求應該放行', () => {
      const result = throttler.check('GET', '/api/documents');
      expect(result.action).toBe('allow');
    });

    it('不同 URL 的請求應該各自獨立放行', () => {
      const r1 = throttler.check('GET', '/api/documents');
      const r2 = throttler.check('GET', '/api/projects');
      const r3 = throttler.check('POST', '/api/documents');

      expect(r1.action).toBe('allow');
      expect(r2.action).toBe('allow');
      expect(r3.action).toBe('allow');
    });

    it('method 為 undefined 時應使用 GET 作為預設', () => {
      const r1 = throttler.check(undefined, '/api/test');
      expect(r1.action).toBe('allow');

      // 記錄回應後，用 GET 方法查詢應能匹配
      throttler.recordResponse(undefined, '/api/test', { cached: true });
      const r2 = throttler.check('GET', '/api/test');
      // 同 key，在 MIN_INTERVAL_MS 內應返回快取
      expect(r2.action).toBe('cache');
    });

    it('url 為 undefined 時不應拋出錯誤', () => {
      const result = throttler.check('GET', undefined);
      expect(result.action).toBe('allow');
    });
  });

  // ===========================================================================
  // 同 URL 去重測試（MIN_INTERVAL_MS）
  // ===========================================================================

  describe('同 URL 去重', () => {
    it('在 MIN_INTERVAL_MS 內的相同請求應返回快取', () => {
      // 第一次請求放行
      const r1 = throttler.check('GET', '/api/documents');
      expect(r1.action).toBe('allow');

      // 記錄回應
      throttler.recordResponse('GET', '/api/documents', { items: [1, 2, 3] });

      // 在最小間隔內再次請求 -> 應返回快取
      vi.advanceTimersByTime(THROTTLE_CONFIG.MIN_INTERVAL_MS - 1);
      const r2 = throttler.check('GET', '/api/documents');
      expect(r2.action).toBe('cache');
      if (r2.action === 'cache') {
        expect(r2.data).toEqual({ items: [1, 2, 3] });
      }
    });

    it('超過 MIN_INTERVAL_MS 後應再次放行', () => {
      // 第一次請求放行
      throttler.check('GET', '/api/documents');
      throttler.recordResponse('GET', '/api/documents', { items: [] });

      // 超過最小間隔
      vi.advanceTimersByTime(THROTTLE_CONFIG.MIN_INTERVAL_MS + 1);

      const result = throttler.check('GET', '/api/documents');
      expect(result.action).toBe('allow');
    });

    it('沒有快取資料時不應返回 cache（即使在間隔內）', () => {
      // 第一次請求但沒有 recordResponse
      throttler.check('GET', '/api/documents');

      // 短暫等待後再次請求
      vi.advanceTimersByTime(100);
      const result = throttler.check('GET', '/api/documents');
      // lastData 為 null，所以不會觸發 cache 檢查
      expect(result.action).toBe('allow');
    });

    it('recordResponse 應該更新快取資料', () => {
      throttler.check('GET', '/api/documents');
      throttler.recordResponse('GET', '/api/documents', { version: 1 });

      vi.advanceTimersByTime(500);
      const r1 = throttler.check('GET', '/api/documents');
      expect(r1.action).toBe('cache');
      if (r1.action === 'cache') {
        expect(r1.data).toEqual({ version: 1 });
      }

      // 等待超過間隔後放行，再次更新快取
      vi.advanceTimersByTime(THROTTLE_CONFIG.MIN_INTERVAL_MS + 1);
      throttler.check('GET', '/api/documents');
      throttler.recordResponse('GET', '/api/documents', { version: 2 });

      vi.advanceTimersByTime(500);
      const r2 = throttler.check('GET', '/api/documents');
      expect(r2.action).toBe('cache');
      if (r2.action === 'cache') {
        expect(r2.data).toEqual({ version: 2 });
      }
    });
  });

  // ===========================================================================
  // 單 URL 滑動窗口限流測試（MAX_PER_URL）
  // ===========================================================================

  describe('單 URL 滑動窗口限流', () => {
    it('超過 MAX_PER_URL 且有快取時應返回快取', () => {
      const url = '/api/documents';

      // 快速發送 MAX_PER_URL 個請求（不 recordResponse，所以不會觸發 dedup cache 檢查）
      // 每次只推進極小的時間，確保全部在 WINDOW_MS 內
      for (let i = 0; i < THROTTLE_CONFIG.MAX_PER_URL; i++) {
        vi.advanceTimersByTime(1);
        throttler.check('GET', url);
      }

      // 記錄回應（設定 lastData）
      throttler.recordResponse('GET', url, { cached: 'data' });

      // 再次請求 -> 此時 timestamps.length >= MAX_PER_URL 且有 lastData
      vi.advanceTimersByTime(THROTTLE_CONFIG.MIN_INTERVAL_MS + 1);
      const result = throttler.check('GET', url);
      expect(result.action).toBe('cache');
    });

    it('超過 MAX_PER_URL 且無快取時應拒絕', () => {
      const url = '/api/no-cache-url';

      // 快速發送 MAX_PER_URL 個請求（全部在窗口內）
      for (let i = 0; i < THROTTLE_CONFIG.MAX_PER_URL; i++) {
        vi.advanceTimersByTime(1);
        throttler.check('GET', url);
      }

      // 不記錄回應（無快取），再次請求
      vi.advanceTimersByTime(THROTTLE_CONFIG.MIN_INTERVAL_MS + 1);
      const result = throttler.check('GET', url);
      expect(result.action).toBe('reject');
      if (result.action === 'reject') {
        expect(result.reason).toContain('頻繁');
      }
    });

    it('窗口過期後計數應重置，請求應再次放行', () => {
      const url = '/api/documents';

      // 快速填滿窗口
      for (let i = 0; i < THROTTLE_CONFIG.MAX_PER_URL; i++) {
        vi.advanceTimersByTime(1);
        throttler.check('GET', url);
      }

      // 等待窗口過期
      vi.advanceTimersByTime(THROTTLE_CONFIG.WINDOW_MS + 1);

      const result = throttler.check('GET', url);
      expect(result.action).toBe('allow');
    });
  });

  // ===========================================================================
  // 全域熔斷器測試（GLOBAL_MAX + COOLDOWN_MS）
  // ===========================================================================

  describe('全域熔斷器', () => {
    it('全域請求超過 GLOBAL_MAX 時應觸發熔斷', () => {
      // 使用不同 URL 快速發送請求，確保全部在窗口內
      for (let i = 0; i < THROTTLE_CONFIG.GLOBAL_MAX; i++) {
        vi.advanceTimersByTime(1);
        const result = throttler.check('GET', `/api/endpoint-${i}`);
        expect(result.action).toBe('allow');
      }

      // 第 GLOBAL_MAX+1 個請求應被拒絕
      vi.advanceTimersByTime(1);
      const result = throttler.check('GET', '/api/endpoint-overflow');
      expect(result.action).toBe('reject');
      if (result.action === 'reject') {
        expect(result.reason).toContain('熔斷');
      }
    });

    it('熔斷期間所有請求都應被拒絕', () => {
      // 快速觸發全域熔斷
      for (let i = 0; i < THROTTLE_CONFIG.GLOBAL_MAX; i++) {
        vi.advanceTimersByTime(1);
        throttler.check('GET', `/api/endpoint-${i}`);
      }
      vi.advanceTimersByTime(1);
      throttler.check('GET', '/api/trigger-breaker');

      // 熔斷期間的請求都應被拒絕
      vi.advanceTimersByTime(100);
      const r1 = throttler.check('GET', '/api/new-request-1');
      expect(r1.action).toBe('reject');

      vi.advanceTimersByTime(1000);
      const r2 = throttler.check('POST', '/api/new-request-2');
      expect(r2.action).toBe('reject');
    });

    it('熔斷冷卻後應恢復正常', () => {
      // 快速觸發全域熔斷
      for (let i = 0; i < THROTTLE_CONFIG.GLOBAL_MAX; i++) {
        vi.advanceTimersByTime(1);
        throttler.check('GET', `/api/endpoint-${i}`);
      }
      vi.advanceTimersByTime(1);
      throttler.check('GET', '/api/trigger-breaker');

      // 等待冷卻 + 窗口過期
      vi.advanceTimersByTime(THROTTLE_CONFIG.COOLDOWN_MS + THROTTLE_CONFIG.WINDOW_MS + 1);

      const result = throttler.check('GET', '/api/recovered');
      expect(result.action).toBe('allow');
    });

    it('拒絕回應應包含剩餘冷卻時間', () => {
      // 快速觸發全域熔斷
      for (let i = 0; i < THROTTLE_CONFIG.GLOBAL_MAX; i++) {
        vi.advanceTimersByTime(1);
        throttler.check('GET', `/api/endpoint-${i}`);
      }
      vi.advanceTimersByTime(1);
      throttler.check('GET', '/api/trigger-breaker');

      // 等待 2 秒後檢查剩餘時間
      vi.advanceTimersByTime(2000);
      const result = throttler.check('GET', '/api/during-cooldown');
      expect(result.action).toBe('reject');
      if (result.action === 'reject') {
        // 剩餘時間應大於 0
        expect(result.reason).toMatch(/\d+s/);
      }
    });
  });

  // ===========================================================================
  // recordResponse 測試
  // ===========================================================================

  describe('recordResponse', () => {
    it('對未知 key 呼叫 recordResponse 不應拋出錯誤', () => {
      // 沒有先 check 就直接 recordResponse
      expect(() => {
        throttler.recordResponse('GET', '/api/unknown', { data: 'test' });
      }).not.toThrow();
    });

    it('recordResponse 後的快取資料應該是最後一次記錄的值', () => {
      throttler.check('GET', '/api/test');

      throttler.recordResponse('GET', '/api/test', { v: 1 });
      throttler.recordResponse('GET', '/api/test', { v: 2 });

      vi.advanceTimersByTime(500);
      const result = throttler.check('GET', '/api/test');
      expect(result.action).toBe('cache');
      if (result.action === 'cache') {
        expect(result.data).toEqual({ v: 2 });
      }
    });
  });

  // ===========================================================================
  // 邊界條件測試
  // ===========================================================================

  describe('邊界條件', () => {
    it('不同 HTTP 方法應該視為不同的 key', () => {
      throttler.check('GET', '/api/documents');
      throttler.recordResponse('GET', '/api/documents', { method: 'GET' });

      throttler.check('POST', '/api/documents');
      throttler.recordResponse('POST', '/api/documents', { method: 'POST' });

      vi.advanceTimersByTime(500);

      const getResult = throttler.check('GET', '/api/documents');
      expect(getResult.action).toBe('cache');
      if (getResult.action === 'cache') {
        expect(getResult.data).toEqual({ method: 'GET' });
      }

      const postResult = throttler.check('POST', '/api/documents');
      expect(postResult.action).toBe('cache');
      if (postResult.action === 'cache') {
        expect(postResult.data).toEqual({ method: 'POST' });
      }
    });

    it('THROTTLE_CONFIG 應有合理的預設值', () => {
      expect(THROTTLE_CONFIG.MIN_INTERVAL_MS).toBeGreaterThan(0);
      expect(THROTTLE_CONFIG.MAX_PER_URL).toBeGreaterThan(0);
      expect(THROTTLE_CONFIG.WINDOW_MS).toBeGreaterThan(0);
      expect(THROTTLE_CONFIG.GLOBAL_MAX).toBeGreaterThan(THROTTLE_CONFIG.MAX_PER_URL);
      expect(THROTTLE_CONFIG.COOLDOWN_MS).toBeGreaterThan(0);
    });
  });
});
