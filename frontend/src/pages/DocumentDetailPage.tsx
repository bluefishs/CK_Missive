/**
 * 公文詳情頁面
 *
 * 使用通用 DetailPageLayout 元件，採用 Tab 架構：
 * - 公文資訊、日期狀態、承案人資、附件紀錄、派工安排、工程關聯
 *
 * @version 4.0.0 - 提取 useDocumentDetail hook，頁面僅負責 UI 渲染
 * @date 2026-02-19
 */

import React from 'react';
import { Button, Space, Popconfirm } from 'antd';
import {
  FileTextOutlined, CalendarOutlined, TeamOutlined, PaperClipOutlined,
  EditOutlined, SaveOutlined, CloseOutlined, DeleteOutlined,
  SendOutlined, EnvironmentOutlined,
} from '@ant-design/icons';

import { DetailPageLayout, createTabItem, getTagColor } from '../components/common/DetailPage';
import { IntegratedEventModal } from '../components/calendar/IntegratedEventModal';
import {
  DocumentInfoTab, DocumentDateStatusTab, DocumentCaseStaffTab,
  DocumentAttachmentsTab, DocumentDispatchTab, DocumentProjectLinkTab,
  DOC_TYPE_OPTIONS, STATUS_OPTIONS,
} from './document/tabs';
import { useDocumentDetail } from './document/hooks/useDocumentDetail';

export const DocumentDetailPage: React.FC = () => {
  const {
    document, loading, saving, activeTab, setActiveTab, isEditing, setIsEditing,
    attachments, attachmentsLoading, fileList, setFileList,
    uploading, uploadProgress, uploadErrors, setUploadErrors, fileSettings,
    cases, casesLoading, users, usersLoading,
    projectStaffMap, staffLoading, selectedContractProjectId, currentAssigneeValues,
    dispatchLinks, dispatchLinksLoading, projectLinks, projectLinksLoading,
    hasDispatchFeature, hasProjectLinkFeature,
    agencyContacts, projectVendors, availableDispatches, availableProjects,
    showIntegratedEventModal, setShowIntegratedEventModal,
    handleProjectChange, handleSave, handleCancelEdit, handleDelete,
    handleAddToCalendar, handleEventCreated,
    handleDownload, handlePreview, handleDeleteAttachment,
    handleCreateDispatch, handleLinkDispatch, handleUnlinkDispatch,
    handleLinkProject, handleUnlinkProject,
    form, returnTo,
  } = useDocumentDetail();

  // === Tab 配置 ===

  const commonTabs = [
    createTabItem(
      'info',
      { icon: <FileTextOutlined />, text: '公文資訊' },
      <DocumentInfoTab form={form} document={document} isEditing={isEditing} />
    ),
    createTabItem(
      'date-status',
      { icon: <CalendarOutlined />, text: '日期狀態' },
      <DocumentDateStatusTab form={form} document={document} isEditing={isEditing} />
    ),
    createTabItem(
      'case-staff',
      { icon: <TeamOutlined />, text: '承案人資' },
      <DocumentCaseStaffTab
        form={form} document={document} isEditing={isEditing}
        cases={cases} casesLoading={casesLoading}
        users={users} usersLoading={usersLoading}
        projectStaffMap={projectStaffMap} staffLoading={staffLoading}
        selectedContractProjectId={selectedContractProjectId}
        currentAssigneeValues={currentAssigneeValues}
        onProjectChange={handleProjectChange}
      />
    ),
    createTabItem(
      'attachments',
      { icon: <PaperClipOutlined />, text: '附件紀錄', count: attachments.length },
      <DocumentAttachmentsTab
        documentId={document?.id ?? null} isEditing={isEditing}
        attachments={attachments} attachmentsLoading={attachmentsLoading}
        fileList={fileList} setFileList={setFileList}
        uploading={uploading} uploadProgress={uploadProgress}
        uploadErrors={uploadErrors} setUploadErrors={setUploadErrors}
        fileSettings={fileSettings}
        onDownload={handleDownload} onPreview={handlePreview} onDelete={handleDeleteAttachment}
      />
    ),
  ];

  const projectSpecificTabs = [
    ...(hasDispatchFeature ? [
      createTabItem(
        'dispatch',
        { icon: <SendOutlined />, text: '派工安排', count: dispatchLinks.length },
        <DocumentDispatchTab
          documentId={document?.id ?? null} document={document} isEditing={isEditing}
          dispatchLinks={dispatchLinks} dispatchLinksLoading={dispatchLinksLoading}
          agencyContacts={agencyContacts} projectVendors={projectVendors}
          availableDispatches={availableDispatches} availableProjects={availableProjects}
          onCreateDispatch={handleCreateDispatch}
          onLinkDispatch={handleLinkDispatch} onUnlinkDispatch={handleUnlinkDispatch}
        />
      ),
    ] : []),
    ...(hasProjectLinkFeature ? [
      createTabItem(
        'project-link',
        { icon: <EnvironmentOutlined />, text: '工程關聯', count: projectLinks.length },
        <DocumentProjectLinkTab
          documentId={document?.id ?? null} document={document} isEditing={isEditing}
          projectLinks={projectLinks} projectLinksLoading={projectLinksLoading}
          availableProjects={availableProjects}
          onLinkProject={handleLinkProject} onUnlinkProject={handleUnlinkProject}
        />
      ),
    ] : []),
  ];

  const tabs = [...commonTabs, ...projectSpecificTabs];

  // === Header 配置 ===

  const headerConfig = {
    title: document?.subject || '公文詳情',
    icon: <FileTextOutlined />,
    backText: returnTo?.includes('taoyuan/dispatch/')
      ? '返回派工單'
      : returnTo?.includes('taoyuan/dispatch')
        ? '返回函文紀錄'
        : '返回公文列表',
    backPath: returnTo || '/documents',
    tags: document ? [
      { text: document.doc_type || '函', color: getTagColor(document.doc_type, DOC_TYPE_OPTIONS, 'blue') },
      { text: document.status || '未設定', color: getTagColor(document.status, STATUS_OPTIONS, 'default') },
    ] : [],
    extra: (
      <Space>
        {isEditing ? (
          <>
            <Button icon={<CloseOutlined />} onClick={handleCancelEdit}>取消</Button>
            <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>
              儲存
            </Button>
          </>
        ) : (
          <>
            <Button icon={<CalendarOutlined />} onClick={handleAddToCalendar}>
              加入行事曆
            </Button>
            <Button type="primary" icon={<EditOutlined />} onClick={() => setIsEditing(true)}>
              編輯
            </Button>
            <Popconfirm
              title="確定要刪除此公文嗎？"
              description="刪除後將無法復原，請確認是否繼續。"
              onConfirm={handleDelete}
              okText="確定刪除" cancelText="取消"
              okButtonProps={{ danger: true }}
            >
              <Button danger icon={<DeleteOutlined />}>刪除</Button>
            </Popconfirm>
          </>
        )}
      </Space>
    ),
  };

  // === 渲染 ===

  return (
    <>
      <DetailPageLayout
        header={headerConfig}
        tabs={tabs}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        loading={loading}
        hasData={!!document}
      />

      <IntegratedEventModal
        visible={showIntegratedEventModal}
        document={document ? {
          id: document.id,
          doc_number: document.doc_number,
          subject: document.subject,
          doc_date: document.doc_date,
          send_date: document.send_date,
          receive_date: document.receive_date,
          sender: document.sender,
          receiver: document.receiver,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          assignee: (document as any).assignee,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          priority_level: String((document as any).priority || 3),
          doc_type: document.doc_type,
          content: document.content,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          notes: (document as any).notes,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          contract_case: (document as any).contract_project_name || undefined
        } : null}
        onClose={() => setShowIntegratedEventModal(false)}
        onSuccess={handleEventCreated}
      />
    </>
  );
};

export default DocumentDetailPage;
