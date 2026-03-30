import React, { useState } from 'react';
import {
  Card,
  Tag,
  Button,
  Typography,
  Spin,
  Tabs,
  Form,
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
import { useParams } from 'react-router-dom';

import { DetailPageHeader } from './contractCase/DetailPageHeader';
import { useContractCaseData } from './contractCase/useContractCaseData';
import { useContractCaseHandlers } from './contractCase/useContractCaseHandlers';
import { CrossModuleCard } from './pmCase';
import { useCrossModuleLookup } from '../hooks/business/usePMCases';
import { Suspense, lazy } from 'react';

const MilestonesGanttTab = lazy(() => import('./pmCase/MilestonesGanttTab'));

import {
  CaseInfoTab,
  AgencyContactTab,
  StaffTab,
  VendorsTab,
  AttachmentsTab,
  RelatedDocumentsTab,
} from './contractCase/tabs';

import type {
  CaseInfoFormValues,
  AgencyContactFormValues,
  StaffFormValues,
  VendorFormValues,
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

  // ERP cross-module lookup via case_code (建案案號，跨模組橋樑)
  // 優先用 case_code，回退 project_code（向後相容舊資料）
  const crossLookupKey = data?.case_code ?? data?.project_code ?? null;
  const { data: crossData } = useCrossModuleLookup(crossLookupKey);
  const pmCaseId = crossData?.pm?.id ?? null;

  const loadUserOptions = async () => {};
  const loadVendorOptions = async () => {
    queryClient.invalidateQueries({ queryKey: ['contract-case-vendor-options'] });
  };

  const handlers = useContractCaseHandlers({
    projectId: propProjectId,
    queryClient,
    reloadData,
    staffList,
    backRoute,
    staffForm,
    vendorForm,
    agencyContactForm,
    setIsEditingCaseInfo,
    setStaffModalVisible,
    setVendorModalVisible,
    setAgencyContactModalVisible,
    setEditingAgencyContactId,
    editingAgencyContactId,
    setEditingStaffId,
    setEditingVendorId,
  });

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

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 50 }}><Spin size="large" /></div>;
  }

  if (!data) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: 50 }}>
          <Title level={4}>案件不存在</Title>
          <Button type="primary" onClick={handlers.handleBack}>返回列表</Button>
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
          form={caseInfoForm} onSave={handlers.handleSaveCaseInfo} calculateProgress={calculateProgress}
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
          onSubmit={handlers.handleAgencyContactSubmit} onDelete={handlers.handleDeleteAgencyContact}
        />
      ),
    },
    {
      key: 'staff',
      label: <span><TeamOutlined /> 承辦同仁 <Tag color="blue" style={{ marginLeft: 8 }}>{staffList.length}</Tag></span>,
      children: (
        <StaffTab
          staffList={staffList} editingStaffId={editingStaffId} setEditingStaffId={setEditingStaffId}
          onRoleChange={handlers.handleStaffRoleChange} onDelete={handlers.handleDeleteStaff}
          modalVisible={staffModalVisible} setModalVisible={setStaffModalVisible}
          form={staffForm} onAddStaff={handlers.handleAddStaff}
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
          onRoleChange={handlers.handleVendorRoleChange} onDelete={handlers.handleDeleteVendor}
          modalVisible={vendorModalVisible} setModalVisible={setVendorModalVisible}
          form={vendorForm} onAddVendor={handlers.handleAddVendor}
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
          onDownload={handlers.handleDownloadAttachment} onPreview={handlers.handlePreviewAttachment}
          onDownloadAll={handlers.handleDownloadAllAttachments} relatedDocsCount={relatedDocs.length}
        />
      ),
    },
    {
      key: 'documents',
      label: <span><FileTextOutlined /> 關聯公文 <Tag color="blue" style={{ marginLeft: 8 }}>{relatedDocs.length}</Tag></span>,
      children: <RelatedDocumentsTab relatedDocs={relatedDocs} onRefresh={reloadData} />,
    },
    {
      key: 'milestones',
      label: <span>里程碑/甘特圖</span>,
      children: pmCaseId ? (
        <Suspense fallback={<Spin />}>
          <MilestonesGanttTab pmCaseId={pmCaseId} />
        </Suspense>
      ) : (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
          尚無關聯 PM 案件，請先在邀標/報價模組建立案件並成案
        </div>
      ),
    },
    {
      key: 'erp',
      label: <span><DollarOutlined /> ERP 財務</span>,
      children: crossLookupKey ? (
        <CrossModuleCard caseCode={crossLookupKey} />
      ) : (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
          尚無 ERP 財務資料，請先在邀標/報價模組建立報價
        </div>
      ),
    },
  ];

  return (
    <div>
      <DetailPageHeader
        projectName={data.project_name} category={data.category}
        status={data.status} onBack={handlers.handleBack}
        onEdit={handlers.handleEdit} onDelete={handlers.handleDelete} deleting={handlers.deleting}
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
