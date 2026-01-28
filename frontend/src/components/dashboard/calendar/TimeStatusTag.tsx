/**
 * 時間狀態標籤元件
 */

import React from 'react';
import { Tag } from 'antd';
import type { TimeStatus } from './types';
import { TIME_STATUS_CONFIG } from './types';

interface TimeStatusTagProps {
  status: TimeStatus;
  count?: number;
}

export const TimeStatusTag: React.FC<TimeStatusTagProps> = ({ status, count }) => {
  const config = TIME_STATUS_CONFIG[status];
  return (
    <Tag
      color={config.color}
      style={{ margin: 0, fontSize: 11, lineHeight: '18px' }}
    >
      {config.label}
      {count !== undefined && count > 1 && ` (${count})`}
    </Tag>
  );
};
