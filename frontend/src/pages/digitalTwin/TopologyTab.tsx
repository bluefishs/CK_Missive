/**
 * Agent 系統拓撲 Tab
 *
 * 顯示 Agent 聯邦節點的拓撲卡片視圖。
 * 由 UnifiedAgentPage 雙模式共用。
 */
import React from 'react';
import { Row, Col, Typography, Badge, Card, Alert, Spin, Tag, Space } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { getAgentTopology } from '../../api/digitalTwin';

const { Text } = Typography;

interface TopologyNode {
  id: string;
  label: string;
  type: string;
  status: string;
  project: string;
  capabilities?: string[];
}

const TYPE_COLORS: Record<string, string> = {
  leader: '#722ed1', engine: '#1890ff', role: '#52c41a', plugin: '#faad14',
};
const STATUS_COLORS: Record<string, 'success' | 'error' | 'default' | 'processing'> = {
  active: 'success', unknown: 'default', error: 'error', busy: 'processing',
};

export const TopologyTab: React.FC = () => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dt-topology'],
    queryFn: getAgentTopology,
    staleTime: 5 * 60_000,
  });

  if (isLoading) return <Spin tip="載入拓撲圖..." style={{ display: 'block', padding: 40, textAlign: 'center' }} />;
  if (isError) return <Alert type="warning" showIcon message="拓撲資料載入失敗" />;

  const nodes = (data?.nodes ?? []) as TopologyNode[];

  return (
    <Row gutter={[12, 12]}>
      {nodes.map(node => (
        <Col xs={24} sm={12} md={8} key={node.id}>
          <Card size="small" style={{ borderLeft: `3px solid ${TYPE_COLORS[node.type] ?? '#d9d9d9'}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <Text strong style={{ fontSize: 13 }}>{node.label}</Text>
              <Badge status={STATUS_COLORS[node.status] ?? 'default'} text={node.status} />
            </div>
            <Text type="secondary" style={{ fontSize: 11 }}>{node.project}</Text>
            {node.capabilities && (
              <div style={{ marginTop: 6 }}>
                <Space wrap size={[2, 2]}>
                  {node.capabilities.slice(0, 4).map(c => <Tag key={c} style={{ fontSize: 10 }}>{c}</Tag>)}
                </Space>
              </div>
            )}
          </Card>
        </Col>
      ))}
    </Row>
  );
};
