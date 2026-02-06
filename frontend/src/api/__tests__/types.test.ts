/**
 * API 型別守衛與轉換工具測試
 *
 * 測試 api/types.ts 中所有匯出的型別守衛函數和回應轉換工具
 */
import { describe, it, expect } from 'vitest';
import {
  isErrorResponse,
  isSuccessResponse,
  isPaginatedResponse,
  isLegacyListResponse,
  normalizePaginatedResponse,
  ErrorCode,
} from '../types';
import type {
  ErrorResponse,
  SuccessResponse,
  PaginatedResponse,
  LegacyListResponse,
} from '../types';

// ============================================================================
// isErrorResponse - 錯誤回應型別守衛
// ============================================================================

describe('isErrorResponse', () => {
  it('標準錯誤回應應該回傳 true', () => {
    const response: ErrorResponse = {
      success: false,
      error: {
        code: ErrorCode.NOT_FOUND,
        message: '找不到資源',
      },
      timestamp: '2026-02-06T12:00:00Z',
    };
    expect(isErrorResponse(response)).toBe(true);
  });

  it('含有詳細錯誤資訊的回應應該回傳 true', () => {
    const response: ErrorResponse = {
      success: false,
      error: {
        code: ErrorCode.VALIDATION_ERROR,
        message: '驗證失敗',
        details: [{ field: 'name', message: '名稱不可為空' }],
      },
      timestamp: '2026-02-06T12:00:00Z',
    };
    expect(isErrorResponse(response)).toBe(true);
  });

  it('成功回應應該回傳 false', () => {
    const response = { success: true, data: {} };
    expect(isErrorResponse(response)).toBe(false);
  });

  it('null 應該回傳 false', () => {
    expect(isErrorResponse(null)).toBe(false);
  });

  it('undefined 應該回傳 false', () => {
    expect(isErrorResponse(undefined)).toBe(false);
  });

  it('非物件型別應該回傳 false', () => {
    expect(isErrorResponse('string')).toBe(false);
    expect(isErrorResponse(123)).toBe(false);
    expect(isErrorResponse(true)).toBe(false);
  });

  it('缺少 error 欄位的失敗回應應該回傳 false', () => {
    const response = { success: false, message: 'error' };
    expect(isErrorResponse(response)).toBe(false);
  });
});

// ============================================================================
// isSuccessResponse - 成功回應型別守衛
// ============================================================================

describe('isSuccessResponse', () => {
  it('標準成功回應應該回傳 true', () => {
    const response: SuccessResponse<{ id: number }> = {
      success: true,
      data: { id: 1 },
    };
    expect(isSuccessResponse(response)).toBe(true);
  });

  it('含有訊息的成功回應應該回傳 true', () => {
    const response: SuccessResponse = {
      success: true,
      data: null,
      message: '操作成功',
    };
    expect(isSuccessResponse(response)).toBe(true);
  });

  it('錯誤回應應該回傳 false', () => {
    const response = {
      success: false,
      error: { code: 'ERR', message: 'fail' },
    };
    expect(isSuccessResponse(response)).toBe(false);
  });

  it('缺少 data 欄位的回應應該回傳 false', () => {
    const response = { success: true, message: 'ok' };
    expect(isSuccessResponse(response)).toBe(false);
  });

  it('null 應該回傳 false', () => {
    expect(isSuccessResponse(null)).toBe(false);
  });

  it('非物件型別應該回傳 false', () => {
    expect(isSuccessResponse(42)).toBe(false);
  });
});

// ============================================================================
// isPaginatedResponse - 分頁回應型別守衛
// ============================================================================

describe('isPaginatedResponse', () => {
  it('標準分頁回應應該回傳 true', () => {
    const response: PaginatedResponse<{ id: number }> = {
      success: true,
      items: [{ id: 1 }, { id: 2 }],
      pagination: {
        total: 50,
        page: 1,
        limit: 20,
        total_pages: 3,
        has_next: true,
        has_prev: false,
      },
    };
    expect(isPaginatedResponse(response)).toBe(true);
  });

  it('空項目的分頁回應應該回傳 true', () => {
    const response: PaginatedResponse = {
      success: true,
      items: [],
      pagination: {
        total: 0,
        page: 1,
        limit: 20,
        total_pages: 0,
        has_next: false,
        has_prev: false,
      },
    };
    expect(isPaginatedResponse(response)).toBe(true);
  });

  it('缺少 pagination 欄位應該回傳 false', () => {
    const response = { success: true, items: [] };
    expect(isPaginatedResponse(response)).toBe(false);
  });

  it('缺少 items 欄位應該回傳 false', () => {
    const response = { success: true, pagination: { total: 0 } };
    expect(isPaginatedResponse(response)).toBe(false);
  });

  it('success 為 false 應該回傳 false', () => {
    const response = {
      success: false,
      items: [],
      pagination: { total: 0 },
    };
    expect(isPaginatedResponse(response)).toBe(false);
  });

  it('null 應該回傳 false', () => {
    expect(isPaginatedResponse(null)).toBe(false);
  });
});

// ============================================================================
// isLegacyListResponse - 舊版列表回應型別守衛
// ============================================================================

describe('isLegacyListResponse', () => {
  it('含有 total 和 items 的舊格式應該回傳 true', () => {
    const response = {
      items: [{ id: 1 }],
      total: 10,
      page: 1,
      limit: 20,
    };
    expect(isLegacyListResponse(response)).toBe(true);
  });

  it('含有 documents 鍵的舊格式應該回傳 true', () => {
    const response = {
      documents: [{ id: 1 }],
      total: 5,
    };
    expect(isLegacyListResponse(response)).toBe(true);
  });

  it('含有 projects 鍵的舊格式應該回傳 true', () => {
    const response = {
      projects: [],
      total: 0,
      page: 1,
    };
    expect(isLegacyListResponse(response)).toBe(true);
  });

  it('含有 pagination 欄位的新格式應該回傳 false', () => {
    const response = {
      total: 10,
      items: [],
      pagination: { total: 10 },
    };
    expect(isLegacyListResponse(response)).toBe(false);
  });

  it('含有 success 欄位的回應應該回傳 false', () => {
    const response = {
      success: true,
      total: 10,
      items: [],
    };
    expect(isLegacyListResponse(response)).toBe(false);
  });

  it('null 應該回傳 false', () => {
    expect(isLegacyListResponse(null)).toBe(false);
  });

  it('缺少 total 欄位應該回傳 false', () => {
    const response = { items: [{ id: 1 }] };
    expect(isLegacyListResponse(response)).toBe(false);
  });
});

// ============================================================================
// normalizePaginatedResponse - 分頁回應正規化
// ============================================================================

describe('normalizePaginatedResponse', () => {
  it('新格式的分頁回應應該直接透傳', () => {
    const response: PaginatedResponse<{ id: number }> = {
      success: true,
      items: [{ id: 1 }],
      pagination: {
        total: 1,
        page: 1,
        limit: 20,
        total_pages: 1,
        has_next: false,
        has_prev: false,
      },
    };
    const result = normalizePaginatedResponse(response);
    expect(result).toBe(response); // 同一個參照
  });

  it('應該正確轉換含有 items 的舊格式', () => {
    const legacy: LegacyListResponse<{ id: number }> = {
      items: [{ id: 1 }, { id: 2 }],
      total: 50,
      page: 2,
      limit: 20,
    };
    const result = normalizePaginatedResponse(legacy);

    expect(result.success).toBe(true);
    expect(result.items).toEqual([{ id: 1 }, { id: 2 }]);
    expect(result.pagination.total).toBe(50);
    expect(result.pagination.page).toBe(2);
    expect(result.pagination.limit).toBe(20);
    expect(result.pagination.total_pages).toBe(3); // Math.ceil(50/20)
    expect(result.pagination.has_next).toBe(true);
    expect(result.pagination.has_prev).toBe(true);
  });

  it('應該正確轉換含有 documents 的舊格式', () => {
    const legacy: LegacyListResponse<{ id: number }> = {
      documents: [{ id: 1 }],
      total: 1,
      page: 1,
      per_page: 10,
    };
    const result = normalizePaginatedResponse(legacy);

    expect(result.items).toEqual([{ id: 1 }]);
    expect(result.pagination.limit).toBe(10); // per_page 作為 limit
  });

  it('應該正確轉換含有 projects 的舊格式', () => {
    const legacy: LegacyListResponse<{ name: string }> = {
      projects: [{ name: 'Project A' }],
      total: 1,
    };
    const result = normalizePaginatedResponse(legacy);

    expect(result.items).toEqual([{ name: 'Project A' }]);
    expect(result.pagination.page).toBe(1); // defaultPage
    expect(result.pagination.limit).toBe(20); // defaultLimit
  });

  it('應該正確轉換含有 vendors 的舊格式', () => {
    const legacy: LegacyListResponse<{ id: number }> = {
      vendors: [{ id: 10 }],
      total: 1,
    };
    const result = normalizePaginatedResponse(legacy);
    expect(result.items).toEqual([{ id: 10 }]);
  });

  it('應該正確轉換含有 users 的舊格式', () => {
    const legacy: LegacyListResponse<{ id: number }> = {
      users: [{ id: 5 }],
      total: 1,
    };
    const result = normalizePaginatedResponse(legacy);
    expect(result.items).toEqual([{ id: 5 }]);
  });

  it('所有列表鍵都不存在時應該回傳空陣列', () => {
    const legacy: LegacyListResponse<unknown> = {
      total: 0,
    };
    const result = normalizePaginatedResponse(legacy);
    expect(result.items).toEqual([]);
  });

  it('應該使用自訂的預設分頁參數', () => {
    const legacy: LegacyListResponse<unknown> = {
      total: 100,
    };
    const result = normalizePaginatedResponse(legacy, 3, 50);

    expect(result.pagination.page).toBe(3);
    expect(result.pagination.limit).toBe(50);
    expect(result.pagination.total_pages).toBe(2); // Math.ceil(100/50)
  });

  it('應該正確計算 has_next 和 has_prev', () => {
    // 第一頁
    const firstPage: LegacyListResponse<unknown> = {
      items: [],
      total: 60,
      page: 1,
      limit: 20,
    };
    const resultFirst = normalizePaginatedResponse(firstPage);
    expect(resultFirst.pagination.has_next).toBe(true);
    expect(resultFirst.pagination.has_prev).toBe(false);

    // 最後一頁
    const lastPage: LegacyListResponse<unknown> = {
      items: [],
      total: 60,
      page: 3,
      limit: 20,
    };
    const resultLast = normalizePaginatedResponse(lastPage);
    expect(resultLast.pagination.has_next).toBe(false);
    expect(resultLast.pagination.has_prev).toBe(true);
  });

  it('應該優先使用 total_pages 而非 pages', () => {
    const legacy: LegacyListResponse<unknown> = {
      items: [],
      total: 100,
      page: 1,
      limit: 10,
      total_pages: 5, // 優先使用此值
      pages: 10,       // 不使用此值
    };
    const result = normalizePaginatedResponse(legacy);
    expect(result.pagination.total_pages).toBe(5);
  });

  it('缺少 total_pages 時應該回退到 pages 欄位', () => {
    const legacy: LegacyListResponse<unknown> = {
      items: [],
      total: 100,
      page: 1,
      limit: 10,
      pages: 10,
    };
    const result = normalizePaginatedResponse(legacy);
    expect(result.pagination.total_pages).toBe(10);
  });
});
