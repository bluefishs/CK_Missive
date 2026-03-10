/**
 * 部門選項 React Query Hook
 *
 * 從 DB 動態載入部門列表，取代硬編碼常數。
 *
 * @version 1.0.0
 * @date 2026-03-06
 */
import { useQuery } from '@tanstack/react-query';
import { usersApi } from '../../api/usersApi';

/**
 * 取得部門選項列表（DB 驅動，5 分鐘快取）
 */
export const useDepartments = () => {
  return useQuery({
    queryKey: ['departments'],
    queryFn: () => usersApi.getDepartments(),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
};
