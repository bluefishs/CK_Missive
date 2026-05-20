/**
 * ADR-0034 動態 Role Permissions hook (React Query)。
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { rolePermissionsApi } from '../../api/rolePermissionsApi';

export const ROLE_PERMISSIONS_QUERY_KEY = ['admin', 'role-permissions'] as const;

export const useRolePermissionsList = () => {
  return useQuery({
    queryKey: [...ROLE_PERMISSIONS_QUERY_KEY, 'list'],
    queryFn: () => rolePermissionsApi.list(),
    staleTime: 30_000,
    refetchOnMount: 'always',
  });
};

export const useRolePermissionsDetail = (role: string | null | undefined) => {
  return useQuery({
    queryKey: [...ROLE_PERMISSIONS_QUERY_KEY, 'detail', role],
    queryFn: () => rolePermissionsApi.get(role!),
    enabled: !!role,
    staleTime: 30_000,
    refetchOnMount: 'always',
  });
};

export const useAvailablePermissions = () => {
  return useQuery({
    queryKey: [...ROLE_PERMISSIONS_QUERY_KEY, 'available'],
    queryFn: () => rolePermissionsApi.getAvailable(),
    staleTime: 60_000,
  });
};

export const useUpdateRolePermissions = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ role, permissions, note }: { role: string; permissions: string[]; note?: string }) =>
      rolePermissionsApi.update(role, permissions, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ROLE_PERMISSIONS_QUERY_KEY });
      // user permissions cache 也要 refetch（影響當前 user 介面）
      queryClient.invalidateQueries({ queryKey: ['userPermissions'] });
    },
  });
};

/** 批次同步指定 role 對應的所有 user.permissions（修 role 後補齊舊用戶） */
export const useSyncRoleUsers = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ role, onlyOutdated }: { role: string; onlyOutdated?: boolean }) =>
      rolePermissionsApi.syncUsers(role, onlyOutdated ?? true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['userPermissions'] });
      // v6.10.1 L39 修：原 ['admin-users'] silent dead → 用 adminUserKeys 真實 prefix
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
    },
  });
};

/** 取 nav 階層樹 + perm 反查（給「依選單階層」編輯介面） */
export const useNavTree = (role: string | null | undefined) => {
  return useQuery({
    queryKey: [...ROLE_PERMISSIONS_QUERY_KEY, 'nav-tree', role],
    queryFn: () => rolePermissionsApi.getNavTree(role || undefined),
    enabled: !!role,
    staleTime: 60_000,
  });
};
