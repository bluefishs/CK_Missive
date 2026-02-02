/**
 * DocumentList 列定義
 * 從 DocumentList.tsx 拆分，提高可維護性
 */

import React from 'react';
import { Typography, Tag, Space, Button, Popover, List, Spin } from 'antd';
import { SearchOutlined, PaperClipOutlined, DownloadOutlined, EyeOutlined, FileOutlined } from '@ant-design/icons';
import type { ColumnsType, ColumnType } from 'antd/es/table';
import Highlighter from 'react-highlight-words';
import { Document } from '../../../types';
import type { DocumentAttachment } from '../../../api/filesApi';
import { formatAgencyDisplay } from '../../../utils/agencyUtils';

// ========== 類型定義 ==========

export interface ColumnSearchState {
  searchText: string;
  searchedColumn: string;
}

export interface AttachmentHandlers {
  attachmentCache: Record<number, DocumentAttachment[]>;
  loadingAttachments: Record<number, boolean>;
  loadAttachments: (documentId: number) => void;
  handleDownloadAttachment: (attachment: DocumentAttachment, e: React.MouseEvent) => void;
  handlePreviewAttachment: (attachment: DocumentAttachment, e: React.MouseEvent) => void;
  formatFileSize: (bytes: number) => string;
  isPreviewable: (contentType?: string) => boolean;
}

export interface GetColumnsOptions {
  getRowNumber: (index: number) => number;
  searchState: ColumnSearchState;
  getColumnSearchProps: (dataIndex: keyof Document) => ColumnType<Document>;
  attachmentHandlers: AttachmentHandlers;
}

// ========== 手機版欄位 ==========

export const getMobileColumns = (
  getRowNumber: (index: number) => number
): ColumnsType<Document> => [
  {
    title: '公文資訊',
    key: 'document_info',
    render: (_: unknown, record: Document, index: number) => (
      <Space direction="vertical" size={0} style={{ width: '100%' }}>
        <Space size={4} wrap>
          <Typography.Text type="secondary" style={{ fontSize: 11 }}>
            #{getRowNumber(index)}
          </Typography.Text>
          <Tag color={record.delivery_method === '電子交換' ? 'green' : 'orange'} style={{ fontSize: 11 }}>
            {record.delivery_method || '電子'}
          </Tag>
          {(record.attachment_count || 0) > 0 && (
            <Tag color="cyan" icon={<PaperClipOutlined />} style={{ fontSize: 11 }}>
              {record.attachment_count}
            </Tag>
          )}
        </Space>
        <Typography.Text strong style={{ fontSize: 13 }}>
          {record.subject || '無主旨'}
        </Typography.Text>
        <Space size={8} style={{ fontSize: 12, color: '#666' }}>
          <span>{record.doc_number || '-'}</span>
          <span>
            {record.doc_date
              ? new Date(record.doc_date).toLocaleDateString('zh-TW')
              : '-'}
          </span>
        </Space>
      </Space>
    ),
  },
];

// ========== 桌面版欄位 ==========

export const getDesktopColumns = (options: GetColumnsOptions): ColumnsType<Document> => {
  const {
    getRowNumber,
    searchState,
    getColumnSearchProps,
    attachmentHandlers,
  } = options;

  const {
    attachmentCache,
    loadingAttachments,
    loadAttachments,
    handleDownloadAttachment,
    handlePreviewAttachment,
    formatFileSize,
    isPreviewable,
  } = attachmentHandlers;

  return [
    // 序號
    {
      title: '序',
      key: 'rowNumber',
      width: 45,
      align: 'center',
      render: (_: unknown, __: Document, index: number) => (
        <Typography.Text type="secondary">{getRowNumber(index)}</Typography.Text>
      ),
    },
    // 發文形式
    {
      title: '發文形式',
      dataIndex: 'delivery_method',
      key: 'delivery_method',
      width: 85,
      align: 'center',
      filters: [
        { text: '電子交換', value: '電子交換' },
        { text: '紙本郵寄', value: '紙本郵寄' },
      ],
      onFilter: (value, record) => record.delivery_method === value,
      render: (method: string) => {
        const colorMap: Record<string, string> = {
          '電子交換': 'green',
          '紙本郵寄': 'orange',
        };
        return <Tag color={colorMap[method] || 'default'}>{method || '電子交換'}</Tag>;
      },
    },
    // 收發單位
    {
      title: '收發單位',
      key: 'correspondent',
      width: 140,
      ellipsis: { showTitle: false },
      sorter: (a, b) => {
        const aValue = a.category === '收文' ? (a.sender || '') : (a.receiver || '');
        const bValue = b.category === '收文' ? (b.sender || '') : (b.receiver || '');
        return aValue.localeCompare(bValue, 'zh-TW');
      },
      sortDirections: ['descend', 'ascend'],
      render: (_: unknown, record: Document) => {
        const rawValue = record.category === '收文' ? record.sender : record.receiver;
        const labelPrefix = record.category === '收文' ? '來文：' : '發至：';
        const labelColor = record.category === '收文' ? '#52c41a' : '#1890ff';
        const displayValue = formatAgencyDisplay(rawValue);

        return (
          <Typography.Text ellipsis={{ tooltip: { title: displayValue, placement: 'topLeft' } }}>
            <span style={{ color: labelColor, fontWeight: 500, fontSize: '11px' }}>
              {labelPrefix}
            </span>
            {searchState.searchedColumn === 'correspondent' ? (
              <Highlighter
                highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
                searchWords={[searchState.searchText]}
                autoEscape
                textToHighlight={displayValue}
              />
            ) : displayValue}
          </Typography.Text>
        );
      },
    },
    // 公文字號
    {
      title: '公文字號',
      dataIndex: 'doc_number',
      key: 'doc_number',
      width: 170,
      ellipsis: { showTitle: false },
      sorter: (a, b) => (a.doc_number || '').localeCompare(b.doc_number || '', 'zh-TW'),
      sortDirections: ['descend', 'ascend'],
      ...getColumnSearchProps('doc_number'),
      render: (text: string) => (
        <Typography.Text
          strong
          style={{ color: '#1890ff' }}
          ellipsis={{ tooltip: { title: text, placement: 'topLeft' } }}
        >
          {searchState.searchedColumn === 'doc_number' ? (
            <Highlighter
              highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
              searchWords={[searchState.searchText]}
              autoEscape
              textToHighlight={text || ''}
            />
          ) : text}
        </Typography.Text>
      ),
    },
    // 公文日期
    {
      title: '公文日期',
      dataIndex: 'doc_date',
      key: 'doc_date',
      width: 95,
      align: 'center',
      sorter: (a, b) => {
        if (!a.doc_date) return 1;
        if (!b.doc_date) return -1;
        return new Date(a.doc_date).getTime() - new Date(b.doc_date).getTime();
      },
      sortDirections: ['descend', 'ascend'],
      render: (date: string) =>
        date
          ? new Date(date).toLocaleDateString('zh-TW', {
              year: 'numeric',
              month: '2-digit',
              day: '2-digit',
            })
          : '-',
    },
    // 主旨
    {
      title: '主旨',
      dataIndex: 'subject',
      key: 'subject',
      width: 300,
      ellipsis: { showTitle: false },
      sorter: (a, b) => (a.subject || '').localeCompare(b.subject || '', 'zh-TW'),
      sortDirections: ['descend', 'ascend'],
      ...getColumnSearchProps('subject'),
      render: (text: string) => (
        <Typography.Paragraph
          style={{ margin: 0, fontSize: '13px' }}
          ellipsis={{
            rows: 2,
            tooltip: {
              title: text,
              placement: 'topLeft',
              styles: { root: { maxWidth: 500 } }
            }
          }}
        >
          {searchState.searchedColumn === 'subject' ? (
            <Highlighter
              highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
              searchWords={[searchState.searchText]}
              autoEscape
              textToHighlight={text || ''}
            />
          ) : text}
        </Typography.Paragraph>
      ),
    },
    // 附件
    {
      title: '附件',
      dataIndex: 'attachment_count',
      key: 'attachment_count',
      width: 55,
      align: 'center',
      sorter: (a, b) => (a.attachment_count || 0) - (b.attachment_count || 0),
      sortDirections: ['descend', 'ascend'],
      render: (count: number | undefined, record: Document) => {
        const attachmentCount = count || 0;

        if (attachmentCount === 0) {
          return <Typography.Text type="secondary">-</Typography.Text>;
        }

        const documentId = record.id;
        const attachments = attachmentCache[documentId] || [];
        const isLoading = loadingAttachments[documentId];

        const attachmentContent = (
          <div style={{ width: 300, maxHeight: 300, overflow: 'auto' }}>
            {isLoading ? (
              <div style={{ textAlign: 'center', padding: '20px' }}>
                <Spin size="small" />
                <div style={{ marginTop: 8 }}>載入中...</div>
              </div>
            ) : attachments.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
                尚無附件資料
              </div>
            ) : (
              <List
                size="small"
                dataSource={attachments}
                renderItem={(attachment: DocumentAttachment) => (
                  <List.Item
                    key={attachment.id}
                    actions={[
                      isPreviewable(attachment.content_type) && (
                        <Button
                          type="text"
                          size="small"
                          icon={<EyeOutlined />}
                          onClick={(e) => handlePreviewAttachment(attachment, e)}
                          title="預覽"
                        />
                      ),
                      <Button
                        type="text"
                        size="small"
                        icon={<DownloadOutlined />}
                        onClick={(e) => handleDownloadAttachment(attachment, e)}
                        title="下載"
                      />,
                    ].filter(Boolean)}
                  >
                    <List.Item.Meta
                      avatar={<FileOutlined style={{ fontSize: 16, color: '#1890ff' }} />}
                      title={
                        <Typography.Text ellipsis style={{ maxWidth: 180 }} title={attachment.filename}>
                          {attachment.filename}
                        </Typography.Text>
                      }
                      description={
                        <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                          {formatFileSize(attachment.file_size)}
                        </Typography.Text>
                      }
                    />
                  </List.Item>
                )}
              />
            )}
          </div>
        );

        return (
          <Popover
            content={attachmentContent}
            title={`附件列表 (${attachmentCount} 個)`}
            trigger="click"
            placement="left"
            onOpenChange={(visible) => {
              if (visible) {
                loadAttachments(documentId);
              }
            }}
          >
            <Tag
              color="cyan"
              icon={<PaperClipOutlined />}
              style={{ cursor: 'pointer' }}
              onClick={(e) => e.stopPropagation()}
            >
              {attachmentCount}
            </Tag>
          </Popover>
        );
      },
    },
    // 承攬案件
    {
      title: '承攬案件',
      dataIndex: 'contract_project_name',
      key: 'contract_project_name',
      width: 160,
      ellipsis: true,
      render: (projectName: string | undefined) => (
        projectName ? (
          <Typography.Text
            ellipsis={{ tooltip: { title: projectName, placement: 'topLeft' } }}
            style={{ color: '#722ed1' }}
          >
            {projectName}
          </Typography.Text>
        ) : (
          <Typography.Text type="secondary">-</Typography.Text>
        )
      ),
    },
  ];
};

export default { getMobileColumns, getDesktopColumns };
