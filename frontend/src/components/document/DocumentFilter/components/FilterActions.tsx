/**
 * FilterActions 元件
 *
 * 篩選器操作按鈕區塊：清除篩選、套用篩選
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

import React from 'react';
import { Button, Tooltip } from 'antd';
import { ClearOutlined, FilterOutlined, InfoCircleOutlined } from '@ant-design/icons';
import type { FilterActionsProps } from '../types';

const FilterActions: React.FC<FilterActionsProps> = ({
  isMobile,
  hasActiveFilters,
  activeFilterCount,
  onReset,
  onApplyFilters,
}) => {
  return (
    <div style={{
      display: 'flex',
      justifyContent: isMobile ? 'flex-end' : 'space-between',
      alignItems: 'center',
      marginTop: isMobile ? 12 : 16,
      flexWrap: 'wrap',
      gap: 8,
    }}>
      {/* 篩選結果提示 - 手機版隱藏 */}
      {!isMobile && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {hasActiveFilters && (
            <>
              <InfoCircleOutlined style={{ color: '#1890ff' }} />
              <span style={{ color: '#666', fontSize: '13px' }}>
                已套用 {activeFilterCount} 個篩選條件
              </span>
            </>
          )}
        </div>
      )}

      <div style={{ display: 'flex', gap: 8 }}>
        <Tooltip title={isMobile ? '' : '清除所有篩選條件，回復預設狀態'}>
          <Button
            onClick={onReset}
            icon={<ClearOutlined />}
            disabled={!hasActiveFilters}
            size={isMobile ? 'small' : 'middle'}
            style={{ borderColor: hasActiveFilters ? '#ff4d4f' : '', color: hasActiveFilters ? '#ff4d4f' : '' }}
          >
            {isMobile ? '' : '清除篩選'}
          </Button>
        </Tooltip>

        <Tooltip title={isMobile ? '' : '套用當前篩選條件。快速鍵：在任一輸入框中按 Enter'}>
          <Button
            type="primary"
            onClick={onApplyFilters}
            icon={<FilterOutlined />}
            size={isMobile ? 'small' : 'middle'}
          >
            {isMobile ? '篩選' : '套用篩選'}
          </Button>
        </Tooltip>
      </div>
    </div>
  );
};

export default FilterActions;
