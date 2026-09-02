/**
 * 附件紀錄面板 —— 純呈現、受控。
 *
 * 2026-09-02 owner：「已承攬 02 承攬報價其附件紀錄(tab)呈現與管理請參照 /documents/2757
 * 附件紀錄(tab)方式設計，以利模組化減少異質同工」。
 *
 * 此前三處附件 UI 是**三份**：
 *   - `pages/document/tabs/DocumentAttachmentsTab`（公文；Dragger＋待上傳卡＋進度＋錯誤＋列表卡，隨表單「儲存」上傳）
 *   - `components/common/AttachmentPanel`（承攬案／報價單；Dragger＋「上傳 N 個檔案」鈕＋EnhancedTable，即時上傳）
 *   - `pages/contractCase/tabs/AttachmentsTab` 自己再畫一張「關聯公文附件」表
 * 三者的列表長相、圖示、預覽判準各寫一份。
 *
 * 這個元件只管「長什麼樣」：列表卡（公文樣式）＋上傳區（Dragger／待上傳／進度／錯誤）。
 * 資料怎麼來、上傳打哪個端點、預覽 Modal 怎麼開，由呼叫端決定 ——
 * 所以公文（受控、儲存時上傳）與案件（自主、即時上傳）都能用同一張臉。
 */
import React from 'react';
import { Alert, Button, Card, Empty, Flex, Popconfirm, Progress, Space, Spin, Tag, Upload } from 'antd';
import {
  CloudUploadOutlined, DeleteOutlined, DownloadOutlined, EyeOutlined, FileImageOutlined,
  FileOutlined, FilePdfOutlined, InboxOutlined, LoadingOutlined, PaperClipOutlined,
} from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload';
import dayjs from 'dayjs';

const { Dragger } = Upload;

/** 統一的附件列形狀 —— 公文附件與案件附件各自映射到這個形狀再交進來 */
export interface AttachmentRecordItem {
  id: number;
  name: string;
  size?: number | null;
  mimeType?: string | null;
  createdAt?: string | null;
  /** 分類標籤（案件附件的 doc_type；公文附件沒有） */
  tag?: { text: string; color?: string } | null;
  /** 次要說明（例如上傳者、備註） */
  note?: string | null;
}

export interface AttachmentRecordsPanelProps {
  items: AttachmentRecordItem[];
  loading?: boolean;
  isEditing: boolean;
  /** 列表卡標題（預設「已上傳附件」） */
  title?: string;
  emptyText?: string;
  onPreview: (item: AttachmentRecordItem) => void;
  onDownload: (item: AttachmentRecordItem) => void;
  onDelete?: (item: AttachmentRecordItem) => void;

  /** ── 上傳區（isEditing 時顯示）── */
  fileList: UploadFile[];
  setFileList: (files: UploadFile[]) => void;
  uploading?: boolean;
  /** 0–100；不給就不畫進度條 */
  uploadProgress?: number;
  uploadErrors?: string[];
  setUploadErrors?: (errors: string[]) => void;
  accept?: string;
  maxFileSizeMB?: number;
  allowedExtensions?: string[];
  uploadHint?: string;
  /**
   * 即時上傳：給了就顯示「上傳 N 個檔案」鈕（案件附件）；
   * 不給就顯示「點擊上方儲存後開始上傳」（公文附件隨表單儲存）。
   */
  onUploadNow?: () => void;
}

const isPreviewableFile = (mimeType?: string | null, filename?: string): boolean => {
  if (mimeType && (mimeType.startsWith('image/') || mimeType === 'application/pdf' || mimeType.startsWith('text/'))) return true;
  const ext = filename?.toLowerCase().split('.').pop() ?? '';
  return ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'txt', 'csv'].includes(ext);
};

const fileIconFor = (mimeType?: string | null, filename?: string) => {
  const ext = filename?.toLowerCase().split('.').pop() ?? '';
  if (mimeType?.startsWith('image/') || ['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(ext)) {
    return <FileImageOutlined style={{ fontSize: 20, color: '#52c41a' }} />;
  }
  if (mimeType === 'application/pdf' || ext === 'pdf') {
    return <FilePdfOutlined style={{ fontSize: 20, color: '#ff4d4f' }} />;
  }
  return <PaperClipOutlined style={{ fontSize: 20, color: '#1890ff' }} />;
};

const formatSize = (bytes?: number | null) => {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
};

export const AttachmentRecordsPanel: React.FC<AttachmentRecordsPanelProps> = ({
  items, loading, isEditing, title = '已上傳附件', emptyText,
  onPreview, onDownload, onDelete,
  fileList, setFileList, uploading, uploadProgress, uploadErrors = [], setUploadErrors,
  accept, maxFileSizeMB = 50, allowedExtensions, uploadHint, onUploadNow,
}) => {
  const validate = (file: File): string | null => {
    const ext = '.' + (file.name.toLowerCase().split('.').pop() || '');
    if (allowedExtensions && !allowedExtensions.includes(ext)) return `不支援 ${ext} 檔案格式`;
    if (file.size > maxFileSizeMB * 1024 * 1024) {
      return `檔案大小 ${(file.size / (1024 * 1024)).toFixed(2)}MB 超過限制 (最大 ${maxFileSizeMB}MB)`;
    }
    return null;
  };

  return (
    <Spin spinning={!!loading}>
      {/* 既有附件列表（公文樣式：一列一檔，圖示＋檔名＋大小＋時間＋操作） */}
      <Card
        size="small"
        title={<Space><PaperClipOutlined /><span>{title}（{items.length} 個）</span></Space>}
        style={{ marginBottom: 16 }}
      >
        {items.length === 0 ? (
          <Empty description={emptyText ?? (isEditing ? `尚無${title}，請上傳檔案` : `尚無${title}`)} image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <Flex vertical gap={0}>
            {items.map(item => (
              <div key={item.id} style={{ display: 'flex', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
                <div style={{ marginRight: 12, flexShrink: 0 }}>{fileIconFor(item.mimeType, item.name)}</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <span>{item.name}</span>
                    {item.tag && <Tag color={item.tag.color ?? 'default'}>{item.tag.text}</Tag>}
                  </div>
                  <div style={{ fontSize: 12, color: '#999' }}>
                    {formatSize(item.size)}
                    {item.createdAt && ` · ${dayjs(item.createdAt).format('YYYY-MM-DD HH:mm')}`}
                    {item.note && ` · ${item.note}`}
                  </div>
                </div>
                <Space style={{ flexShrink: 0, marginLeft: 12 }}>
                  {isPreviewableFile(item.mimeType, item.name) && (
                    <Button type="link" size="small" icon={<EyeOutlined />} style={{ color: '#52c41a' }} onClick={() => onPreview(item)}>預覽</Button>
                  )}
                  <Button type="link" size="small" icon={<DownloadOutlined />} onClick={() => onDownload(item)}>下載</Button>
                  {isEditing && onDelete && (
                    <Popconfirm title="確定要刪除此附件嗎？" onConfirm={() => onDelete(item)} okText="確定" cancelText="取消">
                      <Button type="link" size="small" danger icon={<DeleteOutlined />}>刪除</Button>
                    </Popconfirm>
                  )}
                </Space>
              </div>
            ))}
          </Flex>
        )}
      </Card>

      {/* 上傳區（編輯模式才顯示） */}
      {isEditing && (
        <>
          <Dragger
            multiple fileList={fileList} showUploadList={false} accept={accept} disabled={uploading}
            beforeUpload={(file) => {
              const err = validate(file as unknown as File);
              if (err) { setUploadErrors?.([...uploadErrors, `${file.name}：${err}`]); return Upload.LIST_IGNORE; }
              return false;
            }}
            onChange={({ fileList: fl }) => setFileList(fl)}
            onRemove={(file) => setFileList(fileList.filter(f => f.uid !== file.uid))}
          >
            <p className="ant-upload-drag-icon"><InboxOutlined /></p>
            <p className="ant-upload-text">點擊或拖拽文件到此區域上傳</p>
            <p className="ant-upload-hint">{uploadHint ?? `支援 PDF、DOC、DOCX、XLS、XLSX、JPG、PNG 等格式，單檔最大 ${maxFileSizeMB}MB`}</p>
          </Dragger>

          {fileList.length > 0 && !uploading && (
            <Card size="small" style={{ marginTop: 16, background: '#f6ffed', border: '1px solid #b7eb8f' }}
              title={<span style={{ color: '#52c41a' }}><CloudUploadOutlined style={{ marginRight: 8 }} />待上傳檔案（{fileList.length} 個）</span>}
            >
              <Flex vertical gap={0}>
                {fileList.map(file => (
                  <div key={file.uid} style={{ display: 'flex', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
                    <FileOutlined style={{ color: '#1890ff', marginRight: 12, flexShrink: 0 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div>{file.name}</div>
                      <div style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }}>{formatSize(file.size)}</div>
                    </div>
                    <Button type="link" size="small" danger onClick={() => setFileList(fileList.filter(f => f.uid !== file.uid))}>移除</Button>
                  </div>
                ))}
              </Flex>
              {onUploadNow ? (
                <Button type="primary" icon={<CloudUploadOutlined />} style={{ marginTop: 12 }} onClick={onUploadNow}>
                  上傳 {fileList.length} 個檔案
                </Button>
              ) : (
                <p style={{ color: '#999', fontSize: 12, marginTop: 8, marginBottom: 0 }}>點擊上方「儲存」按鈕後開始上傳</p>
              )}
            </Card>
          )}

          {uploading && (
            <Card size="small" style={{ marginTop: 16, background: '#e6f7ff', border: '1px solid #91d5ff' }}
              title={<span style={{ color: '#1890ff' }}><LoadingOutlined style={{ marginRight: 8 }} />正在上傳檔案...</span>}
            >
              {typeof uploadProgress === 'number'
                ? <Progress percent={uploadProgress} status="active" strokeColor={{ '0%': '#108ee9', '100%': '#87d068' }} size={['100%', 12]} />
                : <Progress percent={100} status="active" showInfo={false} size={['100%', 12]} />}
            </Card>
          )}

          {uploadErrors.length > 0 && (
            <Alert type="warning" showIcon closable style={{ marginTop: 16 }}
              onClose={() => setUploadErrors?.([])}
              title="部分檔案上傳失敗"
              description={<ul style={{ margin: 0, paddingLeft: 20 }}>{uploadErrors.map((e, i) => <li key={i}>{e}</li>)}</ul>}
            />
          )}
        </>
      )}
    </Spin>
  );
};

export default AttachmentRecordsPanel;
