/**
 * 晨報追蹤 Tab — 派工單狀態分佈 + 排序篩選表格
 *
 * 對應 API: POST /taoyuan-dispatch/dispatch/morning-status
 *
 * display_status 分層：
 *   已交付 / 已結案 / 排程中 / 進行中 / 逾期 / 闕漏紀錄 / 待結案
 */
import React, { useMemo, useState } from 'react';
import { Table, Tag, Card, Statistic, Row, Col, Select, Space, Typography, Tooltip, Input } from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CalendarOutlined,
  ExclamationCircleOutlined,
  WarningOutlined,
  SyncOutlined,
  QuestionCircleOutlined,
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
  display_status: string;
  work_category: string;
  work_category_label: string;
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

// display_status 顯示設定（排序依業務重要度）
const STATUS_CONFIG: Record<string, { color: string; icon: React.ReactNode; order: number }> = {
  '逾期':     { color: 'red',     icon: <ExclamationCircleOutlined />, order: 0 },
  '闕漏紀錄': { color: 'magenta', icon: <QuestionCircleOutlined />,   order: 1 },
  '進行中':   { color: 'orange',  icon: <SyncOutlined />,             order: 2 },
  '排程中':   { color: 'blue',    icon: <CalendarOutlined />,         order: 3 },
  '待結案':   { color: 'gold',    icon: <ClockCircleOutlined />,      order: 4 },
  '已交付':   { color: 'green',   icon: <CheckCircleOutlined />,      order: 5 },
  '已結案':   { color: 'default', icon: <CheckCircleOutlined />,      order: 6 },
};

export const MorningReportTrackingTab: React.FC = () => {
  const navigate = useNavigate();
  const [filterStatus, setFilterStatus] = useState<string | undefined>(undefined);
  const [searchText, setSearchText] = useState('');

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
    let result = items;
    if (filterStatus) {
      result = result.filter(i => i.display_status === filterStatus);
    }
    if (searchText) {
      const kw = searchText.toLowerCase();
      result = result.filter(i =>
        i.dispatch_no.toLowerCase().includes(kw) ||
        i.project_name.toLowerCase().includes(kw) ||
        i.handler.includes(kw)
      );
    }
    return result;
  }, [items, filterStatus, searchText]);

  // 統計卡片數據
  const stats = useMemo(() => {
    const done = (summary['已交付'] ?? 0) + (summary['已結案'] ?? 0);
    const overdue = summary['逾期'] ?? 0;
    const missing = summary['闕漏紀錄'] ?? 0;
    const inProgress = summary['進行中'] ?? 0;
    const scheduled = summary['排程中'] ?? 0;
    const pendingClosure = summary['待結案'] ?? 0;
    const actionNeeded = overdue + missing;
    return { done, actionNeeded, overdue, missing, inProgress, scheduled, pendingClosure, total: data?.total ?? 0 };
  }, [summary, data]);

  // 承辦人篩選選項
  const handlerOptions = useMemo(() => {
    const set = new Set(items.map(i => i.handler).filter(Boolean));
    return Array.from(set).sort().map(h => ({ text: h, value: h }));
  }, [items]);

  // 狀態篩選選項
  const statusFilterOptions = useMemo(() =>
    Object.keys(STATUS_CONFIG).map(s => ({ text: s, value: s })),
  []);

  // 作業類別篩選選項
  const categoryOptions = useMemo(() => {
    const set = new Set(items.map(i => i.work_category_label).filter(v => v && v !== '-'));
    return Array.from(set).sort().map(c => ({ text: c, value: c }));
  }, [items]);

  const columns: ColumnsType<MorningStatusItem> = [
    {
      title: '派工單號',
      dataIndex: 'dispatch_no',
      width: 160,
      sorter: (a, b) => a.dispatch_no.localeCompare(b.dispatch_no),
      render: (text: string, record) => (
        <a onClick={() => navigate(`${ROUTES.TAOYUAN_DISPATCH}/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: '工程名稱',
      dataIndex: 'project_name',
      ellipsis: true,
      sorter: (a, b) => a.project_name.localeCompare(b.project_name),
    },
    {
      title: '承辦',
      dataIndex: 'handler',
      width: 80,
      filters: handlerOptions,
      onFilter: (value, record) => record.handler === value,
    },
    {
      title: '作業類別',
      dataIndex: 'work_category_label',
      width: 100,
      filters: categoryOptions,
      onFilter: (value, record) => record.work_category_label === value,
      render: (text: string) =>
        text && text !== '-' ? <Tag>{text}</Tag> : <Text type="secondary">-</Text>,
    },
    {
      title: '狀態',
      dataIndex: 'display_status',
      width: 100,
      filters: statusFilterOptions,
      onFilter: (value, record) => record.display_status === value,
      sorter: (a, b) =>
        (STATUS_CONFIG[a.display_status]?.order ?? 9) - (STATUS_CONFIG[b.display_status]?.order ?? 9),
      defaultSortOrder: 'ascend',
      render: (status: string) => {
        const cfg = STATUS_CONFIG[status] || { color: 'default', icon: null };
        return <Tag color={cfg.color} icon={cfg.icon}>{status}</Tag>;
      },
    },
    {
      title: '進度',
      width: 80,
      sorter: (a, b) => {
        const ra = a.total_records ? a.completed_count / a.total_records : -1;
        const rb = b.total_records ? b.completed_count / b.total_records : -1;
        return ra - rb;
      },
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
      sorter: (a, b) => (a.deadline || '').localeCompare(b.deadline || ''),
    },
    {
      title: '交付期限',
      dataIndex: 'next_event',
      width: 110,
      sorter: (a, b) => (a.next_event || '').localeCompare(b.next_event || ''),
      render: (text: string | null) =>
        text ? <Tag icon={<CalendarOutlined />} color="blue">{text}</Tag> : <Text type="secondary">-</Text>,
    },
  ];

  const toggleFilter = (status: string) => {
    setFilterStatus(prev => prev === status ? undefined : status);
  };

  return (
    <div>
      {/* 統計卡片 — #6 已完成/交付排第一 */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small" hoverable onClick={() => toggleFilter('已交付')}
                style={{ borderTop: filterStatus === '已交付' ? '3px solid #52c41a' : undefined }}>
            <Statistic
              title="已完成/交付"
              value={stats.done}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
              suffix={<Text type="secondary" style={{ fontSize: 12 }}>/{stats.total}</Text>}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" hoverable onClick={() => toggleFilter('排程中')}
                style={{ borderTop: filterStatus === '排程中' ? '3px solid #1890ff' : undefined }}>
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
          <Card size="small" hoverable onClick={() => toggleFilter('進行中')}
                style={{ borderTop: filterStatus === '進行中' ? '3px solid #fa8c16' : undefined }}>
            <Statistic
              title="進行中"
              value={stats.inProgress}
              valueStyle={{ color: '#fa8c16' }}
              prefix={<SyncOutlined />}
              suffix="筆"
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" hoverable onClick={() => toggleFilter('逾期')}
                style={{ borderTop: filterStatus === '逾期' ? '3px solid #cf1322' : undefined }}>
            <Statistic
              title="需處理"
              value={stats.actionNeeded}
              valueStyle={{ color: stats.actionNeeded > 0 ? '#cf1322' : '#999' }}
              prefix={<WarningOutlined />}
              suffix={stats.missing > 0
                ? <Text type="secondary" style={{ fontSize: 11 }}>逾期{stats.overdue}+闕漏{stats.missing}</Text>
                : '筆'
              }
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
            <Input.Search
              placeholder="搜尋單號/工程/承辦"
              allowClear
              size="small"
              style={{ width: 180 }}
              onSearch={setSearchText}
              onChange={e => !e.target.value && setSearchText('')}
            />
            <Select
              value={filterStatus}
              onChange={setFilterStatus}
              allowClear
              placeholder="篩選狀態"
              style={{ width: 140 }}
              size="small"
              options={Object.entries(STATUS_CONFIG).map(([label, _cfg]) => ({
                value: label,
                label: `${label} (${summary[label] ?? 0})`,
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
          pagination={{ pageSize: 25, showSizeChanger: true, showTotal: (t) => `共 ${t} 筆` }}
          scroll={{ x: 950 }}
        />
      </Card>
    </div>
  );
};
