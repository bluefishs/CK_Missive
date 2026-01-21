/**
 * 桃園查估派工管理系統
 *
 * 四頁籤架構:
 * - Tab 1: 工程資訊 (轄管工程清單 + 派工工程)
 * - Tab 2: 函文紀錄 (公文管理)
 * - Tab 3: 派工紀錄
 * - Tab 4: 契金管控
 *
 * @version 2.1.0
 * @date 2026-01-21
 */

import React, { useState } from 'react';
import {
  Typography,
  Card,
  Tag,
  Tabs,
} from 'antd';
import {
  ProjectOutlined,
  FileTextOutlined,
  SendOutlined,
  DollarOutlined,
} from '@ant-design/icons';

import { ProjectsTab } from '../components/taoyuan/ProjectsTab';
import { DocumentsTab } from '../components/taoyuan/DocumentsTab';
import { DispatchOrdersTab } from '../components/taoyuan/DispatchOrdersTab';
import { PaymentsTab } from '../components/taoyuan/PaymentsTab';
import { TAOYUAN_CONTRACT } from '../constants/taoyuanOptions';

const { Title, Text } = Typography;

/**
 * 桃園查估派工管理系統主頁面
 */
export const TaoyuanDispatchPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('1');

  return (
    <div style={{ padding: '24px' }}>
      {/* 頁面標題 */}
      <div style={{ marginBottom: 16 }}>
        <Title level={2} style={{ margin: 0 }}>
          桃園查估派工管理系統
        </Title>
        <Text type="secondary">派工管理 / 函文紀錄 / 契金管控</Text>
      </div>

      {/* 專案資訊卡片 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <Tag color="blue">承攬案件</Tag>
          <Tag color="cyan">{TAOYUAN_CONTRACT.CODE}</Tag>
          <Text strong style={{ fontSize: '14px' }}>
            {TAOYUAN_CONTRACT.NAME}
          </Text>
        </div>
      </Card>

      {/* TAB 頁籤 */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        type="card"
        size="large"
        items={[
          {
            key: '1',
            label: (
              <span>
                <ProjectOutlined />
                工程資訊
              </span>
            ),
            children: <ProjectsTab contractProjectId={TAOYUAN_CONTRACT.PROJECT_ID} />,
          },
          {
            key: '2',
            label: (
              <span>
                <FileTextOutlined />
                函文紀錄
              </span>
            ),
            children: <DocumentsTab contractCode={TAOYUAN_CONTRACT.CODE} />,
          },
          {
            key: '3',
            label: (
              <span>
                <SendOutlined />
                派工紀錄
              </span>
            ),
            children: (
              <DispatchOrdersTab
                contractProjectId={TAOYUAN_CONTRACT.PROJECT_ID}
                contractCode={TAOYUAN_CONTRACT.CODE}
              />
            ),
          },
          {
            key: '4',
            label: (
              <span>
                <DollarOutlined />
                契金管控
              </span>
            ),
            children: <PaymentsTab contractProjectId={TAOYUAN_CONTRACT.PROJECT_ID} />,
          },
        ]}
      />
    </div>
  );
};

export default TaoyuanDispatchPage;
