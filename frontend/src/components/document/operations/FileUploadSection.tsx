/**
 * 檔案上傳區塊組件
 *
 * 提供拖拽上傳、待上傳檔案預覽、上傳進度顯示和錯誤訊息。
 *
 * @version 1.0.0
 * @date 2026-01-19
 */

import React from 'react';
import { Form, Upload, Card, List, Progress, Alert, Empty } from 'antd';
import type { UploadFile, UploadChangeParam, UploadProps } from 'antd/es/upload';
import {
  InboxOutlined,
  FileOutlined,
  LoadingOutlined,
  CloudUploadOutlined,
} from '@ant-design/icons';
import type { FileUploadSectionProps, FileValidationResult } from './types';

const { Dragger } = Upload;

export const FileUploadSection: React.FC<FileUploadSectionProps> = ({
  fileList,
  uploading,
  uploadProgress,
  uploadErrors,
  maxFileSizeMB,
  allowedExtensions: _allowedExtensions,
  readOnly,
  onFileListChange,
  onRemove,
  validateFile,
}) => {
  // 如果是唯讀模式且沒有檔案列表，顯示空狀態
  if (readOnly) {
    return (
      <Empty description="此公文尚無附件" image={Empty.PRESENTED_IMAGE_SIMPLE} />
    );
  }

  const uploadProps: UploadProps = {
    multiple: true,
    fileList,
    showUploadList: false, // 隱藏預設列表，使用自定義卡片顯示
    beforeUpload: (file: File) => {
      // 前端驗證
      const validation: FileValidationResult = validateFile(file);
      if (!validation.valid) {
        return Upload.LIST_IGNORE; // 不加入列表
      }
      return false; // 阻止自動上傳，我們將手動處理
    },
    onChange: ({ fileList: newFileList }: UploadChangeParam<UploadFile>) => {
      onFileListChange(newFileList);
    },
    onRemove: (file: UploadFile) => {
      onRemove(file);
    },
  };

  return (
    <Form.Item label="上傳新附件">
      <Dragger {...uploadProps} disabled={uploading}>
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">點擊或拖拽文件到此區域上傳</p>
        <p className="ant-upload-hint">
          支援 PDF、DOC、DOCX、XLS、XLSX、JPG、PNG 等格式，單檔最大 {maxFileSizeMB}MB
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
                  description={file.size ? `${(file.size / 1024).toFixed(1)} KB` : ''}
                />
              </List.Item>
            )}
          />
          <p style={{ color: '#999', fontSize: 12, marginTop: 8, marginBottom: 0 }}>
            點擊下方「儲存變更」按鈕後開始上傳
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
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
            strokeWidth={12}
          />
          <p
            style={{
              textAlign: 'center',
              color: '#1890ff',
              marginTop: 12,
              marginBottom: 0,
              fontWeight: 500,
            }}
          >
            上傳進度：{uploadProgress}%
          </p>
        </Card>
      )}

      {/* 上傳錯誤訊息 */}
      {uploadErrors.length > 0 && (
        <Alert
          type="warning"
          showIcon
          closable
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
    </Form.Item>
  );
};

export default FileUploadSection;
