/**
 * 安全 API 服務測試
 * SecureApiService Tests
 *
 * 測試範圍:
 * - 單例匯出
 * - getCsrfToken / ensureCsrfToken 快取與重新取得行為
 * - secureRequest 標頭、CSRF 令牌、403 重試邏輯
 * - Auth-disabled 模式 vs 正常模式
 * - 導覽列 API (getNavigationItems, createNavigationItem 等)
 * - 配置管理 API (getConfigurations 等)
 * - 通用 post() 方法
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';

// ---------------------------------------------------------------------------
// Mock 依賴
// ---------------------------------------------------------------------------

const mockApiClientPost = vi.fn();

vi.mock('../../api/client', () => ({
  apiClient: {
    post: (...args: unknown[]) => mockApiClientPost(...args),
  },
  API_BASE_URL: 'http://localhost:8001/api',
}));

const mockIsAuthDisabled = vi.fn(() => false);

vi.mock('../../config/env', () => ({
  isAuthDisabled: () => mockIsAuthDisabled(),
}));

vi.mock('../../utils/logger', () => ({
  logger: {
    error: vi.fn(),
    warn: vi.fn(),
    log: vi.fn(),
    info: vi.fn(),
    debug: vi.fn(),
  },
}));

// ---------------------------------------------------------------------------
// 因為 secureApiService 是模組級單例，每次測試需要重新載入
// ---------------------------------------------------------------------------

async function createFreshService() {
  // vi.resetModules() 可讓 dynamic import 取得全新模組實例
  vi.resetModules();
  const mod = await import('../secureApiService');
  return mod.secureApiService;
}

// ---------------------------------------------------------------------------
// 測試
// ---------------------------------------------------------------------------

describe('SecureApiService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthDisabled.mockReturnValue(false);
  });

  // =========================================================================
  // 單例匯出
  // =========================================================================

  describe('模組匯出', () => {
    it('default export 與 named export 應該是同一個實例', async () => {
      vi.resetModules();
      const mod = await import('../secureApiService');
      expect(mod.default).toBe(mod.secureApiService);
    });

    it('匯出的 secureApiService 應該具備核心方法', async () => {
      const service = await createFreshService();
      expect(typeof service.getCsrfToken).toBe('function');
      expect(typeof service.getNavigationItems).toBe('function');
      expect(typeof service.post).toBe('function');
    });
  });

  // =========================================================================
  // getCsrfToken
  // =========================================================================

  describe('getCsrfToken', () => {
    it('成功取得 CSRF 令牌時應該回傳 token 字串', async () => {
      const service = await createFreshService();
      mockApiClientPost.mockResolvedValueOnce({
        success: true,
        csrf_token: 'test-csrf-token-abc',
      });

      const token = await service.getCsrfToken();
      expect(token).toBe('test-csrf-token-abc');
      expect(mockApiClientPost).toHaveBeenCalledWith(
        '/secure-site-management/csrf-token',
        {}
      );
    });

    it('伺服器回傳 success=false 時應該拋出錯誤', async () => {
      const service = await createFreshService();
      mockApiClientPost.mockResolvedValueOnce({
        success: false,
        csrf_token: null,
      });

      await expect(service.getCsrfToken()).rejects.toThrow('Invalid CSRF token response');
    });

    it('伺服器回傳缺少 csrf_token 時應該拋出錯誤', async () => {
      const service = await createFreshService();
      mockApiClientPost.mockResolvedValueOnce({
        success: true,
        // csrf_token 缺失
      });

      await expect(service.getCsrfToken()).rejects.toThrow('Invalid CSRF token response');
    });

    it('網路錯誤時應該向上傳播錯誤', async () => {
      const service = await createFreshService();
      mockApiClientPost.mockRejectedValueOnce(new Error('Network Error'));

      await expect(service.getCsrfToken()).rejects.toThrow('Network Error');
    });
  });

  // =========================================================================
  // ensureCsrfToken (透過 secureRequest 間接測試)
  // =========================================================================

  describe('ensureCsrfToken (透過 secureRequest 間接驗證)', () => {
    it('首次呼叫時應該自動取得 CSRF 令牌', async () => {
      const service = await createFreshService();

      // 第一次呼叫 = getCsrfToken
      mockApiClientPost.mockResolvedValueOnce({
        success: true,
        csrf_token: 'fresh-token',
      });
      // 第二次呼叫 = 實際 secureRequest
      mockApiClientPost.mockResolvedValueOnce({
        success: true,
        data: { items: [] },
      });

      await service.getNavigationItems();

      // 第一次 post 是 CSRF token 請求
      expect(mockApiClientPost.mock.calls[0][0]).toBe(
        '/secure-site-management/csrf-token'
      );
    });

    it('已有快取 token 時不應該重新取得', async () => {
      const service = await createFreshService();

      // 預先取得 token
      mockApiClientPost.mockResolvedValueOnce({
        success: true,
        csrf_token: 'cached-token',
      });
      await service.getCsrfToken();
      mockApiClientPost.mockClear();

      // 後續請求應直接使用快取的 token
      mockApiClientPost.mockResolvedValueOnce({
        success: true,
        data: { items: [] },
      });

      await service.getNavigationItems();

      // 只有一次呼叫 (實際請求)，沒有再次請求 CSRF token
      expect(mockApiClientPost).toHaveBeenCalledTimes(1);
    });
  });

  // =========================================================================
  // secureRequest - 正常模式
  // =========================================================================

  describe('secureRequest - 正常模式', () => {
    it('請求 body 應包含 action、csrf_token、data', async () => {
      const service = await createFreshService();
      mockApiClientPost
        .mockResolvedValueOnce({ success: true, csrf_token: 'tok-1' })
        .mockResolvedValueOnce({ success: true, data: 'ok' });

      await service.post('/some-endpoint', 'my-action', { key: 'value' });

      const [, body] = mockApiClientPost.mock.calls[1];
      expect(body).toEqual({
        action: 'my-action',
        csrf_token: 'tok-1',
        data: { key: 'value' },
      });
    });

    it('回應帶有新 csrf_token 時應更新快取', async () => {
      const service = await createFreshService();

      // 初始 token
      mockApiClientPost.mockResolvedValueOnce({
        success: true,
        csrf_token: 'initial-token',
      });
      // 第一次請求回傳更新後的 token
      mockApiClientPost.mockResolvedValueOnce({
        success: true,
        data: 'result-1',
        csrf_token: 'rotated-token',
      });
      await service.post('/ep', 'act');
      mockApiClientPost.mockClear();

      // 第二次請求應使用 rotated-token
      mockApiClientPost.mockResolvedValueOnce({
        success: true,
        data: 'result-2',
      });
      await service.post('/ep', 'act2');

      const [, body] = mockApiClientPost.mock.calls[0];
      expect(body.csrf_token).toBe('rotated-token');
    });

    it('回應 success=false 時應拋出含 message 的錯誤', async () => {
      const service = await createFreshService();
      mockApiClientPost
        .mockResolvedValueOnce({ success: true, csrf_token: 'tok' })
        .mockResolvedValueOnce({ success: false, message: '權限不足' });

      await expect(service.post('/ep', 'act')).rejects.toThrow('權限不足');
    });

    it('回應 success=false 但無 message 時應拋出預設錯誤訊息', async () => {
      const service = await createFreshService();
      mockApiClientPost
        .mockResolvedValueOnce({ success: true, csrf_token: 'tok' })
        .mockResolvedValueOnce({ success: false });

      await expect(service.post('/ep', 'act')).rejects.toThrow('Request failed');
    });

    it('端點含 API_BASE_URL 前綴時應自動移除', async () => {
      const service = await createFreshService();
      mockApiClientPost
        .mockResolvedValueOnce({ success: true, csrf_token: 'tok' })
        .mockResolvedValueOnce({ success: true, data: null });

      await service.post('http://localhost:8001/api/some-path', 'act');

      const [endpoint] = mockApiClientPost.mock.calls[1];
      expect(endpoint).toBe('/some-path');
    });

    it('端點含 /api 前綴時應自動移除', async () => {
      const service = await createFreshService();
      mockApiClientPost
        .mockResolvedValueOnce({ success: true, csrf_token: 'tok' })
        .mockResolvedValueOnce({ success: true, data: null });

      await service.post('/api/other-path', 'act');

      const [endpoint] = mockApiClientPost.mock.calls[1];
      expect(endpoint).toBe('/other-path');
    });
  });

  // =========================================================================
  // secureRequest - 403 CSRF 重試
  // =========================================================================

  describe('secureRequest - 403 CSRF 重試邏輯', () => {
    it('收到 403 錯誤時應重新取得 token 並重試一次', async () => {
      const service = await createFreshService();

      // 初始 getCsrfToken
      mockApiClientPost.mockResolvedValueOnce({
        success: true,
        csrf_token: 'old-token',
      });
      // 第一次請求 → 403
      const csrfError = Object.assign(new Error('CSRF expired'), { statusCode: 403 });
      mockApiClientPost.mockRejectedValueOnce(csrfError);
      // 重新取得 CSRF token
      mockApiClientPost.mockResolvedValueOnce({
        success: true,
        csrf_token: 'new-token',
      });
      // 重試請求成功
      mockApiClientPost.mockResolvedValueOnce({
        success: true,
        data: 'retry-success',
      });

      const result = await service.post('/ep', 'act');
      expect(result).toBe('retry-success');
      // 總共 4 次呼叫: getCsrf + 失敗請求 + 重新getCsrf + 重試請求
      expect(mockApiClientPost).toHaveBeenCalledTimes(4);
    });

    it('重試後仍然 403 時不應再次重試 (避免無限迴圈)', async () => {
      const service = await createFreshService();

      mockApiClientPost.mockResolvedValueOnce({
        success: true,
        csrf_token: 'tok',
      });
      const csrfError = Object.assign(new Error('CSRF'), { statusCode: 403 });
      mockApiClientPost.mockRejectedValueOnce(csrfError);
      mockApiClientPost.mockResolvedValueOnce({
        success: true,
        csrf_token: 'tok2',
      });
      // 重試也失敗
      const csrfError2 = Object.assign(new Error('Still CSRF'), { statusCode: 403 });
      mockApiClientPost.mockRejectedValueOnce(csrfError2);

      await expect(service.post('/ep', 'act')).rejects.toThrow('Still CSRF');
    });

    it('非 403 錯誤不應觸發重試', async () => {
      const service = await createFreshService();

      mockApiClientPost.mockResolvedValueOnce({
        success: true,
        csrf_token: 'tok',
      });
      mockApiClientPost.mockRejectedValueOnce(new Error('500 Internal'));

      await expect(service.post('/ep', 'act')).rejects.toThrow('500 Internal');
      // 只有 2 次呼叫: getCsrf + 失敗請求
      expect(mockApiClientPost).toHaveBeenCalledTimes(2);
    });
  });

  // =========================================================================
  // Auth-disabled 模式
  // =========================================================================

  describe('Auth-disabled 模式', () => {
    beforeEach(() => {
      mockIsAuthDisabled.mockReturnValue(true);
    });

    it('應使用 dev-mode-skip 作為 csrf_token', async () => {
      const service = await createFreshService();
      mockApiClientPost.mockResolvedValueOnce({
        success: true,
        data: { items: [] },
      });

      await service.getNavigationItems();

      const [, body] = mockApiClientPost.mock.calls[0];
      expect(body.csrf_token).toBe('dev-mode-skip');
    });

    it('不應呼叫 getCsrfToken', async () => {
      const service = await createFreshService();
      mockApiClientPost.mockResolvedValueOnce({
        success: true,
        data: [],
      });

      await service.getNavigationItems();

      // 只有一次呼叫 (實際請求)，沒有 CSRF token 請求
      expect(mockApiClientPost).toHaveBeenCalledTimes(1);
      expect(mockApiClientPost.mock.calls[0][0]).not.toContain('csrf-token');
    });

    it('回應 success=false 時應拋出錯誤', async () => {
      const service = await createFreshService();
      mockApiClientPost.mockResolvedValueOnce({
        success: false,
        message: 'Dev mode error',
      });

      await expect(service.getNavigationItems()).rejects.toThrow('Dev mode error');
    });

    it('API 呼叫失敗時應向上拋出錯誤', async () => {
      const service = await createFreshService();
      mockApiClientPost.mockRejectedValueOnce(new Error('Network fail'));

      await expect(service.getNavigationItems()).rejects.toThrow('Network fail');
    });
  });

  // =========================================================================
  // 導覽列管理 API
  // =========================================================================

  describe('導覽列管理 API', () => {
    let service: Awaited<ReturnType<typeof createFreshService>>;

    beforeEach(async () => {
      mockIsAuthDisabled.mockReturnValue(true); // 簡化測試，跳過 CSRF
      service = await createFreshService();
    });

    it('getNavigationItems 應呼叫正確的 endpoint 和 action', async () => {
      mockApiClientPost.mockResolvedValueOnce({ success: true, data: [] });
      await service.getNavigationItems();

      expect(mockApiClientPost.mock.calls[0][0]).toBe(
        '/secure-site-management/navigation/action'
      );
      expect(mockApiClientPost.mock.calls[0][1].action).toBe('list');
    });

    it('createNavigationItem 應傳遞 data 參數', async () => {
      mockApiClientPost.mockResolvedValueOnce({ success: true, data: { id: 1 } });
      const itemData = { key: 'new', title: 'New Item', path: '/new' };
      await service.createNavigationItem(itemData);

      const [, body] = mockApiClientPost.mock.calls[0];
      expect(body.action).toBe('create');
      expect(body.data).toEqual(itemData);
    });

    it('updateNavigationItem 應使用 update action', async () => {
      mockApiClientPost.mockResolvedValueOnce({ success: true, data: {} });
      await service.updateNavigationItem({ id: 5, title: 'Updated' });

      expect(mockApiClientPost.mock.calls[0][1].action).toBe('update');
    });

    it('deleteNavigationItem 應傳遞包含 id 的 data', async () => {
      mockApiClientPost.mockResolvedValueOnce({ success: true, data: null });
      await service.deleteNavigationItem(42);

      const [, body] = mockApiClientPost.mock.calls[0];
      expect(body.action).toBe('delete');
      expect(body.data).toEqual({ id: 42 });
    });

    it('getValidPaths 應呼叫 valid-paths endpoint', async () => {
      mockApiClientPost.mockResolvedValueOnce({ success: true, data: ['/a', '/b'] });
      await service.getValidPaths();

      expect(mockApiClientPost.mock.calls[0][0]).toBe(
        '/secure-site-management/navigation/valid-paths'
      );
      expect(mockApiClientPost.mock.calls[0][1].action).toBe('get');
    });

    it('reorderNavigationItems 應傳遞 items 陣列', async () => {
      mockApiClientPost.mockResolvedValueOnce({ success: true, data: null });
      const items = [
        { id: 1, sort_order: 0 },
        { id: 2, sort_order: 1, parent_id: null, level: 0 },
      ];
      await service.reorderNavigationItems(items);

      const [, body] = mockApiClientPost.mock.calls[0];
      expect(body.action).toBe('reorder');
      expect(body.data).toEqual({ items });
    });
  });

  // =========================================================================
  // 配置管理 API
  // =========================================================================

  describe('配置管理 API', () => {
    let service: Awaited<ReturnType<typeof createFreshService>>;

    beforeEach(async () => {
      mockIsAuthDisabled.mockReturnValue(true);
      service = await createFreshService();
    });

    it('getConfigurations 無篩選時 data 應為空物件', async () => {
      mockApiClientPost.mockResolvedValueOnce({ success: true, data: [] });
      await service.getConfigurations();

      const [endpoint, body] = mockApiClientPost.mock.calls[0];
      expect(endpoint).toBe('/secure-site-management/config/action');
      expect(body.action).toBe('list');
      expect(body.data).toEqual({});
    });

    it('getConfigurations 有篩選時應傳遞 filters', async () => {
      mockApiClientPost.mockResolvedValueOnce({ success: true, data: [] });
      await service.getConfigurations({ search: 'theme', category: 'ui' });

      const [, body] = mockApiClientPost.mock.calls[0];
      expect(body.data).toEqual({ search: 'theme', category: 'ui' });
    });

    it('createConfiguration 應使用 create action', async () => {
      mockApiClientPost.mockResolvedValueOnce({ success: true, data: {} });
      await service.createConfiguration({ config_key: 'k', config_value: 'v' });

      expect(mockApiClientPost.mock.calls[0][1].action).toBe('create');
    });

    it('deleteConfiguration 應傳遞 config_key', async () => {
      mockApiClientPost.mockResolvedValueOnce({ success: true, data: null });
      await service.deleteConfiguration('theme_color');

      const [, body] = mockApiClientPost.mock.calls[0];
      expect(body.action).toBe('delete');
      expect(body.data).toEqual({ config_key: 'theme_color' });
    });
  });
});
