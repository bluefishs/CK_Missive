/**
 * 公文附件紀錄 tab。
 *
 * 2026-09-02：UI 抽到共用的 `components/common/AttachmentRecordsPanel`（owner：「附件紀錄 tab
 * 參照 /documents 方式設計，模組化減少異質同工」）。本檔原本 290 行自己畫列表、Dragger、
 * 待上傳卡、進度、錯誤；承攬案／報價單那邊的 AttachmentPanel 又畫一份。現在三處同一張臉，
 * 這裡只剩「公文附件 → 統一列形狀」的映射與受控 props 的轉接。
 * 上傳時機不變：檔案先進 fileList，按表單「儲存」才上傳（由 useDocumentDetailData 負責）。
 */
import React from 'react';
import type { DocumentAttachmentsTabProps } from './types';
import type { DocumentAttachment } from '../../../types/api';
import { AttachmentRecordsPanel, type AttachmentRecordItem } from '../../../components/common/AttachmentRecordsPanel';

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
  const items: AttachmentRecordItem[] = attachments.map((a: DocumentAttachment) => ({
    id: a.id,
    name: a.original_filename || a.filename,
    size: a.file_size ?? null,
    mimeType: a.content_type ?? null,
    createdAt: a.created_at ?? null,
  }));
  return (
    <AttachmentRecordsPanel
      items={items}
      loading={attachmentsLoading}
      isEditing={isEditing}
      title="已上傳附件"
      emptyText={isEditing ? '尚無附件，可拖拽檔案至下方上傳' : '尚無附件'}
      onPreview={(i) => { void onPreview(i.id, i.name); }}
      onDownload={(i) => { void onDownload(i.id, i.name); }}
      onDelete={(i) => { void onDelete(i.id); }}
      fileList={fileList}
      setFileList={setFileList}
      uploading={uploading}
      uploadProgress={uploadProgress}
      uploadErrors={uploadErrors}
      setUploadErrors={setUploadErrors}
      maxFileSizeMB={fileSettings.maxFileSizeMB}
      allowedExtensions={fileSettings.allowedExtensions}
    />
  );
};

export default DocumentAttachmentsTab;
