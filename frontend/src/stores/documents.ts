/**
 * 文件管理 Store
 * 基於 Zustand 的文件狀態管理
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { Document, DocumentFilter } from '../types/document';

interface DocumentsState {
  // 文件列表
  documents: Document[];
  
  // 當前選中的文件
  selectedDocument: Document | null;
  
  // 篩選條件
  filters: DocumentFilter;
  
  // 分頁資訊
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
  
  // Actions
  setDocuments: (documents: Document[]) => void;
  setSelectedDocument: (document: Document | null) => void;
  setFilters: (filters: Partial<DocumentFilter>) => void;
  setPagination: (pagination: Partial<DocumentsState['pagination']>) => void;
  addDocument: (document: Document) => void;
  updateDocument: (id: string, document: Partial<Document>) => void;
  removeDocument: (id: string) => void;
  resetFilters: () => void;
}

const initialFilters: DocumentFilter = {
  search: '',
};

export const useDocumentsStore = create<DocumentsState>()(
  devtools(
    (set, get) => ({
      // Initial state
      documents: [],
      selectedDocument: null,
      filters: initialFilters,
      pagination: {
        page: 1,
        limit: 10,
        total: 0,
        totalPages: 0,
      },

      // Actions
      setDocuments: (documents) => set({ documents }),
      
      setSelectedDocument: (selectedDocument) => set({ selectedDocument }),
      
      setFilters: (newFilters) => set((state) => ({ 
        filters: { ...state.filters, ...newFilters },
        pagination: { ...state.pagination, page: 1 }
      })),
      
      setPagination: (newPagination) => set((state) => ({
        pagination: { ...state.pagination, ...newPagination }
      })),
      
      addDocument: (document) => set((state) => ({
        documents: [...state.documents, document]
      })),
      
      updateDocument: (id, updates) => set((state) => ({
        documents: state.documents.map(doc => 
          doc.id === Number(id) ? { ...doc, ...updates } as Document : doc
        )
      })),
      
      removeDocument: (id) => set((state) => ({
        documents: state.documents.filter(doc => doc.id !== Number(id))
      })),
      
      resetFilters: () => set({ 
        filters: initialFilters,
        pagination: { ...get().pagination, page: 1 }
      }),
    }),
    { name: 'documents-store' }
  )
);

export type { DocumentsState };