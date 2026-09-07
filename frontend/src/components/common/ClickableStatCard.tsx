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
  title: React.ReactNode;
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
    {/* 2026-09-07 owner（手機截圖）：「承攬金額（含稅）」那張卡比同列其他卡高一截 ——
        標題帶了 tooltip 圖示，窄螢幕上圖示被擠到第二行、金額再被擠到第三行。
        卡片高度不齊在一排統計卡裡特別明顯（那一排本來就是拿來對比的）。
        修法：標題不換行、放不下就用省略號（tooltip 本來就會說完整名稱）；
        數值不換行，避免 39,431,750 這種長度把卡片撐成兩行。 */}
    <Statistic
      title={(
        <Text
          style={{
            fontSize: 12,
            color: active ? color : undefined,
            display: 'block',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {title}
        </Text>
      )}
      value={value}
      prefix={icon}
      suffix={suffix}
      styles={{ content: { color: active ? color : undefined, fontSize: 20, whiteSpace: 'nowrap' } }}
    />
  </Card>
);

export default React.memo(ClickableStatCard);
