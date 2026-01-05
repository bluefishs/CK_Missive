import React, { useState, useMemo, useRef } from 'react';
import { Table, Button, Space, Typography, Tag, Empty, TableProps, Input, InputRef } from 'antd';
import type {
  TablePaginationConfig,
  FilterValue,
  TableCurrentDataSource,
  SortOrder,
  SorterResult,
  ColumnType,
  FilterDropdownProps,
} from 'antd/es/table/interface';
import type { ColumnsType } from 'antd/es/table';

import { FileExcelOutlined, SearchOutlined } from '@ant-design/icons';
import Highlighter from 'react-highlight-words';
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
  const [searchText, setSearchText] = useState('');
  const [searchedColumn, setSearchedColumn] = useState('');
  const searchInput = useRef<InputRef>(null);

  // Debug logging
  console.log('=== DocumentList: 收到的 props ===', {
    documentsCount: documents?.length || 0,
    documents: documents,
    loading,
    total,
    pagination
  });

  // 搜尋處理函數
  const handleSearch = (
    selectedKeys: string[],
    confirm: FilterDropdownProps['confirm'],
    dataIndex: string,
  ) => {
    confirm();
    setSearchText(selectedKeys[0]);
    setSearchedColumn(dataIndex);
  };

  const handleReset = (clearFilters: () => void) => {
    clearFilters();
    setSearchText('');
  };

  // 取得搜尋欄位的 column 配置
  const getColumnSearchProps = (dataIndex: keyof Document): ColumnType<Document> => ({
    filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters, close }) => (
      <div style={{ padding: 8 }} onKeyDown={(e) => e.stopPropagation()}>
        <Input
          ref={searchInput}
          placeholder={`搜尋 ${dataIndex}`}
          value={selectedKeys[0]}
          onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
          onPressEnter={() => handleSearch(selectedKeys as string[], confirm, dataIndex as string)}
          style={{ marginBottom: 8, display: 'block' }}
        />
        <Space>
          <Button
            type="primary"
            onClick={() => handleSearch(selectedKeys as string[], confirm, dataIndex as string)}
            icon={<SearchOutlined />}
            size="small"
            style={{ width: 90 }}
          >
            搜尋
          </Button>
          <Button
            onClick={() => clearFilters && handleReset(clearFilters)}
            size="small"
            style={{ width: 90 }}
          >
            重置
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => close()}
          >
            關閉
          </Button>
        </Space>
      </div>
    ),
    filterIcon: (filtered: boolean) => (
      <SearchOutlined style={{ color: filtered ? '#1677ff' : undefined }} />
    ),
    onFilter: (value, record) =>
      record[dataIndex]
        ? record[dataIndex]!.toString().toLowerCase().includes((value as string).toLowerCase())
        : false,
    filterDropdownProps: {
      onOpenChange(open) {
        if (open) {
          setTimeout(() => searchInput.current?.select(), 100);
        }
      },
    },
    render: (text) =>
      searchedColumn === dataIndex ? (
        <Highlighter
          highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
          searchWords={[searchText]}
          autoEscape
          textToHighlight={text ? text.toString() : ''}
        />
      ) : (
        text
      ),
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

  // 狀態顏色映射
  const statusColorMap: Record<string, string> = {
    '待處理': 'orange',
    '處理中': 'blue',
    '已完成': 'green',
    '已歸檔': 'default',
    '使用者確認': 'cyan',
  };

  // 從資料中動態產生狀態篩選選項
  const statusFilters = useMemo(() => {
    const statusSet = new Set(documents.map(d => d.status).filter(Boolean));
    return Array.from(statusSet).map(status => ({ text: status, value: status }));
  }, [documents]);

  // 從資料中動態產生類型篩選選項
  const docTypeFilters = useMemo(() => {
    const typeSet = new Set(documents.map(d => d.doc_type).filter(Boolean));
    return Array.from(typeSet).map(type => ({ text: type, value: type }));
  }, [documents]);

  const columns: ColumnsType<Document> = [
    {
      title: '序號',
      dataIndex: 'id',
      key: 'id',
      width: 70,
      align: 'center',
      sorter: (a, b) => a.id - b.id,
      sortDirections: ['descend', 'ascend'],
      defaultSortOrder: 'descend',
      render: (id: number) => (
        <Typography.Text type="secondary">{id}</Typography.Text>
      ),
    },
    {
      title: '類型',
      dataIndex: 'doc_type',
      key: 'doc_type',
      width: 90,
      align: 'center',
      sorter: (a, b) => (a.doc_type || '').localeCompare(b.doc_type || '', 'zh-TW'),
      sortDirections: ['descend', 'ascend'],
      filters: docTypeFilters.length > 0 ? docTypeFilters : [
        { text: '函', value: '函' },
        { text: '公告', value: '公告' },
        { text: '簽', value: '簽' },
        { text: '書函', value: '書函' },
        { text: '開會通知單', value: '開會通知單' },
        { text: '令', value: '令' },
      ],
      onFilter: (value, record) => record.doc_type === value,
      filterSearch: true,
      render: (type: string) => <Tag color="blue">{type || '-'}</Tag>,
    },
    {
      title: '文號',
      dataIndex: 'doc_number',
      key: 'doc_number',
      width: 180,
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
          {searchedColumn === 'doc_number' ? (
            <Highlighter
              highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
              searchWords={[searchText]}
              autoEscape
              textToHighlight={text || ''}
            />
          ) : text}
        </Typography.Text>
      ),
    },
    {
      title: '日期',
      dataIndex: 'doc_date',
      key: 'doc_date',
      width: 100,
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
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 95,
      align: 'center',
      sorter: (a, b) => (a.status || '').localeCompare(b.status || '', 'zh-TW'),
      sortDirections: ['descend', 'ascend'],
      filters: statusFilters.length > 0 ? statusFilters : [
        { text: '待處理', value: '待處理' },
        { text: '處理中', value: '處理中' },
        { text: '已完成', value: '已完成' },
        { text: '使用者確認', value: '使用者確認' },
      ],
      onFilter: (value, record) => record.status === value,
      filterSearch: true,
      render: (status: string) => {
        const color = statusColorMap[status] || 'default';
        return <Tag color={color}>{status || '-'}</Tag>;
      },
    },
    {
      title: '主旨',
      dataIndex: 'subject',
      key: 'subject',
      width: 280,
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
              overlayStyle: { maxWidth: 500 }
            }
          }}
        >
          {searchedColumn === 'subject' ? (
            <Highlighter
              highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
              searchWords={[searchText]}
              autoEscape
              textToHighlight={text || ''}
            />
          ) : text}
        </Typography.Paragraph>
      ),
    },
    {
      title: '發文單位',
      dataIndex: 'sender',
      key: 'sender',
      width: 140,
      ellipsis: { showTitle: false },
      sorter: (a, b) => (a.sender || '').localeCompare(b.sender || '', 'zh-TW'),
      sortDirections: ['descend', 'ascend'],
      ...getColumnSearchProps('sender'),
      render: (sender: string) => (
        <Typography.Text
          type="secondary"
          ellipsis={{ tooltip: { title: sender, placement: 'topLeft' } }}
        >
          {searchedColumn === 'sender' ? (
            <Highlighter
              highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
              searchWords={[searchText]}
              autoEscape
              textToHighlight={sender || ''}
            />
          ) : sender}
        </Typography.Text>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      align: 'center',
      fixed: 'right',
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
          mode="dropdown"
          size="small"
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
    size: 'middle',
    bordered: false,
    onRow: (record) => ({
      onClick: () => onEdit(record),
      style: { cursor: 'pointer' },
    }),
    pagination: {
      ...pagination,
      total,
      showSizeChanger: true,
      pageSizeOptions: ['10', '20', '50', '100'],
      showTotal: (totalNum, range) => `第 ${range[0]}-${range[1]} 筆，共 ${totalNum} 筆`,
      size: 'default',
    },
    scroll: { x: 1035 }, // 總欄寬: 70+90+180+100+95+280+140+80 = 1035
    tableLayout: 'fixed',
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
