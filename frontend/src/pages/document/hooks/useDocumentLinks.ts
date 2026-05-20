/**
 * useDocumentLinks - 派工/工程關聯操作 Hook
 *
 * 從 useDocumentDetail 提取，封裝派工單 + 工程的關聯/解除關聯/新增操作。
 *
 * @version 1.0.0
 * @date 2026-03-10
 */

import { useCallback, useMemo } from 'react'; // v6.10.2 #4: 移除 useState（dispatchLinks/projectLinks 改 useQuery）
import { App } from 'antd';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  dispatchOrdersApi,
  documentLinksApi,
  documentProjectLinksApi,
  taoyuanProjectsApi,
} from '../../../api/taoyuanDispatchApi';
import { getProjectAgencyContacts } from '../../../api/projectAgencyContacts';
import { projectVendorsApi } from '../../../api/projectVendorsApi';
import type { ProjectVendor } from '../../../api/projectVendorsApi';
import type {
  DispatchOrderCreate, LinkType,
} from '../../../types/api';
import { isReceiveDocument } from '../../../types/api';
import type {
  DispatchOrder, DocumentDispatchLink, DocumentProjectLink, TaoyuanProject,
  TaoyuanProjectCreate,
} from '../../../types/taoyuan';
import type { ProjectAgencyContact } from '../../../types/admin-system';
import type { Document } from '../../../types';
import { queryKeys } from '../../../config/queryConfig';
import { TAOYUAN_CONTRACT } from '../../../constants/taoyuanOptions';
import { logger } from '../../../utils/logger';

export interface UseDocumentLinksReturn {
  // Dispatch links
  dispatchLinks: DocumentDispatchLink[];
  dispatchLinksLoading: boolean;
  loadDispatchLinks: () => Promise<void>;
  handleCreateDispatch: (formValues: Record<string, unknown>) => Promise<void>;
  handleLinkDispatch: (dispatchId: number) => Promise<void>;
  handleUnlinkDispatch: (linkId: number) => Promise<void>;
  // Project links
  projectLinks: DocumentProjectLink[];
  projectLinksLoading: boolean;
  loadProjectLinks: () => Promise<void>;
  handleLinkProject: (projectId: number) => Promise<void>;
  handleUnlinkProject: (linkId: number) => Promise<void>;
  handleCreateAndLinkProject: (data: TaoyuanProjectCreate) => Promise<void>;
  // Query data (for forms)
  agencyContacts: ProjectAgencyContact[];
  projectVendors: ProjectVendor[];
  availableDispatches: DispatchOrder[];
  availableProjects: TaoyuanProject[];
}

interface UseDocumentLinksOptions {
  documentId: string | undefined;
  document: Document | null;
  isEditing: boolean;
  hasDispatchFeature: boolean;
  hasProjectLinkFeature: boolean;
}

export function useDocumentLinks({
  documentId,
  document,
  isEditing,
  hasDispatchFeature,
  hasProjectLinkFeature,
}: UseDocumentLinksOptions): UseDocumentLinksReturn {
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  // v6.10.2 #4 (2026-05-20) — dispatchLinks / projectLinks 從 useState 轉 useQuery
  // 修 L39 同型 chronic bug：原 imperative load + setState 模式造成
  //   invalidate ['document-dispatch-links'] + ['document-project-links'] silent dead
  //   （沒對應 useQuery → invalidate 永遠不生效 → cache 永不刷新）。
  // 改 useQuery 後 invalidate 真活，從 queryKey_drift_baseline.json 移出 2 dead token。
  const docIdNum = documentId ? parseInt(documentId, 10) : undefined;

  const dispatchLinksQuery = useQuery({
    queryKey: ['document-dispatch-links', docIdNum],
    queryFn: () => documentLinksApi.getDispatchLinks(docIdNum!),
    enabled: !!docIdNum,
  });
  const dispatchLinks: DocumentDispatchLink[] = useMemo(
    () => dispatchLinksQuery.data?.dispatch_orders ?? [],
    [dispatchLinksQuery.data?.dispatch_orders],
  );
  const dispatchLinksLoading = dispatchLinksQuery.isLoading || dispatchLinksQuery.isFetching;

  const projectLinksQuery = useQuery({
    queryKey: ['document-project-links', docIdNum],
    queryFn: () => documentProjectLinksApi.getProjectLinks(docIdNum!),
    enabled: !!docIdNum,
  });
  const projectLinks: DocumentProjectLink[] = useMemo(
    () => projectLinksQuery.data?.projects ?? [],
    [projectLinksQuery.data?.projects],
  );
  const projectLinksLoading = projectLinksQuery.isLoading || projectLinksQuery.isFetching;

  // === Query data for dispatch forms ===
  // 使用公文所屬專案 ID，而非硬編碼（支援多年度合約）
  const vendorProjectId = document?.contract_project_id || TAOYUAN_CONTRACT.PROJECT_ID;

  const { data: agencyContactsData } = useQuery({
    queryKey: ['agency-contacts-for-dispatch', vendorProjectId],
    queryFn: () => getProjectAgencyContacts(vendorProjectId),
    enabled: isEditing && hasDispatchFeature,
  });
  const agencyContacts = useMemo(
    () => agencyContactsData?.items ?? [],
    [agencyContactsData?.items]
  );

  const { data: vendorsData } = useQuery({
    queryKey: ['project-vendors-for-dispatch', vendorProjectId],
    queryFn: () => projectVendorsApi.getProjectVendors(vendorProjectId),
    enabled: isEditing && hasDispatchFeature,
  });
  const projectVendors = useMemo(
    () => vendorsData?.associations ?? [],
    [vendorsData?.associations]
  );

  const { data: availableDispatchesData } = useQuery({
    queryKey: ['dispatch-orders-for-link', document?.contract_project_id],
    queryFn: () => dispatchOrdersApi.getList({
      page: 1,
      limit: 200,
      contract_project_id: document?.contract_project_id ?? undefined,
    }),
    enabled: isEditing && hasDispatchFeature && !!document,
  });
  const availableDispatches = useMemo(
    () => availableDispatchesData?.items ?? [],
    [availableDispatchesData?.items]
  );

  const { data: availableProjectsData } = useQuery({
    queryKey: ['projects-for-link'],
    queryFn: () => taoyuanProjectsApi.getList({ page: 1, limit: 50 }),
    enabled: isEditing && hasProjectLinkFeature,
  });
  const availableProjects = useMemo(
    () => availableProjectsData?.items ?? [],
    [availableProjectsData?.items]
  );

  // === Dispatch link operations ===

  // v6.10.2 #4: loadDispatchLinks 改為 refetch wrap，保留外部 imperative API 相容
  const loadDispatchLinks = useCallback(async () => {
    if (!documentId) return;
    logger.info('[loadDispatchLinks] refetch via useQuery');
    try {
      await dispatchLinksQuery.refetch();
    } catch (error) {
      logger.error('[loadDispatchLinks] refetch 失敗:', error);
      message.error('載入派工關聯失敗，請重新整理頁面');
    }
  }, [documentId, message, dispatchLinksQuery]);

  const handleCreateDispatch = useCallback(async (formValues: Record<string, unknown>) => {
    try {
      const docId = parseInt(documentId || '0', 10);
      const isReceiveDoc = isReceiveDocument(document?.category);

      const workTypeString = Array.isArray(formValues.work_type)
        ? formValues.work_type.join(', ')
        : formValues.work_type as string | undefined;

      const dispatchData: DispatchOrderCreate = {
        dispatch_no: formValues.dispatch_no as string,
        project_name: (formValues.project_name as string) || document?.subject || '',
        work_type: workTypeString,
        sub_case_name: formValues.sub_case_name as string | undefined,
        deadline: formValues.deadline as string | undefined,
        case_handler: formValues.case_handler as string | undefined,
        survey_unit: formValues.survey_unit as string | undefined,
        contact_note: formValues.contact_note as string | undefined,
        cloud_folder: formValues.cloud_folder as string | undefined,
        project_folder: formValues.project_folder as string | undefined,
        contract_project_id: document?.contract_project_id || undefined,
        agency_doc_id: isReceiveDoc ? docId : undefined,
        company_doc_id: !isReceiveDoc ? docId : undefined,
      };

      const newDispatch = await dispatchOrdersApi.create(dispatchData);

      if (newDispatch && newDispatch.id) {
        message.success('派工新增成功');
        // v6.10.2 #4: invalidate 已真活（document-dispatch-links 對應 useQuery）
        queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all }); // SSOT
        queryClient.invalidateQueries({ queryKey: queryKeys.documentRelations.allDispatches });
        queryClient.invalidateQueries({ queryKey: ['document-dispatch-links'] });
        // v6.10.2 L39 cleanup: 移除 legacy ['dispatch-orders']（silent dead，SSOT 已涵蓋）

        // 確保新 dispatch 已在 link 中（後端可能 cascade delay）
        const result = await documentLinksApi.getDispatchLinks(docId);
        const hasNewDispatch = (result.dispatch_orders || []).some(
          (d: DocumentDispatchLink) => d.dispatch_order_id === newDispatch.id
        );
        if (!hasNewDispatch) {
          await new Promise(resolve => setTimeout(resolve, 500));
          await loadDispatchLinks();
        }
        // 真活 useQuery 會自動因 invalidate 重 fetch — 無須手動 setDispatchLinks
      }
    } catch (error: unknown) {
      logger.error('[handleCreateDispatch] 錯誤:', error);
      const errorMessage = error instanceof Error ? error.message : '新增派工失敗';
      message.error(errorMessage);
      throw error;
    }
  }, [documentId, document, message, queryClient, loadDispatchLinks]);

  const handleLinkDispatch = useCallback(async (dispatchId: number) => {
    const docId = parseInt(documentId || '0', 10);
    const isReceiveDoc = isReceiveDocument(document?.category);
    const linkType: LinkType = isReceiveDoc ? 'agency_incoming' : 'company_outgoing';
    await documentLinksApi.linkDispatch(docId, dispatchId, linkType);
    message.success('關聯成功');
    await loadDispatchLinks();
    queryClient.invalidateQueries({ queryKey: queryKeys.documentRelations.allDispatches });
  }, [documentId, document, message, queryClient, loadDispatchLinks]);

  const handleUnlinkDispatch = useCallback(async (linkId: number) => {
    const docId = parseInt(documentId || '0', 10);
    await documentLinksApi.unlinkDispatch(docId, linkId);
    message.success('已移除關聯');
    await loadDispatchLinks();
    queryClient.invalidateQueries({ queryKey: queryKeys.documentRelations.allDispatches });
  }, [documentId, message, queryClient, loadDispatchLinks]);

  // === Project link operations ===

  // v6.10.2 #4: loadProjectLinks 改 refetch wrap（同 dispatch 修法）
  const loadProjectLinks = useCallback(async () => {
    if (!documentId) return;
    try {
      await projectLinksQuery.refetch();
    } catch (error) {
      logger.error('載入工程關聯失敗:', error);
      message.error('載入工程關聯失敗，請重新整理頁面');
    }
  }, [documentId, message, projectLinksQuery]);

  const handleLinkProject = useCallback(async (projectId: number) => {
    const docId = parseInt(documentId || '0', 10);
    const isReceiveDoc = isReceiveDocument(document?.category);
    const linkType: LinkType = isReceiveDoc ? 'agency_incoming' : 'company_outgoing';
    await documentProjectLinksApi.linkProject(docId, projectId, linkType);
    message.success('關聯成功');
    await loadProjectLinks();
    queryClient.invalidateQueries({ queryKey: queryKeys.documentRelations.allProjects });
  }, [documentId, document, message, queryClient, loadProjectLinks]);

  const handleUnlinkProject = useCallback(async (linkId: number) => {
    const docId = parseInt(documentId || '0', 10);
    await documentProjectLinksApi.unlinkProject(docId, linkId);
    message.success('已移除關聯');
    await loadProjectLinks();
    queryClient.invalidateQueries({ queryKey: queryKeys.documentRelations.allProjects });
  }, [documentId, message, queryClient, loadProjectLinks]);

  const handleCreateAndLinkProject = useCallback(async (data: TaoyuanProjectCreate) => {
    const newProject = await taoyuanProjectsApi.create(data);
    if (newProject?.id) {
      await handleLinkProject(newProject.id);
      queryClient.invalidateQueries({ queryKey: ['projects-for-link'] });
    }
  }, [handleLinkProject, queryClient]);

  return {
    dispatchLinks,
    dispatchLinksLoading,
    loadDispatchLinks,
    handleCreateDispatch,
    handleLinkDispatch,
    handleUnlinkDispatch,
    projectLinks,
    projectLinksLoading,
    loadProjectLinks,
    handleLinkProject,
    handleUnlinkProject,
    handleCreateAndLinkProject,
    agencyContacts,
    projectVendors,
    availableDispatches,
    availableProjects,
  };
}
