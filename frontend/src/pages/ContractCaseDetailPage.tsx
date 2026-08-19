import React, { useState } from 'react';
import {
  Button,
  Spin,
  Form,
  Space,
  Popconfirm,
} from 'antd';
import {
  InfoCircleOutlined,
  BankOutlined,
  TeamOutlined,
  ShopOutlined,
  PaperClipOutlined,
  FileTextOutlined,
  DollarOutlined,
  EditOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { useParams } from 'react-router-dom';

import { DetailPageLayout, createTabItem } from '../components/common/DetailPage';
import { SourceTenderLink } from '../components/common/SourceTenderLink';
import { ExpenseQRButton } from '../components/common/ExpenseQRCode';
import { useContractCaseData } from './contractCase/useContractCaseData';
import { useContractCaseHandlers } from './contractCase/useContractCaseHandlers';
import { useCrossModuleLookup } from '../hooks/business/usePMCases';
import { STATUS_OPTIONS, CATEGORY_OPTIONS } from './contractCase/tabs';
import { Suspense, lazy } from 'react';

const MilestonesGanttTab = lazy(() => import('./pmCase/MilestonesGanttTab'));

import {
  CaseInfoTab,
  AgencyContactTab,
  StaffTab,
  VendorsTab,
  AttachmentsTab,
  RelatedDocumentsTab,
  FinanceTab,
} from './contractCase/tabs';

import type {
  CaseInfoFormValues,
} from './contractCase/tabs';

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

  const [caseInfoForm] = Form.useForm<CaseInfoFormValues>();

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
    reloadData,
    queryClient,
  } = useContractCaseData(projectId);

  // ERP cross-module lookup via case_code (建案案號，跨模組橋樑)
  // 優先用 case_code，回退 project_code（向後相容舊資料）
  const lookupKey = data?.case_code ?? data?.project_code ?? null;
  const { data: crossData } = useCrossModuleLookup(lookupKey);
  const pmCaseId = crossData?.pm?.id ?? null;

  const handlers = useContractCaseHandlers({
    projectId: propProjectId,
    queryClient,
    backRoute,
    setIsEditingCaseInfo,
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

  // Build status/category tags for header
  const statusOption = STATUS_OPTIONS.find(s => s.value === data?.status);
  const categoryOption = CATEGORY_OPTIONS.find(c => c.value === data?.category);
  const headerTags = [
    ...(categoryOption ? [{ text: categoryOption.label || data?.category || '未分類', color: categoryOption.color }] : [{ text: '未分類', color: 'default' }]),
    ...(statusOption ? [{ text: statusOption.label || data?.status || '未設定', color: statusOption.color }] : [{ text: '未設定', color: 'default' }]),
  ];

  const tabItems = [
    createTabItem('info', { icon: <InfoCircleOutlined />, text: '案件資訊' },
      data ? (
        <CaseInfoTab
          data={data} isEditing={isEditingCaseInfo} setIsEditing={setIsEditingCaseInfo}
          form={caseInfoForm} onSave={handlers.handleSaveCaseInfo} calculateProgress={calculateProgress}
        />
      ) : null
    ),
    createTabItem('agency', { icon: <BankOutlined />, text: '機關承辦', count: agencyContacts.length },
      <AgencyContactTab agencyContacts={agencyContacts} projectId={projectId} />
    ),
    createTabItem('staff', { icon: <TeamOutlined />, text: '承辦同仁', count: staffList.length },
      <StaffTab staffList={staffList} projectId={projectId} />
    ),
    createTabItem('vendors', { icon: <ShopOutlined />, text: '協力廠商', count: vendorList.length },
      <VendorsTab vendorList={vendorList} projectId={projectId} />
    ),
    createTabItem('attachments', { icon: <PaperClipOutlined />, text: '附件紀錄', count: attachments.length },
      <AttachmentsTab
        attachments={attachments} groupedAttachments={groupedAttachments}
        loading={attachmentsLoading} onRefresh={reloadData}
        onDownload={handlers.handleDownloadAttachment} onPreview={handlers.handlePreviewAttachment}
        onDownloadAll={handlers.handleDownloadAllAttachments} relatedDocsCount={relatedDocs.length}
        caseCode={data?.case_code ?? undefined} canWrite
      />
    ),
    createTabItem('documents', { icon: <FileTextOutlined />, text: '關聯公文', count: relatedDocs.length },
      <RelatedDocumentsTab relatedDocs={relatedDocs} onRefresh={reloadData} />
    ),
    createTabItem('milestones', { icon: <FileTextOutlined />, text: '里程碑/甘特圖' },
      pmCaseId ? (
        <Suspense fallback={<Spin />}>
          <MilestonesGanttTab pmCaseId={pmCaseId} />
        </Suspense>
      ) : (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
          尚無關聯 PM 案件，請先在邀標/報價模組建立案件並成案
        </div>
      )
    ),
    createTabItem('finance', { icon: <DollarOutlined />, text: '財務紀錄' },
      data ? (
        <FinanceTab
          caseCode={data.case_code ?? null}
          projectCode={data.project_code ?? null}
          projectName={data.project_name ?? null}
          sourceTenderId={data.source_tender_id ?? null}
        />
      ) : null
    ),
  ];

  const headerExtra = (
    // 2026-08-05 視覺走查發現：手機版這排按鈕**左緣被裁掉**，第一顆
    // 只看得到「源標案」而點不到。DetailPageHeader 外層已 `wrap={isMobile}`，
    // 但這個內層 Space 沒有 wrap，於是整排不換行、向左溢出被切。
    // 斷言看不到這個 —— 按鈕存在、數量正確，只是有一顆碰不到。
    <Space wrap>
      {/* 2026-07-31 L3 回指：顯示本案來自哪個標案（原本雙向都看不到對方） */}
      <SourceTenderLink sourceTenderId={data?.source_tender_id} />
      {/* 2026-07-29：工地人員常從承攬案件頁找案子，故此處也提供核銷 QR
          （比照 PMCaseDetailPage / ERPQuotationDetailPage；沿用同一元件，零新邏輯）。
          僅在有 case_code 時顯示——無 case_code 掃了也無法關聯，見「財務紀錄」分頁的補建指引。 */}
      {data?.case_code && (
        <ExpenseQRButton caseCode={data.case_code} caseName={data.project_name} />
      )}
      {handlers.handleEdit && (
        <Button icon={<EditOutlined />} onClick={handlers.handleEdit}>
          編輯
        </Button>
      )}
      {handlers.handleDelete && (
        <Popconfirm
          title="確定要刪除此承攬案件嗎？"
          description="刪除後將無法復原，關聯的承辦同仁與廠商資料也會一併刪除。"
          onConfirm={handlers.handleDelete}
          okText="確定刪除"
          cancelText="取消"
          okButtonProps={{ danger: true, loading: handlers.deleting }}
        >
          <Button danger icon={<DeleteOutlined />} loading={handlers.deleting}>
            刪除
          </Button>
        </Popconfirm>
      )}
    </Space>
  );

  return (
    <DetailPageLayout
      header={{
        title: data?.project_name || '承攬案件詳情',
        tags: headerTags,
        backText: '返回',
        backPath: backRoute,
        extra: headerExtra,
      }}
      tabs={tabItems}
      activeTab={activeTab}
      onTabChange={setActiveTab}
      loading={loading}
      hasData={!!data}
    />
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
