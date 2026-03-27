/**
 * 派工進度彙整 Tab — 對標 OpenClaw 進度彙整展示
 *
 * 已完成/進行中/逾期分類 + 負責人統計 + 關鍵提醒
 *
 * @version 1.0.0
 * @created 2026-03-27
 */

import React from 'react';
import { Card, Row, Col, Tag, Table, Empty, Spin, Statistic, Alert, Typography, Space, Badge, Tooltip } from 'antd';
import {
  CheckCircleOutlined, ClockCircleOutlined, ExclamationCircleOutlined,
  UserOutlined, FileTextOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';

const { Text } = Typography;

interface DispatchItem {
  dispatch_id: number;
  dispatch_no: string;
  project_name: string;
  case_handler: string | null;
  deadline_date: string | null;
  status: string;
  overdue_days: number;
  completed_records: number;
  total_records: number;
}

interface ProgressReport {
  year: number;
  completed: DispatchItem[];
  in_progress: DispatchItem[];
  overdue: DispatchItem[];
  pending: DispatchItem[];
  key_alerts: string[];
  handler_summary: Record<string, Record<string, number>>;
}

const fetchProgressReport = () =>
  apiClient.post<ProgressReport>('/taoyuan-dispatch/progress-report', {});

// ── 統計卡 ──

const StatsRow: React.FC<{ data: ProgressReport }> = ({ data }) => (
  <Row gutter={12}>
    <Col span={6}>
      <Card size="small">
        <Statistic
          title="已完成"
          value={data.completed.length}
          valueStyle={{ color: '#52c41a' }}
          prefix={<CheckCircleOutlined />}
        />
      </Card>
    </Col>
    <Col span={6}>
      <Card size="small">
        <Statistic
          title="進行中"
          value={data.in_progress.length + data.pending.length}
          valueStyle={{ color: '#1890ff' }}
          prefix={<ClockCircleOutlined />}
        />
      </Card>
    </Col>
    <Col span={6}>
      <Card size="small">
        <Statistic
          title="逾期"
          value={data.overdue.length}
          valueStyle={{ color: '#ff4d4f' }}
          prefix={<ExclamationCircleOutlined />}
        />
      </Card>
    </Col>
    <Col span={6}>
      <Card size="small">
        <Statistic
          title="總計"
          value={data.completed.length + data.in_progress.length + data.overdue.length + data.pending.length}
          prefix={<FileTextOutlined />}
        />
      </Card>
    </Col>
  </Row>
);

// ── 關鍵提醒 ──

const AlertsCard: React.FC<{ alerts: string[] }> = ({ alerts }) => {
  if (!alerts.length) return null;
  return (
    <Card size="small" title="關鍵提醒" style={{ marginTop: 12 }}>
      {alerts.map((a, i) => (
        <Alert
          key={i}
          type={a.includes('逾期') ? 'error' : a.includes('到期') ? 'warning' : 'info'}
          message={a}
          showIcon
          style={{ marginBottom: i < alerts.length - 1 ? 8 : 0 }}
        />
      ))}
    </Card>
  );
};

// ── 逾期列表 ──

const OverdueTable: React.FC<{ items: DispatchItem[] }> = ({ items }) => {
  if (!items.length) return null;

  const columns = [
    {
      title: '派工單號',
      dataIndex: 'dispatch_no',
      key: 'no',
      width: 160,
      render: (no: string) => <Text strong style={{ fontSize: 12 }}>{no.replace(/115年_/, '')}</Text>,
    },
    {
      title: '工程名稱',
      dataIndex: 'project_name',
      key: 'name',
      ellipsis: true,
      render: (name: string) => <Tooltip title={name}><Text style={{ fontSize: 12 }}>{name}</Text></Tooltip>,
    },
    {
      title: '負責人',
      dataIndex: 'case_handler',
      key: 'handler',
      width: 80,
      render: (h: string | null) => h ? <Tag icon={<UserOutlined />}>{h}</Tag> : <Tag>未指派</Tag>,
    },
    {
      title: '逾期',
      dataIndex: 'overdue_days',
      key: 'overdue',
      width: 80,
      sorter: (a: DispatchItem, b: DispatchItem) => b.overdue_days - a.overdue_days,
      render: (days: number) => <Tag color="error">{days} 天</Tag>,
    },
  ];

  return (
    <Card
      size="small"
      title={<span><ExclamationCircleOutlined style={{ color: '#ff4d4f' }} /> 逾期派工單 ({items.length})</span>}
      style={{ marginTop: 12 }}
    >
      <Table dataSource={items} columns={columns} rowKey="dispatch_id" size="small" pagination={false} />
    </Card>
  );
};

// ── 負責人統計 ──

const HandlerSummary: React.FC<{ summary: Record<string, Record<string, number>> }> = ({ summary }) => {
  const data = Object.entries(summary).map(([handler, stats]) => ({
    handler,
    completed: stats.completed ?? 0,
    in_progress: stats.in_progress ?? 0,
    overdue: stats.overdue ?? 0,
    total: stats.total ?? 0,
  }));

  return (
    <Card size="small" title={<span><UserOutlined /> 負責人統計</span>} style={{ marginTop: 12 }}>
      <Space wrap>
        {data.map(d => (
          <Card key={d.handler} size="small" style={{ width: 140 }}>
            <Text strong style={{ fontSize: 13 }}>{d.handler}</Text>
            <div style={{ marginTop: 4 }}>
              <Badge status="success" text={<Text style={{ fontSize: 11 }}>完成 {d.completed ?? 0}</Text>} />
              <br />
              {(d.overdue ?? 0) > 0 ? (
                <Badge status="error" text={<Text style={{ fontSize: 11, color: '#ff4d4f' }}>逾期 {d.overdue}</Text>} />
              ) : (
                <Badge status="processing" text={<Text style={{ fontSize: 11 }}>進行 {d.in_progress ?? 0}</Text>} />
              )}
            </div>
          </Card>
        ))}
      </Space>
    </Card>
  );
};

// ── 主元件 ──

export const DispatchProgressTab: React.FC = () => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dispatch-progress-report'],
    queryFn: fetchProgressReport,
    staleTime: 5 * 60_000,
  });

  if (isLoading) return <Spin tip="載入派工進度..." style={{ display: 'block', padding: 40, textAlign: 'center' }} />;
  if (isError || !data) return <Empty description="無法載入派工進度" />;

  return (
    <div>
      <StatsRow data={data} />
      <AlertsCard alerts={data.key_alerts} />
      <OverdueTable items={data.overdue} />
      <HandlerSummary summary={data.handler_summary} />
    </div>
  );
};
