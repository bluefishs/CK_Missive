/**
 * 晨報追蹤 Tab — 派工單 closure_level 分佈 + 可篩選表格
 *
 * 對應 API: POST /taoyuan-dispatch/dispatch/morning-status
 */
import React, { useMemo, useState } from 'react';
import { Table, Tag, Card, Statistic, Row, Col, Select, Space, Typography, Tooltip } from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CalendarOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import { apiClient } from '../../api/client';
import { TAOYUAN_DISPATCH_ENDPOINTS } from '../../api/endpoints';
import { ROUTES } from '../../router/types';

const { Text } = Typography;

interface MorningStatusItem {
  id: number;
  dispatch_no: string;
  deadline: string;
  deadline_raw: string;
  project_name: string;
  handler: string;
  sub_case: string;
  closure_level: string;
  completed_count: number;
  total_records: number;
  progress: string;
  next_event: string | null;
}

interface MorningStatusResponse {
  success: boolean;
  total: number;
  summary: Record<string, number>;
  items: MorningStatusItem[];
}

const CLOSURE_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode; order: number }> = {
  active: { label: '逾期', color: 'red', icon: <ExclamationCircleOutlined />, order: 0 },
  scheduled: { label: '排程中', color: 'blue', icon: <CalendarOutlined />, order: 1 },
  pending_closure: { label: '待結案', color: 'orange', icon: <FileTextOutlined />, order: 2 },
  all_completed: { label: '已完成', color: 'green', icon: <CheckCircleOutlined />, order: 3 },
  delivered: { label: '已交付', color: 'green', icon: <CheckCircleOutlined />, order: 4 },
  closed: { label: '已結案', color: 'default', icon: <CheckCircleOutlined />, order: 5 },
};

export const MorningReportTrackingTab: React.FC = () => {
  const navigate = useNavigate();
  const [filterLevel, setFilterLevel] = useState<string | undefined>(undefined);

  const { data, isLoading } = useQuery({
    queryKey: ['dispatch-morning-status'],
    queryFn: () =>
      apiClient.post<MorningStatusResponse>(
        TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_MORNING_STATUS, {}
      ),
    staleTime: 60_000,
  });

  const items = useMemo(() => data?.items ?? [], [data]);
  const summary = useMemo(() => data?.summary ?? {}, [data]);

  const filteredItems = useMemo(() => {
    if (!filterLevel) return items;
    return items.filter(i => i.closure_level === filterLevel);
  }, [items, filterLevel]);

  // 統計卡片數據
  const stats = useMemo(() => {
    const active = (summary.active ?? 0);
    const scheduled = (summary.scheduled ?? 0);
    const pendingClosure = (summary.pending_closure ?? 0);
    const done = (summary.delivered ?? 0) + (summary.all_completed ?? 0) + (summary.closed ?? 0);
    return { active, scheduled, pendingClosure, done, total: data?.total ?? 0 };
  }, [summary, data]);

  const columns: ColumnsType<MorningStatusItem> = [
    {
      title: '派工單號',
      dataIndex: 'dispatch_no',
      width: 160,
      render: (text: string, record) => (
        <a onClick={() => navigate(`${ROUTES.TAOYUAN_DISPATCH}/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: '工程名稱',
      dataIndex: 'project_name',
      ellipsis: true,
    },
    {
      title: '承辦',
      dataIndex: 'handler',
      width: 80,
    },
    {
      title: '狀態',
      dataIndex: 'closure_level',
      width: 100,
      render: (level: string) => {
        const cfg = CLOSURE_CONFIG[level] || { label: level, color: 'default', icon: null };
        return <Tag color={cfg.color} icon={cfg.icon}>{cfg.label}</Tag>;
      },
      sorter: (a, b) =>
        (CLOSURE_CONFIG[a.closure_level]?.order ?? 9) - (CLOSURE_CONFIG[b.closure_level]?.order ?? 9),
      defaultSortOrder: 'ascend',
    },
    {
      title: '進度',
      width: 90,
      render: (_: unknown, record) => {
        if (!record.total_records) return <Text type="secondary">-</Text>;
        const pct = Math.round((record.completed_count / record.total_records) * 100);
        const color = pct === 100 ? 'green' : pct >= 50 ? 'blue' : 'orange';
        return (
          <Tooltip title={record.progress}>
            <Tag color={color}>{record.completed_count}/{record.total_records}</Tag>
          </Tooltip>
        );
      },
    },
    {
      title: '履約期限',
      dataIndex: 'deadline',
      width: 110,
    },
    {
      title: '下次事件',
      dataIndex: 'next_event',
      width: 110,
      render: (text: string | null) =>
        text ? <Tag icon={<CalendarOutlined />} color="blue">{text}</Tag> : <Text type="secondary">-</Text>,
    },
  ];

  return (
    <div>
      {/* 統計卡片 */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small" hoverable onClick={() => setFilterLevel(filterLevel === 'active' ? undefined : 'active')}>
            <Statistic
              title="逾期"
              value={stats.active}
              valueStyle={{ color: stats.active > 0 ? '#cf1322' : '#999' }}
              prefix={<ExclamationCircleOutlined />}
              suffix="筆"
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" hoverable onClick={() => setFilterLevel(filterLevel === 'scheduled' ? undefined : 'scheduled')}>
            <Statistic
              title="排程中"
              value={stats.scheduled}
              valueStyle={{ color: '#1890ff' }}
              prefix={<CalendarOutlined />}
              suffix="筆"
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" hoverable onClick={() => setFilterLevel(filterLevel === 'pending_closure' ? undefined : 'pending_closure')}>
            <Statistic
              title="待結案"
              value={stats.pendingClosure}
              valueStyle={{ color: '#fa8c16' }}
              prefix={<ClockCircleOutlined />}
              suffix="筆"
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" hoverable onClick={() => setFilterLevel(undefined)}>
            <Statistic
              title="已完成/交付"
              value={stats.done}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
              suffix={<Text type="secondary" style={{ fontSize: 12 }}>/{stats.total}</Text>}
            />
          </Card>
        </Col>
      </Row>

      {/* 篩選 + 表格 */}
      <Card
        size="small"
        title="派工晨報狀態"
        extra={
          <Space>
            <Select
              value={filterLevel}
              onChange={setFilterLevel}
              allowClear
              placeholder="篩選狀態"
              style={{ width: 140 }}
              options={Object.entries(CLOSURE_CONFIG).map(([k, v]) => ({
                value: k,
                label: `${v.label} (${summary[k] ?? 0})`,
              }))}
            />
          </Space>
        }
      >
        <Table
          dataSource={filteredItems}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          size="small"
          pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 筆` }}
          scroll={{ x: 800 }}
        />
      </Card>
    </div>
  );
};
