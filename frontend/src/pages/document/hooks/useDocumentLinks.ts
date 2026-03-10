/**
 * useDocumentLinks - 派工/工程關聯操作 Hook
 *
 * 從 useDocumentDetail 提取，封裝派工單 + 工程的關聯/解除關聯/新增操作。
 *
 * @version 1.0.0
 * @date 2026-03-10
 */

import { useState, useCallback, useMemo } from 'react';
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

  // Dispatch links state
  const [dispatchLinks, setDispatchLinks] = useState<DocumentDispatchLink[]>([]);
  const [dispatchLinksLoading, setDispatchLinksLoading] = useState(false);

  // Project links state
  const [projectLinks, setProjectLinks] = useState<DocumentProjectLink[]>([]);
  const [projectLinksLoading, setProjectLinksLoading] = useState(false);

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

  const loadDispatchLinks = useCallback(async () => {
    if (!documentId) return;
    setDispatchLinksLoading(true);
    try {
      const docId = parseInt(documentId, 10);
      logger.info('[loadDispatchLinks] 開始載入', { docId });
      const result = await documentLinksApi.getDispatchLinks(docId);
      setDispatchLinks(result.dispatch_orders || []);
    } catch (error) {
      logger.error('[loadDispatchLinks] 載入派工關聯失敗:', error);
      message.error('載入派工關聯失敗，請重新整理頁面');
    } finally {
      setDispatchLinksLoading(false);
    }
  }, [documentId, message]);

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
        queryClient.invalidateQueries({ queryKey: ['dispatch-orders'] });
        queryClient.invalidateQueries({ queryKey: queryKeys.documentRelations.allDispatches });
        queryClient.invalidateQueries({ queryKey: ['document-dispatch-links'] });
        queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });

        const result = await documentLinksApi.getDispatchLinks(docId);
        const links = result.dispatch_orders || [];
        const hasNewDispatch = links.some(
          (d: DocumentDispatchLink) => d.dispatch_order_id === newDispatch.id
        );

        if (hasNewDispatch) {
          setDispatchLinks(links);
        } else {
          await new Promise(resolve => setTimeout(resolve, 500));
          await loadDispatchLinks();
        }
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

  const loadProjectLinks = useCallback(async () => {
    if (!documentId) return;
    setProjectLinksLoading(true);
    try {
      const docId = parseInt(documentId, 10);
      const result = await documentProjectLinksApi.getProjectLinks(docId);
      setProjectLinks(result.projects || []);
    } catch (error) {
      logger.error('載入工程關聯失敗:', error);
      message.error('載入工程關聯失敗，請重新整理頁面');
    } finally {
      setProjectLinksLoading(false);
    }
  }, [documentId, message]);

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
