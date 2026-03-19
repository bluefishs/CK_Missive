import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { Form, App } from 'antd';
import type { UploadFile } from 'antd/es/upload';
import {
  SendOutlined,
  FileTextOutlined,
  ProjectOutlined,
  PaperClipOutlined,
  DollarOutlined,
} from '@ant-design/icons';

import {
  DetailPageLayout,
  createTabItem,
} from '../components/common/DetailPage';
import { useAuthGuard } from '../hooks';
import { useDispatchQueries } from '../hooks/taoyuan/useDispatchQueries';
import { useDispatchMutations } from '../hooks/taoyuan/useDispatchMutations';
import { buildDispatchDetailHeader } from './taoyuanDispatch/DispatchDetailHeader';
import { useDispatchFormValues } from './taoyuanDispatch/useDispatchFormValues';

import {
  DispatchInfoTab,
  DispatchProjectsTab,
  DispatchAttachmentsTab,
  DispatchPaymentTab,
  DispatchWorkflowTab,
  type LinkedProject,
} from './taoyuanDispatch/tabs';

export const TaoyuanDispatchDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { message, modal } = App.useApp();
  const [form] = Form.useForm();

  const { hasPermission } = useAuthGuard();
  const canEdit = hasPermission('documents:edit');
  const canDelete = hasPermission('documents:delete');

  const initialTab = searchParams.get('tab') || 'info';
  const [activeTab, setActiveTab] = useState(initialTab);
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    const tabFromUrl = searchParams.get('tab') || 'info';
    if (tabFromUrl !== activeTab) {
      setActiveTab(tabFromUrl);
    }
  }, [searchParams, activeTab]);

  const handleTabChange = useCallback((tabKey: string) => {
    setActiveTab(tabKey);
    setSearchParams({ tab: tabKey }, { replace: true });
  }, [setSearchParams]);

  const [selectedProjectId, setSelectedProjectId] = useState<number>();

  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);

  const {
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
  } = useDispatchQueries(id);

  const {
    paymentMutation,
    updateMutation,
    deleteMutation,
    linkProjectMutation,
    createProjectMutation,
    unlinkProjectMutation,
    uploadAttachmentsMutation,
    deleteAttachmentMutation,
  } = useDispatchMutations({
    id,
    form,
    message,
    navigate,
    dispatch,
    paymentData,
    refetch,
    refetchPayment,
    refetchAttachments,
    setIsEditing,
    fileList,
    setFileList,
    setUploading,
    setUploadProgress,
    setUploadErrors,
    setSelectedProjectId,
  });

  const watchedWorkTypes: string[] = Form.useWatch('work_type', form) || [];
  const watchedWork01Amount = Form.useWatch('work_01_amount', form) || 0;
  const watchedWork02Amount = Form.useWatch('work_02_amount', form) || 0;
  const watchedWork03Amount = Form.useWatch('work_03_amount', form) || 0;
  const watchedWork04Amount = Form.useWatch('work_04_amount', form) || 0;
  const watchedWork05Amount = Form.useWatch('work_05_amount', form) || 0;
  const watchedWork06Amount = Form.useWatch('work_06_amount', form) || 0;
  const watchedWork07Amount = Form.useWatch('work_07_amount', form) || 0;

  const watchedWorkAmounts = useMemo(() => ({
    work_01_amount: watchedWork01Amount,
    work_02_amount: watchedWork02Amount,
    work_03_amount: watchedWork03Amount,
    work_04_amount: watchedWork04Amount,
    work_05_amount: watchedWork05Amount,
    work_06_amount: watchedWork06Amount,
    work_07_amount: watchedWork07Amount,
  }), [
    watchedWork01Amount, watchedWork02Amount, watchedWork03Amount,
    watchedWork04Amount, watchedWork05Amount, watchedWork06Amount,
    watchedWork07Amount
  ]);

  // Form values management (extracted hook)
  const { handleSave, handleCancelEdit } = useDispatchFormValues({
    id,
    dispatch,
    paymentData,
    form,
    message,
    updateMutation,
    paymentMutation,
    uploadAttachmentsMutation,
    fileList,
    setIsEditing,
  });

  const handleLinkProject = useCallback(() => {
    if (!selectedProjectId) {
      message.warning('請先選擇要關聯的工程');
      return;
    }
    linkProjectMutation.mutate(selectedProjectId);
  }, [selectedProjectId, linkProjectMutation, message]);

  const handleProjectSelectFromInfo = useCallback((projectId: number, projectName: string) => {
    const isAlreadyLinked = linkedProjectIds.includes(projectId);
    if (isAlreadyLinked) {
      message.info(`工程「${projectName}」已經關聯`);
      return;
    }

    modal.confirm({
      title: '建立工程關聯',
      content: `您選擇了工程「${projectName}」，是否同時建立工程關聯？`,
      okText: '是，建立關聯',
      cancelText: '否，僅填入名稱',
      onOk: () => {
        linkProjectMutation.mutate(projectId);
      },
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [linkedProjectIds, message, linkProjectMutation]);

  const handleCreateProjectFromInfo = useCallback((projectName: string) => {
    modal.confirm({
      title: '新增工程',
      content: (
        <div>
          <p>確定要建立以下工程嗎？</p>
          <p style={{ fontWeight: 'bold', color: '#1890ff' }}>{projectName}</p>
          <p style={{ color: '#999', fontSize: 12 }}>
            建立後將自動關聯至此派工單。如需修改名稱，請先取消並重新輸入完整名稱。
          </p>
        </div>
      ),
      okText: '確定建立',
      cancelText: '取消',
      onOk: () => {
        createProjectMutation.mutate(projectName);
      },
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [createProjectMutation]);

  const tabs = [
    createTabItem(
      'info',
      { icon: <SendOutlined />, text: '派工資訊' },
      <DispatchInfoTab
        dispatch={dispatch}
        form={form}
        isEditing={isEditing}
        agencyContacts={agencyContacts}
        projectVendors={projectVendors}
        paymentData={paymentData}
        watchedWorkTypes={watchedWorkTypes}
        watchedWorkAmounts={watchedWorkAmounts}
        availableProjects={availableProjects}
        onProjectSelect={handleProjectSelectFromInfo}
        onCreateProject={handleCreateProjectFromInfo}
      />
    ),
    createTabItem(
      'attachments',
      {
        icon: <PaperClipOutlined />,
        text: '派工附件',
        count: attachments?.length || 0,
      },
      <DispatchAttachmentsTab
        dispatchId={parseInt(id || '0', 10)}
        isEditing={isEditing}
        isLoading={isLoading}
        attachments={attachments || []}
        fileList={fileList}
        setFileList={setFileList}
        uploading={uploading}
        uploadProgress={uploadProgress}
        uploadErrors={uploadErrors}
        setUploadErrors={setUploadErrors}
        uploadAttachmentsMutation={uploadAttachmentsMutation}
        deleteAttachmentMutation={deleteAttachmentMutation}
      />
    ),
    createTabItem(
      'projects',
      {
        icon: <ProjectOutlined />,
        text: '工程關聯',
        count: dispatch?.linked_projects?.length || 0,
      },
      <DispatchProjectsTab
        isLoading={isLoading}
        canEdit={canEdit}
        linkedProjects={(dispatch?.linked_projects || []) as LinkedProject[]}
        filteredProjects={filteredProjects}
        selectedProjectId={selectedProjectId}
        setSelectedProjectId={setSelectedProjectId}
        onLinkProject={handleLinkProject}
        linkProjectLoading={linkProjectMutation.isPending}
        onUnlinkProject={(linkId, _projectId, _proj) => unlinkProjectMutation.mutate(linkId)}
        unlinkProjectLoading={unlinkProjectMutation.isPending}
        navigate={navigate}
        messageError={message.error}
        refetch={refetch}
      />
    ),
    createTabItem(
      'payment',
      { icon: <DollarOutlined />, text: '契金維護' },
      <DispatchPaymentTab
        dispatch={dispatch}
        paymentData={paymentData}
        isEditing={isEditing}
        form={form}
      />
    ),
    createTabItem(
      'correspondence',
      {
        icon: <FileTextOutlined />,
        text: '公文對照',
        count: dispatch?.linked_documents?.length || 0,
      },
      <DispatchWorkflowTab
        dispatchOrderId={parseInt(id || '0', 10)}
        canEdit={canEdit}
        linkedProjects={(dispatch?.linked_projects || []).map((p: LinkedProject) => ({
          project_id: p.project_id,
          project_name: p.project_name,
        }))}
        linkedDocuments={dispatch?.linked_documents || []}
        onRefetchDispatch={refetch}
        contractProjectId={dispatch?.contract_project_id}
        projectName={dispatch?.project_name}
        dispatchNo={dispatch?.dispatch_no}
        workType={dispatch?.work_type}
      />
    ),
  ];

  const headerConfig = buildDispatchDetailHeader({
    dispatchNo: dispatch?.dispatch_no,
    workType: dispatch?.work_type,
    isEditing,
    canEdit,
    canDelete,
    isSaving: updateMutation.isPending,
    onEdit: () => setIsEditing(true),
    onSave: handleSave,
    onCancelEdit: handleCancelEdit,
    onDelete: () => deleteMutation.mutate(),
  });

  return (
    <DetailPageLayout
      header={headerConfig}
      tabs={tabs}
      activeTab={activeTab}
      onTabChange={handleTabChange}
      loading={isLoading}
      hasData={!!dispatch}
    />
  );
};

export default TaoyuanDispatchDetailPage;
