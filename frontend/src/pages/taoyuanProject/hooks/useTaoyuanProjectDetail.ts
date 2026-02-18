/**
 * 桃園轄管工程詳情 Hook
 *
 * 管理所有 Query/Mutation、表單初始化、事件處理。
 */

import { useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { Form, App } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../../config/queryConfig';
import dayjs from 'dayjs';

import { taoyuanProjectsApi, projectLinksApi, dispatchOrdersApi } from '../../../api/taoyuanDispatchApi';
import { getProjectAgencyContacts, type ProjectAgencyContact } from '../../../api/projectAgencyContacts';
import { projectVendorsApi, type ProjectVendor } from '../../../api/projectVendorsApi';
import type { TaoyuanProject, TaoyuanProjectUpdate, DispatchOrder, ProjectDispatchLink } from '../../../types/api';
import { useAuthGuard } from '../../../hooks';
import { TAOYUAN_CONTRACT } from '../../../constants/taoyuanOptions';
import { logger } from '../../../services/logger';

/** 表單初始值對映 */
function projectToFormValues(project: TaoyuanProject) {
  return {
    project_name: project.project_name,
    review_year: project.review_year,
    case_type: project.case_type,
    district: project.district,
    sub_case_name: project.sub_case_name,
    case_handler: project.case_handler,
    survey_unit: project.survey_unit,
    proposer: project.proposer,
    start_point: project.start_point,
    start_coordinate: project.start_coordinate,
    end_point: project.end_point,
    end_coordinate: project.end_coordinate,
    road_length: project.road_length,
    current_width: project.current_width,
    planned_width: project.planned_width,
    urban_plan: project.urban_plan,
    public_land_count: project.public_land_count,
    private_land_count: project.private_land_count,
    rc_count: project.rc_count,
    iron_sheet_count: project.iron_sheet_count,
    construction_cost: project.construction_cost,
    land_cost: project.land_cost,
    compensation_cost: project.compensation_cost,
    total_cost: project.total_cost,
    review_result: project.review_result,
    completion_date: project.completion_date ? dayjs(project.completion_date) : null,
    remark: project.remark,
    land_agreement_status: project.land_agreement_status,
    land_expropriation_status: project.land_expropriation_status,
    building_survey_status: project.building_survey_status,
    acceptance_status: project.acceptance_status,
  };
}

// Return type is inferred from the function below

export function useTaoyuanProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const { hasPermission } = useAuthGuard();
  const canEdit = hasPermission('documents:edit');
  const canDelete = hasPermission('documents:delete');

  // URL 參數驅動 Tab + highlight
  const initialTab = searchParams.get('tab') || 'basic';
  const [activeTab, setActiveTab] = useState(initialTab);
  const highlightDispatchId = searchParams.get('highlight')
    ? parseInt(searchParams.get('highlight')!, 10)
    : undefined;

  // 同步 URL 參數到 activeTab
  useEffect(() => {
    const tabFromUrl = searchParams.get('tab') || 'basic';
    if (tabFromUrl !== activeTab) {
      setActiveTab(tabFromUrl);
    }
  }, [searchParams]); // eslint-disable-line react-hooks/exhaustive-deps

  // Tab 變更時更新 URL
  const handleTabChange = useCallback(
    (tabKey: string) => {
      setActiveTab(tabKey);
      const params: Record<string, string> = { tab: tabKey };
      // 切到 overview 時保留 highlight；切到其他 Tab 時清除
      if (tabKey === 'overview' && highlightDispatchId) {
        params.highlight = String(highlightDispatchId);
      }
      setSearchParams(params, { replace: true });
    },
    [setSearchParams, highlightDispatchId],
  );
  const [isEditing, setIsEditing] = useState(false);
  const [selectedDispatchId, setSelectedDispatchId] = useState<number>();

  // === Queries ===

  const { data: project, isLoading, refetch } = useQuery({
    queryKey: ['taoyuan-project-detail', id],
    queryFn: () => taoyuanProjectsApi.getDetail(parseInt(id || '0', 10)),
    enabled: !!id,
  });

  const { data: linkedDispatchesData, refetch: refetchDispatchLinks } = useQuery({
    queryKey: ['project-dispatch-links', id],
    queryFn: () => projectLinksApi.getDispatchLinks(parseInt(id || '0', 10)),
    enabled: !!id,
  });
  const linkedDispatches = linkedDispatchesData?.dispatch_orders || [];

  const { data: agencyContactsData } = useQuery({
    queryKey: ['agency-contacts', TAOYUAN_CONTRACT.PROJECT_ID],
    queryFn: () => getProjectAgencyContacts(TAOYUAN_CONTRACT.PROJECT_ID),
  });
  const agencyContacts = agencyContactsData?.items ?? [];

  const { data: vendorsData } = useQuery({
    queryKey: ['project-vendors', TAOYUAN_CONTRACT.PROJECT_ID],
    queryFn: () => projectVendorsApi.getProjectVendors(TAOYUAN_CONTRACT.PROJECT_ID),
  });
  const projectVendors = vendorsData?.associations ?? [];

  const { data: availableDispatchesData } = useQuery({
    queryKey: ['dispatch-orders-for-project', project?.contract_project_id],
    queryFn: () =>
      dispatchOrdersApi.getList({
        contract_project_id: project?.contract_project_id,
        limit: 100,
      }),
    enabled: !!project?.contract_project_id && isEditing,
  });
  const availableDispatches = availableDispatchesData?.items || [];

  const linkedDispatchIds = linkedDispatches.map((d) => d.dispatch_order_id);
  const filteredDispatches = availableDispatches.filter(
    (d: DispatchOrder) => !linkedDispatchIds.includes(d.id)
  );

  // === Mutations ===

  const updateMutation = useMutation({
    mutationFn: (data: TaoyuanProjectUpdate) =>
      taoyuanProjectsApi.update(parseInt(id || '0', 10), data),
    onSuccess: () => {
      message.success('工程更新成功');
      refetch();
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanProjects.all });
      setIsEditing(false);
    },
    onError: () => message.error('更新失敗'),
  });

  const deleteMutation = useMutation({
    mutationFn: () => taoyuanProjectsApi.delete(parseInt(id || '0', 10)),
    onSuccess: () => {
      message.success('工程刪除成功');
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanProjects.all });
      navigate('/taoyuan/dispatch');
    },
    onError: () => message.error('刪除失敗'),
  });

  const linkDispatchMutation = useMutation({
    mutationFn: (dispatchOrderId: number) =>
      projectLinksApi.linkDispatch(parseInt(id || '0', 10), dispatchOrderId),
    onSuccess: () => {
      message.success('派工關聯成功');
      setSelectedDispatchId(undefined);
      refetchDispatchLinks();
      queryClient.invalidateQueries({ queryKey: ['dispatch-orders'] });
    },
    onError: () => message.error('關聯失敗'),
  });

  const unlinkDispatchMutation = useMutation({
    mutationFn: (linkId: number) => {
      if (linkId === undefined || linkId === null) {
        logger.error('[unlinkDispatchMutation] linkId 無效:', linkId);
        return Promise.reject(new Error('關聯 ID 無效'));
      }
      const projectId = parseInt(id || '0', 10);
      if (!projectId || projectId === 0) {
        logger.error('[unlinkDispatchMutation] projectId 無效:', id);
        return Promise.reject(new Error('工程 ID 無效'));
      }
      logger.debug('[unlinkDispatchMutation] 準備移除:', { projectId, linkId });
      return projectLinksApi.unlinkDispatch(projectId, linkId);
    },
    onSuccess: () => {
      message.success('已移除派工關聯');
      refetchDispatchLinks();
      queryClient.invalidateQueries({ queryKey: ['dispatch-orders'] });
    },
    onError: (error: Error) => message.error(error.message || '移除關聯失敗'),
  });

  // === Effects ===

  useEffect(() => {
    if (project) {
      form.setFieldsValue(projectToFormValues(project));
    }
  }, [project, form]);

  // === Handlers ===

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const data: TaoyuanProjectUpdate = {
        ...values,
        completion_date: values.completion_date?.format('YYYY-MM-DD') || null,
      };
      updateMutation.mutate(data);
    } catch {
      message.error('請檢查表單欄位');
    }
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    if (project) {
      form.setFieldsValue(projectToFormValues(project));
    }
  };

  const handleLinkDispatch = useCallback(() => {
    if (!selectedDispatchId) {
      message.warning('請先選擇要關聯的派工紀錄');
      return;
    }
    linkDispatchMutation.mutate(selectedDispatchId);
  }, [selectedDispatchId, linkDispatchMutation, message]);

  return {
    id,
    navigate,
    canEdit,
    canDelete,
    form,
    activeTab,
    setActiveTab: handleTabChange,
    highlightDispatchId,
    isEditing,
    setIsEditing,
    project,
    isLoading,
    agencyContacts,
    projectVendors,
    linkedDispatches,
    filteredDispatches,
    selectedDispatchId,
    setSelectedDispatchId,
    updateMutation,
    deleteMutation,
    linkDispatchMutation,
    unlinkDispatchMutation,
    handleSave,
    handleCancelEdit,
    handleLinkDispatch,
    refetch,
    message,
  };
}
