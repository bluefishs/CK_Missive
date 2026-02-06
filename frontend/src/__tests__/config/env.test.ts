/**
 * 環境檢測函數單元測試
 *
 * 測試 config/env.ts 中的環境檢測與內網 IP 判斷函數
 *
 * @version 1.0.0
 * @date 2026-02-06
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// 在匯入被測模組之前 mock import.meta.env
// 使用 dynamic import 以便在每個測試中重設 window.location

describe('isInternalIPAddress', () => {
  // 直接測試此純函數，無需 mock window
  let isInternalIPAddress: (hostname: string) => boolean;

  beforeEach(async () => {
    vi.resetModules();
    const mod = await import('../../config/env');
    isInternalIPAddress = mod.isInternalIPAddress;
  });

  describe('Class A 內網 (10.x.x.x)', () => {
    it('10.0.0.1 應判定為內網 IP', () => {
      expect(isInternalIPAddress('10.0.0.1')).toBe(true);
    });

    it('10.255.255.255 應判定為內網 IP', () => {
      expect(isInternalIPAddress('10.255.255.255')).toBe(true);
    });

    it('10.1.2.3 應判定為內網 IP', () => {
      expect(isInternalIPAddress('10.1.2.3')).toBe(true);
    });
  });

  describe('Class B 內網 (172.16-31.x.x)', () => {
    it('172.16.0.1 應判定為內網 IP', () => {
      expect(isInternalIPAddress('172.16.0.1')).toBe(true);
    });

    it('172.31.255.255 應判定為內網 IP', () => {
      expect(isInternalIPAddress('172.31.255.255')).toBe(true);
    });

    it('172.20.10.5 應判定為內網 IP', () => {
      expect(isInternalIPAddress('172.20.10.5')).toBe(true);
    });

    it('172.15.0.1 不應判定為內網 IP (低於 172.16)', () => {
      expect(isInternalIPAddress('172.15.0.1')).toBe(false);
    });

    it('172.32.0.1 不應判定為內網 IP (高於 172.31)', () => {
      expect(isInternalIPAddress('172.32.0.1')).toBe(false);
    });
  });

  describe('Class C 內網 (192.168.x.x)', () => {
    it('192.168.0.1 應判定為內網 IP', () => {
      expect(isInternalIPAddress('192.168.0.1')).toBe(true);
    });

    it('192.168.1.100 應判定為內網 IP', () => {
      expect(isInternalIPAddress('192.168.1.100')).toBe(true);
    });

    it('192.168.255.255 應判定為內網 IP', () => {
      expect(isInternalIPAddress('192.168.255.255')).toBe(true);
    });
  });

  describe('非內網 IP', () => {
    it('8.8.8.8 不應判定為內網 IP', () => {
      expect(isInternalIPAddress('8.8.8.8')).toBe(false);
    });

    it('1.2.3.4 不應判定為內網 IP', () => {
      expect(isInternalIPAddress('1.2.3.4')).toBe(false);
    });

    it('192.169.0.1 不應判定為內網 IP', () => {
      expect(isInternalIPAddress('192.169.0.1')).toBe(false);
    });

    it('localhost 不應判定為內網 IP', () => {
      expect(isInternalIPAddress('localhost')).toBe(false);
    });

    it('example.com 不應判定為內網 IP', () => {
      expect(isInternalIPAddress('example.com')).toBe(false);
    });

    it('空字串不應判定為內網 IP', () => {
      expect(isInternalIPAddress('')).toBe(false);
    });
  });
});

describe('detectEnvironment', () => {
  let detectEnvironment: () => string;
  const originalLocation = window.location;

  function mockHostname(hostname: string) {
    Object.defineProperty(window, 'location', {
      writable: true,
      value: { ...originalLocation, hostname },
    });
  }

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      writable: true,
      value: originalLocation,
    });
    vi.resetModules();
  });

  it('localhost 應偵測為 localhost 環境', async () => {
    mockHostname('localhost');
    vi.resetModules();
    const mod = await import('../../config/env');
    detectEnvironment = mod.detectEnvironment;
    expect(detectEnvironment()).toBe('localhost');
  });

  it('127.0.0.1 應偵測為 localhost 環境', async () => {
    mockHostname('127.0.0.1');
    vi.resetModules();
    const mod = await import('../../config/env');
    detectEnvironment = mod.detectEnvironment;
    expect(detectEnvironment()).toBe('localhost');
  });

  it('ngrok.io 域名應偵測為 ngrok 環境', async () => {
    mockHostname('abc123.ngrok.io');
    vi.resetModules();
    const mod = await import('../../config/env');
    detectEnvironment = mod.detectEnvironment;
    expect(detectEnvironment()).toBe('ngrok');
  });

  it('ngrok-free.app 域名應偵測為 ngrok 環境', async () => {
    mockHostname('abc123.ngrok-free.app');
    vi.resetModules();
    const mod = await import('../../config/env');
    detectEnvironment = mod.detectEnvironment;
    expect(detectEnvironment()).toBe('ngrok');
  });

  it('192.168.1.100 應偵測為 internal 環境', async () => {
    mockHostname('192.168.1.100');
    vi.resetModules();
    const mod = await import('../../config/env');
    detectEnvironment = mod.detectEnvironment;
    expect(detectEnvironment()).toBe('internal');
  });

  it('10.0.0.5 應偵測為 internal 環境', async () => {
    mockHostname('10.0.0.5');
    vi.resetModules();
    const mod = await import('../../config/env');
    detectEnvironment = mod.detectEnvironment;
    expect(detectEnvironment()).toBe('internal');
  });

  it('example.com 應偵測為 public 環境', async () => {
    mockHostname('example.com');
    vi.resetModules();
    const mod = await import('../../config/env');
    detectEnvironment = mod.detectEnvironment;
    expect(detectEnvironment()).toBe('public');
  });
});

describe('isInternalNetwork', () => {
  const originalLocation = window.location;

  function mockHostname(hostname: string) {
    Object.defineProperty(window, 'location', {
      writable: true,
      value: { ...originalLocation, hostname },
    });
  }

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      writable: true,
      value: originalLocation,
    });
    vi.resetModules();
  });

  it('localhost 應判定為內網', async () => {
    mockHostname('localhost');
    vi.resetModules();
    const mod = await import('../../config/env');
    expect(mod.isInternalNetwork()).toBe(true);
  });

  it('192.168.1.1 應判定為內網', async () => {
    mockHostname('192.168.1.1');
    vi.resetModules();
    const mod = await import('../../config/env');
    expect(mod.isInternalNetwork()).toBe(true);
  });

  it('example.com 不應判定為內網', async () => {
    mockHostname('example.com');
    vi.resetModules();
    const mod = await import('../../config/env');
    expect(mod.isInternalNetwork()).toBe(false);
  });

  it('ngrok 域名不應判定為內網', async () => {
    mockHostname('abc.ngrok-free.app');
    vi.resetModules();
    const mod = await import('../../config/env');
    expect(mod.isInternalNetwork()).toBe(false);
  });
});

describe('INTERNAL_IP_PATTERNS', () => {
  it('應包含 3 個 RFC 1918 內網 IP 模式', async () => {
    vi.resetModules();
    const mod = await import('../../config/env');
    expect(mod.INTERNAL_IP_PATTERNS).toHaveLength(3);
    expect(mod.INTERNAL_IP_PATTERNS.every((p: RegExp) => p instanceof RegExp)).toBe(true);
  });
});
