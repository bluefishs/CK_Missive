/**
 * 案件附件區（共用）— 上傳／列表／預覽／下載／刪除。
 *
 * owner 2026-08-19：「每筆報價單呈現可參照公文模式提供上傳與預覽機制，
 * 統一整體系統呈現與程式維護，降低異質同工機制」。
 *
 * # 為什麼是抽取而不是新寫
 *
 * 盤點全前端 9 處附件實作（共 2,158 行）後發現，`pmCase/QuotationRecordsTab`
 * **四項功能都齊全**（上傳/列表/預覽/刪除）且已在用 `PM.ATTACHMENTS_*` 端點——
 * 它就是最完整的那一份。新寫一個等於製造第 10 份。
 *
 * 這一版把它參數化搬出來，原本那個分頁改為薄包裝（行為不變、零風險），
 * 報價單詳情頁直接用同一個元件。
 *
 * # 尚未遷移的（刻意）
 *
 * 公文的 `ExistingAttachmentsList`(138) + `FileUploadSection`(171) +
 * `DocumentAttachmentsTab`(291) 是每天在用的核心路徑，這一輪不動。
 * 遷移規劃見 `docs/architecture/ATTACHMENT_CONSOLIDATION_PLAN.md`。
 */
import { useState } from 'react';
import { App, Modal, Image } from 'antd';
import type { UploadFile } from 'antd/es/upload';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AttachmentRecordsPanel, type AttachmentRecordItem } from './AttachmentRecordsPanel';
import { apiClient } from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';
import type { CaseAttachment, CaseAttachmentListResponse } from '../../types/attachment';
import { ATTACHMENT_DOC_TYPE_LABELS, ATTACHMENT_DOC_TYPE_COLORS } from '../../types/attachment';
import { getErrorMessage } from '../../utils/apiErrorParser';

export interface AttachmentPanelProps {
  /** 掛載點：附件以 case_code 關聯 */
  caseCode: string;
  /** 是否可寫（上傳區與刪除鈕只在可寫時出現） */
  isEditing?: boolean;
  /** 列表標題，預設「附件」 */
  title?: string;
  /** 上傳區標題，預設「上傳檔案」 */
  uploadTitle?: string;
  /** 空狀態文字 */
  emptyText?: string;
  /** 可接受的副檔名 */
  accept?: string;
  /** 是否顯示「文件類型」欄（報價單相關頁面才有意義） */
  showDocType?: boolean;
}

export function AttachmentPanel({
  caseCode,
  isEditing = false,
  title = '附件',
  uploadTitle = '上傳檔案',
  emptyText,
  accept = '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.jpg,.png,.zip',
  showDocType = false,
}: AttachmentPanelProps) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewTitle, setPreviewTitle] = useState('');
  const [previewType, setPreviewType] = useState<'image' | 'pdf'>('image');
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);

  // queryKey 保持與原本一致 —— 換 key 會讓既有頁面的快取失效鏈斷掉
  // （本專案有 queryKey drift 導致 invalidate 靜靜失效的紀錄，L39）
  const queryKey = ['pm-case-attachments', caseCode];

  const { data, isLoading } = useQuery({
    queryKey,
    queryFn: () => apiClient.post<CaseAttachmentListResponse>(
      API_ENDPOINTS.PM.ATTACHMENTS_LIST(caseCode)
    ),
    enabled: !!caseCode,
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      const files = fileList.map(f => f.originFileObj).filter(Boolean);
      if (files.length === 0) return;
      const formData = new FormData();
      files.forEach(f => formData.append('files', f as Blob));
      setUploading(true);
      return apiClient.postForm<{ success: boolean; files: unknown[]; errors: string[] }>(
        API_ENDPOINTS.PM.ATTACHMENTS_UPLOAD(caseCode), formData,
      );
    },
    onSuccess: (result) => {
      setUploading(false);
      setFileList([]);
      const uploaded = result?.files?.length ?? 0;
      const errors = result?.errors?.length ?? 0;
      if (errors > 0) message.warning(`上傳完成：${uploaded} 成功，${errors} 失敗`);
      else if (uploaded > 0) message.success(`成功上傳 ${uploaded} 個檔案`);
      queryClient.invalidateQueries({ queryKey });
    },
    onError: () => { setUploading(false); message.error('上傳失敗'); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiClient.post(API_ENDPOINTS.PM.ATTACHMENTS_DELETE(id)),
    onSuccess: () => { message.success('已刪除'); queryClient.invalidateQueries({ queryKey }); },
    onError: () => message.error('刪除失敗'),
  });

  const handleDownload = async (record: CaseAttachment) => {
    try {
      const blob = await apiClient.postBlob(API_ENDPOINTS.PM.ATTACHMENTS_DOWNLOAD(record.id));
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = record.file_name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (e) { message.error(getErrorMessage(e, '下載失敗'), 8); }
  };

  const handlePreview = async (record: CaseAttachment) => {
    try {
      const blob = await apiClient.postBlob(API_ENDPOINTS.PM.ATTACHMENTS_DOWNLOAD(record.id));
      const url = window.URL.createObjectURL(blob);
      setPreviewUrl(url);
      setPreviewTitle(record.file_name);
      setPreviewType(record.mime_type?.includes('pdf') ? 'pdf' : 'image');
    } catch (e) { message.error(getErrorMessage(e, '預覽失敗'), 8); }
  };

  const attachments = data?.attachments ?? [];
  // 2026-09-02 owner：「附件紀錄 tab 參照 /documents 方式設計，模組化減少異質同工」。
  // 列表與上傳區的長相交給共用的 AttachmentRecordsPanel（公文那套）；
  // 這裡只剩資料層：查詢／上傳／刪除／預覽 Modal。
  const items: AttachmentRecordItem[] = attachments.map(r => ({
    id: r.id, name: r.file_name, size: r.file_size ?? null, mimeType: r.mime_type ?? null, createdAt: r.created_at ?? null,
    tag: showDocType
      ? (r.doc_type
          ? { text: ATTACHMENT_DOC_TYPE_LABELS[r.doc_type] ?? r.doc_type, color: ATTACHMENT_DOC_TYPE_COLORS[r.doc_type] ?? 'default' }
          : { text: '未分類', color: 'default' })
      : null,
  }));
  const byId = (item: AttachmentRecordItem) => attachments.find(r => r.id === item.id);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <AttachmentRecordsPanel
        items={items} loading={isLoading} isEditing={isEditing} title={title} emptyText={emptyText}
        onPreview={(i) => { const r = byId(i); if (r) void handlePreview(r); }}
        onDownload={(i) => { const r = byId(i); if (r) void handleDownload(r); }}
        onDelete={(i) => deleteMutation.mutate(i.id)}
        fileList={fileList} setFileList={setFileList} uploading={uploading}
        uploadErrors={uploadErrors} setUploadErrors={setUploadErrors}
        accept={accept} maxFileSizeMB={50}
        uploadHint={`${uploadTitle}：支援 PDF、Word、Excel、圖片、壓縮檔（最大 50MB）`}
        onUploadNow={() => uploadMutation.mutate()}
      />
      <Modal
        title={previewTitle}
        open={!!previewUrl}
        footer={null}
        onCancel={() => { if (previewUrl) window.URL.revokeObjectURL(previewUrl); setPreviewUrl(null); }}
        width={previewType === 'pdf' ? 900 : 600}
        styles={{ body: { padding: previewType === 'pdf' ? 0 : 24, minHeight: 400 } }}
      >
        {previewUrl && previewType === 'pdf' && (
          <iframe src={previewUrl} style={{ width: '100%', height: '80vh', border: 'none' }} title={previewTitle} />
        )}
        {previewUrl && previewType === 'image' && (
          <Image src={previewUrl} alt={previewTitle} style={{ maxWidth: '100%' }} preview={false} />
        )}
      </Modal>
    </div>
  );
}

export default AttachmentPanel;
