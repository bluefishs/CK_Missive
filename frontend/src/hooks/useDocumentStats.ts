// @ts-ignore
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/config';

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
      const response = await apiClient.get('/documents-enhanced/statistics');
      return response as unknown as DocumentStats;
    },
    staleTime: 5 * 60 * 1000, // 5分鐘
    gcTime: 10 * 60 * 1000, // 10分鐘
  });
};