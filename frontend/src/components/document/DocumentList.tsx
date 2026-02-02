/**
 * DocumentList 公文列表元件
 *
 * 重構版本：使用提取的 Hooks 和 Column 定義
 * - useAttachments: 附件管理邏輯
 * - documentColumns: 桌面版/手機版欄位定義
 *
 * @version 2.0.0 - 模組化重構
 * @date 2026-01-27
 */

import React, { useState, useRef, useCallback, useMemo } from 'react';
import { Table, Button, Space, Empty, Input, InputRef, App } from 'antd';
import type { TableProps } from 'antd';
import type {
  TablePaginationConfig,
  FilterValue,
  TableCurrentDataSource,
  SortOrder,
  SorterResult,
  ColumnType,
  FilterDropdownProps,
} from 'antd/es/table/interface';

import { FileExcelOutlined, SearchOutlined } from '@ant-design/icons';
import Highlighter from 'react-highlight-words';
import { Document } from '../../types';
import { BatchActions } from './DocumentActions';
import { documentsApi } from '../../api/documentsApi';
import { logger } from '../../utils/logger';
import { useResponsive } from '../../hooks';

// 提取的模組
import { useAttachments } from './hooks/useAttachments';
import { getMobileColumns, getDesktopColumns } from './columns';

// ============================================================================
// 型別定義
// ============================================================================

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

// ============================================================================
// 主元件
// ============================================================================

export const DocumentList: React.FC<DocumentListProps> = ({
  documents,
  loading,
  total,
  pagination,
  sortField: _sortField,
  sortOrder: _sortOrder,
  onTableChange,
  onEdit: _onEdit,
  onDelete: _onDelete,
  onView,
  onCopy: _onCopy,
  onExportPdf: _onExportPdf,
  onSend: _onSend,
  onArchive: _onArchive,
  onAddToCalendar: _onAddToCalendar,
  onExport,
  onBatchExport: _onBatchExport,
  onBatchDelete: _onBatchDelete,
  onBatchArchive: _onBatchArchive,
  onBatchCopy: _onBatchCopy,
  enableBatchOperations = false,
  isExporting = false,
  isAddingToCalendar: _isAddingToCalendar = false,
}) => {
  const { isMobile } = useResponsive();
  const { message } = App.useApp();

  // 批次操作狀態
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [batchLoading, _setBatchLoading] = useState(false);

  // 搜尋狀態
  const [searchText, setSearchText] = useState('');
  const [searchedColumn, setSearchedColumn] = useState('');
  const searchInput = useRef<InputRef>(null);

  // 使用提取的 Hook 管理附件
  const attachmentHandlers = useAttachments();

  // ============================================================================
  // 搜尋處理
  // ============================================================================

  const handleSearch = useCallback((
    selectedKeys: string[],
    confirm: FilterDropdownProps['confirm'],
    dataIndex: string,
  ) => {
    confirm();
    setSearchText(selectedKeys[0] || '');
    setSearchedColumn(dataIndex);
  }, []);

  const handleReset = useCallback((clearFilters: () => void) => {
    clearFilters();
    setSearchText('');
  }, []);

  // 取得搜尋欄位的 column 配置
  const getColumnSearchProps = useCallback((dataIndex: keyof Document): ColumnType<Document> => ({
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
          <Button type="link" size="small" onClick={() => close()}>
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
  }), [handleSearch, handleReset, searchedColumn, searchText]);

  // ============================================================================
  // 流水號計算
  // ============================================================================

  const getRowNumber = useCallback((index: number): number => {
    return (pagination.current - 1) * pagination.pageSize + index + 1;
  }, [pagination.current, pagination.pageSize]);

  // ============================================================================
  // 欄位定義
  // ============================================================================

  const columns = useMemo(() => {
    if (isMobile) {
      return getMobileColumns(getRowNumber);
    }
    return getDesktopColumns({
      getRowNumber,
      searchState: { searchText, searchedColumn },
      getColumnSearchProps,
      attachmentHandlers,
    });
  }, [isMobile, getRowNumber, searchText, searchedColumn, getColumnSearchProps, attachmentHandlers]);

  // ============================================================================
  // 批次操作處理
  // ============================================================================

  const handleBatchExportClick = useCallback(async () => {
    try {
      const documentIds = selectedRowKeys.length > 0
        ? selectedRowKeys.map(key => Number(key))
        : [];

      message.loading({ content: '正在匯出公文...', key: 'export' });
      await documentsApi.exportDocuments(documentIds.length > 0 ? { documentIds } : {});
      message.success({ content: '匯出成功！', key: 'export' });
    } catch (error) {
      logger.error('匯出失敗:', error);
      message.error({ content: '匯出失敗，請稍後再試', key: 'export' });
    }
  }, [selectedRowKeys, message]);

  const handleBatchDeleteClick = useCallback(() => {
    logger.debug('批次刪除按鈕已被點擊，但功能尚未實作。');
  }, []);

  const handleBatchArchiveClick = useCallback(() => {
    logger.debug('批次封存按鈕已被點擊，但功能尚未實作。');
  }, []);

  const handleBatchCopyClick = useCallback(() => {
    logger.debug('批次複製按鈕已被點擊，但功能尚未實作。');
  }, []);

  // ============================================================================
  // 導航處理
  // ============================================================================

  const handleRowClick = useCallback((record: Document) => {
    onView(record);
  }, [onView]);

  // ============================================================================
  // 資料處理
  // ============================================================================

  const safeDocuments = useMemo(() => {
    const docs = Array.isArray(documents) ? documents : [];
    logger.debug('=== DocumentList: 安全文件陣列 ===', {
      documentsCount: docs.length,
      total,
      pagination
    });
    return docs;
  }, [documents, total, pagination]);

  // ============================================================================
  // 表格配置
  // ============================================================================

  const rowSelection = useMemo(() => ({
    selectedRowKeys,
    onChange: (keys: React.Key[]) => setSelectedRowKeys(keys),
  }), [selectedRowKeys]);

  const tableProps: TableProps<Document> = useMemo(() => ({
    columns,
    dataSource: safeDocuments,
    rowKey: 'id',
    loading: loading || batchLoading,
    size: isMobile ? 'small' : 'middle',
    bordered: false,
    onRow: (record) => ({
      onClick: () => handleRowClick(record),
      style: { cursor: 'pointer' },
    }),
    pagination: {
      ...pagination,
      total,
      showSizeChanger: !isMobile,
      pageSizeOptions: ['10', '20', '50', '100'],
      showTotal: isMobile ? undefined : (totalNum, range) => `第 ${range[0]}-${range[1]} 筆，共 ${totalNum} 筆`,
      size: isMobile ? 'small' : 'default',
      showQuickJumper: !isMobile,
    },
    scroll: isMobile ? undefined : { x: 1050 },
    tableLayout: isMobile ? 'auto' : 'fixed',
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
    ...(enableBatchOperations && !isMobile && { rowSelection }),
    ...(onTableChange && { onChange: onTableChange }),
  }), [
    columns, safeDocuments, loading, batchLoading, isMobile, pagination, total,
    handleRowClick, enableBatchOperations, rowSelection, onTableChange
  ]);

  // ============================================================================
  // 渲染
  // ============================================================================

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

export default DocumentList;
