/**
 * Logger 工具測試
 * Logger Utility Tests
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { logger, LogLevel } from '../logger';

describe('logger', () => {
  const originalConsole = { ...console };

  beforeEach(() => {
    // Mock console methods
    console.log = vi.fn();
    console.info = vi.fn();
    console.warn = vi.fn();
    console.error = vi.fn();
    console.debug = vi.fn();
  });

  afterEach(() => {
    // Restore console
    console.log = originalConsole.log;
    console.info = originalConsole.info;
    console.warn = originalConsole.warn;
    console.error = originalConsole.error;
    console.debug = originalConsole.debug;
  });

  describe('log 方法', () => {
    it('應該呼叫 console.log', () => {
      logger.log('測試訊息');
      expect(console.log).toHaveBeenCalled();
    });

    it('應該傳遞多個參數', () => {
      logger.log('訊息', { data: 123 }, [1, 2, 3]);
      expect(console.log).toHaveBeenCalled();
    });
  });

  describe('info 方法', () => {
    it('應該呼叫 console.info', () => {
      logger.info('資訊訊息');
      expect(console.info).toHaveBeenCalled();
    });
  });

  describe('warn 方法', () => {
    it('應該呼叫 console.warn', () => {
      logger.warn('警告訊息');
      expect(console.warn).toHaveBeenCalled();
    });
  });

  describe('error 方法', () => {
    it('應該呼叫 console.error', () => {
      logger.error('錯誤訊息');
      expect(console.error).toHaveBeenCalled();
    });

    it('應該能夠傳遞 Error 物件', () => {
      const error = new Error('測試錯誤');
      logger.error('發生錯誤:', error);
      expect(console.error).toHaveBeenCalled();
    });
  });

  describe('debug 方法', () => {
    it('應該呼叫 console.debug', () => {
      logger.debug('除錯訊息');
      expect(console.debug).toHaveBeenCalled();
    });
  });

  describe('基本型別檢查', () => {
    it('logger 應該是一個物件', () => {
      expect(typeof logger).toBe('object');
    });

    it('logger 應該包含所有日誌方法', () => {
      expect(typeof logger.log).toBe('function');
      expect(typeof logger.info).toBe('function');
      expect(typeof logger.warn).toBe('function');
      expect(typeof logger.error).toBe('function');
      expect(typeof logger.debug).toBe('function');
    });
  });
});
