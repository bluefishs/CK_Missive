/**
 * usersApi 單元測試
 * usersApi Unit Tests
 *
 * 測試使用者管理 API 服務層方法
 *
 * 執行方式:
 *   cd frontend && npx vitest run src/api/__tests__/usersApi.test.ts
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock apiClient
vi.mock('../client', () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
    postList: vi.fn(),
  },
  ApiException: class ApiException extends Error {
    code: string;
    statusCode: number;
    constructor(code: string, message: string, statusCode: number = 500) {
      super(message);
      this.code = code;
      this.statusCode = statusCode;
      this.name = 'ApiException';
    }
  },
}));

// Mock endpoints
vi.mock('../endpoints', () => ({
  API_ENDPOINTS: {
    USERS: {
      LIST: '/users/list',
      CREATE: '/users',
      DETAIL: (id: number) => `/users/${id}/detail`,
      UPDATE: (id: number) => `/users/${id}/update`,
      DELETE: (id: number) => `/users/${id}/delete`,
      STATUS: (id: number) => `/users/${id}/status`,
    },
  },
}));

import { usersApi } from '../usersApi';
import { apiClient, ApiException } from '../client';

// ============================================================================
// Mock 資料
// ============================================================================

const mockUser = {
  id: 1,
  username: 'testuser',
  email: 'test@example.com',
  full_name: '測試使用者',
  role: 'user',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const mockPaginatedResponse = {
  success: true as const,
  items: [mockUser],
  pagination: {
    total: 1,
    page: 1,
    limit: 20,
    total_pages: 1,
    has_next: false,
    has_prev: false,
  },
};

// ============================================================================
// usersApi.getUsers 測試
// ============================================================================

describe('usersApi.getUsers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 postList 呼叫正確的端點', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await usersApi.getUsers();

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/users/list',
      expect.objectContaining({
        page: 1,
        limit: 20,
        sort_by: 'id',
        sort_order: 'asc',
      })
    );
  });

  it('應該正確傳遞搜尋和篩選參數', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await usersApi.getUsers({
      page: 2,
      limit: 10,
      search: '測試',
      role: 'admin',
      is_active: true,
    });

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/users/list',
      expect.objectContaining({
        page: 2,
        limit: 10,
        search: '測試',
        role: 'admin',
        is_active: true,
        sort_by: 'id',
        sort_order: 'asc',
      })
    );
  });

  it('應該正確傳遞排序參數', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await usersApi.getUsers({
      sort_by: 'username',
      sort_order: 'desc',
    });

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/users/list',
      expect.objectContaining({
        sort_by: 'username',
        sort_order: 'desc',
      })
    );
  });

  it('不應該傳遞 undefined 的可選參數', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await usersApi.getUsers({ page: 1 });

    const calledParams = vi.mocked(apiClient.postList).mock.calls[0]![1] as Record<string, unknown>;
    expect(calledParams).not.toHaveProperty('search');
    expect(calledParams).not.toHaveProperty('role');
    expect(calledParams).not.toHaveProperty('is_active');
  });

  it('應該傳遞 is_active 為 false 的篩選條件', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await usersApi.getUsers({ is_active: false });

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/users/list',
      expect.objectContaining({
        is_active: false,
      })
    );
  });

  it('當 postList 返回 404 時應該回退到 POST API（舊版格式）', async () => {
    const apiError = new ApiException('NOT_FOUND', 'Not Found', 404);
    vi.mocked(apiClient.postList).mockRejectedValue(apiError);

    const legacyResponse = {
      items: [mockUser],
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    };
    vi.mocked(apiClient.post).mockResolvedValue(legacyResponse);

    const result = await usersApi.getUsers();

    expect(apiClient.post).toHaveBeenCalledWith(
      '/users/list',
      expect.objectContaining({
        skip: 0,
        limit: 100,
      })
    );
    // 應回傳正規化後的分頁回應
    expect(result).toHaveProperty('items');
    expect(result).toHaveProperty('pagination');
  });

  it('當 postList 返回 404 且帶有搜尋參數時回退應傳遞搜尋參數', async () => {
    const apiError = new ApiException('NOT_FOUND', 'Not Found', 404);
    vi.mocked(apiClient.postList).mockRejectedValue(apiError);

    const legacyResponse = {
      items: [mockUser],
      total: 1,
      page: 1,
      page_size: 10,
      total_pages: 1,
    };
    vi.mocked(apiClient.post).mockResolvedValue(legacyResponse);

    await usersApi.getUsers({
      page: 3,
      limit: 10,
      search: '管理',
      role: 'admin',
      is_active: false,
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      '/users/list',
      expect.objectContaining({
        skip: 20,
        limit: 10,
        search: '管理',
        role: 'admin',
        is_active: false,
      })
    );
  });

  it('當非 404 錯誤時應該拋出錯誤', async () => {
    const apiError = new ApiException('INTERNAL_ERROR', 'Internal Server Error', 500);
    vi.mocked(apiClient.postList).mockRejectedValue(apiError);

    await expect(usersApi.getUsers()).rejects.toThrow('Internal Server Error');
  });
});

// ============================================================================
// usersApi.getUser 測試
// ============================================================================

describe('usersApi.getUser', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 post 呼叫正確的端點取得單一使用者', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(mockUser);

    const result = await usersApi.getUser(1);

    expect(apiClient.post).toHaveBeenCalledWith('/users/1/detail');
    expect(result).toEqual(mockUser);
  });

  it('應該正確拼接 userId 到 URL', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(mockUser);

    await usersApi.getUser(42);

    expect(apiClient.post).toHaveBeenCalledWith('/users/42/detail');
  });
});

// ============================================================================
// usersApi.createUser 測試
// ============================================================================

describe('usersApi.createUser', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 post 呼叫建立端點並傳遞資料', async () => {
    const createData = {
      username: 'newuser',
      email: 'new@example.com',
      full_name: '新使用者',
      role: 'user',
    };

    vi.mocked(apiClient.post).mockResolvedValue({ ...mockUser, ...createData, id: 10 });

    const result = await usersApi.createUser(createData as any);

    expect(apiClient.post).toHaveBeenCalledWith('/users', createData);
    expect(result.username).toBe('newuser');
  });
});

// ============================================================================
// usersApi.updateUser 測試
// ============================================================================

describe('usersApi.updateUser', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 post 呼叫更新端點並傳遞資料', async () => {
    const updateData = { full_name: '更新名稱', role: 'admin' };

    vi.mocked(apiClient.post).mockResolvedValue({ ...mockUser, ...updateData });

    const result = await usersApi.updateUser(1, updateData as any);

    expect(apiClient.post).toHaveBeenCalledWith('/users/1/update', updateData);
    expect(result.full_name).toBe('更新名稱');
    expect(result.role).toBe('admin');
  });
});

// ============================================================================
// usersApi.deleteUser 測試
// ============================================================================

describe('usersApi.deleteUser', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 post 呼叫刪除端點', async () => {
    const deleteResponse = { success: true, message: '刪除成功', deleted_id: 1 };
    vi.mocked(apiClient.post).mockResolvedValue(deleteResponse);

    const result = await usersApi.deleteUser(1);

    expect(apiClient.post).toHaveBeenCalledWith('/users/1/delete');
    expect(result.success).toBe(true);
  });
});

// ============================================================================
// usersApi.updateUserStatus 測試
// ============================================================================

describe('usersApi.updateUserStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 post 呼叫狀態更新端點並傳遞 is_active', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ ...mockUser, is_active: false });

    const result = await usersApi.updateUserStatus(1, false);

    expect(apiClient.post).toHaveBeenCalledWith('/users/1/status', {
      is_active: false,
    });
    expect(result.is_active).toBe(false);
  });

  it('應該正確傳遞 isActive 為 true', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ ...mockUser, is_active: true });

    const result = await usersApi.updateUserStatus(5, true);

    expect(apiClient.post).toHaveBeenCalledWith('/users/5/status', {
      is_active: true,
    });
    expect(result.is_active).toBe(true);
  });
});

// ============================================================================
// usersApi.getUserOptions 測試
// ============================================================================

describe('usersApi.getUserOptions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該從使用者列表轉換為下拉選項格式', async () => {
    const users = [
      { ...mockUser, id: 1, username: 'user1', full_name: '使用者一' },
      { ...mockUser, id: 2, username: 'user2', full_name: undefined },
    ];

    vi.mocked(apiClient.postList).mockResolvedValue({
      ...mockPaginatedResponse,
      items: users,
      pagination: { ...mockPaginatedResponse.pagination, total: 2 },
    });

    const result = await usersApi.getUserOptions();

    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({ id: 1, username: 'user1', full_name: '使用者一' });
    // full_name 為 undefined 時不應包含在選項中
    expect(result[1]).toEqual({ id: 2, username: 'user2' });
  });

  it('預設應該只取得啟用的使用者（activeOnly = true）', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await usersApi.getUserOptions();

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/users/list',
      expect.objectContaining({
        limit: 100,
        is_active: true,
      })
    );
  });

  it('當 activeOnly 為 false 時不應該篩選啟用狀態', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await usersApi.getUserOptions(false);

    const calledParams = vi.mocked(apiClient.postList).mock.calls[0]![1] as Record<string, unknown>;
    expect(calledParams).not.toHaveProperty('is_active');
  });
});

// ============================================================================
// usersApi.searchUsers 測試
// ============================================================================

describe('usersApi.searchUsers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用關鍵字搜尋並返回使用者列表', async () => {
    const searchResults = [
      { ...mockUser, id: 1, username: 'admin1', full_name: '管理員一' },
      { ...mockUser, id: 2, username: 'admin2', full_name: '管理員二' },
    ];

    vi.mocked(apiClient.postList).mockResolvedValue({
      ...mockPaginatedResponse,
      items: searchResults,
    });

    const result = await usersApi.searchUsers('管理', 5);

    expect(result).toHaveLength(2);
    expect(result[0]?.username).toBe('admin1');
  });

  it('應該使用預設 limit 10', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await usersApi.searchUsers('test');

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/users/list',
      expect.objectContaining({
        search: 'test',
        limit: 10,
      })
    );
  });
});
