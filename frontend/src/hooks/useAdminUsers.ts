/**
 * 管理員使用者管理 React Query Hooks
 *
 * 整合 queryConfig 統一快取策略
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  adminUsersApi,
  AdminUserListParams,
  AdminUserUpdate,
  AdminPermissionUpdate,
} from '../api/adminUsersApi';
import { queryKeys, defaultQueryOptions } from '../config/queryConfig';
import type { User, Permission, UserPermissions } from '../types/api';

// ============================================================================
// 查詢鍵擴展
// ============================================================================

const adminUserKeys = {
  all: ['admin', 'users'] as const,
  lists: () => [...adminUserKeys.all, 'list'] as const,
  list: (filters: object) => [...adminUserKeys.lists(), filters] as const,
  permissions: {
    all: ['admin', 'permissions'] as const,
    available: () => [...adminUserKeys.permissions.all, 'available'] as const,
    user: (userId: number) => [...adminUserKeys.permissions.all, 'user', userId] as const,
  },
};

// ============================================================================
// 查詢 Hooks
// ============================================================================

/**
 * 取得使用者列表
 */
export const useAdminUsers = (params?: AdminUserListParams) => {
  return useQuery({
    queryKey: adminUserKeys.list(params || {}),
    queryFn: () => adminUsersApi.getUsers(params),
    ...defaultQueryOptions.list,
  });
};

/**
 * 取得可用權限列表
 */
export const useAvailablePermissions = () => {
  return useQuery({
    queryKey: adminUserKeys.permissions.available(),
    queryFn: () => adminUsersApi.getAvailablePermissions(),
    ...defaultQueryOptions.dropdown,
  });
};

/**
 * 取得使用者權限
 */
export const useUserPermissions = (userId: number | null) => {
  return useQuery({
    queryKey: adminUserKeys.permissions.user(userId ?? 0),
    queryFn: () => adminUsersApi.getUserPermissions(userId!),
    enabled: !!userId,
    ...defaultQueryOptions.detail,
  });
};

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * 建立使用者
 */
export const useCreateAdminUser = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AdminUserUpdate) => adminUsersApi.createUser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminUserKeys.all });
    },
  });
};

/**
 * 更新使用者
 */
export const useUpdateAdminUser = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ userId, data }: { userId: number; data: AdminUserUpdate }) =>
      adminUsersApi.updateUser(userId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminUserKeys.all });
    },
  });
};

/**
 * 刪除使用者
 */
export const useDeleteAdminUser = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: number) => adminUsersApi.deleteUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminUserKeys.all });
    },
  });
};

/**
 * 更新使用者權限
 */
export const useUpdateUserPermissions = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      userId,
      data,
    }: {
      userId: number;
      data: AdminPermissionUpdate;
    }) => adminUsersApi.updateUserPermissions(userId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: adminUserKeys.all });
      queryClient.invalidateQueries({
        queryKey: adminUserKeys.permissions.user(variables.userId),
      });
    },
  });
};

/**
 * 批量更新使用者狀態
 */
export const useBatchUpdateStatus = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      userIds,
      status,
      isActive,
    }: {
      userIds: number[];
      status: string;
      isActive: boolean;
    }) => adminUsersApi.batchUpdateStatus(userIds, status, isActive),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminUserKeys.all });
    },
  });
};

/**
 * 批量刪除使用者
 */
export const useBatchDeleteUsers = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userIds: number[]) => adminUsersApi.batchDelete(userIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminUserKeys.all });
    },
  });
};

/**
 * 批量更新使用者角色
 */
export const useBatchUpdateRole = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      userIds,
      role,
      permissions,
    }: {
      userIds: number[];
      role: string;
      permissions: string[];
    }) => adminUsersApi.batchUpdateRole(userIds, role, permissions),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminUserKeys.all });
    },
  });
};

// ============================================================================
// 組合 Hook
// ============================================================================

/**
 * 使用者管理頁面 Hook
 *
 * 整合列表、權限與操作方法
 */
export const useAdminUsersPage = (params?: AdminUserListParams) => {
  const usersQuery = useAdminUsers(params);
  const permissionsQuery = useAvailablePermissions();
  const createMutation = useCreateAdminUser();
  const updateMutation = useUpdateAdminUser();
  const deleteMutation = useDeleteAdminUser();
  const updatePermissionsMutation = useUpdateUserPermissions();
  const batchStatusMutation = useBatchUpdateStatus();
  const batchDeleteMutation = useBatchDeleteUsers();
  const batchRoleMutation = useBatchUpdateRole();

  return {
    // 列表資料 (直接從 React Query)
    users: usersQuery.data?.users ?? [],
    total: usersQuery.data?.total ?? 0,
    isLoading: usersQuery.isLoading,
    isError: usersQuery.isError,
    error: usersQuery.error,
    refetch: usersQuery.refetch,

    // 權限資料
    roles: permissionsQuery.data?.roles ?? [],
    isPermissionsLoading: permissionsQuery.isLoading,

    // 單一使用者操作
    createUser: createMutation.mutateAsync,
    updateUser: updateMutation.mutateAsync,
    deleteUser: deleteMutation.mutateAsync,
    updatePermissions: updatePermissionsMutation.mutateAsync,

    // 批量操作
    batchUpdateStatus: batchStatusMutation.mutateAsync,
    batchDelete: batchDeleteMutation.mutateAsync,
    batchUpdateRole: batchRoleMutation.mutateAsync,

    // 操作狀態
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isUpdatingPermissions: updatePermissionsMutation.isPending,
    isBatchUpdating:
      batchStatusMutation.isPending ||
      batchDeleteMutation.isPending ||
      batchRoleMutation.isPending,
  };
};

export default useAdminUsersPage;
