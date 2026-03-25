/**
 * 報價紀錄 Tab — PM 案件的報價單上傳/管理
 *
 * 參照 documents 附件紀錄機制：
 * - 編輯模式：顯示上傳區 + 刪除按鈕
 * - 檢視模式：僅顯示列表 + 下載/預覽
 * - 預覽：PDF/圖片 inline，其他類型下載
 *
 * @version 2.0.0 — isEditing 門控 + 預覽
 */
import { useState } from 'react';
import {
  Card, Table, Button, Upload, Space, Popconfirm, App, Empty, Modal, Image,
} from 'antd';
import {
  UploadOutlined, DownloadOutlined, DeleteOutlined, EyeOutlined,
  FileOutlined, FilePdfOutlined, FileExcelOutlined, FileWordOutlined, FileImageOutlined,
} from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload';
import type { ColumnsType } from 'antd/es/table';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';
import dayjs from 'dayjs';

interface Attachment {
  id: number;
  file_name: string;
  file_size?: number;
  mime_type?: string;
  notes?: string;
  uploaded_by?: number;
  created_at?: string;
}

interface AttachmentListResponse {
  success: boolean;
  attachments: Attachment[];
  total: number;
}

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

interface QuotationRecordsTabProps {
  caseCode: string;
  isEditing?: boolean;
}

export default function QuotationRecordsTab({ caseCode, isEditing = false }: QuotationRecordsTabProps) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewTitle, setPreviewTitle] = useState('');
  const [previewType, setPreviewType] = useState<'image' | 'pdf'>('image');

  const queryKey = ['pm-case-attachments', caseCode];

  const { data, isLoading } = useQuery({
    queryKey,
    queryFn: () => apiClient.post<AttachmentListResponse>(
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

  const handleDownload = async (record: Attachment) => {
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
    } catch { message.error('下載失敗'); }
  };

  const handlePreview = async (record: Attachment) => {
    try {
      const blob = await apiClient.postBlob(API_ENDPOINTS.PM.ATTACHMENTS_DOWNLOAD(record.id));
      const url = window.URL.createObjectURL(blob);
      setPreviewUrl(url);
      setPreviewTitle(record.file_name);
      setPreviewType(record.mime_type?.includes('pdf') ? 'pdf' : 'image');
    } catch { message.error('預覽失敗'); }
  };

  const attachments = data?.attachments ?? [];

  const columns: ColumnsType<Attachment> = [
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
    { title: '大小', key: 'size', width: 90, render: (_, r) => formatFileSize(r.file_size) },
    { title: '上傳時間', key: 'created_at', width: 130, render: (_, r) => r.created_at ? dayjs(r.created_at).format('YYYY/MM/DD HH:mm') : '-' },
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
      {/* 上傳區：僅編輯模式顯示 */}
      {isEditing && (
        <Card size="small" title="上傳報價單">
          <Upload.Dragger
            multiple fileList={fileList} beforeUpload={() => false}
            onChange={({ fileList: fl }) => setFileList(fl)}
            accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.jpg,.png,.zip"
          >
            <p className="ant-upload-drag-icon"><UploadOutlined style={{ fontSize: 32, color: '#1890ff' }} /></p>
            <p>點擊或拖曳報價單檔案至此處上傳</p>
            <p style={{ color: '#999', fontSize: 12 }}>支援 PDF、Word、Excel、圖片、壓縮檔（最大 50MB）</p>
          </Upload.Dragger>
          {fileList.length > 0 && (
            <Button type="primary" style={{ marginTop: 12 }} loading={uploading}
              onClick={() => uploadMutation.mutate()}
            >上傳 {fileList.length} 個檔案</Button>
          )}
        </Card>
      )}

      {/* 附件列表 */}
      <Card size="small" title={`報價紀錄 (${attachments.length})`}>
        {attachments.length > 0 ? (
          <Table<Attachment>
            dataSource={attachments} columns={columns} rowKey="id"
            loading={isLoading} size="small" pagination={false}
          />
        ) : (
          <Empty description={isEditing ? '尚無報價紀錄，請上傳報價單' : '尚無報價紀錄'} image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Card>

      {/* 預覽 Modal */}
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
