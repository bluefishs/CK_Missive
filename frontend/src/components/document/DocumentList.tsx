import React, { useState, useEffect } from 'react';
import { Table, Button, Space, Typography, Tag, message, Empty, TableProps } from 'antd';
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
    getColumnConfig('id', '流水號', {
      render: (id: number) => (
        <Typography.Text strong style={{ color: '#666' }}>
          {id}
        </Typography.Text>
      ),
    }),
    getColumnConfig('doc_type', '類型', {
      render: (type: string) => <Tag color="blue">{type || '未分類'}</Tag>,
    }),
    getColumnConfig('doc_number', '文號', {
      render: (text: string) => (
        <Typography.Text strong style={{ color: '#1890ff' }}>
          {text}
        </Typography.Text>
      ),
    }),
    getColumnConfig('doc_date', '發文日期', {
      render: (date: string) =>
        date
          ? new Date(date).toLocaleDateString('zh-TW', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })
          : '無日期',
    }),
    getColumnConfig('category', '類別', {
      render: (category: string) => <Tag color="green">{category || '未分類'}</Tag>,
    }),
    getColumnConfig('subject', '主旨', {
      width: 300,
      render: (text: string, record: Document) => (
        <Typography.Text
          strong
          ellipsis={{ tooltip: text }}
          style={{ cursor: 'pointer' }}
          onClick={() => onView(record)}
        >
          {text}
        </Typography.Text>
      ),
    }),
    getColumnConfig('sender', '發文單位', {
      render: (sender: string) => (
        <Typography.Text style={{ color: '#888' }}>{sender}</Typography.Text>
      ),
    }),
    {
      title: '操作',
      key: 'action',
      fixed: 'right',
      width: 180,
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
          onAddToCalendar={onAddToCalendar} // Pass the prop
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
    pagination: {
      ...pagination,
      total,
      showSizeChanger: true,
      showTotal: (totalNum, range) => `顯示 ${range[0]}-${range[1]} 筆，共 ${totalNum} 筆`,
    },
    scroll: { x: 1500 },
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
