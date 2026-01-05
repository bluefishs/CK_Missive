import React, { useState } from 'react';
import { Table, Button, Space, Typography, Tag, Empty, TableProps } from 'antd';
import type {
  TablePaginationConfig,
  FilterValue,
  TableCurrentDataSource,
  SortOrder,
  SorterResult,
} from 'antd/es/table/interface';
import type { ColumnsType } from 'antd/es/table';

import { FileExcelOutlined } from '@ant-design/icons';
import { Document } from '../../types';
import { DocumentActions, BatchActions } from './DocumentActions';

interface DocumentListProps {
  documents: Document[];
  loading: boolean;
  total: number;
  pagination: {
    current: number;
    pageSize: number;
  };
  sortField?: string;
  sortOrder?: SortOrder;
  onTableChange?: (
    pagination: TablePaginationConfig,
    filters: Record<string, FilterValue | null>,
    sorter: SorterResult<Document> | SorterResult<Document>[],
    extra: TableCurrentDataSource<Document>
  ) => void;
  onEdit: (document: Document) => void;
  onDelete: (document: Document) => void;
  onView: (document: Document) => void;
  onCopy?: (document: Document) => void;
  onExportPdf?: (document: Document) => void;
  onSend?: (document: Document) => void;
  onArchive?: (document: Document) => void;
  onAddToCalendar?: (document: Document) => void; // Add this prop
  onExport?: (() => void) | undefined;
  onBatchExport?: (documents: Document[]) => void;
  onBatchDelete?: (documents: Document[]) => void;
  onBatchArchive?: (documents: Document[]) => void;
  onBatchCopy?: (documents: Document[]) => void;
  enableBatchOperations?: boolean;
  isExporting?: boolean;
  isAddingToCalendar?: boolean;
}

export const DocumentList: React.FC<DocumentListProps> = ({
  documents,
  loading,
  total,
  pagination,
  sortField,
  sortOrder,
  onTableChange,
  onEdit,
  onDelete,
  onView,
  onCopy,
  onExportPdf,
  onSend,
  onArchive,
  onAddToCalendar, // Add this prop
  onExport,
  onBatchExport,
  onBatchDelete,
  onBatchArchive,
  onBatchCopy,
  enableBatchOperations = false,
  isExporting = false,
  isAddingToCalendar = false,
}) => {
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [batchLoading, setBatchLoading] = useState(false);

  // Debug logging
  console.log('=== DocumentList: 收到的 props ===', {
    documentsCount: documents?.length || 0,
    documents: documents,
    loading,
    total,
    pagination
  });

  const handleBatchExportClick = () => {
    console.log('批次匯出按鈕已被點擊，但功能尚未實作。');
    // 未來可以在這裡加入實際的匯出邏輯
  };

  const handleBatchDeleteClick = () => {
    console.log('批次刪除按鈕已被點擊，但功能尚未實作。');
  };

  const handleBatchArchiveClick = () => {
    console.log('批次封存按鈕已被點擊，但功能尚未實作。');
  };

  const handleBatchCopyClick = () => {
    console.log('批次複製按鈕已被點擊，但功能尚未實作。');
  };

  const getColumnConfig = (
    key: string,
    title: string,
    options?: Partial<ColumnsType<Document>[0]>
  ): ColumnsType<Document>[0] => {
    const config: ColumnsType<Document>[0] = {
      key,
      title,
      dataIndex: key,
      sorter: true,
      ...options,
    };

    if (sortField === key && sortOrder) {
      config.sortOrder = sortOrder;
    }

    return config;
  };

  const columns: ColumnsType<Document> = [
    {
      title: '流水號',
      dataIndex: 'id',
      key: 'id',
      sorter: (a, b) => a.id - b.id,
      render: (id: number) => (
        <Typography.Text strong style={{ color: '#666' }}>
          {id}
        </Typography.Text>
      ),
    },
    {
      title: '類型',
      dataIndex: 'doc_type',
      key: 'doc_type',
      sorter: (a, b) => (a.doc_type || '').localeCompare(b.doc_type || '', 'zh-TW'),
      filters: [
        { text: '函', value: '函' },
        { text: '公告', value: '公告' },
        { text: '簽', value: '簽' },
        { text: '書函', value: '書函' },
        { text: '令', value: '令' },
        { text: '其他', value: '其他' },
      ],
      onFilter: (value, record) => record.doc_type === value,
      render: (type: string) => <Tag color="blue">{type || '未分類'}</Tag>,
    },
    {
      title: '文號',
      dataIndex: 'doc_number',
      key: 'doc_number',
      sorter: (a, b) => (a.doc_number || '').localeCompare(b.doc_number || '', 'zh-TW'),
      render: (text: string) => (
        <Typography.Text strong style={{ color: '#1890ff' }}>
          {text}
        </Typography.Text>
      ),
    },
    {
      title: '發文日期',
      dataIndex: 'doc_date',
      key: 'doc_date',
      sorter: (a, b) => {
        if (!a.doc_date) return 1;
        if (!b.doc_date) return -1;
        return new Date(a.doc_date).getTime() - new Date(b.doc_date).getTime();
      },
      render: (date: string) =>
        date
          ? new Date(date).toLocaleDateString('zh-TW', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })
          : '無日期',
    },
    {
      title: '類別',
      dataIndex: 'category',
      key: 'category',
      sorter: (a, b) => (a.category || '').localeCompare(b.category || '', 'zh-TW'),
      filters: [
        { text: '收文', value: 'receive' },
        { text: '發文', value: 'send' },
      ],
      onFilter: (value, record) => record.category === value,
      render: (category: string) => {
        const color = category === 'receive' ? 'green' : category === 'send' ? 'orange' : 'default';
        const label = category === 'receive' ? '收文' : category === 'send' ? '發文' : (category || '未分類');
        return <Tag color={color}>{label}</Tag>;
      },
    },
    {
      title: '主旨',
      dataIndex: 'subject',
      key: 'subject',
      sorter: (a, b) => (a.subject || '').localeCompare(b.subject || '', 'zh-TW'),
      ellipsis: { showTitle: false },
      render: (text: string) => (
        <Typography.Text
          strong
          ellipsis={{ tooltip: text }}
        >
          {text}
        </Typography.Text>
      ),
    },
    {
      title: '發文單位',
      dataIndex: 'sender',
      key: 'sender',
      sorter: (a, b) => (a.sender || '').localeCompare(b.sender || '', 'zh-TW'),
      ellipsis: true,
      render: (sender: string) => (
        <Typography.Text style={{ color: '#888' }}>{sender}</Typography.Text>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: Document) => (
        <DocumentActions
          document={record}
          onView={onView}
          onEdit={onEdit}
          onDelete={onDelete}
          onCopy={onCopy}
          onExportPdf={onExportPdf}
          onSend={onSend}
          onArchive={onArchive}
          onAddToCalendar={onAddToCalendar}
          loadingStates={{
            isExporting: isExporting,
            isAddingToCalendar: isAddingToCalendar,
          }}
          mode="buttons"
        />
      ),
    },
  ];

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => setSelectedRowKeys(keys),
  };

  // Ensure documents is always an array
  const safeDocuments = Array.isArray(documents) ? documents : [];
  console.log('=== DocumentList: 安全文件陣列 ===', {
    originalDocuments: documents,
    safeDocuments: safeDocuments,
    length: safeDocuments.length
  });

  const tableProps: TableProps<Document> = {
    columns,
    dataSource: safeDocuments,
    rowKey: 'id',
    loading: loading || batchLoading,
    onRow: (record) => ({
      onClick: () => onEdit(record),
      style: { cursor: 'pointer' },
    }),
    pagination: {
      ...pagination,
      total,
      showSizeChanger: true,
      showTotal: (totalNum, range) => `顯示 ${range[0]}-${range[1]} 筆，共 ${totalNum} 筆`,
    },
    scroll: { x: 'max-content' },
    locale: {
      emptyText: (
        <Empty
          description={
            loading ? "載入中..." :
            (safeDocuments.length === 0 && total > 0) ? "資料處理中，請稍候..." :
            "暫無資料"
          }
        />
      ),
    },
    ...(enableBatchOperations && { rowSelection }),
  };

  if (onTableChange) {
    tableProps.onChange = onTableChange;
  }

  return (
    <>
      <Space style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Button
          onClick={onExport}
          icon={<FileExcelOutlined />}
          loading={isExporting}
          disabled={loading}
        >
          匯出 Excel
        </Button>
        {enableBatchOperations && (
          <BatchActions
            selectedCount={selectedRowKeys.length}
            onExportSelected={handleBatchExportClick}
            onDeleteSelected={handleBatchDeleteClick}
            onArchiveSelected={handleBatchArchiveClick}
            onCopySelected={handleBatchCopyClick}
            onClearSelection={() => setSelectedRowKeys([])}
            loading={batchLoading}
          />
        )}
      </Space>
      <Table {...tableProps} />
    </>
  );
};
