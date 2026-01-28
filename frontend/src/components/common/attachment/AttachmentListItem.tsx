/**
 * 附件列表項目共用元件
 *
 * 可用於公文、承攬案件、派工單等模組的附件列表
 *
 * @version 1.0.0
 * @date 2026-01-27
 */

import React from 'react';
import { List, Button, Popconfirm, Space, Typography } from 'antd';
import {
  DownloadOutlined,
  DeleteOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import { isPreviewable, formatFileSize, getFileIconConfig } from './attachmentUtils';

const { Text } = Typography;

// ============================================================================
// 型別定義
// ============================================================================

export interface AttachmentItem {
  id: number;
  filename: string;
  originalFilename?: string;
  contentType?: string;
  mimeType?: string;
  fileSize?: number;
  createdAt?: string;
  uploadedAt?: string;
}

export interface AttachmentListItemProps {
  /** 附件資料 */
  attachment: AttachmentItem;
  /** 是否可編輯（顯示刪除按鈕） */
  editable?: boolean;
  /** 是否顯示預覽按鈕 */
  showPreview?: boolean;
  /** 是否顯示下載按鈕 */
  showDownload?: boolean;
  /** 刪除確認中 */
  deleteLoading?: boolean;
  /** 預覽處理函數 */
  onPreview?: (id: number, filename: string) => void;
  /** 下載處理函數 */
  onDownload?: (id: number, filename: string) => void;
  /** 刪除處理函數 */
  onDelete?: (id: number) => void;
  /** 刪除確認訊息 */
  deleteConfirmTitle?: string;
  /** 刪除確認描述 */
  deleteConfirmDescription?: string;
}

// ============================================================================
// 主元件
// ============================================================================

export const AttachmentListItem: React.FC<AttachmentListItemProps> = ({
  attachment,
  editable = false,
  showPreview = true,
  showDownload = true,
  deleteLoading = false,
  onPreview,
  onDownload,
  onDelete,
  deleteConfirmTitle = '確定要刪除此附件嗎？',
  deleteConfirmDescription,
}) => {
  // 解析檔案名稱（支援多種命名慣例）
  const displayFilename = attachment.originalFilename || attachment.filename;
  const contentType = attachment.contentType || attachment.mimeType;
  const fileSize = attachment.fileSize;
  const uploadDate = attachment.createdAt || attachment.uploadedAt;

  // 取得檔案圖示
  const iconConfig = getFileIconConfig(contentType, displayFilename);
  const canPreview = isPreviewable(contentType, displayFilename);

  // 建立操作按鈕陣列
  const actions: React.ReactNode[] = [];

  // 預覽按鈕
  if (showPreview && canPreview && onPreview) {
    actions.push(
      <Button
        key="preview"
        type="link"
        size="small"
        icon={<EyeOutlined />}
        style={{ color: '#52c41a' }}
        onClick={() => onPreview(attachment.id, displayFilename)}
      >
        預覽
      </Button>
    );
  }

  // 下載按鈕
  if (showDownload && onDownload) {
    actions.push(
      <Button
        key="download"
        type="link"
        size="small"
        icon={<DownloadOutlined />}
        onClick={() => onDownload(attachment.id, displayFilename)}
      >
        下載
      </Button>
    );
  }

  // 刪除按鈕
  if (editable && onDelete) {
    actions.push(
      <Popconfirm
        key="delete"
        title={deleteConfirmTitle}
        description={deleteConfirmDescription}
        onConfirm={() => onDelete(attachment.id)}
        okText="確定"
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
    );
  }

  return (
    <List.Item actions={actions}>
      <List.Item.Meta
        avatar={
          <span style={{ fontSize: 20, color: iconConfig.color }}>
            {iconConfig.icon}
          </span>
        }
        title={
          <Text ellipsis={{ tooltip: displayFilename }}>
            {displayFilename}
          </Text>
        }
        description={
          <Space size="small" style={{ fontSize: 12, color: '#999' }}>
            {fileSize !== undefined && <span>{formatFileSize(fileSize)}</span>}
            {uploadDate && (
              <>
                <span>·</span>
                <span>{dayjs(uploadDate).format('YYYY-MM-DD HH:mm')}</span>
              </>
            )}
          </Space>
        }
      />
    </List.Item>
  );
};

export default AttachmentListItem;
