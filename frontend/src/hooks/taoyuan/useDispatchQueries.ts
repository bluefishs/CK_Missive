import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { TaoyuanProject } from '../../types/api';
import {
  dispatchOrdersApi,
  taoyuanProjectsApi,
  dispatchAttachmentsApi,
  contractPaymentsApi,
} from '../../api/taoyuanDispatchApi';
import { getProjectAgencyContacts } from '../../api/projectAgencyContacts';
import { projectVendorsApi } from '../../api/projectVendorsApi';
import { TAOYUAN_CONTRACT } from '../../constants/taoyuanOptions';
import type { LinkedProject } from '../../pages/taoyuanDispatch/tabs';

export function useDispatchQueries(id: string | undefined) {
  const {
    data: dispatch,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['dispatch-order-detail', id],
    queryFn: () => dispatchOrdersApi.getDetail(parseInt(id || '0', 10)),
    enabled: !!id,
    // P-21 (2026-05-06)：dispatch 物件含 linked_documents / linked_projects 等動態 FK，
    // 跨頁面操作（link/unlink/auto-match/payment）會改變這些 FK，
    // 需積極 refetch 避免「5 筆關聯但只顯示 1 筆」類型的 cache stale 事故
    staleTime: 10_000,
    refetchOnMount: 'always',
  });

  const vendorProjectId = dispatch?.contract_project_id || TAOYUAN_CONTRACT.PROJECT_ID;

  const { data: agencyContactsData } = useQuery({
    queryKey: ['agency-contacts', vendorProjectId],
    queryFn: () => getProjectAgencyContacts(vendorProjectId),
  });
  const agencyContacts = useMemo(
    () => agencyContactsData?.items ?? [],
    [agencyContactsData?.items]
  );

  const { data: vendorsData } = useQuery({
    queryKey: ['project-vendors', vendorProjectId],
    queryFn: () => projectVendorsApi.getProjectVendors(vendorProjectId),
  });
  const projectVendors = useMemo(
    () => vendorsData?.associations ?? [],
    [vendorsData?.associations]
  );

  const { data: availableProjectsData } = useQuery({
    queryKey: [
      'taoyuan-projects-for-dispatch-link',
      dispatch?.contract_project_id,
    ],
    queryFn: () =>
      taoyuanProjectsApi.getList({
        contract_project_id:
          dispatch?.contract_project_id || TAOYUAN_CONTRACT.PROJECT_ID,
        limit: 500,
      }),
    enabled: !!dispatch,
  });
  const availableProjects = useMemo(
    () => availableProjectsData?.items ?? [],
    [availableProjectsData?.items]
  );

  const linkedProjectIds = useMemo(
    () => (dispatch?.linked_projects || []).map(
      (p: LinkedProject) => p.project_id
    ),
    [dispatch?.linked_projects]
  );

  const filteredProjects = useMemo(
    () => availableProjects.filter(
      (proj: TaoyuanProject) => !linkedProjectIds.includes(proj.id)
    ),
    [availableProjects, linkedProjectIds]
  );

  const { data: attachments, refetch: refetchAttachments } = useQuery({
    queryKey: ['dispatch-attachments', id],
    queryFn: () =>
      dispatchAttachmentsApi.getAttachments(parseInt(id || '0', 10)),
    enabled: !!id,
  });

  const { data: paymentData, refetch: refetchPayment } = useQuery({
    queryKey: ['dispatch-payment', id],
    queryFn: async () => {
      const result = await contractPaymentsApi.getList(
        parseInt(id || '0', 10)
      );
      return result.items?.[0] || null;
    },
    enabled: !!id,
  });

  return {
    dispatch,
    isLoading,
    refetch,
    agencyContacts,
    projectVendors,
    availableProjects,
    linkedProjectIds,
    filteredProjects,
    attachments,
    refetchAttachments,
    paymentData,
    refetchPayment,
  };
}
