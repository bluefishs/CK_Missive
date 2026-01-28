/**
 * 附件列表共用元件
 *
 * 顯示已上傳的附件列表，支援預覽、下載、刪除操作
 *
 * @version 1.0.0
 * @date 2026-01-27
 */

import React from 'react';
import { Card, List, Empty, Space } from 'antd';
import { PaperClipOutlined } from '@ant-design/icons';

import { AttachmentListItem, AttachmentItem } from './AttachmentListItem';

// ============================================================================
// 型別定義
// ============================================================================

export interface AttachmentListProps {
  /** 附件陣列 */
  attachments: AttachmentItem[];
  /** 是否載入中 */
  loading?: boolean;
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
  /** 自訂標題 */
  title?: React.ReactNode;
  /** 空資料時的提示文字 */
  emptyText?: string;
  /** 是否顯示卡片外框 */
  showCard?: boolean;
  /** 刪除確認訊息 */
  deleteConfirmTitle?: string;
  /** 刪除確認描述 */
  deleteConfirmDescription?: string;
}

// ============================================================================
// 主元件
// ============================================================================

export const AttachmentList: React.FC<AttachmentListProps> = ({
  attachments,
  loading = false,
  editable = false,
  showPreview = true,
  showDownload = true,
  deleteLoading = false,
  onPreview,
  onDownload,
  onDelete,
  title,
  emptyText = '尚無附件',
  showCard = true,
  deleteConfirmTitle,
  deleteConfirmDescription,
}) => {
  // 預設標題
  const defaultTitle = (
    <Space>
      <PaperClipOutlined />
      <span>已上傳附件（{attachments.length} 個）</span>
    </Space>
  );

  // 列表內容
  const listContent = attachments.length > 0 ? (
    <List
      size="small"
      loading={loading}
      dataSource={attachments}
      renderItem={(item) => (
        <AttachmentListItem
          attachment={item}
          editable={editable}
          showPreview={showPreview}
          showDownload={showDownload}
          deleteLoading={deleteLoading}
          onPreview={onPreview}
          onDownload={onDownload}
          onDelete={onDelete}
          deleteConfirmTitle={deleteConfirmTitle}
          deleteConfirmDescription={deleteConfirmDescription}
        />
      )}
    />
  ) : (
    <Empty description={emptyText} image={Empty.PRESENTED_IMAGE_SIMPLE} />
  );

  // 是否包裝 Card
  if (showCard) {
    return (
      <Card size="small" title={title || defaultTitle} loading={loading}>
        {listContent}
      </Card>
    );
  }

  return listContent;
};

export default AttachmentList;
