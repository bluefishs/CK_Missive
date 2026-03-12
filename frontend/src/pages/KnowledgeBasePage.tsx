/**
 * KnowledgeBasePage - 知識庫瀏覽器主頁面
 *
 * 三個 Tab：知識地圖 (211 卡片)、ADR 記錄 (11 筆)、架構圖 (Mermaid)
 * 路由：/admin/knowledge-base
 *
 * @version 1.0.0
 */
import React from 'react';
import { Tabs, Typography } from 'antd';
import { BookOutlined, AuditOutlined, ApartmentOutlined } from '@ant-design/icons';

import { KnowledgeMapTab } from './knowledgeBase/KnowledgeMapTab';
import { AdrTab } from './knowledgeBase/AdrTab';
import { DiagramsTab } from './knowledgeBase/DiagramsTab';

const KnowledgeBasePage: React.FC = () => {
  return (
    <div style={{ padding: '0 4px' }}>
      <Typography.Title level={4} style={{ marginBottom: 16 }}>
        知識庫瀏覽器
      </Typography.Title>
      <Tabs
        defaultActiveKey="map"
        items={[
          {
            key: 'map',
            label: <span><BookOutlined /> 知識地圖</span>,
            children: <KnowledgeMapTab />,
          },
          {
            key: 'adr',
            label: <span><AuditOutlined /> 架構決策 (ADR)</span>,
            children: <AdrTab />,
          },
          {
            key: 'diagrams',
            label: <span><ApartmentOutlined /> 架構圖</span>,
            children: <DiagramsTab />,
          },
        ]}
      />
    </div>
  );
};

export default KnowledgeBasePage;
