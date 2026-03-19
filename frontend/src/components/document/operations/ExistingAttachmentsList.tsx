/**
 * 既有附件列表組件
 *
 * 顯示公文現有的附件列表，提供預覽、下載、刪除功能。
 *
 * @version 1.0.0
 * @date 2026-01-19
 */

import React from 'react';
import { Card, Button, Popconfirm, Space, Flex, Typography } from 'antd';
import {
  PaperClipOutlined,
  DownloadOutlined,
  DeleteOutlined,
  EyeOutlined,
  FileOutlined,
  FilePdfOutlined,
  FileImageOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import type { ExistingAttachmentsListProps } from './types';
import type { DocumentAttachment } from '../../../types';

/**
 * 根據檔案類型返回對應圖示
 */
const getFileIcon = (contentType: string | undefined, filename: string) => {
  const ext = filename.split('.').pop()?.toLowerCase();

  if (contentType?.startsWith('image/') || ['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(ext || '')) {
    return <FileImageOutlined style={{ fontSize: 24, color: '#52c41a' }} />;
  }
  if (contentType === 'application/pdf' || ext === 'pdf') {
    return <FilePdfOutlined style={{ fontSize: 24, color: '#ff4d4f' }} />;
  }
  return <FileOutlined style={{ fontSize: 24, color: '#1890ff' }} />;
};

/**
 * 判斷檔案是否可預覽
 */
const isPreviewable = (contentType: string | undefined, filename: string): boolean => {
  const ext = filename.split('.').pop()?.toLowerCase();
  const previewableTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/gif', 'text/plain'];
  const previewableExts = ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'txt'];

  return previewableTypes.includes(contentType || '') || previewableExts.includes(ext || '');
};

export const ExistingAttachmentsList: React.FC<ExistingAttachmentsListProps> = ({
  attachments,
  loading,
  readOnly,
  onDownload,
  onPreview,
  onDelete,
}) => {
  if (attachments.length === 0) {
    return null;
  }

  return (
    <Card
      size="small"
      title={
        <Space>
          <PaperClipOutlined />
          <span>已上傳附件（{attachments.length} 個）</span>
        </Space>
      }
      style={{ marginBottom: 16 }}
      loading={loading}
    >
      <Flex vertical>
        {attachments.map((item: DocumentAttachment) => (
          <Flex
            key={item.id}
            align="center"
            justify="space-between"
            style={{ padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}
          >
            <Flex align="center" gap={12} style={{ flex: 1, minWidth: 0 }}>
              {getFileIcon(item.content_type, item.original_filename || item.filename)}
              <div style={{ minWidth: 0 }}>
                <Typography.Text strong ellipsis={{ tooltip: item.original_filename || item.filename }}>
                  {item.original_filename || item.filename}
                </Typography.Text>
                <div>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    {item.file_size ? `${(item.file_size / 1024).toFixed(1)} KB` : ''}
                    {item.created_at && ` · ${dayjs(item.created_at).format('YYYY-MM-DD HH:mm')}`}
                  </Typography.Text>
                </div>
              </div>
            </Flex>
            <Space size={0}>
              {isPreviewable(item.content_type, item.original_filename || item.filename) && (
                <Button
                  type="link"
                  size="small"
                  icon={<EyeOutlined />}
                  onClick={() => onPreview(item.id, item.original_filename || item.filename)}
                  style={{ color: '#52c41a' }}
                >
                  預覽
                </Button>
              )}
              <Button
                type="link"
                size="small"
                icon={<DownloadOutlined />}
                onClick={() => onDownload(item.id, item.original_filename || item.filename)}
              >
                下載
              </Button>
              {!readOnly && (
                <Popconfirm
                  title="確定要刪除此附件嗎？"
                  onConfirm={() => onDelete(item.id)}
                  okText="確定"
                  cancelText="取消"
                >
                  <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                    刪除
                  </Button>
                </Popconfirm>
              )}
            </Space>
          </Flex>
        ))}
      </Flex>
    </Card>
  );
};

export default ExistingAttachmentsList;
