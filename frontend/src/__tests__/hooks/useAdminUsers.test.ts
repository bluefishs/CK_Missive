/**
 * useAdminUsers hooks 單元測試
 *
 * 測試管理員使用者管理 React Query Hooks
 *
 * 執行方式:
 *   cd frontend && npm run test -- useAdminUsers.test
 *
 * @version 1.0.0
 * @created 2026-03-16
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { createWrapper } from '../../test/testUtils';

// ============================================================================
// Mocks
// ============================================================================

const mockGetUsers = vi.fn();
const mockGetAvailablePermissions = vi.fn();
const mockGetUserPermissions = vi.fn();
const mockCreateUser = vi.fn();
const mockUpdateUser = vi.fn();
const mockDeleteUser = vi.fn();
const mockUpdateUserPermissions = vi.fn();
const mockBatchUpdateStatus = vi.fn();
const mockBatchDelete = vi.fn();
const mockBatchUpdateRole = vi.fn();

vi.mock('../../api/adminUsersApi', () => ({
  adminUsersApi: {
    getUsers: (...args: unknown[]) => mockGetUsers(...args),
    getAvailablePermissions: (...args: unknown[]) => mockGetAvailablePermissions(...args),
    getUserPermissions: (...args: unknown[]) => mockGetUserPermissions(...args),
    createUser: (...args: unknown[]) => mockCreateUser(...args),
    updateUser: (...args: unknown[]) => mockUpdateUser(...args),
    deleteUser: (...args: unknown[]) => mockDeleteUser(...args),
    updateUserPermissions: (...args: unknown[]) => mockUpdateUserPermissions(...args),
    batchUpdateStatus: (...args: unknown[]) => mockBatchUpdateStatus(...args),
    batchDelete: (...args: unknown[]) => mockBatchDelete(...args),
    batchUpdateRole: (...args: unknown[]) => mockBatchUpdateRole(...args),
  },
}));

vi.mock('../../config/queryConfig', () => ({
  defaultQueryOptions: {
    list: { staleTime: 30000 },
    dropdown: { staleTime: 300000 },
    detail: { staleTime: 60000 },
  },
}));

// Import after mocks
import {
  useAdminUsers,
  useAvailablePermissions,
  useUserPermissions,
  useCreateAdminUser,
  useAdminUsersPage,
} from '../../hooks/system/useAdminUsers';

describe('useAdminUsers hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetUsers.mockResolvedValue({ users: [], total: 0 });
    mockGetAvailablePermissions.mockResolvedValue({ roles: [] });
    mockGetUserPermissions.mockResolvedValue({ permissions: [] });
  });

  // ==========================================================================
  // useAdminUsers
  // ==========================================================================

  describe('useAdminUsers', () => {
    it('starts in loading state', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useAdminUsers(), { wrapper });

      expect(result.current.isLoading).toBe(true);
    });

    it('fetches users list successfully', async () => {
      const mockData = {
        users: [{ id: 1, username: 'admin', full_name: '管理員' }],
        total: 1,
      };
      mockGetUsers.mockResolvedValue(mockData);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useAdminUsers(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockData);
      expect(mockGetUsers).toHaveBeenCalledWith(undefined);
    });

    it('passes filter params to API', async () => {
      const params = { page: 1, limit: 10, search: 'test' };
      const wrapper = createWrapper();
      renderHook(() => useAdminUsers(params), { wrapper });

      await waitFor(() => expect(mockGetUsers).toHaveBeenCalledWith(params));
    });
  });

  // ==========================================================================
  // useAvailablePermissions
  // ==========================================================================

  describe('useAvailablePermissions', () => {
    it('fetches available permissions', async () => {
      const mockData = { roles: ['admin', 'user', 'viewer'] };
      mockGetAvailablePermissions.mockResolvedValue(mockData);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useAvailablePermissions(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockData);
    });
  });

  // ==========================================================================
  // useUserPermissions
  // ==========================================================================

  describe('useUserPermissions', () => {
    it('does not fetch when userId is null', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useUserPermissions(null), { wrapper });

      expect(result.current.fetchStatus).toBe('idle');
      expect(mockGetUserPermissions).not.toHaveBeenCalled();
    });

    it('fetches permissions when userId is provided', async () => {
      mockGetUserPermissions.mockResolvedValue({ permissions: ['read', 'write'] });

      const wrapper = createWrapper();
      const { result } = renderHook(() => useUserPermissions(42), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(mockGetUserPermissions).toHaveBeenCalledWith(42);
    });
  });

  // ==========================================================================
  // useCreateAdminUser
  // ==========================================================================

  describe('useCreateAdminUser', () => {
    it('exposes mutateAsync function', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCreateAdminUser(), { wrapper });

      expect(typeof result.current.mutateAsync).toBe('function');
      expect(result.current.isPending).toBe(false);
    });
  });

  // ==========================================================================
  // useAdminUsersPage
  // ==========================================================================

  describe('useAdminUsersPage', () => {
    it('returns default empty state', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useAdminUsersPage(), { wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(result.current.users).toEqual([]);
      expect(result.current.total).toBe(0);
      expect(result.current.roles).toEqual([]);
      expect(result.current.isCreating).toBe(false);
      expect(result.current.isUpdating).toBe(false);
      expect(result.current.isDeleting).toBe(false);
      expect(result.current.isBatchUpdating).toBe(false);
    });

    it('exposes all CRUD and batch mutation functions', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useAdminUsersPage(), { wrapper });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      expect(typeof result.current.createUser).toBe('function');
      expect(typeof result.current.updateUser).toBe('function');
      expect(typeof result.current.deleteUser).toBe('function');
      expect(typeof result.current.updatePermissions).toBe('function');
      expect(typeof result.current.batchUpdateStatus).toBe('function');
      expect(typeof result.current.batchDelete).toBe('function');
      expect(typeof result.current.batchUpdateRole).toBe('function');
    });
  });
});
