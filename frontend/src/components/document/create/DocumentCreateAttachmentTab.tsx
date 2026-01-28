/**
 * 公文建立 - 附件紀錄 Tab
 *
 * 共用於收文和發文建立頁面
 *
 * @version 1.0.0
 * @date 2026-01-28
 */

import React from 'react';
import {
  Card,
  Upload,
  Spin,
  List,
  Alert,
  Progress,
  Button,
  App,
} from 'antd';
import {
  InboxOutlined,
  CloudUploadOutlined,
  FileOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd/es/upload/interface';
import type { FileSettings } from '../../../hooks/business/useDocumentCreateForm';

const { Dragger } = Upload;

export interface DocumentCreateAttachmentTabProps {
  fileList: UploadFile[];
  setFileList: React.Dispatch<React.SetStateAction<UploadFile[]>>;
  uploading: boolean;
  uploadProgress: number;
  uploadErrors: string[];
  clearUploadErrors: () => void;
  fileSettings: FileSettings;
  validateFile: (file: File) => { valid: boolean; error?: string };
}

export const DocumentCreateAttachmentTab: React.FC<DocumentCreateAttachmentTabProps> = ({
  fileList,
  setFileList,
  uploading,
  uploadProgress,
  uploadErrors,
  clearUploadErrors,
  fileSettings,
  validateFile,
}) => {
  const { message } = App.useApp();

  const uploadProps: UploadProps = {
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
    onChange: ({ fileList: newFileList }) => {
      setFileList(newFileList);
    },
    onRemove: (file) => {
      const newFileList = fileList.filter(item => item.uid !== file.uid);
      setFileList(newFileList);
    },
  };

  const handleRemoveFile = (uid: string) => {
    const newList = fileList.filter(f => f.uid !== uid);
    setFileList(newList);
  };

  return (
    <Spin spinning={uploading}>
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
              <List.Item
                actions={[
                  <Button
                    key="remove"
                    type="link"
                    size="small"
                    danger
                    onClick={() => handleRemoveFile(file.uid)}
                  >
                    移除
                  </Button>
                ]}
              >
                <List.Item.Meta
                  avatar={<FileOutlined style={{ color: '#1890ff' }} />}
                  title={file.name}
                  description={`${((file.size || 0) / 1024).toFixed(1)} KB`}
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
          onClose={clearUploadErrors}
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
    </Spin>
  );
};

export default DocumentCreateAttachmentTab;
