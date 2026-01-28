/**
 * DocumentFilter 元件
 *
 * 公文篩選元件，提供多種篩選條件
 * 已重構為模組化架構，分離為多個子元件
 *
 * @version 2.0.0
 * @date 2026-01-26
 */

import React, { useState } from 'react';
import { Card, Typography, Tag, Button, Divider } from 'antd';
import dayjs from 'dayjs';
import {
  SearchOutlined,
  FilterOutlined,
  DownOutlined,
  UpOutlined,
} from '@ant-design/icons';
import { DocumentFilter as DocumentFilterType } from '../../../types';
import { useResponsive } from '../../../hooks';
import { useFilterOptions } from './hooks';
import { PrimaryFilters, AdvancedFilters, FilterActions } from './components';
import type { DocumentFilterProps } from './types';

const { Title } = Typography;

/**
 * DocumentFilter 主元件
 *
 * 組合主要篩選、進階篩選和操作按鈕子元件
 */
const DocumentFilterComponent: React.FC<DocumentFilterProps> = ({
  filters,
  onFiltersChange,
  onReset,
}) => {
  // RWD 響應式
  const { isMobile } = useResponsive();

  // 預設收闔篩選區，公文資訊最大化
  const [expanded, setExpanded] = useState(false);
  const [localFilters, setLocalFilters] = useState<DocumentFilterType>(filters);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null);

  // 從 API 獲取篩選選項
  const {
    yearOptions,
    contractCaseOptions,
    senderOptions,
    receiverOptions,
  } = useFilterOptions();

  // 單欄位更新
  const handleFilterChange = <K extends keyof DocumentFilterType>(field: K, value: DocumentFilterType[K]) => {
    setLocalFilters(prev => ({ ...prev, [field]: value }));
  };

  // 批次更新多個篩選條件（解決日期範圍連續更新問題）
  const handleMultipleFilterChange = (updates: Partial<DocumentFilterType>) => {
    setLocalFilters(prev => ({ ...prev, ...updates }));
  };

  // 套用篩選
  const handleApplyFilters = () => {
    onFiltersChange(localFilters);
  };

  // 重置篩選
  const handleReset = () => {
    const emptyFilters: DocumentFilterType = {};
    setLocalFilters(emptyFilters);
    setDateRange(null);
    onReset();
  };

  // 日期範圍變更
  const handleDateRangeChange = (dates: [dayjs.Dayjs | null, dayjs.Dayjs | null] | null) => {
    setDateRange(dates);
  };

  // 計算作用中篩選數量
  const hasActiveFilters = Object.values(filters).some(value =>
    value !== undefined && value !== ''
  );

  const activeFilterCount = Object.values(filters).filter(value =>
    value !== undefined && value !== ''
  ).length;

  return (
    <Card style={{ marginBottom: isMobile ? 12 : 16 }} size={isMobile ? 'small' : 'default'}>
      {/* 標題列 */}
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: isMobile ? 12 : 16 }}>
        <SearchOutlined style={{ marginRight: 8 }} />
        <Title level={5} style={{ margin: 0, flexGrow: 1, fontSize: isMobile ? 14 : undefined }}>
          {isMobile ? '篩選' : '搜尋與篩選'}
        </Title>

        {hasActiveFilters && (
          <Tag color="blue" style={{ marginRight: 8, fontSize: isMobile ? 12 : undefined }}>
            <FilterOutlined style={{ marginRight: 4 }} />
            {activeFilterCount}
          </Tag>
        )}

        <Button
          type="text"
          size="small"
          onClick={() => setExpanded(!expanded)}
          icon={expanded ? <UpOutlined /> : <DownOutlined />}
        >
          {isMobile ? '' : (expanded ? '收起' : '展開')}
        </Button>
      </div>

      {/* 主要篩選條件 */}
      <PrimaryFilters
        localFilters={localFilters}
        isMobile={isMobile}
        contractCaseOptions={contractCaseOptions}
        onFilterChange={handleFilterChange}
        onApplyFilters={handleApplyFilters}
      />

      {/* 進階查詢 (可展開) */}
      {expanded && (
        <>
          <Divider style={{ margin: isMobile ? '12px 0' : '16px 0', fontSize: isMobile ? 12 : undefined }}>
            進階查詢
          </Divider>

          <AdvancedFilters
            localFilters={localFilters}
            isMobile={isMobile}
            yearOptions={yearOptions}
            senderOptions={senderOptions}
            receiverOptions={receiverOptions}
            dateRange={dateRange}
            onFilterChange={handleFilterChange}
            onMultipleFilterChange={handleMultipleFilterChange}
            onDateRangeChange={handleDateRangeChange}
            onApplyFilters={handleApplyFilters}
          />
        </>
      )}

      {/* 操作按鈕 */}
      <FilterActions
        isMobile={isMobile}
        hasActiveFilters={hasActiveFilters}
        activeFilterCount={activeFilterCount}
        onReset={handleReset}
        onApplyFilters={handleApplyFilters}
      />
    </Card>
  );
};

// 匯出元件
export { DocumentFilterComponent as DocumentFilter };

// 匯出型別供外部使用
export type { DocumentFilterProps } from './types';

// 匯出子元件供獨立使用
export { PrimaryFilters, AdvancedFilters, FilterActions, FilterFieldWrapper } from './components';
export { useFilterOptions, useAutocompleteSuggestions } from './hooks';
export { DOC_TYPE_OPTIONS, DELIVERY_METHOD_OPTIONS, STATUS_OPTIONS } from './constants';
