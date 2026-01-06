import React, { useState, useMemo } from 'react';
import {
  Table,
  Card,
  Input,
  Select,
  Button,
  Space,
  Row,
  Col,
  DatePicker,
  AutoComplete,
  Typography,
  Tag,
  App
} from 'antd';
import {
  SearchOutlined,
  SortAscendingOutlined,
  SortDescendingOutlined,
  ReloadOutlined,
  DownloadOutlined,
  ClearOutlined
} from '@ant-design/icons';
import type { ColumnsType, TableProps, ColumnType } from 'antd/es/table';
import type { SortOrder } from 'antd/es/table/interface';
import dayjs from 'dayjs';

const { Text } = Typography;
const { Option } = Select;
const { RangePicker } = DatePicker;

export interface FilterConfig {
  key: string;
  label: string;
  type: 'text' | 'select' | 'dateRange' | 'number' | 'autocomplete';
  options?: Array<{ value: any; label: string }>;
  placeholder?: string;
  autoCompleteOptions?: string[];
}

export interface SortConfig {
  field: string;
  order: SortOrder;
}

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
  const handleFilterChange = (key: string, value: any) => {
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

  // 渲染過濾器
  const renderFilter = (config: FilterConfig) => {
    const value = filters[config.key];

    switch (config.type) {
      case 'text':
        return (
          <Input
            placeholder={config.placeholder || `搜索 ${config.label}`}
            value={value || ''}
            onChange={(e) => handleFilterChange(config.key, e.target.value)}
            allowClear
          />
        );

      case 'select':
        return (
          <Select
            placeholder={config.placeholder || `選擇 ${config.label}`}
            value={value}
            onChange={(val) => handleFilterChange(config.key, val)}
            allowClear
            style={{ width: '100%' }}
          >
            {config.options?.map(option => (
              <Option key={option.value} value={option.value}>
                {option.label}
              </Option>
            ))}
          </Select>
        );

      case 'autocomplete':
        return (
          <AutoComplete
            placeholder={config.placeholder || `搜索 ${config.label}`}
            value={value || ''}
            onChange={(val) => handleFilterChange(config.key, val)}
            options={config.autoCompleteOptions?.map(option => ({ value: option })) || []}
            filterOption={(inputValue, option) =>
              option?.value.toLowerCase().includes(inputValue.toLowerCase()) || false
            }
          />
        );

      case 'dateRange':
        return (
          <RangePicker
            placeholder={['開始日期', '結束日期']}
            value={value}
            onChange={(dates) => handleFilterChange(config.key, dates)}
            style={{ width: '100%' }}
          />
        );

      case 'number':
        return (
          <Input
            type="number"
            placeholder={config.placeholder || `輸入 ${config.label}`}
            value={value || ''}
            onChange={(e) => handleFilterChange(config.key, e.target.value)}
            allowClear
          />
        );

      default:
        return null;
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

      {/* 過濾器區域 */}
      <div style={{ marginBottom: 16 }}>
        <Row gutter={[16, 8]} align="middle">
          {/* 全文搜索 */}
          <Col xs={24} sm={8} md={6}>
            <Input
              placeholder="全文搜索..."
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
            />
          </Col>

          {/* 自定義過濾器 */}
          {filterConfigs.map(config => (
            <Col xs={24} sm={8} md={4} key={config.key}>
              <div>
                <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
                  {config.label}
                </Text>
                {renderFilter(config)}
              </div>
            </Col>
          ))}

          {/* 操作按鈕 */}
          <Col flex="auto">
            <div style={{ textAlign: 'right' }}>
              <Space>
                <Button
                  icon={<ClearOutlined />}
                  onClick={handleClearFilters}
                  title="清除所有篩選"
                >
                  清除
                </Button>
                {onRefresh && (
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={onRefresh}
                    title="重新整理"
                  >
                    重新整理
                  </Button>
                )}
                {enableExport && (
                  <Button
                    type="primary"
                    icon={<DownloadOutlined />}
                    onClick={handleExport}
                    title="導出數據"
                  >
                    導出
                  </Button>
                )}
                {customActions}
              </Space>
            </div>
          </Col>
        </Row>
      </div>

      {/* 狀態指示器 */}
      {(Object.keys(filters).length > 0 || searchText || sortConfig) && (
        <div style={{ marginBottom: 16 }}>
          <Space wrap>
            <Text type="secondary">已套用篩選:</Text>
            {searchText && (
              <Tag closable onClose={() => setSearchText('')}>
                搜索: {searchText}
              </Tag>
            )}
            {Object.entries(filters).map(([key, value]) => {
              if (!value) return null;
              const config = filterConfigs.find(c => c.key === key);
              if (!config) return null;
              
              let displayValue = value;
              if (config.type === 'dateRange' && Array.isArray(value)) {
                displayValue = `${value[0]?.format('YYYY-MM-DD')} ~ ${value[1]?.format('YYYY-MM-DD')}`;
              }
              
              return (
                <Tag key={key} closable onClose={() => handleFilterChange(key, null)}>
                  {config.label}: {String(displayValue)}
                </Tag>
              );
            })}
            {sortConfig && (
              <Tag closable onClose={() => setSortConfig(null)}>
                排序: {sortConfig.field} ({sortConfig.order === 'ascend' ? '升序' : '降序'})
              </Tag>
            )}
          </Space>
        </div>
      )}

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