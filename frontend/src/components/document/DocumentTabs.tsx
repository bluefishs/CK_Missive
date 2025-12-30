import React, { useState, useEffect } from 'react';
import { Tabs, Card, Statistic, Row, Col, Badge, Typography, Space } from 'antd';
import {
  InboxOutlined,
  SendOutlined,
  UnorderedListOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { DocumentList } from './DocumentList';
import { Document, DocumentFilter } from '../../types';
import { documentsApi } from '../../api/documents';
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

  // Fetch API statistics on component mount and when filters change
  useEffect(() => {
    const fetchStats = async () => {
      try {
        // Extract current filters, excluding pagination and category for statistics
        const statsFilters = { ...filters };
        delete statsFilters.page;
        delete statsFilters.limit;
        delete statsFilters.category; // Don't include category in statistics call as we calculate all three separately

        const stats = await documentsApi.getStatistics(statsFilters);
        console.log('=== 取得 API 統計數據 ===', stats);
        console.log('=== 當前篩選條件 ===', statsFilters);
        setApiStats(stats);
      } catch (error) {
        console.error('Failed to fetch statistics:', error);
        // Fallback to prop-based stats if API fails
        setApiStats(null);
      }
    };
    fetchStats();
  }, [filters]);

  // Handle tab changes by updating filters
  const handleTabChange = (tabKey: string) => {
    if (onFiltersChange) {
      const newFilters: DocumentFilter = { ...filters };

      switch (tabKey) {
        case 'all':
          delete newFilters.category;
          break;
        case 'received':
          newFilters.category = 'receive';
          break;
        case 'sent':
          newFilters.category = 'send';
          break;
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

  const getStatistics = () => {
    // Use API statistics first, then fallback to props
    const effectiveStats = {
      total: apiStats?.total ?? (totalAll || total || documents.length),
      received: apiStats?.receive ?? (totalReceived || 0),
      sent: apiStats?.send ?? (totalSent || 0),
    };

    return (
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={16}>
          <Col span={8}>
            <Statistic title="全部公文" value={effectiveStats.total} prefix={<FileTextOutlined />} />
          </Col>
          <Col span={8}>
            <Statistic title="收文" value={effectiveStats.received} prefix={<InboxOutlined />} />
          </Col>
          <Col span={8}>
            <Statistic title="發文" value={effectiveStats.sent} prefix={<SendOutlined />} />
          </Col>
        </Row>
      </Card>
    );
  };

  // Use API statistics for badges and statistics card
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
          <Badge count={effectiveStats.total} showZero color="blue" />
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
          <Badge count={effectiveStats.received} showZero color="green" />
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
          <Badge count={effectiveStats.sent} showZero color="red" />
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
    <>
      <Title level={4} style={{ marginBottom: '24px' }}>
        公文儀表板
      </Title>
      {getStatistics()}
      <Tabs activeKey={activeTab} onChange={handleTabChange} items={tabItems} />
    </>
  );
};
