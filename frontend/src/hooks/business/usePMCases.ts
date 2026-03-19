/**
 * PM 案件管理 React Query Hooks
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { pmCasesApi, pmMilestonesApi, pmStaffApi } from '../../api/pm';
import { defaultQueryOptions } from '../../config/queryConfig';
import type {
  PMCaseCreate,
  PMCaseUpdate,
  PMCaseListParams,
  PMMilestoneCreate,
  PMMilestoneUpdate,
  PMCaseStaffCreate,
  PMCaseStaffUpdate,
} from '../../types/pm';

// Query keys
const pmKeys = {
  all: ['pm-cases'] as const,
  lists: () => [...pmKeys.all, 'list'] as const,
  list: (filters: object) => [...pmKeys.lists(), filters] as const,
  details: () => [...pmKeys.all, 'detail'] as const,
  detail: (id: number) => [...pmKeys.details(), id] as const,
  summary: (params?: object) => ['pm-cases', 'summary', params] as const,
  milestones: (pmCaseId: number) => ['pm-milestones', pmCaseId] as const,
  staff: (pmCaseId: number) => ['pm-case-staff', pmCaseId] as const,
};

/** 取得 PM 案件列表 */
export const usePMCases = (params?: PMCaseListParams) => {
  return useQuery({
    queryKey: pmKeys.list(params || {}),
    queryFn: () => pmCasesApi.list(params),
    ...defaultQueryOptions.list,
  });
};

/** 取得 PM 案件詳情 */
export const usePMCase = (id: number | null | undefined) => {
  return useQuery({
    queryKey: pmKeys.detail(id ?? 0),
    queryFn: () => pmCasesApi.detail(id!),
    ...defaultQueryOptions.detail,
    enabled: !!id,
  });
};

/** 取得 PM 案件統計摘要 */
export const usePMCaseSummary = (params?: { year?: number }) => {
  return useQuery({
    queryKey: pmKeys.summary(params),
    queryFn: () => pmCasesApi.summary(params),
    ...defaultQueryOptions.statistics,
  });
};

/** 建立 PM 案件 */
export const useCreatePMCase = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PMCaseCreate) => pmCasesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pmKeys.all });
    },
  });
};

/** 更新 PM 案件 */
export const useUpdatePMCase = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: PMCaseUpdate }) =>
      pmCasesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pmKeys.all });
    },
  });
};

/** 刪除 PM 案件 */
export const useDeletePMCase = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => pmCasesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pmKeys.all });
    },
  });
};

/** 重新計算進度 (根據里程碑完成率) */
export const useRecalculatePMProgress = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => pmCasesApi.recalculateProgress(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pmKeys.all });
    },
  });
};

/** 取得案件甘特圖 (Mermaid Gantt) */
export const usePMCaseGantt = (pmCaseId: number | null) => {
  return useQuery({
    queryKey: [...pmKeys.detail(pmCaseId ?? 0), 'gantt'] as const,
    queryFn: () => pmCasesApi.gantt(pmCaseId!),
    enabled: !!pmCaseId,
    staleTime: 5 * 60 * 1000,
  });
};

/** 多年度案件趨勢 */
export const usePMYearlyTrend = () => {
  return useQuery({
    queryKey: ['pm-cases', 'yearly-trend'] as const,
    queryFn: () => pmCasesApi.yearlyTrend(),
    ...defaultQueryOptions.statistics,
  });
};

/** 案號關聯公文查詢 */
export const usePMLinkedDocuments = (caseCode: string | null) => {
  return useQuery({
    queryKey: ['pm-linked-docs', caseCode] as const,
    queryFn: () => pmCasesApi.linkedDocuments(caseCode!),
    enabled: !!caseCode,
    staleTime: 5 * 60 * 1000,
  });
};

/** 跨模組案號查詢 */
export const useCrossModuleLookup = (caseCode: string | null) => {
  return useQuery({
    queryKey: ['cross-lookup', caseCode] as const,
    queryFn: () => pmCasesApi.crossLookup(caseCode!),
    enabled: !!caseCode,
    staleTime: 5 * 60 * 1000,
  });
};

// ============================================================================
// 里程碑 Hooks
// ============================================================================

/** 取得案件里程碑列表 */
export const usePMMilestones = (pmCaseId: number) => {
  return useQuery({
    queryKey: pmKeys.milestones(pmCaseId),
    queryFn: () => pmMilestonesApi.list(pmCaseId),
    ...defaultQueryOptions.list,
    enabled: !!pmCaseId,
  });
};

/** 建立里程碑 */
export const useCreatePMMilestone = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PMMilestoneCreate) => pmMilestonesApi.create(data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: pmKeys.milestones(variables.pm_case_id) });
      queryClient.invalidateQueries({ queryKey: pmKeys.detail(variables.pm_case_id) });
    },
  });
};

/** 更新里程碑 */
export const useUpdatePMMilestone = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (variables: { id: number; pmCaseId: number; data: PMMilestoneUpdate }) =>
      pmMilestonesApi.update(variables.id, variables.data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: pmKeys.milestones(variables.pmCaseId) });
    },
  });
};

/** 刪除里程碑 */
export const useDeletePMMilestone = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (variables: { id: number; pmCaseId: number }) =>
      pmMilestonesApi.delete(variables.id),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: pmKeys.milestones(variables.pmCaseId) });
      queryClient.invalidateQueries({ queryKey: pmKeys.detail(variables.pmCaseId) });
    },
  });
};

// ============================================================================
// 案件人員 Hooks
// ============================================================================

/** 取得案件人員列表 */
export const usePMCaseStaff = (pmCaseId: number) => {
  return useQuery({
    queryKey: pmKeys.staff(pmCaseId),
    queryFn: () => pmStaffApi.list(pmCaseId),
    ...defaultQueryOptions.list,
    enabled: !!pmCaseId,
  });
};

/** 建立案件人員 */
export const useCreatePMCaseStaff = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PMCaseStaffCreate) => pmStaffApi.create(data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: pmKeys.staff(variables.pm_case_id) });
      queryClient.invalidateQueries({ queryKey: pmKeys.detail(variables.pm_case_id) });
    },
  });
};

/** 更新案件人員 */
export const useUpdatePMCaseStaff = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (variables: { id: number; pmCaseId: number; data: PMCaseStaffUpdate }) =>
      pmStaffApi.update(variables.id, variables.data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: pmKeys.staff(variables.pmCaseId) });
    },
  });
};

/** 刪除案件人員 */
export const useDeletePMCaseStaff = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (variables: { id: number; pmCaseId: number }) =>
      pmStaffApi.delete(variables.id),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: pmKeys.staff(variables.pmCaseId) });
      queryClient.invalidateQueries({ queryKey: pmKeys.detail(variables.pmCaseId) });
    },
  });
};
