/**
 * 發文新增頁面
 *
 * 使用 useDocumentCreateForm Hook 和共用 Tab 元件
 * 重構自原有 825 行程式碼
 *
 * @version 2.0.0
 * @date 2026-01-28
 */

import React from 'react';
import { Form, Button, Space } from 'antd';
import {
  FileTextOutlined,
  PaperClipOutlined,
  TeamOutlined,
  SaveOutlined,
  CloseOutlined,
} from '@ant-design/icons';

import {
  DetailPageLayout,
  createTabItem,
} from '../components/common/DetailPage';
import {
  DocumentCreateInfoTab,
  DocumentCreateStaffTab,
  DocumentCreateAttachmentTab,
} from '../components/document/create';
import { useDocumentCreateForm } from '../hooks';

// =============================================================================
// 主元件
// =============================================================================

export const SendDocumentCreatePage: React.FC = () => {
  const [form] = Form.useForm();

  const formState = useDocumentCreateForm({
    mode: 'send',
    form,
  });

  const {
    loading,
    saving,
    activeTab,
    setActiveTab,
    // 資料選項
    cases,
    casesLoading,
    staffLoading,
    usersLoading,
    agenciesLoading,
    fileSettings,
    // 附件
    fileList,
    setFileList,
    uploading,
    uploadProgress,
    uploadErrors,
    clearUploadErrors,
    // 發文專用
    nextNumber,
    nextNumberLoading,
    // 事件
    handleProjectChange,
    validateFile,
    handleSave,
    handleCancel,
    // 工具
    buildAssigneeOptions,
    buildAgencyOptions,
  } = formState;

  // =============================================================================
  // Tab 配置
  // =============================================================================

  const tabs = [
    createTabItem(
      'info',
      { icon: <FileTextOutlined />, text: '公文資訊' },
      <DocumentCreateInfoTab
        mode="send"
        form={form}
        agenciesLoading={agenciesLoading}
        buildAgencyOptions={buildAgencyOptions}
        nextNumber={nextNumber}
        nextNumberLoading={nextNumberLoading}
      />
    ),
    createTabItem(
      'case-staff',
      { icon: <TeamOutlined />, text: '承案人資' },
      <DocumentCreateStaffTab
        form={form}
        cases={cases}
        casesLoading={casesLoading}
        staffLoading={staffLoading}
        usersLoading={usersLoading}
        buildAssigneeOptions={buildAssigneeOptions}
        handleProjectChange={handleProjectChange}
      />
    ),
    createTabItem(
      'attachments',
      { icon: <PaperClipOutlined />, text: '附件紀錄', count: fileList.length },
      <DocumentCreateAttachmentTab
        fileList={fileList}
        setFileList={setFileList}
        uploading={uploading}
        uploadProgress={uploadProgress}
        uploadErrors={uploadErrors}
        clearUploadErrors={clearUploadErrors}
        fileSettings={fileSettings}
        validateFile={validateFile}
      />
    ),
  ];

  // =============================================================================
  // Header 配置
  // =============================================================================

  const headerConfig = {
    title: '新增發文',
    icon: <FileTextOutlined />,
    backText: '返回發文字號管理',
    backPath: '/document-numbers',
    tags: [
      { text: '發文', color: 'blue' },
      { text: '新增中', color: 'processing' },
    ],
    extra: (
      <Space>
        <Button icon={<CloseOutlined />} onClick={handleCancel}>
          取消
        </Button>
        <Button
          type="primary"
          icon={<SaveOutlined />}
          loading={saving}
          onClick={handleSave}
        >
          儲存
        </Button>
      </Space>
    ),
  };

  // =============================================================================
  // 渲染
  // =============================================================================

  return (
    <DetailPageLayout
      header={headerConfig}
      tabs={tabs}
      activeTab={activeTab}
      onTabChange={setActiveTab}
      loading={loading}
      hasData={true}
    />
  );
};

export default SendDocumentCreatePage;
