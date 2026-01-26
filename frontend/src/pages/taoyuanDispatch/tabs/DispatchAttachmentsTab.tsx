/**
 * 派工單附件管理 Tab
 *
 * 從 TaoyuanDispatchDetailPage.tsx 的 renderAttachmentsTab 函數拆分而來
 * 支援附件上傳、預覽、下載、刪除功能
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

import React from 'react';
import {
  Card,
  Upload,
  Button,
  Space,
  List,
  Popconfirm,
  Spin,
  Empty,
  Progress,
  Alert,
  App,
} from 'antd';
import type { UploadProps, UploadFile, UploadChangeParam } from 'antd/es/upload';
import {
  PaperClipOutlined,
  DownloadOutlined,
  DeleteOutlined,
  EyeOutlined,
  FilePdfOutlined,
  FileImageOutlined,
  InboxOutlined,
  FileOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import type { DispatchAttachmentsTabProps } from './types';
import type { DispatchAttachment } from '../../../types/api';
import { dispatchAttachmentsApi } from '../../../api/taoyuanDispatchApi';

const { Dragger } = Upload;

// ============================================================================
// 檔案設定常數
// ============================================================================

/** 允許的副檔名 */
const ALLOWED_EXTENSIONS = [
  'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
  'jpg', 'jpeg', 'png', 'gif', 'bmp',
  'zip', 'rar', '7z',
  'txt', 'csv',
];

/** 最大檔案大小 (50MB) */
const MAX_FILE_SIZE = 50 * 1024 * 1024;

// ============================================================================
// 子元件：上傳區域
// ============================================================================

interface UploadSectionProps {
  uploadProps: UploadProps;
  uploading: boolean;
  fileList: UploadFile[];
  setFileList: React.Dispatch<React.SetStateAction<UploadFile[]>>;
  uploadProgress: number;
  uploadErrors: string[];
  setUploadErrors: React.Dispatch<React.SetStateAction<string[]>>;
  onStartUpload: () => void;
}

const UploadSection: React.FC<UploadSectionProps> = ({
  uploadProps,
  uploading,
  fileList,
  setFileList,
  uploadProgress,
  uploadErrors,
  setUploadErrors,
  onStartUpload,
}) => (
  <Card size="small" style={{ marginBottom: 16 }} title="上傳附件">
    <Dragger {...uploadProps} disabled={uploading}>
      <p className="ant-upload-drag-icon">
        <InboxOutlined />
      </p>
      <p className="ant-upload-text">點擊或拖拽檔案到此區域上傳</p>
      <p className="ant-upload-hint">
        支援 PDF、DOC、DOCX、XLS、XLSX、JPG、PNG 等格式，單檔最大 50MB
      </p>
    </Dragger>

    {/* 待上傳檔案預覽 */}
    {fileList.length > 0 && !uploading && (
      <Card
        size="small"
        style={{ marginTop: 16, background: '#f6ffed', border: '1px solid #b7eb8f' }}
        title={
          <span style={{ color: '#52c41a' }}>
            <PaperClipOutlined style={{ marginRight: 8 }} />
            待上傳檔案（{fileList.length} 個）
          </span>
        }
      >
        <List
          size="small"
          dataSource={fileList}
          renderItem={(file: UploadFile) => (
            <List.Item
              actions={[
                <Button
                  key="remove"
                  type="link"
                  size="small"
                  danger
                  onClick={() => setFileList((prev) => prev.filter((f) => f.uid !== file.uid))}
                >
                  移除
                </Button>,
              ]}
            >
              <List.Item.Meta
                avatar={<FileOutlined style={{ color: '#1890ff' }} />}
                title={file.name}
                description={file.size ? `${(file.size / 1024).toFixed(1)} KB` : ''}
              />
            </List.Item>
          )}
        />
        <Button
          type="primary"
          style={{ marginTop: 12 }}
          onClick={onStartUpload}
          loading={uploading}
        >
          開始上傳
        </Button>
      </Card>
    )}

    {/* 上傳進度 */}
    {uploading && (
      <Card
        size="small"
        style={{ marginTop: 16, background: '#e6f7ff', border: '1px solid #91d5ff' }}
        title={
          <span style={{ color: '#1890ff' }}>
            <LoadingOutlined style={{ marginRight: 8 }} />
            正在上傳檔案...
          </span>
        }
      >
        <Progress
          percent={uploadProgress}
          status="active"
          strokeColor={{ '0%': '#108ee9', '100%': '#87d068' }}
          strokeWidth={12}
        />
      </Card>
    )}

    {/* 上傳錯誤訊息 */}
    {uploadErrors.length > 0 && (
      <Alert
        type="warning"
        showIcon
        closable
        onClose={() => setUploadErrors([])}
        style={{ marginTop: 16 }}
        message="部分檔案上傳失敗"
        description={
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {uploadErrors.map((err, idx) => (
              <li key={idx}>{err}</li>
            ))}
          </ul>
        }
      />
    )}
  </Card>
);

// ============================================================================
// 子元件：附件列表
// ============================================================================

interface AttachmentListProps {
  attachments: DispatchAttachment[];
  isEditing: boolean;
  onPreview: (attachmentId: number, filename: string) => void;
  onDownload: (attachmentId: number, filename: string) => void;
  onDelete: (attachmentId: number) => void;
  deleteLoading: boolean;
}

const AttachmentList: React.FC<AttachmentListProps> = ({
  attachments,
  isEditing,
  onPreview,
  onDownload,
  onDelete,
  deleteLoading,
}) => {
  /** 取得檔案圖示 */
  const getFileIcon = (mimeType: string | undefined, filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (mimeType?.startsWith('image/') || ['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(ext || '')) {
      return <FileImageOutlined style={{ fontSize: 24, color: '#52c41a' }} />;
    }
    if (mimeType === 'application/pdf' || ext === 'pdf') {
      return <FilePdfOutlined style={{ fontSize: 24, color: '#ff4d4f' }} />;
    }
    return <FileOutlined style={{ fontSize: 24, color: '#1890ff' }} />;
  };

  /** 判斷檔案是否可預覽 */
  const isPreviewable = (mimeType?: string, filename?: string): boolean => {
    if (mimeType) {
      if (mimeType.startsWith('image/') ||
          mimeType === 'application/pdf' ||
          mimeType.startsWith('text/')) {
        return true;
      }
    }
    if (filename) {
      const ext = filename.toLowerCase().split('.').pop();
      return ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'txt', 'csv'].includes(ext || '');
    }
    return false;
  };

  return (
    <Card
      size="small"
      title={
        <Space>
          <PaperClipOutlined />
          <span>已上傳附件（{attachments.length} 個）</span>
        </Space>
      }
    >
      <List
        size="small"
        dataSource={attachments}
        renderItem={(item: DispatchAttachment) => (
          <List.Item
            actions={[
              // 預覽按鈕（僅支援 PDF/圖片/文字檔）
              isPreviewable(item.mime_type, item.original_name || item.file_name) && (
                <Button
                  key="preview"
                  type="link"
                  size="small"
                  icon={<EyeOutlined />}
                  style={{ color: '#52c41a' }}
                  onClick={() => onPreview(item.id, item.original_name || item.file_name)}
                >
                  預覽
                </Button>
              ),
              <Button
                key="download"
                type="link"
                size="small"
                icon={<DownloadOutlined />}
                onClick={() => onDownload(item.id, item.original_name || item.file_name)}
              >
                下載
              </Button>,
              isEditing && (
                <Popconfirm
                  key="delete"
                  title="確定要刪除此附件嗎？"
                  description="刪除後無法復原，請確認是否繼續？"
                  onConfirm={() => onDelete(item.id)}
                  okText="確定刪除"
                  okButtonProps={{ danger: true }}
                  cancelText="取消"
                >
                  <Button
                    type="link"
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                    loading={deleteLoading}
                  >
                    刪除
                  </Button>
                </Popconfirm>
              ),
            ].filter(Boolean)}
          >
            <List.Item.Meta
              avatar={getFileIcon(item.mime_type, item.original_name || item.file_name)}
              title={item.original_name || item.file_name}
              description={
                <span style={{ fontSize: 12, color: '#999' }}>
                  {item.file_size ? `${(item.file_size / 1024).toFixed(1)} KB` : ''}
                  {item.created_at && ` · ${dayjs(item.created_at).format('YYYY-MM-DD HH:mm')}`}
                </span>
              }
            />
          </List.Item>
        )}
      />
    </Card>
  );
};

// ============================================================================
// 主元件
// ============================================================================

export const DispatchAttachmentsTab: React.FC<DispatchAttachmentsTabProps> = ({
  dispatchId,
  isEditing,
  isLoading,
  attachments,
  fileList,
  setFileList,
  uploading,
  uploadProgress,
  uploadErrors,
  setUploadErrors,
  uploadAttachmentsMutation,
  deleteAttachmentMutation,
}) => {
  const { message } = App.useApp();

  /** 驗證檔案 */
  const validateFile = (file: File): { valid: boolean; message?: string } => {
    const ext = file.name.split('.').pop()?.toLowerCase();

    if (file.size > MAX_FILE_SIZE) {
      message.error(`檔案 ${file.name} 超過 50MB 限制`);
      return { valid: false, message: '檔案超過大小限制' };
    }
    if (!ext || !ALLOWED_EXTENSIONS.includes(ext)) {
      message.error(`檔案 ${file.name} 格式不支援`);
      return { valid: false, message: '不支援的檔案格式' };
    }
    return { valid: true };
  };

  /** 預覽附件 */
  const handlePreview = async (attachmentId: number, filename: string) => {
    try {
      const blob = await dispatchAttachmentsApi.getAttachmentBlob(attachmentId);
      const previewUrl = window.URL.createObjectURL(blob);
      window.open(previewUrl, '_blank');
      // 10 秒後釋放記憶體
      setTimeout(() => window.URL.revokeObjectURL(previewUrl), 10000);
    } catch (error) {
      console.error('預覽附件失敗:', error);
      message.error(`預覽 ${filename} 失敗`);
    }
  };

  /** 下載附件 */
  const handleDownload = (attachmentId: number, filename: string) => {
    dispatchAttachmentsApi.downloadAttachment(attachmentId, filename);
  };

  /** 刪除附件 */
  const handleDelete = (attachmentId: number) => {
    deleteAttachmentMutation.mutate(attachmentId);
  };

  /** Upload 元件屬性 */
  const uploadProps: UploadProps = {
    multiple: true,
    fileList,
    showUploadList: false,
    beforeUpload: (file: File) => {
      const validation = validateFile(file);
      if (!validation.valid) {
        return Upload.LIST_IGNORE;
      }
      return false;
    },
    onChange: ({ fileList: newFileList }: UploadChangeParam<UploadFile>) => {
      setFileList(newFileList);
    },
    onRemove: (file: UploadFile) => {
      setFileList((prev) => prev.filter((f) => f.uid !== file.uid));
    },
  };

  return (
    <Spin spinning={isLoading}>
      {/* 上傳區塊（僅編輯模式顯示）*/}
      {isEditing && (
        <UploadSection
          uploadProps={uploadProps}
          uploading={uploading}
          fileList={fileList}
          setFileList={setFileList}
          uploadProgress={uploadProgress}
          uploadErrors={uploadErrors}
          setUploadErrors={setUploadErrors}
          onStartUpload={() => uploadAttachmentsMutation.mutate()}
        />
      )}

      {/* 已上傳附件列表 */}
      {(attachments?.length ?? 0) > 0 ? (
        <AttachmentList
          attachments={attachments}
          isEditing={isEditing}
          onPreview={handlePreview}
          onDownload={handleDownload}
          onDelete={handleDelete}
          deleteLoading={deleteAttachmentMutation.isPending}
        />
      ) : (
        !isEditing && (
          <Empty description="此派工單尚無附件" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )
      )}
    </Spin>
  );
};

export default DispatchAttachmentsTab;
