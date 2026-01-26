/**
 * 附件紀錄 Tab
 *
 * @version 1.0.0
 * @date 2026-01-23
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
import {
  PaperClipOutlined,
  DownloadOutlined,
  DeleteOutlined,
  EyeOutlined,
  FilePdfOutlined,
  FileImageOutlined,
  InboxOutlined,
  CloudUploadOutlined,
  FileOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import type { DocumentAttachmentsTabProps } from './types';
import type { UploadFile, UploadChangeParam } from 'antd/es/upload';
import type { DocumentAttachment } from '../../../types/api';

const { Dragger } = Upload;

export const DocumentAttachmentsTab: React.FC<DocumentAttachmentsTabProps> = ({
  isEditing,
  attachments,
  attachmentsLoading,
  fileList,
  setFileList,
  uploading,
  uploadProgress,
  uploadErrors,
  setUploadErrors,
  fileSettings,
  onDownload,
  onPreview,
  onDelete,
}) => {
  const { message } = App.useApp();

  /** 判斷是否可預覽 */
  const isPreviewable = (contentType?: string, filename?: string): boolean => {
    if (contentType) {
      if (contentType.startsWith('image/') ||
          contentType === 'application/pdf' ||
          contentType.startsWith('text/')) {
        return true;
      }
    }
    if (filename) {
      const ext = filename.toLowerCase().split('.').pop();
      return ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'txt', 'csv'].includes(ext || '');
    }
    return false;
  };

  /** 取得檔案圖示 */
  const getFileIcon = (contentType?: string, filename?: string) => {
    const ext = filename?.toLowerCase().split('.').pop();
    if (contentType?.startsWith('image/') || ['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(ext || '')) {
      return <FileImageOutlined style={{ fontSize: 20, color: '#52c41a' }} />;
    }
    if (contentType === 'application/pdf' || ext === 'pdf') {
      return <FilePdfOutlined style={{ fontSize: 20, color: '#ff4d4f' }} />;
    }
    return <PaperClipOutlined style={{ fontSize: 20, color: '#1890ff' }} />;
  };

  /** 檔案驗證 */
  const validateFile = (file: File): { valid: boolean; error?: string } => {
    const { allowedExtensions, maxFileSizeMB } = fileSettings;
    const fileName = file.name.toLowerCase();
    const ext = '.' + (fileName.split('.').pop() || '');

    if (!allowedExtensions.includes(ext)) {
      return {
        valid: false,
        error: `不支援 ${ext} 檔案格式`,
      };
    }

    const maxSizeBytes = maxFileSizeMB * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      return {
        valid: false,
        error: `檔案大小 ${sizeMB}MB 超過限制 (最大 ${maxFileSizeMB}MB)`,
      };
    }

    return { valid: true };
  };

  /** Upload 元件屬性 */
  const uploadProps = {
    multiple: true,
    fileList,
    showUploadList: false,
    beforeUpload: (file: File) => {
      const validation = validateFile(file);
      if (!validation.valid) {
        message.error(validation.error);
        return Upload.LIST_IGNORE;
      }
      return false;
    },
    onChange: ({ fileList: newFileList }: UploadChangeParam<UploadFile>) => {
      setFileList(newFileList);
    },
    onRemove: (file: UploadFile) => {
      const newFileList = fileList.filter(item => item.uid !== file.uid);
      setFileList(newFileList);
    },
  };

  return (
    <Spin spinning={attachmentsLoading}>
      {/* 既有附件列表 */}
      {attachments.length > 0 && (
        <Card
          size="small"
          title={
            <Space>
              <PaperClipOutlined />
              <span>已上傳附件（{attachments.length} 個）</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <List
            size="small"
            dataSource={attachments}
            renderItem={(item: DocumentAttachment) => (
              <List.Item
                actions={[
                  isPreviewable(item.content_type, item.original_filename || item.filename) && (
                    <Button
                      key="preview"
                      type="link"
                      size="small"
                      icon={<EyeOutlined />}
                      onClick={() => onPreview(item.id, item.original_filename || item.filename)}
                      style={{ color: '#52c41a' }}
                    >
                      預覽
                    </Button>
                  ),
                  <Button
                    key="download"
                    type="link"
                    size="small"
                    icon={<DownloadOutlined />}
                    onClick={() => onDownload(item.id, item.original_filename || item.filename)}
                  >
                    下載
                  </Button>,
                  isEditing && (
                    <Popconfirm
                      key="delete"
                      title="確定要刪除此附件嗎？"
                      onConfirm={() => onDelete(item.id)}
                      okText="確定"
                      cancelText="取消"
                    >
                      <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                        刪除
                      </Button>
                    </Popconfirm>
                  ),
                ].filter(Boolean)}
              >
                <List.Item.Meta
                  avatar={getFileIcon(item.content_type, item.original_filename || item.filename)}
                  title={item.original_filename || item.filename}
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
      )}

      {/* 上傳區域（編輯模式才顯示）*/}
      {isEditing ? (
        <>
          <Dragger {...uploadProps} disabled={uploading}>
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">點擊或拖拽文件到此區域上傳</p>
            <p className="ant-upload-hint">
              支援 PDF、DOC、DOCX、XLS、XLSX、JPG、PNG 等格式，單檔最大 {fileSettings.maxFileSizeMB}MB
            </p>
          </Dragger>

          {/* 待上傳檔案預覽 */}
          {fileList.length > 0 && !uploading && (
            <Card
              size="small"
              style={{ marginTop: 16, background: '#f6ffed', border: '1px solid #b7eb8f' }}
              title={
                <span style={{ color: '#52c41a' }}>
                  <CloudUploadOutlined style={{ marginRight: 8 }} />
                  待上傳檔案（{fileList.length} 個）
                </span>
              }
            >
              <List
                size="small"
                dataSource={fileList}
                renderItem={(file: UploadFile) => (
                  <List.Item>
                    <List.Item.Meta
                      avatar={<FileOutlined style={{ color: '#1890ff' }} />}
                      title={file.name}
                      description={`${file.size ? (file.size / 1024).toFixed(1) : 0} KB`}
                    />
                  </List.Item>
                )}
              />
              <p style={{ color: '#999', fontSize: 12, marginTop: 8, marginBottom: 0 }}>
                點擊上方「儲存」按鈕後開始上傳
              </p>
            </Card>
          )}

          {/* 上傳進度條 */}
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
        </>
      ) : (
        attachments.length === 0 && (
          <Empty description="此公文尚無附件" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )
      )}
    </Spin>
  );
};

export default DocumentAttachmentsTab;
