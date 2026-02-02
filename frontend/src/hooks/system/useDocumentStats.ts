import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';

interface DocumentStats {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
  draft: number;
}

export const useDocumentStats = () => {
  return useQuery({
    queryKey: ['documentStats'],
    queryFn: async (): Promise<DocumentStats> => {
      const response = await apiClient.post(API_ENDPOINTS.DOCUMENTS.STATISTICS);
      return response as unknown as DocumentStats;
    },
    staleTime: 5 * 60 * 1000, // 5分鐘
    gcTime: 10 * 60 * 1000, // 10分鐘
  });
};