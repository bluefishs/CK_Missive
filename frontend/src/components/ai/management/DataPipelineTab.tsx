/**
 * DataPipelineTab - 資料管線整合視圖
 *
 * 單一頁面：Embedding + Entity 管線狀態(上) + 知識圖譜(下)。
 * Embedding 是圖譜的前置步驟，統一顯示管線進度。
 *
 * @version 2.0.0
 * @created 2026-02-27
 * @updated 2026-02-27 — 移除 Segmented，改為單一整合頁面
 */
import React from 'react';
import { Divider, Typography } from 'antd';
import { ApartmentOutlined } from '@ant-design/icons';

import { EmbeddingTab } from './EmbeddingTab';
import { KnowledgeGraphTab } from './KnowledgeGraphTab';

const { Text } = Typography;

export const DataPipelineTab: React.FC = () => {
  return (
    <div>
      <EmbeddingTab />

      <Divider style={{ margin: '16px 0' }}>
        <Text type="secondary" style={{ fontSize: 13 }}>
          <ApartmentOutlined /> 知識圖譜
        </Text>
      </Divider>

      <KnowledgeGraphTab />
    </div>
  );
};
