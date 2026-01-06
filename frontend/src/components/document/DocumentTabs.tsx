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
  // Set active tab based on current category filter
  const [activeTab, setActiveTab] = useState(() => {
    return filters.category === 'receive' ? 'received' :
           filters.category === 'send' ? 'sent' : 'all';
  });
  const [sortField, setSortField] = useState<string>('');
  const [sortOrder, setSortOrder] = useState<SortOrder>(null);
  const [apiStats, setApiStats] = useState<{total: number; receive: number; send: number} | null>(null);

  // Update active tab when filters change
  React.useEffect(() => {
    const newTab = filters.category === 'receive' ? 'received' :
                   filters.category === 'send' ? 'sent' : 'all';
    setActiveTab(newTab);
  }, [filters.category]);

  // Fetch API statistics on component mount
  useEffect(() => {
    const fetchStats = async () => {
      try {
        // 使用新版統一 API（POST-only 資安機制）
        const stats = await documentsApi.getStatistics();
        console.log('=== 取得 API 統計數據 ===', stats);
        setApiStats({
          total: stats.total || stats.total_documents || 0,
          receive: stats.receive || stats.receive_count || 0,
          send: stats.send || stats.send_count || 0,
        });
      } catch (error) {
        console.error('Failed to fetch statistics:', error);
        // Fallback to prop-based stats if API fails
        setApiStats(null);
      }
    };
    fetchStats();
  }, []);

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

  // Use API statistics for tab badges
  const effectiveStats = {
    total: apiStats?.total ?? (totalAll || total || documents.length),
    received: apiStats?.receive ?? (totalReceived || 0),
    sent: apiStats?.send ?? (totalSent || 0),
  };

  console.log('=== 有效統計數據 ===', effectiveStats);
  console.log('=== API統計狀態 ===', apiStats);
  const tabItems = [
    {
      key: 'all',
      label: (
        <Space>
          <UnorderedListOutlined />
          <Title level={5} style={{ margin: 0 }}>
            全部公文
          </Title>
          <Badge count={effectiveStats.total} showZero overflowCount={99999} color="blue" />
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
          onExport={onExport}
          isExporting={isExporting}
          onAddToCalendar={onAddToCalendar}
          isAddingToCalendar={isAddingToCalendar}
          enableBatchOperations
        />
      ),
    },
    {
      key: 'received',
      label: (
        <Space>
          <InboxOutlined />
          <Title level={5} style={{ margin: 0 }}>
            收文
          </Title>
          <Badge count={effectiveStats.received} showZero overflowCount={99999} color="green" />
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
          onExport={onExport}
          isExporting={isExporting}
          onAddToCalendar={onAddToCalendar}
          isAddingToCalendar={isAddingToCalendar}
          enableBatchOperations
        />
      ),
    },
    {
      key: 'sent',
      label: (
        <Space>
          <SendOutlined />
          <Title level={5} style={{ margin: 0 }}>
            發文
          </Title>
          <Badge count={effectiveStats.sent} showZero overflowCount={99999} color="red" />
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
          onExport={onExport}
          isExporting={isExporting}
          onAddToCalendar={onAddToCalendar}
          isAddingToCalendar={isAddingToCalendar}
          enableBatchOperations
        />
      ),
    },
  ];

  return (
    <Tabs activeKey={activeTab} onChange={handleTabChange} items={tabItems} />
  );
};
