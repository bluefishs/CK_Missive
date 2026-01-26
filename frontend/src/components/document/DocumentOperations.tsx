/**
 * DocumentOperations 元件
 *
 * 公文操作彈窗元件 - 支援查看、編輯、新增、複製公文
 * 重構版本：業務邏輯委派給 Hooks，元件只負責 UI 渲染
 *
 * @version 2.0.0
 * @date 2026-01-26
 */
import React from 'react';
import {
  Modal,
  Form,
  Button,
  App,
  Space,
  Tag,
  Tabs,
} from 'antd';
import {
  FileTextOutlined,
  CopyOutlined,
  CalendarOutlined,
} from '@ant-design/icons';
import { Document } from '../../types';
import { calendarIntegrationService } from '../../services/calendarIntegrationService';
import { logger } from '../../utils/logger';
// 子組件與 Hooks
import {
  CriticalChangeConfirmModal,
  DuplicateFileModal,
  useDocumentOperations,
  useDocumentForm,
  BasicInfoTab,
  DateStatusTab,
  ProjectStaffTab,
  AttachmentTab,
  SystemInfoTab,
  type OperationMode,
} from './operations';

// ============================================================================
// 型別定義
// ============================================================================

interface DocumentOperationsProps {
  document: Document | null;
  operation: OperationMode | null;
  visible: boolean;
  onClose: () => void;
  onSave: (document: Partial<Document>) => Promise<Document | void>;
}

// ============================================================================
// 主元件
// ============================================================================

export const DocumentOperations: React.FC<DocumentOperationsProps> = ({
  document,
  operation,
  visible,
  onClose,
  onSave,
}) => {
  const { message } = App.useApp();
  const [form] = Form.useForm();

  // 使用 Hook 管理狀態與操作
  const ops = useDocumentOperations({
    document,
    operation,
    visible,
    message,
  });

  // 使用 Hook 管理表單邏輯
  const formOps = useDocumentForm({
    form,
    document,
    operation,
    visible,
    message,
    fetchAttachments: ops.fetchAttachments,
    fetchProjectStaff: ops.fetchProjectStaff,
    setSelectedProjectId: ops.setSelectedProjectId,
    setCriticalChangeModal: ops.setCriticalChangeModal,
    setExistingAttachments: () => {},
    setFileList: () => {},
  });

  // ============================================================================
  // 輔助函數
  // ============================================================================

  const getOperationText = () => {
    switch (operation) {
      case 'create': return '新增儲存';
      case 'edit': return '儲存變更';
      case 'copy': return '複製儲存';
      default: return '儲存';
    }
  };

  const getModalTitle = () => {
    const icons = {
      view: <FileTextOutlined />,
      edit: <FileTextOutlined />,
      create: <FileTextOutlined />,
      copy: <CopyOutlined />,
    };
    const titles = {
      view: '查看公文詳情',
      edit: '編輯公文',
      create: '新增公文',
      copy: '複製公文',
    };
    return (
      <Space>
        {operation && icons[operation]}
        {operation && titles[operation]}
      </Space>
    );
  };

  // ============================================================================
  // 事件處理
  // ============================================================================

  const performSave = async (documentData: Partial<Document>) => {
    try {
      ops.setLoading(true);
      const savedDocument = await onSave(documentData);
      const targetDocumentId = (savedDocument as Document)?.id || document?.id;

      if (targetDocumentId && ops.fileList.length > 0) {
        try {
          const uploadResult = await ops.uploadFiles(targetDocumentId, ops.fileList);
          const successCount = uploadResult.files?.length || 0;
          const errorCount = uploadResult.errors?.length || 0;

          if (successCount > 0 && errorCount === 0) {
            message.success(`附件上傳成功（共 ${successCount} 個檔案）`);
          } else if (successCount > 0 && errorCount > 0) {
            message.warning(`部分附件上傳成功（成功 ${successCount} 個，失敗 ${errorCount} 個）`);
          } else if (successCount === 0 && errorCount > 0) {
            message.error(`附件上傳失敗（共 ${errorCount} 個錯誤）`);
          }
          ops.setFileList([]);
        } catch (uploadError) {
          logger.error('File upload failed:', uploadError);
          const errorMsg = uploadError instanceof Error ? uploadError.message : '上傳失敗';
          message.error(`附件上傳失敗: ${errorMsg}`);
        }
      } else if (ops.fileList.length > 0 && !targetDocumentId) {
        message.warning('無法取得公文 ID，附件稍後上傳');
      }

      message.success(`${getOperationText()}成功！`);
      onClose();
    } catch (error) {
      logger.error('Save document failed:', error);
      message.error(`${getOperationText()}失敗`);
    } finally {
      ops.setLoading(false);
    }
  };

  const handleCriticalChangeConfirm = async () => {
    if (ops.criticalChangeModal.pendingData) {
      ops.setCriticalChangeModal({ visible: false, changes: [], pendingData: null });
      await performSave(ops.criticalChangeModal.pendingData);
    }
  };

  const handleSubmit = async () => {
    await formOps.handleSubmit(onSave, performSave);
  };

  const handleAddToCalendar = async () => {
    if (!document) return;
    try {
      ops.setCalendarLoading(true);
      await calendarIntegrationService.addDocumentToCalendar(document);
    } catch (error) {
      logger.error('Add to calendar failed:', error);
    } finally {
      ops.setCalendarLoading(false);
    }
  };

  // ============================================================================
  // 建立 Tab 項目
  // ============================================================================

  const tabItems = [
    {
      key: '1',
      label: '基本資料',
      children: <BasicInfoTab document={document} />,
    },
    {
      key: '2',
      label: '日期與狀態',
      children: <DateStatusTab />,
    },
    {
      key: '3',
      label: '案件與人員',
      children: (
        <ProjectStaffTab
          cases={ops.cases}
          users={ops.users}
          casesLoading={ops.casesLoading}
          usersLoading={ops.usersLoading}
          selectedProjectId={ops.selectedProjectId}
          projectStaffMap={ops.projectStaffMap}
          staffLoading={ops.staffLoading}
          onProjectChange={formOps.handleProjectChange}
        />
      ),
    },
    {
      key: '4',
      label: (
        <span>
          附件上傳
          {ops.existingAttachments.length > 0 && (
            <Tag color="blue" style={{ marginLeft: 8 }}>
              {ops.existingAttachments.length}
            </Tag>
          )}
        </span>
      ),
      children: (
        <AttachmentTab
          existingAttachments={ops.existingAttachments}
          attachmentsLoading={ops.attachmentsLoading}
          fileList={ops.fileList}
          uploading={ops.uploading}
          uploadProgress={ops.uploadProgress}
          uploadErrors={ops.uploadErrors}
          fileSettings={ops.fileSettings}
          isReadOnly={ops.isReadOnly}
          onDownload={ops.handleDownload}
          onPreview={ops.handlePreviewAttachment}
          onDelete={ops.handleDeleteAttachment}
          onFileListChange={ops.handleFileListChange}
          onRemove={ops.handleRemoveFile}
          onClearErrors={ops.handleClearUploadErrors}
          validateFile={ops.validateFile}
          onCheckDuplicate={ops.handleCheckDuplicate}
        />
      ),
    },
    ...(ops.isReadOnly && document
      ? [
          {
            key: '5',
            label: '系統資訊',
            children: <SystemInfoTab document={document} />,
          },
        ]
      : []),
  ];

  // ============================================================================
  // 渲染
  // ============================================================================

  return (
    <Modal
      title={getModalTitle()}
      open={visible}
      onCancel={onClose}
      width={800}
      footer={
        ops.isReadOnly ? (
          <Space>
            {document && (
              <Button
                icon={<CalendarOutlined />}
                loading={ops.calendarLoading}
                onClick={handleAddToCalendar}
              >
                加入行事曆
              </Button>
            )}
            <Button onClick={onClose}>關閉</Button>
          </Space>
        ) : (
          <Space>
            <Button onClick={onClose}>取消</Button>
            <Button type="primary" loading={ops.loading} onClick={handleSubmit}>
              {getOperationText()}
            </Button>
          </Space>
        )
      }
    >
      <Form form={form} layout="vertical" disabled={ops.isReadOnly}>
        <Tabs defaultActiveKey="1" items={tabItems} />
      </Form>

      <CriticalChangeConfirmModal
        visible={ops.criticalChangeModal.visible}
        changes={ops.criticalChangeModal.changes}
        loading={ops.loading}
        onConfirm={handleCriticalChangeConfirm}
        onCancel={() =>
          ops.setCriticalChangeModal({ visible: false, changes: [], pendingData: null })
        }
      />

      <DuplicateFileModal
        visible={ops.duplicateModal.visible}
        file={ops.duplicateModal.file}
        existingAttachment={ops.duplicateModal.existingAttachment}
        onOverwrite={ops.handleOverwriteFile}
        onKeepBoth={ops.handleKeepBoth}
        onCancel={ops.handleCancelDuplicate}
      />
    </Modal>
  );
};

// 重新匯出 DocumentSendModal（保持向後相容）
export { DocumentSendModal } from './operations';
