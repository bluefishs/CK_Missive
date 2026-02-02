/**
 * 公文關聯管理 Hook
 *
 * 提供統一的公文-派工、公文-工程關聯管理功能
 * 減少 DocumentDetailPage 中的重複邏輯
 *
 * @version 1.0.0
 * @date 2026-01-21
 */

import { useState, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';
import {
  documentLinksApi,
  documentProjectLinksApi,
  dispatchOrdersApi,
  taoyuanProjectsApi,
} from '../../api/taoyuanDispatchApi';
import type {
  DocumentDispatchLink,
  DocumentProjectLink,
  DispatchOrder,
  TaoyuanProject,
  LinkType,
} from '../../types/api';

// =============================================================================
// 派工關聯 Hook
// =============================================================================

export interface UseDispatchLinksOptions {
  documentId: number | null;
  enabled?: boolean;
}

export interface UseDispatchLinksReturn {
  // 狀態
  links: DocumentDispatchLink[];
  isLoading: boolean;
  selectedDispatchId?: number;
  searchKeyword: string;
  isLinking: boolean;

  // 查詢結果
  availableDispatches: DispatchOrder[];
  filteredDispatches: DispatchOrder[];

  // 操作
  setSelectedDispatchId: (id?: number) => void;
  setSearchKeyword: (keyword: string) => void;
  linkDispatch: (dispatchId: number, linkType: LinkType) => Promise<void>;
  unlinkDispatch: (linkId: number) => Promise<void>;
  refresh: () => void;
}

export function useDispatchLinks({
  documentId,
  enabled = true,
}: UseDispatchLinksOptions): UseDispatchLinksReturn {
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  // 狀態
  const [links, setLinks] = useState<DocumentDispatchLink[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedDispatchId, setSelectedDispatchId] = useState<number>();
  const [searchKeyword, setSearchKeyword] = useState('');
  const [isLinking, setIsLinking] = useState(false);

  // 載入關聯
  const loadLinks = useCallback(async () => {
    if (!documentId) return;
    setIsLoading(true);
    try {
      const result = await documentLinksApi.getDispatchLinks(documentId);
      setLinks(result.dispatch_orders || []);
    } catch (error) {
      console.error('載入派工關聯失敗:', error);
      setLinks([]);
    } finally {
      setIsLoading(false);
    }
  }, [documentId]);

  // 查詢可關聯的派工紀錄
  const { data: availableDispatchesData } = useQuery({
    queryKey: ['dispatch-orders-for-link', searchKeyword],
    queryFn: async () => {
      const result = await dispatchOrdersApi.getList({
        search: searchKeyword || undefined,
        page: 1,
        limit: 50,
      });
      return result;
    },
    enabled: enabled && !!documentId,
  });

  // 已關聯的派工 ID 列表
  const linkedDispatchIds = links.map((link) => link.dispatch_order_id);

  // 過濾掉已關聯的派工
  const availableDispatches = availableDispatchesData?.items ?? [];
  const filteredDispatches = availableDispatches.filter(
    (dispatch) => !linkedDispatchIds.includes(dispatch.id)
  );

  // 關聯派工
  const linkDispatch = useCallback(
    async (dispatchId: number, linkType: LinkType) => {
      if (!documentId) return;
      setIsLinking(true);
      try {
        await documentLinksApi.linkDispatch(documentId, dispatchId, linkType);
        message.success('關聯成功');
        setSelectedDispatchId(undefined);
        await loadLinks();
        queryClient.invalidateQueries({ queryKey: ['dispatch-orders-for-link'] });
      } catch (error: unknown) {
        message.error(error instanceof Error ? error.message : '關聯失敗');
      } finally {
        setIsLinking(false);
      }
    },
    [documentId, loadLinks, message, queryClient]
  );

  // 移除關聯
  const unlinkDispatch = useCallback(
    async (linkId: number) => {
      if (!documentId) return;
      try {
        await documentLinksApi.unlinkDispatch(documentId, linkId);
        message.success('已移除關聯');
        await loadLinks();
        queryClient.invalidateQueries({ queryKey: ['dispatch-orders-for-link'] });
      } catch (error) {
        message.error('移除關聯失敗');
      }
    },
    [documentId, loadLinks, message, queryClient]
  );

  return {
    links,
    isLoading,
    selectedDispatchId,
    searchKeyword,
    isLinking,
    availableDispatches,
    filteredDispatches,
    setSelectedDispatchId,
    setSearchKeyword,
    linkDispatch,
    unlinkDispatch,
    refresh: loadLinks,
  };
}

// =============================================================================
// 工程關聯 Hook
// =============================================================================

export interface UseProjectLinksOptions {
  documentId: number | null;
  enabled?: boolean;
}

export interface UseProjectLinksReturn {
  // 狀態
  links: DocumentProjectLink[];
  isLoading: boolean;
  selectedProjectId?: number;
  searchKeyword: string;
  isLinking: boolean;

  // 查詢結果
  availableProjects: TaoyuanProject[];
  filteredProjects: TaoyuanProject[];

  // 操作
  setSelectedProjectId: (id?: number) => void;
  setSearchKeyword: (keyword: string) => void;
  linkProject: (projectId: number, linkType: LinkType, notes?: string) => Promise<void>;
  unlinkProject: (linkId: number) => Promise<void>;
  refresh: () => void;
}

export function useProjectLinks({
  documentId,
  enabled = true,
}: UseProjectLinksOptions): UseProjectLinksReturn {
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  // 狀態
  const [links, setLinks] = useState<DocumentProjectLink[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState<number>();
  const [searchKeyword, setSearchKeyword] = useState('');
  const [isLinking, setIsLinking] = useState(false);

  // 載入關聯
  const loadLinks = useCallback(async () => {
    if (!documentId) return;
    setIsLoading(true);
    try {
      const result = await documentProjectLinksApi.getProjectLinks(documentId);
      setLinks(result.projects || []);
    } catch (error) {
      console.error('載入工程關聯失敗:', error);
      setLinks([]);
    } finally {
      setIsLoading(false);
    }
  }, [documentId]);

  // 查詢可關聯的工程
  const { data: availableProjectsData } = useQuery({
    queryKey: ['projects-for-link', searchKeyword],
    queryFn: async () => {
      const result = await taoyuanProjectsApi.getList({
        search: searchKeyword || undefined,
        page: 1,
        limit: 50,
      });
      return result;
    },
    enabled: enabled && !!documentId,
  });

  // 已關聯的工程 ID 列表
  const linkedProjectIds = links.map((link) => link.project_id);

  // 過濾掉已關聯的工程
  const availableProjects = availableProjectsData?.items ?? [];
  const filteredProjects = availableProjects.filter(
    (project) => !linkedProjectIds.includes(project.id)
  );

  // 關聯工程
  const linkProject = useCallback(
    async (projectId: number, linkType: LinkType, notes?: string) => {
      if (!documentId) return;
      setIsLinking(true);
      try {
        await documentProjectLinksApi.linkProject(documentId, projectId, linkType, notes);
        message.success('關聯成功');
        setSelectedProjectId(undefined);
        await loadLinks();
        queryClient.invalidateQueries({ queryKey: ['projects-for-link'] });
      } catch (error: unknown) {
        message.error(error instanceof Error ? error.message : '關聯失敗');
      } finally {
        setIsLinking(false);
      }
    },
    [documentId, loadLinks, message, queryClient]
  );

  // 移除關聯
  const unlinkProject = useCallback(
    async (linkId: number) => {
      if (!documentId) return;
      try {
        await documentProjectLinksApi.unlinkProject(documentId, linkId);
        message.success('已移除關聯');
        await loadLinks();
        queryClient.invalidateQueries({ queryKey: ['projects-for-link'] });
      } catch (error) {
        message.error('移除關聯失敗');
      }
    },
    [documentId, loadLinks, message, queryClient]
  );

  return {
    links,
    isLoading,
    selectedProjectId,
    searchKeyword,
    isLinking,
    availableProjects,
    filteredProjects,
    setSelectedProjectId,
    setSearchKeyword,
    linkProject,
    unlinkProject,
    refresh: loadLinks,
  };
}
