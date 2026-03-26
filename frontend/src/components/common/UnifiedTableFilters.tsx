/**
 * UnifiedTable - 過濾器渲染元件
 *
 * 從 UnifiedTable.tsx 提取的過濾器區域與狀態指示器
 *
 * @version 1.0.0
 * @date 2026-03-25
 */

import React from 'react';
import {
  Input,
  Select,
  AutoComplete,
  DatePicker,
  Button,
  Space,
  Row,
  Col,
  Typography,
  Tag,
} from 'antd';
import {
  SearchOutlined,
  ClearOutlined,
  ReloadOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import type { SortOrder } from 'antd/es/table/interface';

import type { FilterConfig } from './UnifiedTable';

const { Text } = Typography;
const { Option } = Select;
const { RangePicker } = DatePicker;

export interface SortConfig {
  field: string;
  order: SortOrder;
}

/** Render a single filter input based on its config */
// eslint-disable-next-line react-refresh/only-export-components
export function renderFilterInput(
  config: FilterConfig,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  value: any,
  onFilterChange: (key: string, value: unknown) => void,
): React.ReactNode {
  switch (config.type) {
    case 'text':
      return (
        <Input
          placeholder={config.placeholder || `搜索 ${config.label}`}
          value={value || ''}
          onChange={(e) => onFilterChange(config.key, e.target.value)}
          allowClear
        />
      );

    case 'select':
      return (
        <Select
          placeholder={config.placeholder || `選擇 ${config.label}`}
          value={value}
          onChange={(val) => onFilterChange(config.key, val)}
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
          onChange={(val) => onFilterChange(config.key, val)}
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
          onChange={(dates) => onFilterChange(config.key, dates)}
          style={{ width: '100%' }}
        />
      );

    case 'number':
      return (
        <Input
          type="number"
          placeholder={config.placeholder || `輸入 ${config.label}`}
          value={value || ''}
          onChange={(e) => onFilterChange(config.key, e.target.value)}
          allowClear
        />
      );

    default:
      return null;
  }
}

export interface UnifiedTableFilterBarProps {
  searchText: string;
  onSearchTextChange: (value: string) => void;
  filterConfigs: FilterConfig[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  filters: Record<string, any>;
  onFilterChange: (key: string, value: unknown) => void;
  onClearFilters: () => void;
  onRefresh?: () => void;
  enableExport?: boolean;
  onExport?: () => void;
  customActions?: React.ReactNode;
  sortConfig: SortConfig | null;
  onClearSort: () => void;
}

/** Filter bar area: search input, per-field filters, action buttons */
export const UnifiedTableFilterBar: React.FC<UnifiedTableFilterBarProps> = ({
  searchText,
  onSearchTextChange,
  filterConfigs,
  filters,
  onFilterChange,
  onClearFilters,
  onRefresh,
  enableExport,
  onExport,
  customActions,
  sortConfig,
  onClearSort,
}) => (
  <>
    {/* 過濾器區域 */}
    <div style={{ marginBottom: 16 }}>
      <Row gutter={[16, 8]} align="middle">
        {/* 全文搜索 */}
        <Col xs={24} sm={8} md={6}>
          <Input
            placeholder="全文搜索..."
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => onSearchTextChange(e.target.value)}
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
              {renderFilterInput(config, filters[config.key], onFilterChange)}
            </div>
          </Col>
        ))}

        {/* 操作按鈕 */}
        <Col flex="auto">
          <div style={{ textAlign: 'right' }}>
            <Space>
              <Button
                icon={<ClearOutlined />}
                onClick={onClearFilters}
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
                  onClick={onExport}
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
            <Tag closable onClose={() => onSearchTextChange('')}>
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
              <Tag key={key} closable onClose={() => onFilterChange(key, null)}>
                {config.label}: {String(displayValue)}
              </Tag>
            );
          })}
          {sortConfig && (
            <Tag closable onClose={onClearSort}>
              排序: {sortConfig.field} ({sortConfig.order === 'ascend' ? '升序' : '降序'})
            </Tag>
          )}
        </Space>
      </div>
    )}
  </>
);
