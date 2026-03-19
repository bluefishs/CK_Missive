import React, { useState } from 'react';
import {
  Card,
  Tag,
  Button,
  Typography,
  Spin,
  Tabs,
  Form,
  App,
} from 'antd';
import {
  InfoCircleOutlined,
  BankOutlined,
  TeamOutlined,
  ShopOutlined,
  PaperClipOutlined,
  FileTextOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { ROUTES } from '../router/types';
import { queryKeys } from '../config/queryConfig';

import { projectsApi } from '../api/projectsApi';
import { filesApi } from '../api/filesApi';
import { projectStaffApi } from '../api/projectStaffApi';
import { projectVendorsApi } from '../api/projectVendorsApi';
import {
  createAgencyContact,
  updateAgencyContact,
  deleteAgencyContact,
} from '../api/projectAgencyContacts';
import { logger } from '../utils/logger';

import { DetailPageHeader } from './contractCase/DetailPageHeader';
import { useContractCaseData } from './contractCase/useContractCaseData';
import { CrossModuleCard } from './pmCase';
import { useCrossModuleLookup } from '../hooks/business/usePMCases';
import { Suspense, lazy } from 'react';

const MilestonesTab = lazy(() => import('./pmCase/MilestonesTab'));
const GanttTab = lazy(() => import('./pmCase/GanttTab'));

import {
  CaseInfoTab,
  AgencyContactTab,
  StaffTab,
  VendorsTab,
  AttachmentsTab,
  RelatedDocumentsTab,
} from './contractCase/tabs';

import type {
  LocalGroupedAttachment,
  CaseInfoFormValues,
  AgencyContactFormValues,
  StaffFormValues,
  VendorFormValues,
  ApiErrorResponse,
  PydanticValidationError,
} from './contractCase/tabs';

const { Title } = Typography;

// ============================================================================
// Shared content component — used by both /contract-cases/:id and /pm/cases/:id
// ============================================================================

export interface ContractCaseDetailContentProps {
  projectId: number;
  backRoute?: string;
}

export const ContractCaseDetailContent: React.FC<ContractCaseDetailContentProps> = ({
  projectId: propProjectId,
  backRoute,
}) => {
  const navigate = useNavigate();
  const { message } = App.useApp();

  const [activeTab, setActiveTab] = useState('info');
  const [isEditingCaseInfo, setIsEditingCaseInfo] = useState(false);
  const [editingStaffId, setEditingStaffId] = useState<number | null>(null);
  const [editingVendorId, setEditingVendorId] = useState<number | null>(null);
  const [staffModalVisible, setStaffModalVisible] = useState(false);
  const [vendorModalVisible, setVendorModalVisible] = useState(false);
  const [agencyContactModalVisible, setAgencyContactModalVisible] = useState(false);
  const [editingAgencyContactId, setEditingAgencyContactId] = useState<number | null>(null);

  const [staffForm] = Form.useForm<StaffFormValues>();
  const [vendorForm] = Form.useForm<VendorFormValues>();
  const [caseInfoForm] = Form.useForm<CaseInfoFormValues>();
  const [agencyContactForm] = Form.useForm<AgencyContactFormValues>();

  const projectId = propProjectId;

  const {
    data,
    staffList,
    vendorList,
    agencyContacts,
    relatedDocs,
    attachments,
    groupedAttachments,
    attachmentsLoading,
    loading,
    userOptions,
    vendorOptions,
    reloadData,
    queryClient,
  } = useContractCaseData(projectId);

  // ERP cross-module lookup via project_code
  const { data: crossData } = useCrossModuleLookup(data?.project_code ?? null);
  const hasErpData = !!crossData?.erp;
  const pmCaseId = crossData?.pm?.id ?? null;

  const loadUserOptions = async () => {};
  const loadVendorOptions = async () => {};

  const handleBack = () => navigate(backRoute || ROUTES.CONTRACT_CASES);

  const calculateProgress = () => {
    if (!data || !data.start_date || !data.end_date) return 0;
    const startDate = new Date(data.start_date);
    const endDate = new Date(data.end_date);
    const currentDate = new Date();
    if (currentDate < startDate) return 0;
    if (currentDate > endDate) return 100;
    const totalDays = endDate.getTime() - startDate.getTime();
    const passedDays = currentDate.getTime() - startDate.getTime();
    return Math.round((passedDays / totalDays) * 100);
  };

  const handleSaveCaseInfo = async (values: CaseInfoFormValues) => {
    if (!data) return;
    const pid = propProjectId;
    try {
      const autoProgress = values.status === '已結案' ? 100 : values.progress;
      const startDate = values.date_range?.[0] ? dayjs(values.date_range[0]).format('YYYY-MM-DD') : undefined;
      const endDate = values.date_range?.[1] ? dayjs(values.date_range[1]).format('YYYY-MM-DD') : undefined;
      const updateData = {
        project_name: values.project_name,
        year: values.year,
        client_agency: values.client_agency || undefined,
        contract_doc_number: values.contract_doc_number || undefined,
        project_code: values.project_code || undefined,
        category: values.category || undefined,
        case_nature: values.case_nature || undefined,
        contract_amount: values.contract_amount || undefined,
        winning_amount: values.winning_amount || undefined,
        start_date: startDate,
        end_date: endDate,
        status: values.status || undefined,
        progress: autoProgress ?? undefined,
        project_path: values.project_path || undefined,
        notes: values.notes || undefined,
        has_dispatch_management: values.has_dispatch_management,
      };
      await projectsApi.updateProject(pid, updateData as Parameters<typeof projectsApi.updateProject>[1]);
      queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
      queryClient.invalidateQueries({ queryKey: ['taoyuan-dispatch-orders', 'contract-projects'] });
      queryClient.invalidateQueries({ queryKey: ['contract-case-detail', pid] });
      setIsEditingCaseInfo(false);
      message.success('案件資訊已更新');
    } catch (error) {
      logger.error('更新案件資訊失敗:', error);
      const axiosError = error as { response?: { data?: ApiErrorResponse } };
      message.error(axiosError.response?.data?.detail as string || '更新案件資訊失敗');
    }
  };

  const handleAgencyContactSubmit = async (values: AgencyContactFormValues) => {
    const pid = propProjectId;
    try {
      if (editingAgencyContactId) {
        await updateAgencyContact(editingAgencyContactId, values);
        message.success('更新成功');
      } else {
        await createAgencyContact({ ...values, project_id: pid });
        message.success('新增成功');
      }
      setAgencyContactModalVisible(false);
      setEditingAgencyContactId(null);
      agencyContactForm.resetFields();
      reloadData();
    } catch {
      message.error('儲存失敗');
    }
  };

  const handleDeleteAgencyContact = async (contactId: number) => {
    try {
      await deleteAgencyContact(contactId);
      message.success('刪除成功');
      reloadData();
    } catch {
      message.error('刪除失敗');
    }
  };

  const handleAddStaff = async (values: StaffFormValues) => {
    const pid = propProjectId;
    try {
      await projectStaffApi.addStaff({
        project_id: pid,
        user_id: values.user_id,
        role: values.role,
        is_primary: values.role === '計畫主持',
        start_date: dayjs().format('YYYY-MM-DD'),
        status: 'active',
      });
      staffForm.resetFields();
      setStaffModalVisible(false);
      message.success('新增承辦同仁成功');
      reloadData();
    } catch (error) {
      const axiosError = error as { response?: { data?: ApiErrorResponse } };
      const detail = axiosError.response?.data?.detail;
      let errorMsg = '新增承辦同仁失敗';
      if (typeof detail === 'string') {
        errorMsg = detail;
      } else if (Array.isArray(detail) && detail.length > 0) {
        errorMsg = detail.map((d: PydanticValidationError) => d.msg || d.message || JSON.stringify(d)).join(', ');
      }
      message.error(errorMsg);
    }
  };

  const handleStaffRoleChange = async (staffId: number, newRole: string) => {
    const pid = propProjectId;
    const staff = staffList.find(s => s.id === staffId);
    if (!staff) return;
    try {
      await projectStaffApi.updateStaff(pid, staff.user_id, { role: newRole, is_primary: newRole === '計畫主持' });
      queryClient.invalidateQueries({ queryKey: ['contract-case-detail', pid] });
      setEditingStaffId(null);
      message.success('角色已更新');
    } catch {
      message.error('更新角色失敗');
      setEditingStaffId(null);
    }
  };

  const handleDeleteStaff = async (staffId: number) => {
    const pid = propProjectId;
    const staff = staffList.find(s => s.id === staffId);
    if (!staff) return;
    try {
      await projectStaffApi.deleteStaff(pid, staff.user_id);
      queryClient.invalidateQueries({ queryKey: ['contract-case-detail', pid] });
      message.success('已移除同仁');
    } catch {
      message.error('移除同仁失敗');
    }
  };

  const handleAddVendor = async (values: VendorFormValues) => {
    const pid = propProjectId;
    try {
      const vendorData: {
        project_id: number; vendor_id: number; role: string; status: string;
        contract_amount?: number; start_date?: string; end_date?: string;
      } = { project_id: pid, vendor_id: values.vendor_id, role: values.role, status: 'active' };
      if (values.contract_amount) vendorData.contract_amount = values.contract_amount;
      if (values.start_date) vendorData.start_date = dayjs(values.start_date).format('YYYY-MM-DD');
      if (values.end_date) vendorData.end_date = dayjs(values.end_date).format('YYYY-MM-DD');
      await projectVendorsApi.addVendor(vendorData);
      vendorForm.resetFields();
      setVendorModalVisible(false);
      message.success('新增協力廠商成功');
      reloadData();
    } catch {
      message.error('新增協力廠商失敗');
    }
  };

  const handleVendorRoleChange = async (vendorId: number, newRole: string) => {
    const pid = propProjectId;
    try {
      await projectVendorsApi.updateVendor(pid, vendorId, { role: newRole });
      queryClient.invalidateQueries({ queryKey: ['contract-case-detail', pid] });
      setEditingVendorId(null);
      message.success('角色已更新');
    } catch {
      message.error('更新角色失敗');
      setEditingVendorId(null);
    }
  };

  const handleDeleteVendor = async (vendorId: number) => {
    const pid = propProjectId;
    try {
      await projectVendorsApi.deleteVendor(pid, vendorId);
      queryClient.invalidateQueries({ queryKey: ['contract-case-detail', pid] });
      message.success('已移除廠商');
    } catch {
      message.error('移除廠商失敗');
    }
  };

  const handleDownloadAttachment = async (attachmentId: number, filename: string) => {
    try { await filesApi.downloadAttachment(attachmentId, filename); }
    catch { message.error('下載附件失敗'); }
  };

  const handlePreviewAttachment = async (attachmentId: number, filename: string) => {
    try {
      const blob = await filesApi.getAttachmentBlob(attachmentId);
      const previewUrl = window.URL.createObjectURL(blob);
      window.open(previewUrl, '_blank');
      setTimeout(() => window.URL.revokeObjectURL(previewUrl), 10000);
    } catch { message.error(`預覽 ${filename} 失敗`); }
  };

  const handleDownloadAllAttachments = async (group: LocalGroupedAttachment) => {
    message.loading({ content: `正在下載 ${group.file_count} 個檔案...`, key: 'download-all' });
    for (const att of group.attachments) {
      try { await filesApi.downloadAttachment(att.id, att.filename); }
      catch (error) { logger.error(`下載 ${att.filename} 失敗:`, error); }
    }
    message.success({ content: '下載完成', key: 'download-all' });
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 50 }}><Spin size="large" /></div>;
  }

  if (!data) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: 50 }}>
          <Title level={4}>案件不存在</Title>
          <Button type="primary" onClick={handleBack}>返回列表</Button>
        </div>
      </Card>
    );
  }

  const tabItems = [
    {
      key: 'info',
      label: <span><InfoCircleOutlined /> 案件資訊</span>,
      children: (
        <CaseInfoTab
          data={data} isEditing={isEditingCaseInfo} setIsEditing={setIsEditingCaseInfo}
          form={caseInfoForm} onSave={handleSaveCaseInfo} calculateProgress={calculateProgress}
        />
      ),
    },
    {
      key: 'agency',
      label: <span><BankOutlined /> 機關承辦 <Tag color="blue" style={{ marginLeft: 8 }}>{agencyContacts.length}</Tag></span>,
      children: (
        <AgencyContactTab
          agencyContacts={agencyContacts} modalVisible={agencyContactModalVisible}
          setModalVisible={setAgencyContactModalVisible} editingId={editingAgencyContactId}
          setEditingId={setEditingAgencyContactId} form={agencyContactForm}
          onSubmit={handleAgencyContactSubmit} onDelete={handleDeleteAgencyContact}
        />
      ),
    },
    {
      key: 'staff',
      label: <span><TeamOutlined /> 承辦同仁 <Tag color="blue" style={{ marginLeft: 8 }}>{staffList.length}</Tag></span>,
      children: (
        <StaffTab
          staffList={staffList} editingStaffId={editingStaffId} setEditingStaffId={setEditingStaffId}
          onRoleChange={handleStaffRoleChange} onDelete={handleDeleteStaff}
          modalVisible={staffModalVisible} setModalVisible={setStaffModalVisible}
          form={staffForm} onAddStaff={handleAddStaff}
          userOptions={userOptions} loadUserOptions={loadUserOptions}
        />
      ),
    },
    {
      key: 'vendors',
      label: <span><ShopOutlined /> 協力廠商 <Tag color="blue" style={{ marginLeft: 8 }}>{vendorList.length}</Tag></span>,
      children: (
        <VendorsTab
          vendorList={vendorList} editingVendorId={editingVendorId} setEditingVendorId={setEditingVendorId}
          onRoleChange={handleVendorRoleChange} onDelete={handleDeleteVendor}
          modalVisible={vendorModalVisible} setModalVisible={setVendorModalVisible}
          form={vendorForm} onAddVendor={handleAddVendor}
          vendorOptions={vendorOptions} loadVendorOptions={loadVendorOptions}
        />
      ),
    },
    {
      key: 'attachments',
      label: <span><PaperClipOutlined /> 附件紀錄 <Tag color="blue" style={{ marginLeft: 8 }}>{attachments.length}</Tag></span>,
      children: (
        <AttachmentsTab
          attachments={attachments} groupedAttachments={groupedAttachments}
          loading={attachmentsLoading} onRefresh={reloadData}
          onDownload={handleDownloadAttachment} onPreview={handlePreviewAttachment}
          onDownloadAll={handleDownloadAllAttachments} relatedDocsCount={relatedDocs.length}
        />
      ),
    },
    {
      key: 'documents',
      label: <span><FileTextOutlined /> 關聯公文 <Tag color="blue" style={{ marginLeft: 8 }}>{relatedDocs.length}</Tag></span>,
      children: <RelatedDocumentsTab relatedDocs={relatedDocs} onRefresh={reloadData} />,
    },
    ...(pmCaseId ? [{
      key: 'milestones',
      label: <span>里程碑</span>,
      children: (
        <Suspense fallback={<Spin />}>
          <MilestonesTab pmCaseId={pmCaseId} />
        </Suspense>
      ),
    }, {
      key: 'gantt',
      label: <span>甘特圖</span>,
      children: (
        <Suspense fallback={<Spin />}>
          <GanttTab pmCaseId={pmCaseId} />
        </Suspense>
      ),
    }] : []),
    ...(hasErpData && data?.project_code ? [{
      key: 'erp',
      label: <span><DollarOutlined /> ERP 財務</span>,
      children: <CrossModuleCard caseCode={data.project_code} />,
    }] : []),
  ];

  return (
    <div>
      <DetailPageHeader
        projectName={data.project_name} category={data.category}
        status={data.status} onBack={handleBack}
      />
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} size="large" />
      </Card>
    </div>
  );
};

// ============================================================================
// Route wrapper — extracts projectId from URL params
// ============================================================================

export const ContractCaseDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const projectId = id ? parseInt(id, 10) : 0;

  if (!projectId) {
    return <div>Invalid project ID</div>;
  }

  return <ContractCaseDetailContent projectId={projectId} />;
};

export default ContractCaseDetailPage;
