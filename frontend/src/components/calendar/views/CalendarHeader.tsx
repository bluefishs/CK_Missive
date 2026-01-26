/**
 * 行事曆頭部控制元件
 * 包含視圖切換、新增事件、篩選按鈕
 */

import React from 'react';
import { Button, Space, Select, Radio } from 'antd';
import {
  FilterOutlined, PlusOutlined, CalendarOutlined, UnorderedListOutlined, TableOutlined
} from '@ant-design/icons';
import type { ViewMode } from './types';

export interface CalendarHeaderProps {
  viewMode: ViewMode;
  isMobile: boolean;
  onViewModeChange: (mode: ViewMode) => void;
  onAddEvent: () => void;
  onOpenFilter: () => void;
}

export const CalendarHeader: React.FC<CalendarHeaderProps> = ({
  viewMode,
  isMobile,
  onViewModeChange,
  onAddEvent,
  onOpenFilter
}) => {
  return (
    <div style={{
      display: 'flex',
      justifyContent: isMobile ? 'space-between' : 'flex-end',
      alignItems: 'center',
      flexWrap: 'wrap',
      gap: '8px'
    }}>
      <Space wrap size={isMobile ? 'small' : 'middle'}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={onAddEvent}
        >
          {isMobile ? '' : '新增事件'}
        </Button>
        <Button
          icon={<FilterOutlined />}
          onClick={onOpenFilter}
        >
          {isMobile ? '' : '篩選'}
        </Button>
        {/* 視圖切換 - 響應式 */}
        {isMobile ? (
          <Select
            value={viewMode}
            onChange={(value) => onViewModeChange(value)}
            style={{ width: 100 }}
            options={[
              { label: '月曆', value: 'month' },
              { label: '列表', value: 'list' },
              { label: '時間軸', value: 'timeline' }
            ]}
          />
        ) : (
          <Radio.Group
            value={viewMode}
            onChange={(e) => onViewModeChange(e.target.value)}
            buttonStyle="solid"
          >
            <Radio.Button value="month">
              <CalendarOutlined /> 月檢視
            </Radio.Button>
            <Radio.Button value="list">
              <UnorderedListOutlined /> 列表
            </Radio.Button>
            <Radio.Button value="timeline">
              <TableOutlined /> 時間軸
            </Radio.Button>
          </Radio.Group>
        )}
      </Space>
    </div>
  );
};

export default CalendarHeader;
