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
import {
  Card, Button, Upload, Space, Popconfirm, App, Empty, Modal, Image, Tag,
} from 'antd';
import {
  UploadOutlined, DownloadOutlined, DeleteOutlined, EyeOutlined,
  FileOutlined, FilePdfOutlined, FileExcelOutlined, FileWordOutlined, FileImageOutlined,
} from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload';
import type { ColumnsType } from 'antd/es/table';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { EnhancedTable } from './EnhancedTable';
import { apiClient } from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';
import type { CaseAttachment, CaseAttachmentListResponse } from '../../types/attachment';
import { ATTACHMENT_DOC_TYPE_LABELS, ATTACHMENT_DOC_TYPE_COLORS } from '../../types/attachment';
import { getErrorMessage } from '../../utils/apiErrorParser';

const getFileIcon = (mime?: string) => {
  if (!mime) return <FileOutlined />;
  if (mime.includes('pdf')) return <FilePdfOutlined style={{ color: '#ff4d4f' }} />;
  if (mime.includes('sheet') || mime.includes('excel')) return <FileExcelOutlined style={{ color: '#52c41a' }} />;
  if (mime.includes('word') || mime.includes('document')) return <FileWordOutlined style={{ color: '#1890ff' }} />;
  if (mime.includes('image')) return <FileImageOutlined style={{ color: '#722ed1' }} />;
  return <FileOutlined />;
};

const formatFileSize = (bytes?: number) => {
  if (!bytes) return '-';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
};

const isPreviewable = (mime?: string) =>
  !!mime && (mime.includes('image') || mime.includes('pdf'));

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

  const columns: ColumnsType<CaseAttachment> = [
    {
      title: '檔案',
      key: 'file',
      render: (_, r) => (
        <Space>
          {getFileIcon(r.mime_type)}
          <span>{r.file_name}</span>
        </Space>
      ),
    },
    ...(showDocType ? [{
      title: '類型',
      key: 'doc_type',
      width: 130,
      // 未分類顯示「—」而不是空白：空白會被讀成「沒有這個欄位」，
      // 而 NULL 的意思是「還沒有人分類過」，兩者不同。
      render: (_: unknown, r: CaseAttachment) => (
        r.doc_type
          ? <Tag color={ATTACHMENT_DOC_TYPE_COLORS[r.doc_type] ?? 'default'}>
              {ATTACHMENT_DOC_TYPE_LABELS[r.doc_type] ?? r.doc_type}
            </Tag>
          : <span style={{ color: '#999' }}>—</span>
      ),
    } as ColumnsType<CaseAttachment>[number]] : []),
    { title: '大小', key: 'size', width: 90, render: (_, r) => formatFileSize(r.file_size) },
    {
      title: '上傳時間', key: 'created_at', width: 130,
      render: (_, r) => r.created_at ? dayjs(r.created_at).format('YYYY/MM/DD HH:mm') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: isEditing ? 120 : 80,
      render: (_, r) => (
        <Space size={4}>
          {isPreviewable(r.mime_type) && (
            <Button type="text" size="small" icon={<EyeOutlined />} onClick={() => handlePreview(r)} />
          )}
          <Button type="text" size="small" icon={<DownloadOutlined />} onClick={() => handleDownload(r)} />
          {isEditing && (
            <Popconfirm title="確定刪除此檔案？" onConfirm={() => deleteMutation.mutate(r.id)}>
              <Button type="text" size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {isEditing && (
        <Card size="small" title={uploadTitle}>
          <Upload.Dragger
            multiple fileList={fileList} beforeUpload={() => false}
            onChange={({ fileList: fl }) => setFileList(fl)}
            accept={accept}
          >
            <p className="ant-upload-drag-icon"><UploadOutlined style={{ fontSize: 32, color: '#1890ff' }} /></p>
            <p>點擊或拖曳檔案至此處上傳</p>
            <p style={{ color: '#999', fontSize: 12 }}>支援 PDF、Word、Excel、圖片、壓縮檔（最大 50MB）</p>
          </Upload.Dragger>
          {fileList.length > 0 && (
            <Button type="primary" style={{ marginTop: 12 }} loading={uploading}
              onClick={() => uploadMutation.mutate()}
            >上傳 {fileList.length} 個檔案</Button>
          )}
        </Card>
      )}

      <Card size="small" title={`${title} (${attachments.length})`}>
        {attachments.length > 0 ? (
          <EnhancedTable<CaseAttachment>
            dataSource={attachments} columns={columns} rowKey="id"
            loading={isLoading} size="small" pagination={false}
          />
        ) : (
          <Empty
            description={emptyText ?? (isEditing ? `尚無${title}，請上傳檔案` : `尚無${title}`)}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        )}
      </Card>

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
