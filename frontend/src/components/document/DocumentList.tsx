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

import { FileExcelOutlined, SearchOutlined, PaperClipOutlined } from '@ant-design/icons';
import Highlighter from 'react-highlight-words';
import { message } from 'antd';
import { Document } from '../../types';
import { DocumentActions, BatchActions } from './DocumentActions';
import { documentsApi } from '../../api/documentsApi';

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

  const handleBatchExportClick = async () => {
    try {
      // 如果有選取項目，匯出選取的公文；否則匯出全部
      const documentIds = selectedRowKeys.length > 0
        ? selectedRowKeys.map(key => Number(key))
        : undefined;

      message.loading({ content: '正在匯出公文...', key: 'export' });

      await documentsApi.exportDocuments({ documentIds });

      message.success({ content: '匯出成功！', key: 'export' });
    } catch (error) {
      console.error('匯出失敗:', error);
      message.error({ content: '匯出失敗，請稍後再試', key: 'export' });
    }
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
      title: '發文形式',
      dataIndex: 'delivery_method',
      key: 'delivery_method',
      width: 85,
      align: 'center',
      filters: [
        { text: '電子', value: '電子' },
        { text: '紙本', value: '紙本' },
        { text: '電子+紙本', value: '電子+紙本' },
      ],
      onFilter: (value, record) => record.delivery_method === value,
      render: (method: string) => {
        const colorMap: Record<string, string> = {
          '電子': 'green',
          '紙本': 'orange',
          '電子+紙本': 'blue',
        };
        return <Tag color={colorMap[method] || 'default'}>{method || '電子'}</Tag>;
      },
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
      title: '公文字號',
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
              styles: { root: { maxWidth: 500 } }
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
      title: '收發單位',
      key: 'correspondent',
      width: 160,
      ellipsis: { showTitle: false },
      sorter: (a, b) => {
        // 收文顯示 sender，發文顯示 receiver
        const aValue = a.category === '收文' ? (a.sender || '') : (a.receiver || '');
        const bValue = b.category === '收文' ? (b.sender || '') : (b.receiver || '');
        return aValue.localeCompare(bValue, 'zh-TW');
      },
      sortDirections: ['descend', 'ascend'],
      filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters, close }) => (
        <div style={{ padding: 8 }} onKeyDown={(e) => e.stopPropagation()}>
          <Input
            ref={searchInput}
            placeholder="搜尋收發單位"
            value={selectedKeys[0]}
            onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
            onPressEnter={() => handleSearch(selectedKeys as string[], confirm, 'correspondent')}
            style={{ marginBottom: 8, display: 'block' }}
          />
          <Space>
            <Button
              type="primary"
              onClick={() => handleSearch(selectedKeys as string[], confirm, 'correspondent')}
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
            <Button type="link" size="small" onClick={() => close()}>
              關閉
            </Button>
          </Space>
        </div>
      ),
      filterIcon: (filtered: boolean) => (
        <SearchOutlined style={{ color: filtered ? '#1677ff' : undefined }} />
      ),
      onFilter: (value, record) => {
        // 收文搜尋 sender，發文搜尋 receiver
        const targetValue = record.category === '收文' ? record.sender : record.receiver;
        return targetValue
          ? targetValue.toString().toLowerCase().includes((value as string).toLowerCase())
          : false;
      },
      render: (_: any, record: Document) => {
        // 收文顯示 sender (發文機關)，發文顯示 receiver (受文機關)
        const rawValue = record.category === '收文' ? record.sender : record.receiver;
        const labelPrefix = record.category === '收文' ? '來文：' : '發至：';
        const labelColor = record.category === '收文' ? '#52c41a' : '#1890ff';

        // 解析機關名稱：提取括號內的名稱，處理多個機關用 | 分隔的情況
        // 格式: "CODE (NAME)" 或 "CODE (NAME) | CODE (NAME)"
        const extractAgencyName = (value: string | undefined): string => {
          if (!value) return '-';
          // 處理多個機關的情況
          const agencies = value.split(' | ').map(agency => {
            // 提取括號內的名稱
            const match = agency.match(/\(([^)]+)\)/);
            return match ? match[1] : agency; // 如果沒有括號，返回原值
          });
          return agencies.join('、');
        };

        const displayValue = extractAgencyName(rawValue);

        return (
          <Typography.Text
            ellipsis={{ tooltip: { title: displayValue, placement: 'topLeft' } }}
          >
            <span style={{ color: labelColor, fontWeight: 500, fontSize: '11px' }}>
              {labelPrefix}
            </span>
            {searchedColumn === 'correspondent' ? (
              <Highlighter
                highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
                searchWords={[searchText]}
                autoEscape
                textToHighlight={displayValue}
              />
            ) : displayValue}
          </Typography.Text>
        );
      },
    },
    {
      title: '承攬案件',
      dataIndex: 'contract_project_name',
      key: 'contract_project_name',
      width: 180,
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
    {
      title: '業務同仁',
      dataIndex: 'assigned_staff',
      key: 'assigned_staff',
      width: 150,
      render: (staff: Array<{ user_id: number; name: string; role: string }> | undefined) => {
        if (!staff || staff.length === 0) {
          return <Typography.Text type="secondary">-</Typography.Text>;
        }
        return (
          <Space size={[0, 4]} wrap>
            {staff.map((s, index) => (
              <Tag key={index} color="blue">
                {s.name}
                <span style={{ fontSize: '10px', color: '#999', marginLeft: 2 }}>
                  ({s.role})
                </span>
              </Tag>
            ))}
          </Space>
        );
      },
    },
    {
      title: '附件',
      dataIndex: 'has_attachment',
      key: 'has_attachment',
      width: 60,
      align: 'center',
      filters: [
        { text: '有附件', value: true },
        { text: '無附件', value: false },
      ],
      onFilter: (value, record) => record.has_attachment === value,
      render: (hasAttachment: boolean) => (
        hasAttachment ? (
          <Tag color="cyan" icon={<PaperClipOutlined />}>有</Tag>
        ) : (
          <Typography.Text type="secondary">-</Typography.Text>
        )
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
