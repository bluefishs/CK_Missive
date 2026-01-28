/**
 * 附件上傳共用元件
 *
 * 包含拖拽上傳、待上傳列表、上傳進度、錯誤訊息
 *
 * @version 1.0.0
 * @date 2026-01-27
 */

import React from 'react';
import {
  Card,
  Upload,
  Button,
  List,
  Progress,
  Alert,
  App,
} from 'antd';
import type { UploadProps, UploadFile, UploadChangeParam } from 'antd/es/upload';
import {
  InboxOutlined,
  CloudUploadOutlined,
  FileOutlined,
  LoadingOutlined,
} from '@ant-design/icons';

import {
  validateFile,
  DEFAULT_ALLOWED_EXTENSIONS,
  DEFAULT_MAX_FILE_SIZE_MB,
  formatFileSize,
} from './attachmentUtils';

const { Dragger } = Upload;

// ============================================================================
// 型別定義
// ============================================================================

export interface AttachmentUploaderProps {
  /** 檔案列表 */
  fileList: UploadFile[];
  /** 設定檔案列表 */
  setFileList: React.Dispatch<React.SetStateAction<UploadFile[]>>;
  /** 是否正在上傳 */
  uploading?: boolean;
  /** 上傳進度 (0-100) */
  uploadProgress?: number;
  /** 上傳錯誤訊息 */
  uploadErrors?: string[];
  /** 清除錯誤訊息 */
  setUploadErrors?: React.Dispatch<React.SetStateAction<string[]>>;
  /** 允許的副檔名 */
  allowedExtensions?: string[];
  /** 最大檔案大小 (MB) */
  maxFileSizeMB?: number;
  /** 是否顯示開始上傳按鈕 */
  showUploadButton?: boolean;
  /** 開始上傳回調 */
  onStartUpload?: () => void;
  /** 是否停用 */
  disabled?: boolean;
  /** 自訂上傳提示文字 */
  uploadHint?: string;
  /** 自訂標題 */
  title?: string;
}

// ============================================================================
// 主元件
// ============================================================================

export const AttachmentUploader: React.FC<AttachmentUploaderProps> = ({
  fileList,
  setFileList,
  uploading = false,
  uploadProgress = 0,
  uploadErrors = [],
  setUploadErrors,
  allowedExtensions = DEFAULT_ALLOWED_EXTENSIONS,
  maxFileSizeMB = DEFAULT_MAX_FILE_SIZE_MB,
  showUploadButton = true,
  onStartUpload,
  disabled = false,
  uploadHint,
  title,
}) => {
  const { message } = App.useApp();

  // 建立 Upload 元件屬性
  const uploadProps: UploadProps = {
    multiple: true,
    fileList,
    showUploadList: false,
    beforeUpload: (file: File) => {
      const validation = validateFile(file, {
        allowedExtensions,
        maxFileSizeMB,
      });

      if (!validation.valid) {
        message.error(validation.error);
        return Upload.LIST_IGNORE;
      }

      return false; // 阻止自動上傳
    },
    onChange: ({ fileList: newFileList }: UploadChangeParam<UploadFile>) => {
      setFileList(newFileList);
    },
    onRemove: (file: UploadFile) => {
      setFileList((prev) => prev.filter((f) => f.uid !== file.uid));
    },
  };

  // 格式化允許的副檔名顯示
  const formatExtensions = (): string => {
    const exts = allowedExtensions
      .map((e) => e.replace('.', '').toUpperCase())
      .slice(0, 8);
    const suffix = allowedExtensions.length > 8 ? ' 等' : '';
    return exts.join('、') + suffix;
  };

  const defaultHint = `支援 ${formatExtensions()} 格式，單檔最大 ${maxFileSizeMB}MB`;

  return (
    <>
      {/* 拖拽上傳區域 */}
      <Dragger {...uploadProps} disabled={uploading || disabled}>
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">點擊或拖拽檔案到此區域上傳</p>
        <p className="ant-upload-hint">{uploadHint || defaultHint}</p>
      </Dragger>

      {/* 待上傳檔案列表 */}
      {fileList.length > 0 && !uploading && (
        <Card
          size="small"
          style={{
            marginTop: 16,
            background: '#f6ffed',
            border: '1px solid #b7eb8f',
          }}
          title={
            <span style={{ color: '#52c41a' }}>
              <CloudUploadOutlined style={{ marginRight: 8 }} />
              {title || `待上傳檔案（${fileList.length} 個）`}
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
                    onClick={() =>
                      setFileList((prev) => prev.filter((f) => f.uid !== file.uid))
                    }
                  >
                    移除
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  avatar={<FileOutlined style={{ color: '#1890ff' }} />}
                  title={file.name}
                  description={formatFileSize(file.size)}
                />
              </List.Item>
            )}
          />

          {showUploadButton && onStartUpload && (
            <Button
              type="primary"
              style={{ marginTop: 12 }}
              onClick={onStartUpload}
              loading={uploading}
            >
              開始上傳
            </Button>
          )}

          {!showUploadButton && (
            <p
              style={{
                color: '#999',
                fontSize: 12,
                marginTop: 8,
                marginBottom: 0,
              }}
            >
              點擊上方「儲存」按鈕後開始上傳
            </p>
          )}
        </Card>
      )}

      {/* 上傳進度條 */}
      {uploading && (
        <Card
          size="small"
          style={{
            marginTop: 16,
            background: '#e6f7ff',
            border: '1px solid #91d5ff',
          }}
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
            size={['100%', 12]}
          />
        </Card>
      )}

      {/* 上傳錯誤訊息 */}
      {uploadErrors.length > 0 && (
        <Alert
          type="warning"
          showIcon
          closable
          onClose={() => setUploadErrors?.([])}
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
  );
};

export default AttachmentUploader;
