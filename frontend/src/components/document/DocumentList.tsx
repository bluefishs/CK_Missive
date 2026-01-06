import React, { useState, useRef } from 'react';
import { Table, Button, Space, Typography, Tag, Empty, TableProps, Input, InputRef, Popover, List, Spin, App } from 'antd';
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

import { FileExcelOutlined, SearchOutlined, PaperClipOutlined, DownloadOutlined, EyeOutlined, FileOutlined } from '@ant-design/icons';
import Highlighter from 'react-highlight-words';
import { Document } from '../../types';
import { DocumentActions, BatchActions } from './DocumentActions';
import { documentsApi, DocumentAttachment } from '../../api/documentsApi';

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
  sortField: _sortField,
  sortOrder: _sortOrder,
  onTableChange,
  onEdit,
  onDelete,
  onView,
  onCopy,
  onExportPdf,
  onSend,
  onArchive,
  onAddToCalendar: _onAddToCalendar,
  onExport,
  onBatchExport: _onBatchExport,
  onBatchDelete: _onBatchDelete,
  onBatchArchive: _onBatchArchive,
  onBatchCopy: _onBatchCopy,
  enableBatchOperations = false,
  isExporting = false,
  isAddingToCalendar = false,
}) => {
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [batchLoading, _setBatchLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [searchedColumn, setSearchedColumn] = useState('');
  const searchInput = useRef<InputRef>(null);
  const { message } = App.useApp();

  // 附件管理狀態
  const [attachmentCache, setAttachmentCache] = useState<Record<number, DocumentAttachment[]>>({});
  const [loadingAttachments, setLoadingAttachments] = useState<Record<number, boolean>>({});

  // 載入附件列表
  const loadAttachments = async (documentId: number) => {
    if (attachmentCache[documentId]) {
      return; // 已載入過，直接使用快取
    }

    setLoadingAttachments(prev => ({ ...prev, [documentId]: true }));
    try {
      const attachments = await documentsApi.getDocumentAttachments(documentId);
      setAttachmentCache(prev => ({ ...prev, [documentId]: attachments }));
    } catch (error) {
      console.error('載入附件失敗:', error);
      message.error('載入附件列表失敗');
    } finally {
      setLoadingAttachments(prev => ({ ...prev, [documentId]: false }));
    }
  };

  // 下載附件
  const handleDownloadAttachment = async (attachment: DocumentAttachment, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await documentsApi.downloadAttachment(attachment.id, attachment.filename);
      message.success(`下載 ${attachment.filename} 成功`);
    } catch (error) {
      message.error(`下載 ${attachment.filename} 失敗`);
    }
  };

  // 預覽附件 (POST-only 資安機制)
  const handlePreviewAttachment = async (attachment: DocumentAttachment, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const blob = await documentsApi.getAttachmentBlob(attachment.id);
      const previewUrl = window.URL.createObjectURL(blob);
      window.open(previewUrl, '_blank');
      // 延遲釋放 URL，讓新視窗有時間載入
      setTimeout(() => window.URL.revokeObjectURL(previewUrl), 10000);
    } catch (error) {
      message.error(`預覽 ${attachment.filename} 失敗`);
    }
  };

  // 格式化檔案大小
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // 判斷是否可預覽的檔案類型
  const isPreviewable = (contentType?: string): boolean => {
    if (!contentType) return false;
    return contentType.startsWith('image/') ||
           contentType === 'application/pdf' ||
           contentType.startsWith('text/');
  };

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
    setSearchText(selectedKeys[0] || '');
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
        : [];

      message.loading({ content: '正在匯出公文...', key: 'export' });

      await documentsApi.exportDocuments(documentIds.length > 0 ? { documentIds } : {});

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


  // 計算流水號（基於分頁位置，非資料庫 ID）
  const getRowNumber = (index: number): number => {
    return (pagination.current - 1) * pagination.pageSize + index + 1;
  };

  // 欄位順序：序號、發文形式、收發單位、公文字號、公文日期、主旨、附件、承攬案件、操作
  // 預設排序：公文日期降冪（最新日期在最上方，由後端控制）
  // 序號為流水號（依排序後的順序計算），非資料庫 ID
  // 移除：類型、狀態、業務同仁
  const columns: ColumnsType<Document> = [
    {
      title: '序號',
      key: 'rowNumber',
      width: 70,
      align: 'center',
      render: (_: any, __: Document, index: number) => (
        <Typography.Text type="secondary">{getRowNumber(index)}</Typography.Text>
      ),
    },
    {
      title: '發文形式',
      dataIndex: 'delivery_method',
      key: 'delivery_method',
      width: 95,
      align: 'center',
      filters: [
        { text: '電子交換', value: '電子交換' },
        { text: '紙本郵寄', value: '紙本郵寄' },
        { text: '電子+紙本', value: '電子+紙本' },
      ],
      onFilter: (value, record) => record.delivery_method === value,
      render: (method: string) => {
        const colorMap: Record<string, string> = {
          '電子交換': 'green',
          '紙本郵寄': 'orange',
          '電子+紙本': 'blue',
        };
        return <Tag color={colorMap[method] || 'default'}>{method || '電子交換'}</Tag>;
      },
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
      title: '公文日期',
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
      title: '附件',
      dataIndex: 'has_attachment',
      key: 'has_attachment',
      width: 70,
      align: 'center',
      filters: [
        { text: '有附件', value: true },
        { text: '無附件', value: false },
      ],
      onFilter: (value, record) => record.has_attachment === value,
      render: (hasAttachment: boolean, record: Document) => {
        if (!hasAttachment) {
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
            title={`附件列表 (${attachments.length > 0 ? attachments.length + ' 個' : '載入中...'})`}
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
              查看
            </Tag>
          </Popover>
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
    scroll: { x: 1215 }, // 總欄寬: 70+95+160+180+100+280+70+180+80 = 1215
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
