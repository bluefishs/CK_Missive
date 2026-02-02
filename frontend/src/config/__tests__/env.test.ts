/**
 * 環境變數配置測試
 * Environment Configuration Tests
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock import.meta.env
const mockEnv: Record<string, string | boolean> = {
  DEV: true,
};

vi.mock('import.meta', () => ({
  env: mockEnv,
}));

describe('env configuration', () => {
  let originalWindow: Window & typeof globalThis;

  beforeEach(() => {
    originalWindow = global.window;
    vi.resetModules();
  });

  afterEach(() => {
    global.window = originalWindow;
  });

  describe('INTERNAL_IP_PATTERNS', () => {
    it('應該匹配 Class A 內網 IP (10.x.x.x)', async () => {
      const { INTERNAL_IP_PATTERNS } = await import('../env');

      expect(INTERNAL_IP_PATTERNS.some(p => p.test('10.0.0.1'))).toBe(true);
      expect(INTERNAL_IP_PATTERNS.some(p => p.test('10.255.255.255'))).toBe(true);
      expect(INTERNAL_IP_PATTERNS.some(p => p.test('10.50.100.200'))).toBe(true);
    });

    it('應該匹配 Class B 內網 IP (172.16-31.x.x)', async () => {
      const { INTERNAL_IP_PATTERNS } = await import('../env');

      expect(INTERNAL_IP_PATTERNS.some(p => p.test('172.16.0.1'))).toBe(true);
      expect(INTERNAL_IP_PATTERNS.some(p => p.test('172.31.255.255'))).toBe(true);
      expect(INTERNAL_IP_PATTERNS.some(p => p.test('172.20.100.50'))).toBe(true);
    });

    it('不應該匹配 172.32.x.x (超出範圍)', async () => {
      const { INTERNAL_IP_PATTERNS } = await import('../env');

      expect(INTERNAL_IP_PATTERNS.some(p => p.test('172.32.0.1'))).toBe(false);
      expect(INTERNAL_IP_PATTERNS.some(p => p.test('172.15.0.1'))).toBe(false);
    });

    it('應該匹配 Class C 內網 IP (192.168.x.x)', async () => {
      const { INTERNAL_IP_PATTERNS } = await import('../env');

      expect(INTERNAL_IP_PATTERNS.some(p => p.test('192.168.0.1'))).toBe(true);
      expect(INTERNAL_IP_PATTERNS.some(p => p.test('192.168.255.255'))).toBe(true);
      expect(INTERNAL_IP_PATTERNS.some(p => p.test('192.168.50.210'))).toBe(true);
    });

    it('不應該匹配公網 IP', async () => {
      const { INTERNAL_IP_PATTERNS } = await import('../env');

      expect(INTERNAL_IP_PATTERNS.some(p => p.test('8.8.8.8'))).toBe(false);
      expect(INTERNAL_IP_PATTERNS.some(p => p.test('1.1.1.1'))).toBe(false);
      expect(INTERNAL_IP_PATTERNS.some(p => p.test('203.0.113.1'))).toBe(false);
    });
  });

  describe('isInternalIPAddress', () => {
    it('應該正確識別內網 IP', async () => {
      const { isInternalIPAddress } = await import('../env');

      expect(isInternalIPAddress('192.168.1.1')).toBe(true);
      expect(isInternalIPAddress('10.0.0.1')).toBe(true);
      expect(isInternalIPAddress('172.16.0.1')).toBe(true);
    });

    it('應該正確識別公網 IP', async () => {
      const { isInternalIPAddress } = await import('../env');

      expect(isInternalIPAddress('8.8.8.8')).toBe(false);
      expect(isInternalIPAddress('google.com')).toBe(false);
    });
  });

  describe('detectEnvironment', () => {
    it('當 window undefined 時應該返回 localhost', async () => {
      // @ts-expect-error - intentionally setting window to undefined for test
      delete global.window;

      const { detectEnvironment } = await import('../env');
      expect(detectEnvironment()).toBe('localhost');
    });
  });

  describe('API_BASE_URL', () => {
    it('應該包含 /api 後綴', async () => {
      const { API_BASE_URL } = await import('../env');

      expect(API_BASE_URL).toContain('/api');
    });

    it('應該是有效的 URL 格式', async () => {
      const { API_BASE_URL } = await import('../env');

      expect(API_BASE_URL).toMatch(/^https?:\/\//);
    });
  });

  describe('isAuthDisabled', () => {
    it('應該返回 boolean', async () => {
      const { isAuthDisabled } = await import('../env');

      expect(typeof isAuthDisabled()).toBe('boolean');
    });
  });

  describe('向後相容性', () => {
    it('AUTH_DISABLED 應該等於 AUTH_DISABLED_ENV', async () => {
      const { AUTH_DISABLED, AUTH_DISABLED_ENV } = await import('../env');

      expect(AUTH_DISABLED).toBe(AUTH_DISABLED_ENV);
    });

    it('isInternalIP 應該等於 isInternalNetwork', async () => {
      const { isInternalIP, isInternalNetwork } = await import('../env');

      expect(isInternalIP).toBe(isInternalNetwork);
    });
  });

  describe('ENV_CONFIG', () => {
    it('應該包含所有環境變數', async () => {
      const { ENV_CONFIG } = await import('../env');

      expect(ENV_CONFIG).toHaveProperty('VITE_AUTH_DISABLED');
      expect(ENV_CONFIG).toHaveProperty('VITE_API_BASE_URL');
      expect(ENV_CONFIG).toHaveProperty('VITE_GOOGLE_CLIENT_ID');
      expect(ENV_CONFIG).toHaveProperty('NODE_ENV');
      expect(ENV_CONFIG).toHaveProperty('DEV');
    });
  });
});
