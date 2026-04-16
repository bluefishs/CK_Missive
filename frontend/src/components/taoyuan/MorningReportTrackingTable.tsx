/**
 * MorningReportTrackingTable — 晨報追蹤表格（可嵌入 DispatchOverviewTab）
 *
 * 從 MorningReportTrackingTab 抽出的表格元件。
 * 接收 morning-status API 資料 + 外部篩選條件。
 */
import React, { useMemo, useState } from 'react';
import { Table, Tag, Card, Select, Space, Typography, Tooltip, Input } from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CalendarOutlined,
  ExclamationCircleOutlined,
  SyncOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import { ROUTES } from '../../router/types';

const { Text } = Typography;

export interface MorningStatusItem {
  id: number;
  dispatch_no: string;
  deadline: string;
  project_name: string;
  handler: string;
  display_status: string;
  work_category_label: string;
  completed_count: number;
  total_records: number;
  progress: string;
  next_event: string | null;
}

export interface MorningStatusResponse {
  success: boolean;
  total: number;
  summary: Record<string, number>;
  items: MorningStatusItem[];
}

const STATUS_CONFIG: Record<string, { color: string; icon: React.ReactNode; order: number }> = {
  '逾期':     { color: 'red',     icon: <ExclamationCircleOutlined />, order: 0 },
  '闕漏紀錄': { color: 'magenta', icon: <QuestionCircleOutlined />,   order: 1 },
  '進行中':   { color: 'orange',  icon: <SyncOutlined />,             order: 2 },
  '排程中':   { color: 'blue',    icon: <CalendarOutlined />,         order: 3 },
  '待結案':   { color: 'gold',    icon: <ClockCircleOutlined />,      order: 4 },
  '已交付':   { color: 'green',   icon: <CheckCircleOutlined />,      order: 5 },
  '已結案':   { color: 'default', icon: <CheckCircleOutlined />,      order: 6 },
};

interface Props {
  data: MorningStatusResponse | undefined;
  isLoading: boolean;
  externalFilter?: string;
}

export const MorningReportTrackingTable: React.FC<Props> = ({
  data,
  isLoading,
  externalFilter,
}) => {
  const navigate = useNavigate();
  const [filterStatus, setFilterStatus] = useState<string | undefined>(undefined);
  const [searchText, setSearchText] = useState('');

  const items = useMemo(() => (data?.items ?? []) as MorningStatusItem[], [data]);
  const summary = useMemo(() => data?.summary ?? {}, [data]);

  // 合併外部 + 內部篩選
  const activeFilter = externalFilter || filterStatus;

  const filteredItems = useMemo(() => {
    let result = items;
    if (activeFilter) {
      // 「已交付」卡片點擊時也包含「已結案」
      if (activeFilter === '已交付') {
        result = result.filter(i => i.display_status === '已交付' || i.display_status === '已結案');
      } else {
        result = result.filter(i => i.display_status === activeFilter);
      }
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
  }, [items, activeFilter, searchText]);

  const handlerOptions = useMemo(() => {
    const set = new Set(items.map(i => i.handler).filter(Boolean));
    return Array.from(set).sort().map(h => ({ text: h, value: h }));
  }, [items]);

  const statusFilterOptions = useMemo(() =>
    Object.keys(STATUS_CONFIG).map(s => ({ text: s, value: s })),
  []);

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

  return (
    <Card
      size="small"
      title="派工狀態追蹤"
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
          {!externalFilter && (
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
          )}
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
  );
};
