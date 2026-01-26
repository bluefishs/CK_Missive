/**
 * 附件紀錄 Tab
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

import React from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Typography,
  Tooltip,
  Empty,
} from 'antd';
import {
  PaperClipOutlined,
  DownloadOutlined,
  EyeOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { useNavigate } from 'react-router-dom';
import type { AttachmentsTabProps, Attachment, LocalGroupedAttachment } from './types';

const { Text } = Typography;

// 輔助函數
const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
};

const isPreviewable = (contentType?: string, filename?: string): boolean => {
  if (contentType) {
    if (contentType.startsWith('image/') ||
        contentType === 'application/pdf' ||
        contentType.startsWith('text/')) {
      return true;
    }
  }
  if (filename) {
    const ext = filename.toLowerCase().split('.').pop();
    return ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'txt', 'csv'].includes(ext || '');
  }
  return false;
};

export const AttachmentsTab: React.FC<AttachmentsTabProps> = ({
  attachments,
  groupedAttachments,
  loading,
  onRefresh,
  onDownload,
  onPreview,
  onDownloadAll,
  relatedDocsCount,
}) => {
  const navigate = useNavigate();

  // 分組附件表格欄位（父層：公文）
  const groupedColumns: ColumnsType<LocalGroupedAttachment> = [
    {
      title: '公文字號',
      dataIndex: 'document_number',
      key: 'document_number',
      width: 200,
      render: (text: string, record) => (
        <Tooltip title={record.document_subject}>
          <Button
            type="link"
            style={{ padding: 0, fontWeight: 500 }}
            onClick={() => navigate(`/documents/${record.document_id}`)}
          >
            {text}
          </Button>
        </Tooltip>
      ),
    },
    {
      title: '檔案數',
      dataIndex: 'file_count',
      key: 'file_count',
      width: 100,
      align: 'center',
      render: (count: number) => <Tag color="blue">{count} 個</Tag>,
    },
    {
      title: '總大小',
      dataIndex: 'total_size',
      key: 'total_size',
      width: 100,
      render: (size: number) => formatFileSize(size),
    },
    {
      title: '最後更新',
      dataIndex: 'last_updated',
      key: 'last_updated',
      width: 110,
      render: (date: string) => date ? dayjs(date).format('YYYY-MM-DD') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Tooltip title="全部下載">
          <Button
            size="small"
            icon={<DownloadOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              onDownloadAll(record);
            }}
          >
            全部下載
          </Button>
        </Tooltip>
      ),
    },
  ];

  // 展開列：單一附件明細
  const expandedColumns: ColumnsType<Attachment> = [
    {
      title: '檔案名稱',
      dataIndex: 'filename',
      key: 'filename',
      ellipsis: true,
      render: (text) => (
        <Space>
          <PaperClipOutlined style={{ color: '#1890ff' }} />
          <Text ellipsis={{ tooltip: text }}>{text}</Text>
        </Space>
      ),
    },
    {
      title: '大小',
      dataIndex: 'file_size',
      key: 'file_size',
      width: 100,
      render: (size) => formatFileSize(size),
    },
    {
      title: '上傳時間',
      dataIndex: 'uploaded_at',
      key: 'uploaded_at',
      width: 110,
      render: (date: string) => date ? dayjs(date).format('YYYY-MM-DD') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="下載">
            <Button
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => onDownload(record.id, record.filename)}
            />
          </Tooltip>
          {isPreviewable(record.content_type, record.filename) && (
            <Tooltip title="預覽">
              <Button
                size="small"
                icon={<EyeOutlined />}
                onClick={() => onPreview(record.id, record.filename)}
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Card
      title={
        <Space>
          <PaperClipOutlined />
          <span>附件紀錄</span>
          <Tag color="blue">{attachments.length} 個檔案</Tag>
          {groupedAttachments.length > 0 && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              (來自 {groupedAttachments.length} 筆公文)
            </Text>
          )}
        </Space>
      }
      extra={
        <Button
          icon={<ReloadOutlined />}
          onClick={onRefresh}
          loading={loading}
        >
          重新整理
        </Button>
      }
      loading={loading}
    >
      {groupedAttachments.length > 0 ? (
        <Table
          columns={groupedColumns}
          dataSource={groupedAttachments}
          rowKey="document_id"
          pagination={false}
          size="middle"
          expandable={{
            expandedRowRender: (record) => (
              <Table
                columns={expandedColumns}
                dataSource={record.attachments}
                rowKey="id"
                pagination={false}
                size="small"
                showHeader={false}
                style={{ margin: 0 }}
              />
            ),
            rowExpandable: (record) => record.attachments.length > 0,
          }}
        />
      ) : (
        <Empty
          description={
            relatedDocsCount === 0 ? (
              <span>
                尚無關聯公文<br />
                <Text type="secondary">
                  請先在「關聯公文」頁籤中關聯公文，附件將自動彙整於此。
                </Text>
              </span>
            ) : (
              <span>
                關聯公文中尚無附件<br />
                <Text type="secondary">
                  可至「關聯公文」頁籤點擊公文字號進入公文詳情頁上傳附件。
                </Text>
              </span>
            )
          }
        />
      )}
    </Card>
  );
};

export default AttachmentsTab;
