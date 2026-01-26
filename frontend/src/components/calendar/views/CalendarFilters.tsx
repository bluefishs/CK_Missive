/**
 * 行事曆篩選面板元件
 */

import React from 'react';
import { Modal, Form, Row, Col, Select, DatePicker, Input, Radio } from 'antd';
import type { FilterState } from './types';
import { EVENT_TYPE_CONFIG, PRIORITY_CONFIG } from './constants';

const { RangePicker } = DatePicker;
const { Search } = Input;

export interface CalendarFiltersProps {
  visible: boolean;
  filters: FilterState;
  isMobile: boolean;
  onClose: () => void;
  onFiltersChange: (filters: FilterState) => void;
}

export const CalendarFilters: React.FC<CalendarFiltersProps> = ({
  visible,
  filters,
  isMobile,
  onClose,
  onFiltersChange
}) => {
  const updateFilter = <K extends keyof FilterState>(key: K, value: FilterState[K]) => {
    onFiltersChange({ ...filters, [key]: value });
  };

  return (
    <Modal
      title="事件篩選"
      open={visible}
      onCancel={onClose}
      onOk={onClose}
      width={isMobile ? '95%' : 600}
      style={{ maxWidth: '95vw' }}
    >
      <Form layout="vertical">
        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item label="事件類型">
              <Select
                mode="multiple"
                placeholder="選擇事件類型"
                value={filters.eventTypes}
                onChange={(value) => updateFilter('eventTypes', value)}
                options={Object.entries(EVENT_TYPE_CONFIG).map(([key, config]) => ({
                  label: config.name,
                  value: key
                }))}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item label="優先級">
              <Select
                mode="multiple"
                placeholder="選擇優先級"
                value={filters.priorities}
                onChange={(value) => updateFilter('priorities', value)}
                options={Object.entries(PRIORITY_CONFIG).map(([key, config]) => ({
                  label: config.name,
                  value: Number(key)
                }))}
              />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item label="狀態">
              <Select
                mode="multiple"
                placeholder="選擇狀態"
                value={filters.statuses}
                onChange={(value) => updateFilter('statuses', value)}
                options={[
                  { label: '待處理', value: 'pending' },
                  { label: '已完成', value: 'completed' },
                  { label: '已取消', value: 'cancelled' }
                ]}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item label="日期範圍">
              <RangePicker
                value={filters.dateRange}
                onChange={(dates) => updateFilter(
                  'dateRange',
                  dates && dates[0] && dates[1] ? [dates[0], dates[1]] : null
                )}
                style={{ width: '100%' }}
              />
            </Form.Item>
          </Col>
        </Row>
        <Form.Item label="關鍵字搜尋">
          <Search
            placeholder="搜尋事件標題或描述"
            value={filters.searchText}
            onChange={(e) => updateFilter('searchText', e.target.value)}
            allowClear
          />
        </Form.Item>
        <Form.Item label="提醒設定">
          <Radio.Group
            value={filters.hasReminders}
            onChange={(e) => updateFilter('hasReminders', e.target.value)}
          >
            <Radio value={undefined}>全部</Radio>
            <Radio value={true}>有提醒</Radio>
            <Radio value={false}>無提醒</Radio>
          </Radio.Group>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default CalendarFilters;
