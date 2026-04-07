/**
 * ClickableStatCard — 可點擊互動的統計卡片
 *
 * 點擊後觸發篩選回呼，切換高亮狀態。
 * 參照 /calendar 互動機制設計。
 *
 * 用法：
 *   <ClickableStatCard
 *     title="逾期公文" value={5} color="#ff4d4f"
 *     icon={<WarningOutlined />}
 *     active={filter === 'overdue'}
 *     onClick={() => setFilter('overdue')}
 *   />
 *
 * @version 1.0.0
 */
import React from 'react';
import { Card, Statistic, Typography } from 'antd';

const { Text } = Typography;

interface ClickableStatCardProps {
  title: string;
  value: number | string;
  icon?: React.ReactNode;
  color?: string;
  suffix?: string;
  active?: boolean;
  onClick?: () => void;
  size?: 'small' | 'default';
}

const ClickableStatCard: React.FC<ClickableStatCardProps> = ({
  title, value, icon, color, suffix, active, onClick, size = 'small',
}) => (
  <Card
    size={size}
    hoverable={!!onClick}
    onClick={onClick}
    style={{
      cursor: onClick ? 'pointer' : 'default',
      borderColor: active ? (color || '#1890ff') : undefined,
      borderWidth: active ? 2 : 1,
      background: active ? `${color || '#1890ff'}08` : undefined,
      transition: 'all 0.2s',
    }}
  >
    <Statistic
      title={<Text style={{ fontSize: 12, color: active ? color : undefined }}>{title}</Text>}
      value={value}
      prefix={icon}
      suffix={suffix}
      valueStyle={{ color: active ? color : undefined, fontSize: 20 }}
    />
  </Card>
);

export default React.memo(ClickableStatCard);
