/**
 * Agent 主動警報卡片
 *
 * 顯示按嚴重度分組的警報統計 + 警報列表
 *
 * @version 1.0.0
 * @date 2026-03-18
 */

import React from 'react';
import { Card, Col, Row, Statistic, Table, Tag } from 'antd';
import { AlertOutlined, ClockCircleOutlined } from '@ant-design/icons';
import type { ProactiveAlertsResponse } from '../../../types/ai';

interface AgentAlertsCardProps {
  alerts: ProactiveAlertsResponse | null | undefined;
}

export const AgentAlertsCard: React.FC<AgentAlertsCardProps> = ({ alerts }) => {
  if (!alerts || alerts.total_alerts === 0) return null;

  return (
    <Card
      title={<><AlertOutlined /> 主動警報 ({alerts.total_alerts})</>}
      size="small"
    >
      <Row gutter={[16, 12]} style={{ marginBottom: 12 }}>
        {Object.entries(alerts.by_severity).map(([severity, count]) => (
          <Col xs={8} sm={6} key={severity}>
            <Statistic
              title={severity}
              value={count}
              styles={{ content: {
                color: severity === 'critical' ? '#f5222d'
                  : severity === 'warning' ? '#faad14'
                  : '#1890ff',
                fontSize: 20,
              } }}
            />
          </Col>
        ))}
      </Row>
      <Table
        dataSource={alerts.alerts.slice(0, 20)}
        rowKey={(_, i) => `alert-${i}`}
        size="small"
        pagination={false}
        scroll={{ x: 500 }}
        columns={[
          {
            title: '嚴重度',
            dataIndex: 'severity',
            key: 'severity',
            width: 80,
            render: (v: string) => (
              <Tag color={v === 'critical' ? 'red' : v === 'warning' ? 'orange' : 'blue'}>
                {v}
              </Tag>
            ),
          },
          {
            title: '類型',
            dataIndex: 'alert_type',
            key: 'type',
            width: 100,
            render: (v: string) => {
              const labels: Record<string, string> = {
                deadline: '截止日', overdue: '逾期', data_quality: '資料品質',
              };
              return <Tag icon={<ClockCircleOutlined />}>{labels[v] || v}</Tag>;
            },
          },
          {
            title: '標題',
            dataIndex: 'title',
            key: 'title',
            ellipsis: true,
          },
          {
            title: '訊息',
            dataIndex: 'message',
            key: 'message',
            ellipsis: true,
          },
        ]}
      />
    </Card>
  );
};
