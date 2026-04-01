/**
 * 標案檢索 React Query Hooks
 */
import { useQuery } from '@tanstack/react-query';
import { tenderApi } from '../../api/tenderApi';
import type { TenderSearchParams } from '../../types/tender';

export function useTenderSearch(params: TenderSearchParams | null) {
  return useQuery({
    queryKey: ['tender', 'search', params],
    queryFn: () => tenderApi.search(params!),
    enabled: !!params?.query,
    staleTime: 5 * 60 * 1000, // 5 min
  });
}

export function useTenderDetail(unitId: string | null, jobNumber: string | null) {
  return useQuery({
    queryKey: ['tender', 'detail', unitId, jobNumber],
    queryFn: () => tenderApi.getDetail(unitId!, jobNumber!),
    enabled: !!unitId && !!jobNumber,
    staleTime: 10 * 60 * 1000, // 10 min
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
    staleTime: 30 * 60 * 1000, // 30 min
  });
}
