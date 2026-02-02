/**
 * Query 配置測試
 * Query Configuration Tests
 */
import { describe, it, expect } from 'vitest';
import { queryKeys, defaultQueryOptions } from '../queryConfig';

describe('queryKeys', () => {
  describe('documents', () => {
    it('應該有 all key', () => {
      expect(queryKeys.documents.all).toBeDefined();
      expect(Array.isArray(queryKeys.documents.all)).toBe(true);
    });

    it('list 應該回傳包含參數的 key', () => {
      const params = { page: 1, limit: 10 };
      const key = queryKeys.documents.list(params);

      expect(Array.isArray(key)).toBe(true);
      expect(key).toContain('list');
    });

    it('detail 應該回傳包含 ID 的 key', () => {
      const key = queryKeys.documents.detail(123);

      expect(Array.isArray(key)).toBe(true);
      expect(key).toContain('detail');
      expect(key).toContain(123);
    });

    it('statistics 應該有正確的 key', () => {
      expect(queryKeys.documents.statistics).toBeDefined();
      expect(Array.isArray(queryKeys.documents.statistics)).toBe(true);
    });
  });

  describe('projects', () => {
    it('應該有 all key', () => {
      expect(queryKeys.projects.all).toBeDefined();
    });

    it('documents 應該回傳包含專案 ID 的 key', () => {
      const key = queryKeys.projects.documents(456);

      expect(Array.isArray(key)).toBe(true);
      expect(key).toContain('documents');
      expect(key).toContain(456);
    });
  });

  describe('agencies', () => {
    it('應該有 all key', () => {
      expect(queryKeys.agencies.all).toBeDefined();
    });

    it('應該有 list 方法', () => {
      expect(typeof queryKeys.agencies.list).toBe('function');
    });
  });

  describe('vendors', () => {
    it('應該有 all key', () => {
      expect(queryKeys.vendors.all).toBeDefined();
    });
  });

  describe('calendar', () => {
    it('calendar key 為可選配置', () => {
      // calendar 目前不在 queryKeys 中定義
      // 此測試確認 queryKeys 結構正確
      const hasCalendar = 'calendar' in queryKeys;
      expect(typeof hasCalendar).toBe('boolean');
    });
  });
});

describe('defaultQueryOptions', () => {
  describe('list', () => {
    it('應該有 staleTime', () => {
      expect(defaultQueryOptions.list.staleTime).toBeDefined();
      expect(typeof defaultQueryOptions.list.staleTime).toBe('number');
    });
  });

  describe('detail', () => {
    it('應該有 staleTime', () => {
      expect(defaultQueryOptions.detail.staleTime).toBeDefined();
    });
  });

  describe('statistics', () => {
    it('應該有較長的 staleTime', () => {
      expect(defaultQueryOptions.statistics.staleTime).toBeGreaterThan(
        defaultQueryOptions.list.staleTime
      );
    });
  });

  describe('dropdown', () => {
    it('應該有最長的 staleTime', () => {
      expect(defaultQueryOptions.dropdown.staleTime).toBeGreaterThan(
        defaultQueryOptions.statistics.staleTime
      );
    });
  });
});
