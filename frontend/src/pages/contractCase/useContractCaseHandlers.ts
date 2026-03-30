/**
 * 承攬案件詳情頁 CRUD Handlers
 *
 * 從 ContractCaseDetailPage 拆分，集中管理所有實體操作 handler
 *
 * @version 1.0.0
 * @date 2026-03-29
 */

import { App, FormInstance } from 'antd';
import dayjs from 'dayjs';
import { useNavigate } from 'react-router-dom';
import { useState, useCallback } from 'react';
import { ROUTES } from '../../router/types';
import { queryKeys } from '../../config/queryConfig';
import { projectsApi } from '../../api/projectsApi';
import { filesApi } from '../../api/filesApi';
import { projectStaffApi } from '../../api/projectStaffApi';
import { projectVendorsApi } from '../../api/projectVendorsApi';
import {
  createAgencyContact,
  updateAgencyContact,
  deleteAgencyContact,
} from '../../api/projectAgencyContacts';
import { logger } from '../../utils/logger';
import type { QueryClient } from '@tanstack/react-query';
import type {
  CaseInfoFormValues,
  AgencyContactFormValues,
  StaffFormValues,
  VendorFormValues,
  LocalGroupedAttachment,
  ApiErrorResponse,
  PydanticValidationError,
} from './tabs';

interface UseContractCaseHandlersOptions {
  projectId: number;
  queryClient: QueryClient;
  reloadData: () => void;
  staffList: { id: number; user_id: number }[];
  backRoute?: string;
  // Form instances
  staffForm: FormInstance;
  vendorForm: FormInstance;
  agencyContactForm: FormInstance;
  // Modal state setters
  setIsEditingCaseInfo: (v: boolean) => void;
  setStaffModalVisible: (v: boolean) => void;
  setVendorModalVisible: (v: boolean) => void;
  setAgencyContactModalVisible: (v: boolean) => void;
  setEditingAgencyContactId: (v: number | null) => void;
  editingAgencyContactId: number | null;
  setEditingStaffId: (v: number | null) => void;
  setEditingVendorId: (v: number | null) => void;
}

export function useContractCaseHandlers(opts: UseContractCaseHandlersOptions) {
  const {
    projectId, queryClient, reloadData, staffList, backRoute,
    staffForm, vendorForm, agencyContactForm,
    setIsEditingCaseInfo, setStaffModalVisible, setVendorModalVisible,
    setAgencyContactModalVisible, setEditingAgencyContactId, editingAgencyContactId,
    setEditingStaffId, setEditingVendorId,
  } = opts;

  const navigate = useNavigate();
  const { message } = App.useApp();
  const [deleting, setDeleting] = useState(false);

  const handleBack = useCallback(() => navigate(backRoute || ROUTES.CONTRACT_CASES), [navigate, backRoute]);
  const handleEdit = useCallback(() => navigate(`${ROUTES.CONTRACT_CASES}/${projectId}/edit`), [navigate, projectId]);

  const handleDelete = useCallback(async () => {
    setDeleting(true);
    try {
      await projectsApi.deleteProject(projectId);
      queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
      message.success('案件已刪除');
      navigate(backRoute || ROUTES.CONTRACT_CASES);
    } catch (error) {
      const axiosError = error as { response?: { data?: ApiErrorResponse } };
      message.error(axiosError.response?.data?.detail as string || '刪除案件失敗，可能仍有關聯資料');
    } finally {
      setDeleting(false);
    }
  }, [projectId, queryClient, message, navigate, backRoute]);

  const handleSaveCaseInfo = useCallback(async (values: CaseInfoFormValues) => {
    try {
      const autoProgress = values.status === '已結案' ? 100 : values.progress;
      const startDate = values.date_range?.[0] ? dayjs(values.date_range[0] as unknown as string).format('YYYY-MM-DD') : undefined;
      const endDate = values.date_range?.[1] ? dayjs(values.date_range[1] as unknown as string).format('YYYY-MM-DD') : undefined;
      const updateData = {
        project_name: values.project_name, year: values.year,
        client_agency: values.client_agency || undefined,
        contract_doc_number: values.contract_doc_number || undefined,
        project_code: values.project_code || undefined,
        category: values.category || undefined,
        case_nature: values.case_nature || undefined,
        contract_amount: values.contract_amount || undefined,
        winning_amount: values.winning_amount || undefined,
        start_date: startDate, end_date: endDate,
        status: values.status || undefined,
        progress: autoProgress ?? undefined,
        project_path: values.project_path || undefined,
        notes: values.notes || undefined,
        has_dispatch_management: values.has_dispatch_management,
      };
      await projectsApi.updateProject(projectId, updateData as Parameters<typeof projectsApi.updateProject>[1]);
      queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
      queryClient.invalidateQueries({ queryKey: ['taoyuan-dispatch-orders', 'contract-projects'] });
      queryClient.invalidateQueries({ queryKey: ['contract-case-detail', projectId] });
      setIsEditingCaseInfo(false);
      message.success('案件資訊已更新');
    } catch (error) {
      logger.error('更新案件資訊失敗:', error);
      const axiosError = error as { response?: { data?: ApiErrorResponse } };
      message.error(axiosError.response?.data?.detail as string || '更新案件資訊失敗');
    }
  }, [projectId, queryClient, message, setIsEditingCaseInfo]);

  const handleAgencyContactSubmit = useCallback(async (values: AgencyContactFormValues) => {
    try {
      if (editingAgencyContactId) {
        await updateAgencyContact(editingAgencyContactId, values);
        message.success('更新成功');
      } else {
        await createAgencyContact({ ...values, project_id: projectId });
        message.success('新增成功');
      }
      setAgencyContactModalVisible(false);
      setEditingAgencyContactId(null);
      agencyContactForm.resetFields();
      reloadData();
    } catch {
      message.error('儲存失敗');
    }
  }, [projectId, editingAgencyContactId, message, setAgencyContactModalVisible, setEditingAgencyContactId, agencyContactForm, reloadData]);

  const handleDeleteAgencyContact = useCallback(async (contactId: number) => {
    try { await deleteAgencyContact(contactId); message.success('刪除成功'); reloadData(); }
    catch { message.error('刪除失敗'); }
  }, [message, reloadData]);

  const handleAddStaff = useCallback(async (values: StaffFormValues) => {
    try {
      await projectStaffApi.addStaff({
        project_id: projectId, user_id: values.user_id, role: values.role,
        is_primary: values.role === '計畫主持', start_date: dayjs().format('YYYY-MM-DD'), status: 'active',
      });
      staffForm.resetFields();
      setStaffModalVisible(false);
      message.success('新增承辦同仁成功');
      reloadData();
    } catch (error) {
      const axiosError = error as { response?: { data?: ApiErrorResponse } };
      const detail = axiosError.response?.data?.detail;
      let errorMsg = '新增承辦同仁失敗';
      if (typeof detail === 'string') errorMsg = detail;
      else if (Array.isArray(detail) && detail.length > 0) {
        errorMsg = detail.map((d: PydanticValidationError) => d.msg || d.message || JSON.stringify(d)).join(', ');
      }
      message.error(errorMsg);
    }
  }, [projectId, staffForm, setStaffModalVisible, message, reloadData]);

  const handleStaffRoleChange = useCallback(async (staffId: number, newRole: string) => {
    const staff = staffList.find(s => s.id === staffId);
    if (!staff) return;
    try {
      await projectStaffApi.updateStaff(projectId, staff.user_id, { role: newRole, is_primary: newRole === '計畫主持' });
      queryClient.invalidateQueries({ queryKey: ['contract-case-detail', projectId] });
      setEditingStaffId(null);
      message.success('角色已更新');
    } catch { message.error('更新角色失敗'); setEditingStaffId(null); }
  }, [projectId, staffList, queryClient, message, setEditingStaffId]);

  const handleDeleteStaff = useCallback(async (staffId: number) => {
    const staff = staffList.find(s => s.id === staffId);
    if (!staff) return;
    try {
      await projectStaffApi.deleteStaff(projectId, staff.user_id);
      queryClient.invalidateQueries({ queryKey: ['contract-case-detail', projectId] });
      message.success('已移除同仁');
    } catch { message.error('移除同仁失敗'); }
  }, [projectId, staffList, queryClient, message]);

  const handleAddVendor = useCallback(async (values: VendorFormValues) => {
    try {
      const vendorData: {
        project_id: number; vendor_id: number; role: string; status: string;
        contract_amount?: number; start_date?: string; end_date?: string;
      } = { project_id: projectId, vendor_id: values.vendor_id, role: values.role, status: 'active' };
      if (values.contract_amount) vendorData.contract_amount = values.contract_amount;
      if (values.start_date) vendorData.start_date = dayjs(values.start_date as unknown as string).format('YYYY-MM-DD');
      if (values.end_date) vendorData.end_date = dayjs(values.end_date as unknown as string).format('YYYY-MM-DD');
      await projectVendorsApi.addVendor(vendorData);
      vendorForm.resetFields();
      setVendorModalVisible(false);
      message.success('新增協力廠商成功');
      reloadData();
    } catch { message.error('新增協力廠商失敗'); }
  }, [projectId, vendorForm, setVendorModalVisible, message, reloadData]);

  const handleVendorRoleChange = useCallback(async (vendorId: number, newRole: string) => {
    try {
      await projectVendorsApi.updateVendor(projectId, vendorId, { role: newRole });
      queryClient.invalidateQueries({ queryKey: ['contract-case-detail', projectId] });
      setEditingVendorId(null);
      message.success('角色已更新');
    } catch { message.error('更新角色失敗'); setEditingVendorId(null); }
  }, [projectId, queryClient, message, setEditingVendorId]);

  const handleDeleteVendor = useCallback(async (vendorId: number) => {
    try {
      await projectVendorsApi.deleteVendor(projectId, vendorId);
      queryClient.invalidateQueries({ queryKey: ['contract-case-detail', projectId] });
      message.success('已移除廠商');
    } catch { message.error('移除廠商失敗'); }
  }, [projectId, queryClient, message]);

  const handleDownloadAttachment = useCallback(async (attachmentId: number, filename: string) => {
    try { await filesApi.downloadAttachment(attachmentId, filename); }
    catch { message.error('下載附件失敗'); }
  }, [message]);

  const handlePreviewAttachment = useCallback(async (attachmentId: number, filename: string) => {
    try {
      const blob = await filesApi.getAttachmentBlob(attachmentId);
      const previewUrl = window.URL.createObjectURL(blob);
      window.open(previewUrl, '_blank');
      setTimeout(() => window.URL.revokeObjectURL(previewUrl), 10000);
    } catch { message.error(`預覽 ${filename} 失敗`); }
  }, [message]);

  const handleDownloadAllAttachments = useCallback(async (group: LocalGroupedAttachment) => {
    message.loading({ content: `正在下載 ${group.file_count} 個檔案...`, key: 'download-all' });
    for (const att of group.attachments) {
      try { await filesApi.downloadAttachment(att.id, att.filename); }
      catch (error) { logger.error(`下載 ${att.filename} 失敗:`, error); }
    }
    message.success({ content: '下載完成', key: 'download-all' });
  }, [message]);

  return {
    deleting,
    handleBack,
    handleEdit,
    handleDelete,
    handleSaveCaseInfo,
    handleAgencyContactSubmit,
    handleDeleteAgencyContact,
    handleAddStaff,
    handleStaffRoleChange,
    handleDeleteStaff,
    handleAddVendor,
    handleVendorRoleChange,
    handleDeleteVendor,
    handleDownloadAttachment,
    handlePreviewAttachment,
    handleDownloadAllAttachments,
  };
}
