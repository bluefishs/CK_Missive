import React, { useState, useEffect } from 'react';
import { Tabs, Badge, Typography, Space } from 'antd';
import {
  InboxOutlined,
  SendOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons';
import { DocumentList } from './DocumentList';
import { Document, DocumentFilter } from '../../types';
import { documentsApi } from '../../api/documentsApi';
import type {
  TablePaginationConfig,
  SorterResult,
  TableCurrentDataSource,
  FilterValue,
  SortOrder,
} from 'antd/es/table/interface';
import { logger } from '../../utils/logger';
import { useResponsive } from '../../hooks';

const { Title } = Typography;

interface DocumentTabsProps {
  documents: Document[];
  loading?: boolean;
  filters: DocumentFilter & { page: number; limit: number };
  total: number;
  onEdit: (document: Document) => void;
  onDelete: (document: Document) => void;
  onView: (document: Document) => void;
  onExport?: () => void;
  onTableChange?: (
    pagination: TablePaginationConfig,
    filters: Record<string, FilterValue | null>,
    sorter: SorterResult<Document> | SorterResult<Document>[],
    extra: TableCurrentDataSource<Document>
  ) => void;
  onFiltersChange?: (filters: DocumentFilter) => void;
  isExporting?: boolean;
  onAddToCalendar?: (document: Document) => void;
  isAddingToCalendar?: boolean;
  totalAll?: number;
  totalReceived?: number;
  totalSent?: number;
}

export const DocumentTabs: React.FC<DocumentTabsProps> = ({
  documents,
  loading = false,
  filters,
  total,
  onEdit,
  onDelete,
  onView,
  onExport,
  onTableChange,
  onFiltersChange,
  isExporting = false,
  onAddToCalendar,
  isAddingToCalendar,
  totalAll,
  totalReceived,
  totalSent,
}) => {
  // RWD 響應式
  const { isMobile } = useResponsive();

  // Set active tab based on current category filter
  const [activeTab, setActiveTab] = useState(() => {
    return filters.category === 'receive' ? 'received' :
           filters.category === 'send' ? 'sent' : 'all';
  });
  const [sortField, setSortField] = useState<string>('');
  const [sortOrder, setSortOrder] = useState<SortOrder>(null);
  const [filteredStats, setFilteredStats] = useState<{total: number; receive: number; send: number} | null>(null);
  const [isLoadingStats, setIsLoadingStats] = useState(false);

  // Update active tab when filters change
  React.useEffect(() => {
    const newTab = filters.category === 'receive' ? 'received' :
                   filters.category === 'send' ? 'sent' : 'all';
    setActiveTab(newTab);
  }, [filters.category]);

  // 當篩選條件變更時，重新取得統計數據
  useEffect(() => {
    const fetchFilteredStats = async () => {
      setIsLoadingStats(true);
      try {
        // 使用新的篩選統計 API
        // 移除 category 以便取得全部/收文/發文的分類統計
        const { category: _, page: __, limit: ___, ...filterParams } = filters;

        const stats = await documentsApi.getFilteredStatistics(filterParams);
        logger.debug('=== 篩選統計數據 ===', stats, '篩選條件:', filterParams);

        if (stats.success) {
          setFilteredStats({
            total: stats.total,
            receive: stats.receive_count,
            send: stats.send_count,
          });
        }
      } catch (error) {
        logger.error('取得篩選統計失敗:', error);
        // 降級：保留現有統計資料，不清空也不用 total 覆蓋
        // 避免觸發不必要的 re-render
      } finally {
        setIsLoadingStats(false);
      }
    };

    fetchFilteredStats();
  }, [
    filters.search,
    filters.keyword,
    filters.doc_type,
    filters.year,
    filters.sender,
    filters.receiver,
    filters.delivery_method,
    filters.doc_date_from,
    filters.doc_date_to,
    filters.contract_case,
    // 移除 total 依賴：total 變化會觸發無限迴圈
    // (fetchFilteredStats → setFilteredStats → re-render → total 變化 → 再次觸發)
  ]);

  // Handle tab changes by updating filters
  const handleTabChange = (tabKey: string) => {
    if (onFiltersChange) {
      let newFilters: DocumentFilter;

      switch (tabKey) {
        case 'all':
          // eslint-disable-next-line @typescript-eslint/no-unused-vars
          const { category: _, ...restFilters } = filters;
          newFilters = restFilters;
          break;
        case 'received':
          newFilters = { ...filters, category: 'receive' };
          break;
        case 'sent':
          newFilters = { ...filters, category: 'send' };
          break;
        default:
          newFilters = { ...filters };
      }

      onFiltersChange(newFilters);
    }
    setActiveTab(tabKey);
  };

  const handleTableChange = (
    pagination: TablePaginationConfig,
    tableFilters: Record<string, FilterValue | null>,
    sorter: SorterResult<Document> | SorterResult<Document>[],
    extra: TableCurrentDataSource<Document>
  ) => {
    if (extra.action === 'sort') {
      const singleSorter = Array.isArray(sorter) ? sorter[0] : sorter;
      if (singleSorter && singleSorter.field && singleSorter.order) {
        setSortField(singleSorter.field as string);
        setSortOrder(singleSorter.order);
      } else {
        setSortField('');
        setSortOrder(null);
      }
    }

    if (onTableChange) {
      onTableChange(pagination, tableFilters, sorter, extra);
    }
  };

  // 使用篩選後的統計數據顯示 Tab 標籤
  const effectiveStats = {
    total: filteredStats?.total ?? (totalAll || total || documents.length),
    received: filteredStats?.receive ?? (totalReceived || 0),
    sent: filteredStats?.send ?? (totalSent || 0),
  };

  logger.debug('=== 有效統計數據 (篩選後) ===', effectiveStats, isLoadingStats ? '(載入中...)' : '');
  const tabItems = [
    {
      key: 'all',
      label: (
        <Space size={isMobile ? 4 : 8}>
          <UnorderedListOutlined />
          {!isMobile && (
            <Title level={5} style={{ margin: 0 }}>
              全部
            </Title>
          )}
          <Badge count={effectiveStats.total} showZero overflowCount={9999} color="blue" />
        </Space>
      ),
      children: (
        <DocumentList
          documents={documents}
          loading={loading}
          total={total}
          pagination={{ current: filters.page, pageSize: filters.limit }}
          sortField={sortField}
          sortOrder={sortOrder}
          onTableChange={handleTableChange}
          onEdit={onEdit}
          onDelete={onDelete}
          onView={onView}
          {...(onExport && { onExport })}
          isExporting={isExporting}
          {...(onAddToCalendar && { onAddToCalendar })}
          {...(isAddingToCalendar !== undefined && { isAddingToCalendar })}
          enableBatchOperations
        />
      ),
    },
    {
      key: 'received',
      label: (
        <Space size={isMobile ? 4 : 8}>
          <InboxOutlined />
          {!isMobile && (
            <Title level={5} style={{ margin: 0 }}>
              收文
            </Title>
          )}
          <Badge count={effectiveStats.received} showZero overflowCount={9999} color="green" />
        </Space>
      ),
      children: (
        <DocumentList
          documents={documents}
          loading={loading}
          total={total}
          pagination={{ current: filters.page, pageSize: filters.limit }}
          sortField={sortField}
          sortOrder={sortOrder}
          onEdit={onEdit}
          onDelete={onDelete}
          onView={onView}
          onTableChange={handleTableChange}
          {...(onExport && { onExport })}
          isExporting={isExporting}
          {...(onAddToCalendar && { onAddToCalendar })}
          {...(isAddingToCalendar !== undefined && { isAddingToCalendar })}
          enableBatchOperations
        />
      ),
    },
    {
      key: 'sent',
      label: (
        <Space size={isMobile ? 4 : 8}>
          <SendOutlined />
          {!isMobile && (
            <Title level={5} style={{ margin: 0 }}>
              發文
            </Title>
          )}
          <Badge count={effectiveStats.sent} showZero overflowCount={9999} color="red" />
        </Space>
      ),
      children: (
        <DocumentList
          documents={documents}
          loading={loading}
          total={total}
          pagination={{ current: filters.page, pageSize: filters.limit }}
          sortField={sortField}
          sortOrder={sortOrder}
          onEdit={onEdit}
          onDelete={onDelete}
          onView={onView}
          onTableChange={handleTableChange}
          {...(onExport && { onExport })}
          isExporting={isExporting}
          {...(onAddToCalendar && { onAddToCalendar })}
          {...(isAddingToCalendar !== undefined && { isAddingToCalendar })}
          enableBatchOperations
        />
      ),
    },
  ];

  return (
    <Tabs
      activeKey={activeTab}
      onChange={handleTabChange}
      items={tabItems}
      size={isMobile ? 'small' : 'large'}
    />
  );
};
