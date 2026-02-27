/**
 * useAdminUsers Hook 單元測試
 *
 * 管理員使用者管理 React Query Hooks 測試
 * 涵蓋：查詢、CRUD、批量操作、快取失效
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// ---------------------------------------------------------------------------
// Hoisted mocks
// ---------------------------------------------------------------------------

const { mockAdminUsersApi } = vi.hoisted(() => ({
  mockAdminUsersApi: {
    getUsers: vi.fn(),
    getAvailablePermissions: vi.fn(),
    getUserPermissions: vi.fn(),
    createUser: vi.fn(),
    updateUser: vi.fn(),
    deleteUser: vi.fn(),
    updateUserPermissions: vi.fn(),
    batchUpdateStatus: vi.fn(),
    batchDelete: vi.fn(),
    batchUpdateRole: vi.fn(),
  },
}));

vi.mock('../../../api/adminUsersApi', () => ({
  adminUsersApi: mockAdminUsersApi,
}));

vi.mock('../../../config/queryConfig', () => ({
  defaultQueryOptions: {
    list: { staleTime: 0, gcTime: 0, refetchOnWindowFocus: false },
    dropdown: { staleTime: 0, gcTime: 0, refetchOnWindowFocus: false, refetchOnMount: false },
    detail: { staleTime: 0, gcTime: 0, refetchOnWindowFocus: false },
  },
}));

vi.mock('../../../utils/logger', () => ({
  logger: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

import {
  useAdminUsers,
  useAvailablePermissions,
  useUserPermissions,
  useCreateAdminUser,
  useUpdateAdminUser,
  useDeleteAdminUser,
  useUpdateUserPermissions,
  useBatchUpdateStatus,
  useBatchDeleteUsers,
  useBatchUpdateRole,
  useAdminUsersPage,
} from '../useAdminUsers';

// ---------------------------------------------------------------------------
// 測試輔助
// ---------------------------------------------------------------------------

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

function createWrapper() {
  const queryClient = createQueryClient();
  return {
    wrapper: ({ children }: { children: React.ReactNode }) =>
      React.createElement(QueryClientProvider, { client: queryClient }, children),
    queryClient,
  };
}

/** 模擬使用者列表回應 */
const mockUsersResponse = {
  users: [
    { id: 1, username: 'user1', full_name: 'User One', email: 'u1@test.com', role: 'user', is_admin: false, is_active: true },
    { id: 2, username: 'admin1', full_name: 'Admin One', email: 'a1@test.com', role: 'admin', is_admin: true, is_active: true },
  ],
  items: [],
  total: 2,
  page: 1,
  per_page: 20,
};

/** 模擬可用權限回應 */
const mockPermissionsResponse = {
  roles: [
    { key: 'user', name_zh: '一般使用者', name_en: 'User' },
    { key: 'admin', name_zh: '管理員', name_en: 'Admin' },
    { key: 'superuser', name_zh: '超級管理員', name_en: 'Super Admin' },
  ],
  permissions: ['documents:read', 'documents:create', 'admin:users'],
};

/** 模擬使用者權限回應 */
const mockUserPermissionsResponse = {
  user_id: 1,
  permissions: ['documents:read'],
  role: 'user',
};

/** 模擬新建使用者 */
const mockCreatedUser = {
  id: 3,
  username: 'newuser',
  full_name: 'New User',
  email: 'new@test.com',
  role: 'user',
  is_admin: false,
  is_active: true,
};

// ---------------------------------------------------------------------------
// 測試開始
// ---------------------------------------------------------------------------

describe('useAdminUsers Hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAdminUsersApi.getUsers.mockResolvedValue(mockUsersResponse);
    mockAdminUsersApi.getAvailablePermissions.mockResolvedValue(mockPermissionsResponse);
    mockAdminUsersApi.getUserPermissions.mockResolvedValue(mockUserPermissionsResponse);
    mockAdminUsersApi.createUser.mockResolvedValue(mockCreatedUser);
    mockAdminUsersApi.updateUser.mockResolvedValue({ ...mockCreatedUser, full_name: 'Updated' });
    mockAdminUsersApi.deleteUser.mockResolvedValue(undefined);
    mockAdminUsersApi.updateUserPermissions.mockResolvedValue(mockUserPermissionsResponse);
    mockAdminUsersApi.batchUpdateStatus.mockResolvedValue(undefined);
    mockAdminUsersApi.batchDelete.mockResolvedValue(undefined);
    mockAdminUsersApi.batchUpdateRole.mockResolvedValue(undefined);
  });

  // =========================================================================
  // 1. useAdminUsers — 使用者列表查詢
  // =========================================================================

  describe('useAdminUsers — 使用者列表查詢', () => {
    it('應成功載入使用者列表', async () => {
      const { wrapper } = createWrapper();
      const { result } = renderHook(() => useAdminUsers(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockUsersResponse);
      expect(mockAdminUsersApi.getUsers).toHaveBeenCalledWith(undefined);
    });

    it('應使用分頁參數查詢', async () => {
      const { wrapper } = createWrapper();
      const params = { page: 2, per_page: 10, role: 'admin' };

      const { result } = renderHook(() => useAdminUsers(params), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockAdminUsersApi.getUsers).toHaveBeenCalledWith(params);
    });

    it('應使用搜尋參數查詢', async () => {
      const { wrapper } = createWrapper();
      const params = { search: 'admin', status: 'active' };

      renderHook(() => useAdminUsers(params), { wrapper });

      await waitFor(() => {
        expect(mockAdminUsersApi.getUsers).toHaveBeenCalledWith(params);
      });
    });

    it('API 錯誤時應進入 error 狀態', async () => {
      mockAdminUsersApi.getUsers.mockRejectedValue(new Error('Server error'));
      const { wrapper } = createWrapper();

      const { result } = renderHook(() => useAdminUsers(), { wrapper });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error).toBeInstanceOf(Error);
      expect(result.current.error?.message).toBe('Server error');
    });
  });

  // =========================================================================
  // 2. useAvailablePermissions — 可用權限查詢
  // =========================================================================

  describe('useAvailablePermissions — 可用權限查詢', () => {
    it('應成功載入可用權限', async () => {
      const { wrapper } = createWrapper();
      const { result } = renderHook(() => useAvailablePermissions(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockPermissionsResponse);
      expect(result.current.data?.roles).toHaveLength(3);
    });
  });

  // =========================================================================
  // 3. useUserPermissions — 單一使用者權限查詢
  // =========================================================================

  describe('useUserPermissions — 使用者權限查詢', () => {
    it('userId 有效時應查詢權限', async () => {
      const { wrapper } = createWrapper();
      const { result } = renderHook(() => useUserPermissions(1), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockUserPermissionsResponse);
      expect(mockAdminUsersApi.getUserPermissions).toHaveBeenCalledWith(1);
    });

    it('userId 為 null 時不應查詢（enabled=false）', async () => {
      const { wrapper } = createWrapper();
      const { result } = renderHook(() => useUserPermissions(null), { wrapper });

      // 不應呼叫 API
      expect(mockAdminUsersApi.getUserPermissions).not.toHaveBeenCalled();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.fetchStatus).toBe('idle');
    });
  });

  // =========================================================================
  // 4. useCreateAdminUser — 建立使用者
  // =========================================================================

  describe('useCreateAdminUser — 建立使用者', () => {
    it('應成功建立使用者', async () => {
      const { wrapper, queryClient } = createWrapper();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useCreateAdminUser(), { wrapper });

      await act(async () => {
        const created = await result.current.mutateAsync({
          username: 'newuser',
          full_name: 'New User',
          email: 'new@test.com',
          role: 'user',
        });
        expect(created).toEqual(mockCreatedUser);
      });

      expect(mockAdminUsersApi.createUser).toHaveBeenCalledWith({
        username: 'newuser',
        full_name: 'New User',
        email: 'new@test.com',
        role: 'user',
      });

      // 應失效快取
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ['admin', 'users'] })
      );
    });

    it('建立失敗時應拋出錯誤', async () => {
      mockAdminUsersApi.createUser.mockRejectedValue(new Error('Email already exists'));
      const { wrapper } = createWrapper();

      const { result } = renderHook(() => useCreateAdminUser(), { wrapper });

      let caughtError: Error | null = null;
      await act(async () => {
        try {
          await result.current.mutateAsync({ username: 'dup' });
        } catch (e) {
          caughtError = e as Error;
        }
      });

      expect(caughtError).toBeInstanceOf(Error);
      expect(caughtError!.message).toBe('Email already exists');
    });
  });

  // =========================================================================
  // 5. useUpdateAdminUser — 更新使用者
  // =========================================================================

  describe('useUpdateAdminUser — 更新使用者', () => {
    it('應成功更新使用者', async () => {
      const { wrapper, queryClient } = createWrapper();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useUpdateAdminUser(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync({
          userId: 1,
          data: { full_name: 'Updated Name' },
        });
      });

      expect(mockAdminUsersApi.updateUser).toHaveBeenCalledWith(1, { full_name: 'Updated Name' });
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ['admin', 'users'] })
      );
    });
  });

  // =========================================================================
  // 6. useDeleteAdminUser — 刪除使用者
  // =========================================================================

  describe('useDeleteAdminUser — 刪除使用者', () => {
    it('應成功刪除使用者', async () => {
      const { wrapper, queryClient } = createWrapper();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useDeleteAdminUser(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync(1);
      });

      expect(mockAdminUsersApi.deleteUser).toHaveBeenCalledWith(1);
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ['admin', 'users'] })
      );
    });

    it('刪除失敗時應拋出錯誤', async () => {
      mockAdminUsersApi.deleteUser.mockRejectedValue(new Error('Cannot delete admin'));
      const { wrapper } = createWrapper();

      const { result } = renderHook(() => useDeleteAdminUser(), { wrapper });

      let caughtError: Error | null = null;
      await act(async () => {
        try {
          await result.current.mutateAsync(999);
        } catch (e) {
          caughtError = e as Error;
        }
      });

      expect(caughtError).toBeInstanceOf(Error);
      expect(caughtError!.message).toBe('Cannot delete admin');
    });
  });

  // =========================================================================
  // 7. useUpdateUserPermissions — 更新使用者權限
  // =========================================================================

  describe('useUpdateUserPermissions — 更新使用者權限', () => {
    it('應成功更新權限並失效相關快取', async () => {
      const { wrapper, queryClient } = createWrapper();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useUpdateUserPermissions(), { wrapper });

      const permData = {
        userId: 1,
        data: { user_id: 1, permissions: ['documents:read', 'documents:create'], role: 'user' },
      };

      await act(async () => {
        await result.current.mutateAsync(permData);
      });

      expect(mockAdminUsersApi.updateUserPermissions).toHaveBeenCalledWith(1, permData.data);

      // 應失效使用者列表和使用者權限快取
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ['admin', 'users'] })
      );
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ['admin', 'permissions', 'user', 1] })
      );
    });
  });

  // =========================================================================
  // 8. 批量操作
  // =========================================================================

  describe('useBatchUpdateStatus — 批量更新狀態', () => {
    it('應成功批量更新使用者狀態', async () => {
      const { wrapper, queryClient } = createWrapper();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useBatchUpdateStatus(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync({
          userIds: [1, 2, 3],
          status: 'inactive',
          isActive: false,
        });
      });

      expect(mockAdminUsersApi.batchUpdateStatus).toHaveBeenCalledWith(
        [1, 2, 3], 'inactive', false
      );
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ['admin', 'users'] })
      );
    });
  });

  describe('useBatchDeleteUsers — 批量刪除使用者', () => {
    it('應成功批量刪除使用者', async () => {
      const { wrapper, queryClient } = createWrapper();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useBatchDeleteUsers(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync([4, 5]);
      });

      expect(mockAdminUsersApi.batchDelete).toHaveBeenCalledWith([4, 5]);
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ['admin', 'users'] })
      );
    });

    it('批量刪除失敗時應拋出錯誤', async () => {
      mockAdminUsersApi.batchDelete.mockRejectedValue(new Error('Batch delete failed'));
      const { wrapper } = createWrapper();

      const { result } = renderHook(() => useBatchDeleteUsers(), { wrapper });

      let caughtError: Error | null = null;
      await act(async () => {
        try {
          await result.current.mutateAsync([999]);
        } catch (e) {
          caughtError = e as Error;
        }
      });

      expect(caughtError).toBeInstanceOf(Error);
      expect(caughtError!.message).toBe('Batch delete failed');
    });
  });

  describe('useBatchUpdateRole — 批量更新角色', () => {
    it('應成功批量更新角色', async () => {
      const { wrapper, queryClient } = createWrapper();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useBatchUpdateRole(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync({
          userIds: [1, 2],
          role: 'admin',
          permissions: ['documents:read', 'admin:users'],
        });
      });

      expect(mockAdminUsersApi.batchUpdateRole).toHaveBeenCalledWith(
        [1, 2], 'admin', ['documents:read', 'admin:users']
      );
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ['admin', 'users'] })
      );
    });
  });

  // =========================================================================
  // 9. useAdminUsersPage — 組合 Hook
  // =========================================================================

  describe('useAdminUsersPage — 組合 Hook', () => {
    it('應回傳使用者列表和權限資料', async () => {
      const { wrapper } = createWrapper();
      const { result } = renderHook(() => useAdminUsersPage(), { wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.users).toEqual(mockUsersResponse.users);
      expect(result.current.total).toBe(2);
      expect(result.current.roles).toEqual(mockPermissionsResponse.roles);
    });

    it('應提供所有操作方法', async () => {
      const { wrapper } = createWrapper();
      const { result } = renderHook(() => useAdminUsersPage(), { wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      // 單一操作方法
      expect(typeof result.current.createUser).toBe('function');
      expect(typeof result.current.updateUser).toBe('function');
      expect(typeof result.current.deleteUser).toBe('function');
      expect(typeof result.current.updatePermissions).toBe('function');

      // 批量操作方法
      expect(typeof result.current.batchUpdateStatus).toBe('function');
      expect(typeof result.current.batchDelete).toBe('function');
      expect(typeof result.current.batchUpdateRole).toBe('function');

      // refetch
      expect(typeof result.current.refetch).toBe('function');
    });

    it('初始狀態下所有 mutation 應為 idle', async () => {
      const { wrapper } = createWrapper();
      const { result } = renderHook(() => useAdminUsersPage(), { wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.isCreating).toBe(false);
      expect(result.current.isUpdating).toBe(false);
      expect(result.current.isDeleting).toBe(false);
      expect(result.current.isUpdatingPermissions).toBe(false);
      expect(result.current.isBatchUpdating).toBe(false);
    });

    it('使用參數應傳遞至查詢', async () => {
      const { wrapper } = createWrapper();
      const params = { page: 3, per_page: 5, role: 'user' };

      const { result } = renderHook(() => useAdminUsersPage(params), { wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(mockAdminUsersApi.getUsers).toHaveBeenCalledWith(params);
    });

    it('createUser 應透過 mutation 建立使用者', async () => {
      const { wrapper } = createWrapper();
      const { result } = renderHook(() => useAdminUsersPage(), { wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        const created = await result.current.createUser({
          username: 'newuser',
          email: 'new@test.com',
        });
        expect(created).toEqual(mockCreatedUser);
      });

      expect(mockAdminUsersApi.createUser).toHaveBeenCalled();
    });

    it('updateUser 應透過 mutation 更新使用者', async () => {
      const { wrapper } = createWrapper();
      const { result } = renderHook(() => useAdminUsersPage(), { wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        await result.current.updateUser({
          userId: 1,
          data: { full_name: 'Updated' },
        });
      });

      expect(mockAdminUsersApi.updateUser).toHaveBeenCalledWith(1, { full_name: 'Updated' });
    });

    it('deleteUser 應透過 mutation 刪除使用者', async () => {
      const { wrapper } = createWrapper();
      const { result } = renderHook(() => useAdminUsersPage(), { wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        await result.current.deleteUser(2);
      });

      expect(mockAdminUsersApi.deleteUser).toHaveBeenCalledWith(2);
    });

    it('API 回傳空資料時應使用預設值', async () => {
      mockAdminUsersApi.getUsers.mockResolvedValue({ users: undefined, total: undefined });
      mockAdminUsersApi.getAvailablePermissions.mockResolvedValue({ roles: undefined });

      const { wrapper } = createWrapper();
      const { result } = renderHook(() => useAdminUsersPage(), { wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.users).toEqual([]);
      expect(result.current.total).toBe(0);
      expect(result.current.roles).toEqual([]);
    });

    it('API 錯誤時 isError 應為 true', async () => {
      mockAdminUsersApi.getUsers.mockRejectedValue(new Error('Forbidden'));

      const { wrapper } = createWrapper();
      const { result } = renderHook(() => useAdminUsersPage(), { wrapper });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error).toBeInstanceOf(Error);
    });
  });

  // =========================================================================
  // 10. 邊界情況
  // =========================================================================

  describe('邊界情況', () => {
    it('批量操作空陣列時應正常呼叫 API', async () => {
      const { wrapper } = createWrapper();
      const { result } = renderHook(() => useBatchDeleteUsers(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync([]);
      });

      expect(mockAdminUsersApi.batchDelete).toHaveBeenCalledWith([]);
    });

    it('多個 mutation 可並行操作', async () => {
      const { wrapper } = createWrapper();
      const { result: createResult } = renderHook(() => useCreateAdminUser(), { wrapper });
      const { result: deleteResult } = renderHook(() => useDeleteAdminUser(), { wrapper });

      await act(async () => {
        await Promise.all([
          createResult.current.mutateAsync({ username: 'a' }),
          deleteResult.current.mutateAsync(1),
        ]);
      });

      expect(mockAdminUsersApi.createUser).toHaveBeenCalled();
      expect(mockAdminUsersApi.deleteUser).toHaveBeenCalled();
    });

    it('updatePermissions 應傳遞正確的使用者 ID 和權限資料', async () => {
      const { wrapper } = createWrapper();
      const { result } = renderHook(() => useAdminUsersPage(), { wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      const permData = {
        user_id: 5,
        permissions: ['documents:read', 'documents:create', 'documents:edit'],
        role: 'admin',
      };

      await act(async () => {
        await result.current.updatePermissions({ userId: 5, data: permData });
      });

      expect(mockAdminUsersApi.updateUserPermissions).toHaveBeenCalledWith(5, permData);
    });
  });
});
