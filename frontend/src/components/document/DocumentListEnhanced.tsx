import React, { useState } from 'react';
import {
  Table,
  Button,
  Space,
  Typography,
  Tag,
  Empty,
  Tooltip,
  Dropdown,
  Menu,
  Switch,
  Input,
  Checkbox,
  Pagination,
  Spin,
} from 'antd';
import type {
  TablePaginationConfig,
  FilterValue,
  TableCurrentDataSource,
  SortOrder,
  SorterResult,
} from 'antd/es/table/interface';
import type { ColumnsType, ColumnType } from 'antd/es/table';

import {
  FileExcelOutlined,
  SortAscendingOutlined,
  FilterOutlined,
  SettingOutlined,
  SearchOutlined,
  PaperClipOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { Document } from '../../types';
import { BatchActions } from './DocumentActions';
import { DocumentCard } from './DocumentCard';
import { useResponsive } from '../../hooks/useResponsive';
import './DocumentCard.css';

const { Text } = Typography;

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
  onAddToCalendar?: (document: Document) => void;
  onExport?: (() => void) | undefined;
  onBatchExport?: (documents: Document[]) => void;
  onBatchDelete?: (documents: Document[]) => void;
  onBatchArchive?: (documents: Document[]) => void;
  onBatchCopy?: (documents: Document[]) => void;
  enableBatchOperations?: boolean;
  isExporting?: boolean;
  isAddingToCalendar?: boolean;
}

// 定義可顯示的欄位配置
interface ColumnConfig {
  key: string;
  title: string;
  visible: boolean;
  sortable: boolean;
  filterable: boolean;
  width?: number;
}

const defaultColumnConfigs: ColumnConfig[] = [
  { key: 'doc_number', title: '公文字號', visible: true, sortable: true, filterable: true, width: 165 },
  { key: 'subject', title: '主旨', visible: true, sortable: true, filterable: true, width: 320 },
  { key: 'doc_type', title: '類型', visible: true, sortable: true, filterable: true, width: 80 },
  { key: 'sender', title: '發文單位', visible: true, sortable: true, filterable: true, width: 130 },
  { key: 'receiver', title: '受文單位', visible: true, sortable: true, filterable: true, width: 130 },
  { key: 'contract_case', title: '承攬案件', visible: true, sortable: true, filterable: true, width: 160 },
  { key: 'doc_date', title: '公文日期', visible: true, sortable: true, filterable: false, width: 95 },
  { key: 'attachment_count', title: '附件', visible: true, sortable: true, filterable: false, width: 60 },
  { key: 'status', title: '狀態', visible: true, sortable: true, filterable: true, width: 80 },
  { key: 'created_at', title: '建立時間', visible: false, sortable: true, filterable: false, width: 100 },
  { key: 'updated_at', title: '更新時間', visible: false, sortable: true, filterable: false, width: 100 },
];

export const DocumentListEnhanced: React.FC<DocumentListProps> = ({
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
  onAddToCalendar: _onAddToCalendar, // 日曆功能已內建於 DocumentActions
  onExport,
  onBatchExport,
  onBatchDelete,
  onBatchArchive,
  onBatchCopy,
  enableBatchOperations = true,
  isExporting = false,
  isAddingToCalendar = false,
}) => {
  const { isMobile, responsiveValue } = useResponsive();
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [columnConfigs, setColumnConfigs] = useState<ColumnConfig[]>(defaultColumnConfigs);

  // 格式化日期
  const formatDate = (dateString: string | null | undefined): string => {
    if (!dateString) return '-';
    try {
      return new Date(dateString).toLocaleDateString('zh-TW');
    } catch {
      return dateString;
    }
  };

  // 格式化狀態標籤
  const formatStatusTag = (status: string | null | undefined) => {
    if (!status) return <Tag color="default">未設定</Tag>;

    const statusColors: Record<string, string> = {
      '收文完成': 'green',
      '使用者確認': 'blue',
      '收文異常': 'red',
      '待處理': 'orange',
      '已辦畢': 'green',
      '處理中': 'processing',
    };

    return <Tag color={statusColors[status] || 'default'}>{status}</Tag>;
  };

  // 處理欄位顯示切換
  const handleColumnVisibilityChange = (columnKey: string, visible: boolean) => {
    setColumnConfigs(prev =>
      prev.map(config =>
        config.key === columnKey ? { ...config, visible } : config
      )
    );
  };

  // 手機版簡化欄位
  const generateMobileColumns = (): ColumnsType<Document> => [
    {
      title: '公文資訊',
      dataIndex: 'subject',
      key: 'subject',
      render: (_: string, record: Document) => (
        <Space direction="vertical" size={0}>
          <strong style={{ fontSize: '13px' }}>{record.subject || '-'}</strong>
          <small style={{ color: '#666' }}>
            {record.doc_number || '-'}
          </small>
          {record.status && formatStatusTag(record.status)}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 60,
      render: (_: any, record: Document) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          size="small"
          onClick={() => onView(record)}
        />
      ),
    },
  ];

  // 生成表格欄位配置
  const generateColumns = (): ColumnsType<Document> => {
    // 手機版使用簡化欄位
    if (isMobile) {
      return generateMobileColumns();
    }

    const visibleConfigs = columnConfigs.filter(config => config.visible);
    const columns: ColumnsType<Document> = [];

    visibleConfigs.forEach(config => {
      let column: ColumnType<Document> = {
        title: (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span>{config.title}</span>
            {config.sortable && (
              <Tooltip title="可排序">
                <SortAscendingOutlined style={{ fontSize: '12px', color: '#999' }} />
              </Tooltip>
            )}
            {config.filterable && (
              <Tooltip title="可篩選">
                <FilterOutlined style={{ fontSize: '12px', color: '#999' }} />
              </Tooltip>
            )}
          </div>
        ),
        dataIndex: config.key,
        key: config.key,
        width: config.width,
        ellipsis: true,
        sorter: config.sortable,
        sortOrder: sortField === config.key ? (sortOrder ?? null) : null,
      };

      // 特殊欄位處理
      switch (config.key) {
        case 'doc_number':
          column.render = (text: string) => (
            <Text copyable style={{ fontSize: '13px', fontFamily: 'monospace' }}>
              {text || '-'}
            </Text>
          );
          break;

        case 'subject':
          column.render = (text: string) => (
            <Tooltip title={text}>
              <div style={{
                maxWidth: '280px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap'
              }}>
                {text || '-'}
              </div>
            </Tooltip>
          );
          break;

        case 'doc_type':
          column.render = (text: string) => (
            <Tag color="blue">{text || '-'}</Tag>
          );
          break;

        case 'sender':
        case 'receiver':
          column.render = (text: string) => (
            <Tooltip title={text}>
              <div style={{
                maxWidth: '140px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap'
              }}>
                {text || '-'}
              </div>
            </Tooltip>
          );
          break;

        case 'contract_case':
          column.render = (text: string) => (
            <Tooltip title={text}>
              <div style={{
                maxWidth: '180px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                color: text ? '#1890ff' : undefined
              }}>
                {text || '-'}
              </div>
            </Tooltip>
          );
          break;

        case 'doc_date':
        case 'created_at':
        case 'updated_at':
          column.render = (text: string) => (
            <span style={{ fontSize: '13px' }}>
              {formatDate(text)}
            </span>
          );
          break;

        case 'status':
          column.render = (text: string) => formatStatusTag(text);
          break;

        case 'attachment_count':
          column.render = (count: number) => (
            count && count > 0 ? (
              <Tooltip title={`${count} 個附件`}>
                <Tag icon={<PaperClipOutlined />} color="cyan">
                  {count}
                </Tag>
              </Tooltip>
            ) : (
              <span style={{ color: '#ccc' }}>-</span>
            )
          );
          break;
      }

      // 增加欄位篩選功能
      if (config.filterable) {
        column.filterDropdown = ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
          <div style={{ padding: 8 }}>
            <Input
              placeholder={`搜尋${config.title}`}
              value={selectedKeys[0]}
              onChange={e => setSelectedKeys(e.target.value ? [e.target.value] : [])}
              onPressEnter={() => confirm()}
              style={{ width: 188, marginBottom: 8, display: 'block' }}
            />
            <Space>
              <Button
                type="primary"
                onClick={() => confirm()}
                icon={<SearchOutlined />}
                size="small"
                style={{ width: 90 }}
              >
                搜尋
              </Button>
              <Button
                onClick={() => {
                  if (clearFilters) {
                    clearFilters();
                  }
                }}
                size="small"
                style={{ width: 90 }}
              >
                重設
              </Button>
            </Space>
          </div>
        );
        column.filterIcon = (filtered: boolean) => (
          <SearchOutlined style={{ color: filtered ? '#1890ff' : undefined }} />
        );
        column.onFilter = (value, record) => {
          const fieldValue = record[config.key as keyof Document];
          return String(fieldValue || '').toLowerCase().includes(String(value).toLowerCase());
        };
      }

      columns.push(column);
    });

    // 操作欄位已移除 - 用戶點擊行進入詳情頁後，在頂部功能鈕進行操作
    // 此設計可讓列表頁資訊最大化

    return columns;
  };

  // 欄位配置選單
  const columnConfigMenu = (
    <Menu>
      <Menu.ItemGroup title="顯示欄位">
        {columnConfigs.map(config => (
          <Menu.Item key={config.key} style={{ padding: '4px 12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span>{config.title}</span>
              <Switch
                size="small"
                checked={config.visible}
                onChange={(checked) => handleColumnVisibilityChange(config.key, checked)}
                style={{ marginLeft: 8 }}
              />
            </div>
          </Menu.Item>
        ))}
      </Menu.ItemGroup>
      <Menu.Divider />
      <Menu.Item key="reset">
        <Button
          type="link"
          size="small"
          onClick={() => setColumnConfigs(defaultColumnConfigs)}
          style={{ padding: 0 }}
        >
          重設為預設值
        </Button>
      </Menu.Item>
    </Menu>
  );

  const rowSelection = enableBatchOperations ? {
    selectedRowKeys,
    onChange: (selectedRowKeys: React.Key[]) => {
      setSelectedRowKeys(selectedRowKeys);
    },
    onSelectAll: (selected: boolean, _selectedRows: Document[], _changeRows: Document[]) => {
      if (selected) {
        const newSelectedKeys = documents.map(doc => doc.id);
        setSelectedRowKeys(newSelectedKeys);
      } else {
        setSelectedRowKeys([]);
      }
    },
  } : undefined;

  const selectedDocuments = documents.filter(doc => selectedRowKeys.includes(doc.id));

  return (
    <div>
      {/* 表格工具列 */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: isMobile ? 12 : 16,
        padding: isMobile ? '8px 12px' : '12px 16px',
        backgroundColor: '#fafafa',
        borderRadius: '6px',
        flexWrap: 'wrap',
        gap: 8
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? 8 : 16 }}>
          <Text style={{ fontSize: isMobile ? '13px' : '14px' }}>
            共 <Text strong>{total}</Text> 筆
            {selectedRowKeys.length > 0 && (
              <span style={{ marginLeft: 4 }}>
                (選 <Text strong style={{ color: '#1890ff' }}>{selectedRowKeys.length}</Text>)
              </span>
            )}
          </Text>

          {selectedRowKeys.length > 0 && enableBatchOperations && !isMobile && (
            <BatchActions
              selectedCount={selectedRowKeys.length}
              onExportSelected={() => onBatchExport?.(selectedDocuments)}
              onDeleteSelected={() => onBatchDelete?.(selectedDocuments)}
              onArchiveSelected={() => onBatchArchive?.(selectedDocuments)}
              onCopySelected={() => onBatchCopy?.(selectedDocuments)}
              onClearSelection={() => setSelectedRowKeys([])}
            />
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {onExport && (
            <Tooltip title="匯出Excel">
              <Button
                icon={<FileExcelOutlined />}
                onClick={onExport}
                loading={isExporting}
                size={isMobile ? 'small' : 'middle'}
              >
                {isMobile ? '' : '匯出'}
              </Button>
            </Tooltip>
          )}

          {!isMobile && (
            <Dropdown overlay={columnConfigMenu} trigger={['click']} placement="bottomRight">
              <Tooltip title="欄位設定">
                <Button icon={<SettingOutlined />}>
                  欄位
                </Button>
              </Tooltip>
            </Dropdown>
          )}
        </div>
      </div>

      {/* 手機版：卡片列表 */}
      {isMobile ? (
        <Spin spinning={loading}>
          <div className="document-card-list">
            {documents.length > 0 ? (
              <>
                {documents.map((doc) => (
                  <DocumentCard
                    key={doc.id}
                    document={doc}
                    onClick={onView}
                  />
                ))}
                <div className="document-card-pagination">
                  <Pagination
                    current={pagination.current}
                    pageSize={pagination.pageSize}
                    total={total}
                    size="small"
                    simple
                    onChange={(page, pageSize) => {
                      if (onTableChange) {
                        onTableChange(
                          { current: page, pageSize },
                          {},
                          {} as any,
                          { currentDataSource: documents, action: 'paginate' }
                        );
                      }
                    }}
                  />
                </div>
              </>
            ) : (
              <div className="document-card-list-empty">
                <Empty
                  description="暫無資料"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              </div>
            )}
          </div>
        </Spin>
      ) : (
        /* 桌面版：表格 */
        <Table<Document>
          columns={generateColumns()}
          dataSource={documents}
          rowKey="id"
          loading={loading}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) =>
              `第 ${range[0]}-${range[1]} 筆，共 ${total} 筆`,
            pageSizeOptions: ['10', '20', '50', '100'],
            size: 'default',
          }}
          rowSelection={rowSelection}
          {...(onTableChange && { onChange: onTableChange })}
          scroll={{ x: 1200, y: 600 }}
          size="small"
          locale={{
            emptyText: (
              <Empty
                description="暫無資料"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )
          }}
          style={{
            backgroundColor: '#fff',
            borderRadius: '6px',
            overflow: 'hidden'
          }}
          className="enhanced-document-table"
          onRow={(record) => ({
            onClick: () => onView(record),
            style: { cursor: 'pointer' }
          })}
        />
      )}

      {/* 表格功能說明 - 僅桌面版顯示 */}
      {!isMobile && (
        <div style={{
          marginTop: 16,
          padding: '8px 16px',
          backgroundColor: '#f6f8fa',
          borderRadius: '4px',
          border: '1px solid #e1e8ed'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontSize: '12px', color: '#666' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <SortAscendingOutlined />
              <span>點擊欄位標題排序</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <SearchOutlined />
              <span>點擊篩選圖示搜尋</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <SettingOutlined />
              <span>自訂顯示欄位</span>
            </div>
            {enableBatchOperations && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <Checkbox />
                <span>批次操作</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// 加入 CSS 樣式
const styles = `
.enhanced-document-table .ant-table-thead > tr > th {
  background-color: #fafafa;
  font-weight: 600;
}

.enhanced-document-table .ant-table-tbody > tr:hover > td {
  background-color: #f5f9ff;
}

.enhanced-document-table .ant-table-tbody > tr.ant-table-row-selected > td {
  background-color: #e6f7ff;
}

.enhanced-document-table .ant-table-filter-trigger-container {
  padding: 0 4px;
}
`;

// 動態注入樣式
if (typeof document !== 'undefined') {
  const styleSheet = document.createElement("style");
  styleSheet.innerText = styles;
  document.head.appendChild(styleSheet);
}

export default DocumentListEnhanced;