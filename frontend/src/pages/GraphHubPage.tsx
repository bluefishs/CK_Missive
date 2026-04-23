/**
 * GraphHubPage — 各類圖譜統一入口（ADR-0031 Phase 7）
 *
 * 提供 5 個圖譜的 preview card 與一鍵跳轉：
 *   1. 知識圖譜（業務實體 KG，2504 entities）
 *   2. 程式碼圖譜（Code-graph，5721 entities）
 *   3. 資料庫圖譜（DB schema）
 *   4. ERP 財務圖譜
 *   5. 標案圖譜（機關→標案→廠商）
 *
 * 另有 2 個 Wiki 類入口（分屬兩個世界觀）：
 *   - LLM Wiki（業務領域知識，外顯世界）
 *   - Memory Wiki（助理自我記憶，內在心智）
 *
 * @version 1.0.0 — 2026-04-22 (ADR-0031)
 */

import React from 'react';
import { Card, Col, Row, Space, Tag, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';
import {
  ApartmentOutlined,
  ArrowRightOutlined,
  BookOutlined,
  BranchesOutlined,
  ClusterOutlined,
  DatabaseOutlined,
  DeploymentUnitOutlined,
  DollarOutlined,
  FileSearchOutlined,
} from '@ant-design/icons';
import { ROUTES } from '../router/types';

const { Title, Paragraph, Text } = Typography;

interface GraphCardSpec {
  route: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  tag?: { color: string; text: string };
  domain: 'graph' | 'wiki';
}

const GRAPH_CARDS: GraphCardSpec[] = [
  {
    route: ROUTES.KNOWLEDGE_GRAPH,
    title: '知識圖譜',
    description: '業務實體網絡：公文 / 案件 / 機關 / 廠商 / 人員跨域關聯與最短路徑查詢',
    icon: <DeploymentUnitOutlined style={{ fontSize: 28, color: '#52c41a' }} />,
    tag: { color: 'green', text: '2,504 實體' },
    domain: 'graph',
  },
  {
    route: ROUTES.CODE_GRAPH,
    title: '程式碼圖譜',
    description: '程式碼結構圖：ORM models / API routes / Services / TypeScript types 跨層依賴',
    icon: <BranchesOutlined style={{ fontSize: 28, color: '#1677ff' }} />,
    tag: { color: 'blue', text: '5,721 實體' },
    domain: 'graph',
  },
  {
    route: ROUTES.DB_GRAPH,
    title: '資料庫圖譜',
    description: 'PostgreSQL schema 視覺化：資料表關聯、外鍵、索引結構',
    icon: <DatabaseOutlined style={{ fontSize: 28, color: '#722ed1' }} />,
    domain: 'graph',
  },
  {
    route: ROUTES.ERP_GRAPH,
    title: 'ERP 財務圖譜',
    description: '報價 / 費用 / 資產 / 廠商 跨案件追蹤與金流網絡',
    icon: <DollarOutlined style={{ fontSize: 28, color: '#faad14' }} />,
    domain: 'graph',
  },
  {
    route: ROUTES.TENDER_GRAPH,
    title: '標案圖譜',
    description: '機關 → 標案 → 廠商 關係網絡；投標戰情與廠商生態',
    icon: <ApartmentOutlined style={{ fontSize: 28, color: '#eb2f96' }} />,
    domain: 'graph',
  },
];

const WIKI_CARDS: GraphCardSpec[] = [
  {
    route: ROUTES.WIKI,
    title: 'LLM Wiki',
    description: '業務領域知識（外顯世界）：220 pages 機關 / 專案 / 派工的結構化敘述',
    icon: <BookOutlined style={{ fontSize: 28, color: '#13c2c2' }} />,
    tag: { color: 'cyan', text: '220 pages' },
    domain: 'wiki',
  },
  {
    route: ROUTES.MEMORY_DASHBOARD,
    title: '記憶中樞 Memory Wiki',
    description: '助理自我記憶（內在心智）：日記 / 模式 / 提案 / 結晶 / 週自傳',
    icon: <ClusterOutlined style={{ fontSize: 28, color: '#fa541c' }} />,
    tag: { color: 'orange', text: 'ADR-0022' },
    domain: 'wiki',
  },
];

const renderCard = (spec: GraphCardSpec, navigate: ReturnType<typeof useNavigate>) => (
  <Col xs={24} md={12} lg={8} key={spec.route}>
    <Card
      hoverable
      onClick={() => navigate(spec.route)}
      style={{ height: '100%' }}
    >
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        <Space>
          {spec.icon}
          <Title level={5} style={{ margin: 0 }}>{spec.title}</Title>
          {spec.tag && <Tag color={spec.tag.color}>{spec.tag.text}</Tag>}
        </Space>
        <Paragraph type="secondary" style={{ margin: 0, fontSize: 13, minHeight: 40 }}>
          {spec.description}
        </Paragraph>
        <Text type="secondary" style={{ fontSize: 12 }}>
          開啟 <ArrowRightOutlined />
        </Text>
      </Space>
    </Card>
  </Col>
);

export const GraphHubPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div style={{ padding: 24, maxWidth: 1400, margin: '0 auto' }}>
      <Space direction="vertical" size={4} style={{ marginBottom: 20 }}>
        <Title level={3} style={{ margin: 0 }}>
          <FileSearchOutlined /> 圖譜與 Wiki 中樞
        </Title>
        <Text type="secondary">
          ADR-0031：各類圖譜與 Wiki 的統一入口。圖譜（業務/程式碼/資料）屬視覺化查詢；
          Wiki 分外顯世界（LLM Wiki）與內在心智（Memory Wiki）兩種世界觀。
        </Text>
      </Space>

      <Title level={4} style={{ marginBottom: 12 }}>
        <DeploymentUnitOutlined /> 圖譜（Graphs）
      </Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
        {GRAPH_CARDS.map((spec) => renderCard(spec, navigate))}
      </Row>

      <Title level={4} style={{ marginBottom: 12 }}>
        <BookOutlined /> Wiki
      </Title>
      <Row gutter={[16, 16]}>
        {WIKI_CARDS.map((spec) => renderCard(spec, navigate))}
      </Row>
    </div>
  );
};

export default GraphHubPage;
