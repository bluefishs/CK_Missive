// @ts-ignore
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentService } from '../services';
import type { Document, DocumentFilter , DocumentStatus} from '../types/document';
import { useDocumentsStore } from '../stores';

interface DocumentListParams extends DocumentFilter {
  page?: number;
  limit?: number;
}

export const useDocuments = (params?: DocumentListParams) => {
  const { setDocuments, setPagination } = useDocumentsStore();
  
  return useQuery({
    queryKey: ['documents', params],
    queryFn: async () => {
      console.log('=== useDocuments: 開始獲取文件資料 ===', params);
      const result = await documentService.getDocuments(params);
      console.log('=== useDocuments: 獲取到的資料 ===', result);
      console.log('=== useDocuments: 文件數量 ===', result.items?.length || 0);

      if (result.items && Array.isArray(result.items)) {
        setDocuments([...result.items]);
        console.log('=== useDocuments: 已設置文件到 store ===', result.items.length);
      } else {
        console.warn('=== useDocuments: 警告 - items 不是陣列 ===', result.items);
        setDocuments([]);
      }

      setPagination({
        page: result.page,
        limit: result.limit,
        total: result.total,
        totalPages: result.total_pages,
      });
      console.log('=== useDocuments: 已設置分頁資訊 ===', {
        page: result.page,
        limit: result.limit,
        total: result.total,
        totalPages: result.total_pages,
      });

      return result;
    },
    staleTime: 30 * 1000, // 30秒快取
    gcTime: 5 * 60 * 1000, // 5分鐘垃圾回收
  });
};

export const useDocument = (id: string) => {
  const { setSelectedDocument } = useDocumentsStore();
  
  return useQuery({
    queryKey: ['document', id],
    queryFn: async () => {
      const document = await documentService.getDocument(id as any);
      setSelectedDocument(document);
      return document;
    },
    enabled: !!id,
  });
};

export const useCreateDocument = () => {
  const queryClient = useQueryClient();
  const { addDocument } = useDocumentsStore();
  
  return useMutation({
    mutationFn: documentService.createDocument,
    onSuccess: (newDocument: Document) => {
      addDocument(newDocument);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
};

export const useUpdateDocument = () => {
  const queryClient = useQueryClient();
  const { updateDocument } = useDocumentsStore();
  
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Document> }) => 
      documentService.updateDocument(id as any, data),
    onSuccess: (updatedDocument: Document, variables: { id: string; data: Partial<Document> }) => {
      updateDocument(variables.id, updatedDocument);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['document', variables.id] });
    },
  });
};

export const useDeleteDocument = () => {
  const queryClient = useQueryClient();
  const { removeDocument } = useDocumentsStore();
  
  return useMutation<void, Error, string>({
    mutationFn: (id: string) => documentService.deleteDocument(id as any),
    onSuccess: (_: void, id: string) => {
      removeDocument(id);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
};