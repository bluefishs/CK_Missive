/**
 * 證照附件預覽元件
 *
 * 支援圖片預覽、PDF 檔案顯示、刪除操作
 * 從 CertificationFormPage 提取
 *
 * @version 1.0.0
 */
import React from 'react';
import { Button, Space, Image, Upload } from 'antd';
import { DeleteOutlined, EyeOutlined, FileOutlined, UploadOutlined } from '@ant-design/icons';
import { getAttachmentUrl, isImageAttachment } from './useCertificationAttachment';

interface AttachmentPreviewProps {
  attachmentPreview: string | null;
  attachmentFile: File | null;
  isEdit: boolean;
  hasExistingAttachment: boolean;
  deleteAttachmentPending: boolean;
  onClearFile: () => void;
  onDeleteAttachment: () => void;
  onFileSelect: (file: File) => boolean;
}

const AttachmentPreview: React.FC<AttachmentPreviewProps> = ({
  attachmentPreview,
  attachmentFile,
  isEdit,
  hasExistingAttachment,
  deleteAttachmentPending,
  onClearFile,
  onDeleteAttachment,
  onFileSelect,
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* 現有附件預覽 */}
      {attachmentPreview && (
        <div
          style={{
            border: '1px solid #d9d9d9',
            borderRadius: 8,
            padding: 12,
            background: '#fafafa',
          }}
        >
          {attachmentPreview.startsWith('file:') ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <FileOutlined style={{ fontSize: 24, color: '#1890ff' }} />
              <span>{attachmentPreview.replace('file:', '')}</span>
              {attachmentFile && (
                <Button size="small" icon={<DeleteOutlined />} onClick={onClearFile} danger>
                  取消選擇
                </Button>
              )}
            </div>
          ) : isImageAttachment(attachmentPreview) ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <Image
                src={
                  attachmentPreview.startsWith('data:')
                    ? attachmentPreview
                    : getAttachmentUrl(attachmentPreview)
                }
                alt="證照掃描檔"
                style={{ maxWidth: 300, maxHeight: 200 }}
                preview={{ mask: <EyeOutlined /> }}
              />
              <Space>
                {attachmentFile ? (
                  <Button size="small" icon={<DeleteOutlined />} onClick={onClearFile} danger>
                    取消選擇
                  </Button>
                ) : (
                  isEdit &&
                  hasExistingAttachment && (
                    <Button
                      size="small"
                      icon={<DeleteOutlined />}
                      onClick={onDeleteAttachment}
                      loading={deleteAttachmentPending}
                      disabled={deleteAttachmentPending}
                      danger
                    >
                      刪除附件
                    </Button>
                  )
                )}
              </Space>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <FileOutlined style={{ fontSize: 24, color: '#1890ff' }} />
              <a
                href={getAttachmentUrl(attachmentPreview)}
                target="_blank"
                rel="noopener noreferrer"
              >
                查看附件
              </a>
              {isEdit && hasExistingAttachment && (
                <Button
                  size="small"
                  icon={<DeleteOutlined />}
                  onClick={onDeleteAttachment}
                  loading={deleteAttachmentPending}
                  disabled={deleteAttachmentPending}
                  danger
                >
                  刪除
                </Button>
              )}
            </div>
          )}
        </div>
      )}

      {/* 上傳按鈕 */}
      <Upload
        accept=".jpg,.jpeg,.png,.gif,.bmp,.pdf"
        beforeUpload={onFileSelect}
        showUploadList={false}
        maxCount={1}
      >
        <Button icon={<UploadOutlined />}>
          {attachmentPreview ? '更換附件' : '選擇檔案'}
        </Button>
      </Upload>
      <div style={{ color: '#999', fontSize: 12 }}>
        支援格式: JPG、PNG、GIF、BMP、PDF，檔案大小限制 10MB
      </div>
    </div>
  );
};

export default AttachmentPreview;
