/**
 * DataAnalyticsTab - 數據分析整合視圖
 *
 * 單一頁面：統計卡片(上) + 搜尋歷史表格(下)。
 * 不再使用 Segmented 切換，統計與歷史自然上下排列。
 *
 * @version 2.0.0
 * @created 2026-02-27
 * @updated 2026-02-27 — 移除 Segmented，改為單一整合頁面
 */
import React from 'react';
import { Divider, Typography } from 'antd';
import { HistoryOutlined } from '@ant-design/icons';

import { OverviewTab } from './OverviewTab';
import { HistoryTab } from './HistoryTab';

const { Text } = Typography;

export const DataAnalyticsTab: React.FC = () => {
  return (
    <div>
      <OverviewTab />

      <Divider style={{ margin: '16px 0' }}>
        <Text type="secondary" style={{ fontSize: 13 }}>
          <HistoryOutlined /> 搜尋歷史明細
        </Text>
      </Divider>

      <HistoryTab />
    </div>
  );
};
