/**
 * 行事曆統計數據元件
 * 顯示事件統計並支援快速篩選
 */

import React from 'react';
import { Card, Row, Col, Tooltip, Statistic, Tag, Button, Space } from 'antd';
import {
  CalendarOutlined, ClockCircleOutlined, BellOutlined,
  ExclamationCircleOutlined, CheckCircleOutlined
} from '@ant-design/icons';
import type { CalendarStatistics as StatisticsType, QuickFilterType } from './types';

export interface CalendarStatisticsProps {
  statistics: StatisticsType;
  filteredCount: number;
  quickFilter: QuickFilterType;
  quickFilterLabel: string | null;
  isMobile: boolean;
  batchProcessing: boolean;
  onQuickFilter: (filterType: QuickFilterType) => void;
  onBatchMarkComplete: () => void;
  onBatchMarkCancelled: () => void;
}

export const CalendarStatistics: React.FC<CalendarStatisticsProps> = ({
  statistics,
  filteredCount,
  quickFilter,
  quickFilterLabel,
  isMobile,
  batchProcessing,
  onQuickFilter,
  onBatchMarkComplete,
  onBatchMarkCancelled
}) => {
  return (
    <Card size={isMobile ? 'small' : 'default'}>
      {/* 快速篩選提示 */}
      {quickFilter && quickFilter !== 'all' && (
        <div style={{ marginBottom: 12 }}>
          <Tag
            color="blue"
            closable
            onClose={() => onQuickFilter(null)}
          >
            目前篩選：{quickFilterLabel}（顯示 {filteredCount} 筆）
          </Tag>
        </div>
      )}
      <Row gutter={[16, 16]}>
        <Col xs={12} sm={12} md={6}>
          <Tooltip title="點擊顯示全部事件">
            <div
              onClick={() => onQuickFilter('all')}
              style={{
                cursor: 'pointer',
                padding: 4,
                borderRadius: 4,
                background: quickFilter === 'all' ? '#e6f7ff' : 'transparent'
              }}
            >
              <Statistic
                title="總事件數"
                value={statistics.total}
                prefix={<CalendarOutlined />}
                valueStyle={{ color: '#1890ff', fontSize: isMobile ? '18px' : '24px' }}
              />
            </div>
          </Tooltip>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Tooltip title="點擊篩選今日事件">
            <div
              onClick={() => onQuickFilter('today')}
              style={{
                cursor: 'pointer',
                padding: 4,
                borderRadius: 4,
                background: quickFilter === 'today' ? '#f6ffed' : 'transparent'
              }}
            >
              <Statistic
                title="今日事件"
                value={statistics.today}
                valueStyle={{ color: '#52c41a', fontSize: isMobile ? '18px' : '24px' }}
                prefix={<ClockCircleOutlined />}
              />
            </div>
          </Tooltip>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Tooltip title="點擊篩選本週事件">
            <div
              onClick={() => onQuickFilter('thisWeek')}
              style={{
                cursor: 'pointer',
                padding: 4,
                borderRadius: 4,
                background: quickFilter === 'thisWeek' ? '#fffbe6' : 'transparent'
              }}
            >
              <Statistic
                title="本週事件"
                value={statistics.thisWeek}
                valueStyle={{ color: '#faad14', fontSize: isMobile ? '18px' : '24px' }}
                prefix={<CalendarOutlined />}
              />
            </div>
          </Tooltip>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Tooltip title="點擊篩選即將到來事件">
            <div
              onClick={() => onQuickFilter('upcoming')}
              style={{
                cursor: 'pointer',
                padding: 4,
                borderRadius: 4,
                background: quickFilter === 'upcoming' ? '#f9f0ff' : 'transparent'
              }}
            >
              <Statistic
                title="即將到來"
                value={statistics.upcoming}
                valueStyle={{ color: '#722ed1', fontSize: isMobile ? '18px' : '24px' }}
                prefix={<BellOutlined />}
              />
            </div>
          </Tooltip>
        </Col>
      </Row>
      {statistics.overdue > 0 && (
        <div style={{ marginTop: 16, display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
          <Tooltip title="點擊查看已逾期事件">
            <Tag
              color="red"
              style={{
                cursor: 'pointer',
                padding: quickFilter === 'overdue' ? '4px 8px' : undefined,
                border: quickFilter === 'overdue' ? '2px solid #ff4d4f' : undefined
              }}
              onClick={() => onQuickFilter('overdue')}
            >
              <ExclamationCircleOutlined /> {statistics.overdue} 個事件已逾期
              {quickFilter !== 'overdue' && ' (點擊查看)'}
            </Tag>
          </Tooltip>
          {/* 批次處理按鈕 - 逾期事件操作 */}
          {(quickFilter === 'overdue' || statistics.overdue > 0) && (
            <Space size="small">
              <Button
                type="primary"
                size="small"
                icon={<CheckCircleOutlined />}
                loading={batchProcessing}
                onClick={onBatchMarkComplete}
              >
                {isMobile ? '全標完成' : '一鍵標記完成'}
              </Button>
              <Button
                size="small"
                danger
                loading={batchProcessing}
                onClick={onBatchMarkCancelled}
              >
                {isMobile ? '全標取消' : '批次標記取消'}
              </Button>
            </Space>
          )}
        </div>
      )}
    </Card>
  );
};

export default CalendarStatistics;
