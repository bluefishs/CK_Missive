/**
 * 派工單附件管理 Tab
 *
 * 重構版本：使用共用附件元件
 *
 * @version 2.0.0 - 使用 SharedAttachment 元件
 * @date 2026-01-27
 */

import React from 'react';
import { Spin, Empty, App } from 'antd';
import type { UploadFile } from 'antd/es/upload';

import {
  AttachmentList,
  AttachmentUploader,
  type AttachmentItem,
} from '../../../components/common/attachment';
import type { DispatchAttachmentsTabProps } from './types';
import type { DispatchAttachment } from '../../../types/api';
import { dispatchAttachmentsApi } from '../../../api/taoyuanDispatchApi';
import { logger } from '../../../services/logger';

// ============================================================================
// 檔案設定常數
// ============================================================================

const ALLOWED_EXTENSIONS = [
  '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
  '.jpg', '.jpeg', '.png', '.gif', '.bmp',
  '.zip', '.rar', '.7z',
  '.txt', '.csv',
];

const MAX_FILE_SIZE_MB = 50;

// ============================================================================
// 主元件
// ============================================================================

export const DispatchAttachmentsTab: React.FC<DispatchAttachmentsTabProps> = ({
  dispatchId: _dispatchId,
  isEditing,
  isLoading,
  attachments,
  fileList,
  setFileList,
  uploading,
  uploadProgress,
  uploadErrors,
  setUploadErrors,
  uploadAttachmentsMutation: _uploadAttachmentsMutation,
  deleteAttachmentMutation,
}) => {
  const { message } = App.useApp();

  // 轉換為共用元件格式
  const normalizedAttachments: AttachmentItem[] = (attachments || []).map(
    (item: DispatchAttachment) => ({
      id: item.id,
      filename: item.file_name,
      originalFilename: item.original_name,
      contentType: item.mime_type,
      fileSize: item.file_size,
      createdAt: item.created_at,
    })
  );

  /** 預覽附件 */
  const handlePreview = async (attachmentId: number, filename: string) => {
    try {
      const blob = await dispatchAttachmentsApi.getAttachmentBlob(attachmentId);
      const previewUrl = window.URL.createObjectURL(blob);
      window.open(previewUrl, '_blank');
      setTimeout(() => window.URL.revokeObjectURL(previewUrl), 10000);
    } catch (error) {
      logger.error('預覽附件失敗:', error);
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

  return (
    <Spin spinning={isLoading}>
      {/* 上傳區塊（僅編輯模式顯示）*/}
      {isEditing && (
        <div style={{ marginBottom: 16 }}>
          <AttachmentUploader
            fileList={fileList}
            setFileList={setFileList as React.Dispatch<React.SetStateAction<UploadFile[]>>}
            uploading={uploading}
            uploadProgress={uploadProgress}
            uploadErrors={uploadErrors}
            setUploadErrors={setUploadErrors}
            allowedExtensions={ALLOWED_EXTENSIONS}
            maxFileSizeMB={MAX_FILE_SIZE_MB}
            showUploadButton={false}
          />
        </div>
      )}

      {/* 已上傳附件列表 */}
      {normalizedAttachments.length > 0 ? (
        <AttachmentList
          attachments={normalizedAttachments}
          editable={isEditing}
          onPreview={handlePreview}
          onDownload={handleDownload}
          onDelete={handleDelete}
          deleteLoading={deleteAttachmentMutation.isPending}
          deleteConfirmTitle="確定要刪除此附件嗎？"
          deleteConfirmDescription="刪除後無法復原，請確認是否繼續？"
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
