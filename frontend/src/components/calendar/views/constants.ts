/**
 * 行事曆視圖共用常數
 */

import React from 'react';
import {
  AlertOutlined, CalendarOutlined, EyeOutlined, BellOutlined, UnorderedListOutlined
} from '@ant-design/icons';

/** 事件類型配置 */
export const EVENT_TYPE_CONFIG: Record<string, { name: string; color: string; icon: React.ReactNode }> = {
  deadline: { name: '截止提醒', color: 'red', icon: React.createElement(AlertOutlined) },
  meeting: { name: '會議安排', color: 'purple', icon: React.createElement(CalendarOutlined) },
  review: { name: '審核提醒', color: 'blue', icon: React.createElement(EyeOutlined) },
  reminder: { name: '一般提醒', color: 'orange', icon: React.createElement(BellOutlined) },
  reference: { name: '參考事件', color: 'default', icon: React.createElement(UnorderedListOutlined) }
};

/** 優先級配置 */
export const PRIORITY_CONFIG: Record<number, { name: string; color: string }> = {
  1: { name: '緊急', color: 'red' },
  2: { name: '重要', color: 'orange' },
  3: { name: '普通', color: 'blue' },
  4: { name: '低', color: 'green' },
  5: { name: '最低', color: 'default' }
};

/** 事件類型顏色對應的實際顏色值 */
export const EVENT_TYPE_COLOR_VALUES: Record<string, string> = {
  red: '#ff4d4f',
  orange: '#fa8c16',
  blue: '#1890ff',
  purple: '#722ed1',
  default: '#666'
};

/** 快速篩選標籤映射 */
export const QUICK_FILTER_LABELS: Record<string, string> = {
  all: '全部事件',
  today: '今日事件',
  thisWeek: '本週事件',
  upcoming: '下週事件',
  overdue: '已逾期'
};
