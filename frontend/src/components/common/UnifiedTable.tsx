import React, { useState, useMemo } from 'react';
import {
  Table,
  Card,
  Button,
  Space,
  Typography,
  App
} from 'antd';
import {
  SortAscendingOutlined,
  SortDescendingOutlined,
} from '@ant-design/icons';
import type { ColumnsType, TableProps, ColumnType } from 'antd/es/table';
import dayjs from 'dayjs';

import { UnifiedTableFilterBar, type SortConfig } from './UnifiedTableFilters';

const { Text } = Typography;

export interface FilterConfig {
  key: string;
  label: string;
  type: 'text' | 'select' | 'dateRange' | 'number' | 'autocomplete';
  options?: Array<{ value: string | number; label: string }>;
  placeholder?: string;
  autoCompleteOptions?: string[];
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- generic default type for flexible usage
export interface UnifiedTableProps<T = any> extends Omit<TableProps<T>, 'columns' | 'title'> {
  columns: ColumnsType<T>;
  data: T[];
  loading?: boolean;
  title?: string;
  subtitle?: string;
  filterConfigs?: FilterConfig[];
  enableExport?: boolean;
  enableSequenceNumber?: boolean;
  showTotal?: boolean;
  onExport?: (filteredData: T[]) => void;
  onRefresh?: () => void;
  customActions?: React.ReactNode;
  sequenceNumberTitle?: string;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- generic constraint for flexible record types
function UnifiedTable<T extends Record<string, any>>({
  columns,
  data,
  loading = false,
  title,
  subtitle,
  filterConfigs = [],
  enableExport = false,
  enableSequenceNumber = false,
  showTotal = true,
  onExport,
  onRefresh,
  customActions,
  sequenceNumberTitle = '序號',
  ...tableProps
}: UnifiedTableProps<T>) {
  const { message } = App.useApp();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- filter values can be any type (string, number, date range, etc.)
  const [filters, setFilters] = useState<Record<string, any>>({});
  const [sortConfig, setSortConfig] = useState<SortConfig | null>(null);
  const [searchText, setSearchText] = useState('');

  // 過濾和排序後的數據
  const processedData = useMemo(() => {
    let filteredData = [...data];

    // 全文搜索
    if (searchText.trim()) {
      const searchLower = searchText.toLowerCase();
      filteredData = filteredData.filter(item =>
        Object.values(item).some(value => {
          if (value == null) return false;
          return String(value).toLowerCase().includes(searchLower);
        })
      );
    }

    // 欄位過濾
    Object.entries(filters).forEach(([key, value]) => {
      if (value == null || value === '' || (Array.isArray(value) && value.length === 0)) {
        return;
      }

      const filterConfig = filterConfigs.find(config => config.key === key);
      if (!filterConfig) return;

      if (filterConfig.type === 'dateRange' && Array.isArray(value)) {
        const [start, end] = value;
        if (start && end) {
          filteredData = filteredData.filter(item => {
            const itemDate = dayjs(item[key]);
            return itemDate.isAfter(start.startOf('day')) && itemDate.isBefore(end.endOf('day'));
          });
        }
      } else if (filterConfig.type === 'select') {
        if (Array.isArray(value)) {
          filteredData = filteredData.filter(item => value.includes(item[key]));
        } else {
          filteredData = filteredData.filter(item => item[key] === value);
        }
      } else if (filterConfig.type === 'text' || filterConfig.type === 'autocomplete') {
        filteredData = filteredData.filter(item =>
          String(item[key] || '').toLowerCase().includes(String(value).toLowerCase())
        );
      } else if (filterConfig.type === 'number') {
        filteredData = filteredData.filter(item => Number(item[key]) === Number(value));
      }
    });

    // 排序
    if (sortConfig) {
      filteredData.sort((a, b) => {
        const aValue = a[sortConfig.field];
        const bValue = b[sortConfig.field];
        
        if (aValue == null && bValue == null) return 0;
        if (aValue == null) return sortConfig.order === 'ascend' ? -1 : 1;
        if (bValue == null) return sortConfig.order === 'ascend' ? 1 : -1;

        // 數字比較
        if (typeof aValue === 'number' && typeof bValue === 'number') {
          return sortConfig.order === 'ascend' ? aValue - bValue : bValue - aValue;
        }

        // 日期比較
        if (dayjs(aValue).isValid() && dayjs(bValue).isValid()) {
          const diff = dayjs(aValue).diff(dayjs(bValue));
          return sortConfig.order === 'ascend' ? diff : -diff;
        }

        // 字符串比較
        const aStr = String(aValue).toLowerCase();
        const bStr = String(bValue).toLowerCase();
        return sortConfig.order === 'ascend' 
          ? aStr.localeCompare(bStr)
          : bStr.localeCompare(aStr);
      });
    }

    return filteredData;
  }, [data, filters, sortConfig, searchText, filterConfigs]);

  // 處理過濾器變化
  const handleFilterChange = (key: string, value: unknown) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  // 清除所有過濾器
  const handleClearFilters = () => {
    setFilters({});
    setSearchText('');
    setSortConfig(null);
  };

  // 排序變化
  const handleSortChange = (field: string) => {
    setSortConfig(prev => {
      if (prev?.field === field) {
        if (prev.order === 'ascend') {
          return { field, order: 'descend' };
        } else if (prev.order === 'descend') {
          return null; // 清除排序
        }
      }
      return { field, order: 'ascend' };
    });
  };

  // 導出功能
  const handleExport = () => {
    if (onExport) {
      onExport(processedData);
    } else {
      // 預設導出為 JSON
      const dataStr = JSON.stringify(processedData, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${title || 'data'}_${dayjs().format('YYYYMMDD_HHmmss')}.json`;
      link.click();
      URL.revokeObjectURL(url);
      message.success('數據已導出');
    }
  };

  // 增強的列配置（添加排序功能）
  const enhancedColumns = useMemo(() => {
    let cols = [...columns];

    // 添加序號列
    if (enableSequenceNumber) {
      cols.unshift({
        title: sequenceNumberTitle,
        key: '__sequence__',
        width: 80,
        align: 'center',
        render: (_, __, index) => {
          const { current = 1, pageSize = 10 } = tableProps.pagination || {};
          return (current - 1) * pageSize + index + 1;
        }
      });
    }

    // 為可排序列添加排序指示器
    cols = cols.map(col => {
      const columnType = col as ColumnType<T>;
      if (columnType.dataIndex && typeof columnType.dataIndex === 'string') {
        const field = columnType.dataIndex;
        const currentSort = sortConfig?.field === field ? sortConfig.order : null;
        const originalTitle = typeof columnType.title === 'function'
          ? 'Column'
          : columnType.title;

        return {
          ...col,
          title: (
            <Space>
              <span>{originalTitle}</span>
              <Button
                type="text"
                size="small"
                icon={
                  currentSort === 'ascend' ? <SortAscendingOutlined /> :
                  currentSort === 'descend' ? <SortDescendingOutlined /> :
                  <SortAscendingOutlined style={{ opacity: 0.3 }} />
                }
                onClick={() => handleSortChange(field)}
                style={{ padding: 0 }}
              />
            </Space>
          )
        };
      }
      return col;
    });

    return cols;
  }, [columns, enableSequenceNumber, sequenceNumberTitle, sortConfig, tableProps.pagination]);

  return (
    <Card>
      {/* 標題區域 */}
      {(title || subtitle) && (
        <div style={{ marginBottom: 16 }}>
          {title && <Text strong style={{ fontSize: 16, display: 'block' }}>{title}</Text>}
          {subtitle && <Text type="secondary">{subtitle}</Text>}
        </div>
      )}

      {/* 過濾器區域 + 狀態指示器 */}
      <UnifiedTableFilterBar
        searchText={searchText}
        onSearchTextChange={setSearchText}
        filterConfigs={filterConfigs}
        filters={filters}
        onFilterChange={handleFilterChange}
        onClearFilters={handleClearFilters}
        onRefresh={onRefresh}
        enableExport={enableExport}
        onExport={handleExport}
        customActions={customActions}
        sortConfig={sortConfig}
        onClearSort={() => setSortConfig(null)}
      />

      {/* 數據表格 */}
      <Table
        {...tableProps}
        columns={enhancedColumns}
        dataSource={processedData}
        loading={loading}
        pagination={showTotal ? {
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total: number, range: [number, number]) =>
            `第 ${range[0]}-${range[1]} 項，共 ${total} 項`,
          ...(tableProps.pagination !== false ? tableProps.pagination : {})
        } : (tableProps.pagination ?? false)}
      />

      {/* 統計信息 */}
      {showTotal && (
        <div style={{ marginTop: 16, textAlign: 'right' }}>
          <Text type="secondary">
            顯示 {processedData.length} 項，共 {data.length} 項數據
            {processedData.length !== data.length && ' (已篩選)'}
          </Text>
        </div>
      )}
    </Card>
  );
}

export default UnifiedTable;