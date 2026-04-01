/**
 * 標案檢索 React Query Hooks
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { tenderApi } from '../../api/tenderApi';
import type { TenderSearchParams } from '../../types/tender';

export function useTenderSearch(params: TenderSearchParams | null) {
  return useQuery({
    queryKey: ['tender', 'search', params],
    queryFn: () => tenderApi.search(params!),
    enabled: !!params?.query,
    staleTime: 5 * 60 * 1000,
  });
}

export function useTenderDetail(unitId: string | null, jobNumber: string | null) {
  return useQuery({
    queryKey: ['tender', 'detail', unitId, jobNumber],
    queryFn: () => tenderApi.getDetail(unitId!, jobNumber!),
    enabled: !!unitId && !!jobNumber,
    staleTime: 10 * 60 * 1000,
  });
}

export function useTenderCompanySearch(companyName: string | null, page = 1) {
  return useQuery({
    queryKey: ['tender', 'company', companyName, page],
    queryFn: () => tenderApi.searchByCompany(companyName!, page),
    enabled: !!companyName,
    staleTime: 5 * 60 * 1000,
  });
}

export function useTenderRecommend(keywords?: string[]) {
  return useQuery({
    queryKey: ['tender', 'recommend', keywords],
    queryFn: () => tenderApi.recommend(keywords),
    staleTime: 30 * 60 * 1000,
  });
}

// ========== 訂閱 ==========

export function useTenderSubscriptions() {
  return useQuery({
    queryKey: ['tender', 'subscriptions'],
    queryFn: () => tenderApi.listSubscriptions(),
    staleTime: 60 * 1000,
  });
}

export function useCreateSubscription() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: tenderApi.createSubscription,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tender', 'subscriptions'] }),
  });
}

export function useDeleteSubscription() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: tenderApi.deleteSubscription,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tender', 'subscriptions'] }),
  });
}

// ========== 書籤 ==========

export function useTenderBookmarks() {
  return useQuery({
    queryKey: ['tender', 'bookmarks'],
    queryFn: () => tenderApi.listBookmarks(),
    staleTime: 60 * 1000,
  });
}

export function useCreateBookmark() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: tenderApi.createBookmark,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tender', 'bookmarks'] }),
  });
}

export function useUpdateBookmark() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: tenderApi.updateBookmark,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tender', 'bookmarks'] }),
  });
}

export function useDeleteBookmark() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: tenderApi.deleteBookmark,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tender', 'bookmarks'] }),
  });
}
