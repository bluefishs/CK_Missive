/**
 * 坤哥 — 記憶圖譜板塊
 *
 * 呈現三層記憶心智架構：
 *   - 身份層（SOUL.md，由 IdentityTab 呈現）
 *   - 世界觀層（wiki/entities, wiki/topics 220 nodes / KG 2504 entities）
 *   - 自我觀層（wiki/memory/ diary / patterns / autobiographies）
 *
 * 資料來源：
 *   - /ai/memory/stats — Memory Wiki 聚合統計
 *   - /ai/graph/stats — Knowledge Graph 實體/關係統計
 *
 * @version 1.0.0 — D3-B 填充
 */

import React from 'react';
import { Card, Typography, Row, Col, Button, Space, Alert } from 'antd';
import { useNavigate } from 'react-router-dom';
import {
  BookOutlined,
  DatabaseOutlined,
  ArrowRightOutlined,
  NodeIndexOutlined,
} from '@ant-design/icons';
import { useMemoryStats } from '../../hooks/useMemoryData';
import { MemoryStatsRow } from '../../components/memory/MemoryStatsRow';

const { Title, Paragraph, Text } = Typography;

export const MemoryTab: React.FC = () => {
  const navigate = useNavigate();
  const { data: stats, isLoading } = useMemoryStats();

  return (
    <div>
      <Card bordered={false}>
        <Title level={3} style={{ marginTop: 0 }}>
          <DatabaseOutlined /> 記憶圖譜
        </Title>
        <Paragraph type="secondary" style={{ fontSize: 15 }}>
          我的心智由三層 wiki 組成：<Text strong>身份層</Text>（慢變，我是誰）
          · <Text strong>世界觀層</Text>（中速，我知道的世界）
          · <Text strong>自我觀層</Text>（快變，我學到的經驗）。
        </Paragraph>
        <Alert
          type="info"
          showIcon
          message="節點即世界觀"
          description="每個 Wiki 節點、每筆 KG 實體、每個結晶 pattern，都是公司時間複利的一個具象化片段。"
        />
      </Card>

      <Card bordered={false} style={{ marginTop: 16 }} title="自我觀層統計">
        <MemoryStatsRow stats={stats} loading={isLoading} />
      </Card>

      <Card bordered={false} style={{ marginTop: 16 }} title="深入探索">
        <Row gutter={[12, 12]}>
          <Col xs={24} md={8}>
            <Card
              hoverable
              size="small"
              onClick={() => navigate('/ai/memory')}
              style={{ height: '100%' }}
            >
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Space>
                  <BookOutlined style={{ fontSize: 20, color: '#1677ff' }} />
                  <Text strong>Memory Wiki 完整儀表板</Text>
                </Space>
                <Text type="secondary" style={{ fontSize: 13 }}>
                  diary / patterns / proposals / autobiography / 技能星雲 五頁籤
                </Text>
                <Button type="link" style={{ padding: 0 }}>
                  開啟 <ArrowRightOutlined />
                </Button>
              </Space>
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card
              hoverable
              size="small"
              onClick={() => navigate('/ai/wiki')}
              style={{ height: '100%' }}
            >
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Space>
                  <NodeIndexOutlined style={{ fontSize: 20, color: '#722ed1' }} />
                  <Text strong>LLM Wiki Force-Graph</Text>
                </Space>
                <Text type="secondary" style={{ fontSize: 13 }}>
                  220 節點 · 477 雙向連結 · 4-Phase Karpathy ingest→compile→query→lint
                </Text>
                <Button type="link" style={{ padding: 0 }}>
                  開啟 <ArrowRightOutlined />
                </Button>
              </Space>
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card
              hoverable
              size="small"
              onClick={() => navigate('/ai/knowledge-graph')}
              style={{ height: '100%' }}
            >
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Space>
                  <DatabaseOutlined style={{ fontSize: 20, color: '#52c41a' }} />
                  <Text strong>知識圖譜 Hub</Text>
                </Space>
                <Text type="secondary" style={{ fontSize: 13 }}>
                  2,504 canonical entities · 跨域關係查詢 · 最短路徑
                </Text>
                <Button type="link" style={{ padding: 0 }}>
                  開啟 <ArrowRightOutlined />
                </Button>
              </Space>
            </Card>
          </Col>
        </Row>
      </Card>

      <Card
        bordered={false}
        style={{ marginTop: 16, textAlign: 'center', background: 'transparent' }}
      >
        <Paragraph italic type="secondary" style={{ margin: 0 }}>
          「每次互動都是公司的時間複利，捨棄記憶等於捨棄資產。」
        </Paragraph>
        <Paragraph type="secondary" style={{ margin: 0, fontSize: 12 }}>
          — 坤哥三信念 · 記憶即資產
        </Paragraph>
      </Card>
    </div>
  );
};

export default MemoryTab;
