/**
 * MorningReportTrackingTable — 晨報追蹤表格（可嵌入 DispatchOverviewTab）
 *
 * 從 MorningReportTrackingTab 抽出的表格元件。
 * 接收 morning-status API 資料 + 外部篩選條件。
 */
import React, { useMemo, useState } from 'react';
import { Table, Tag, Card, Select, Space, Typography, Tooltip, Input, DatePicker, App } from 'antd';
import { useMutation } from '@tanstack/react-query';
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
import dayjs from 'dayjs';
import { ROUTES } from '../../router/types';
import { apiClient } from '../../api/client';
import { TAOYUAN_DISPATCH_ENDPOINTS } from '../../api/endpoints';
import { useDispatchCacheInvalidator } from '../../hooks/taoyuan/useDispatchCacheInvalidator';

const { Text } = Typography;

export interface MorningStatusItem {
  id: number;
  dispatch_no: string;
  deadline: string;
  project_name: string;
  handler: string;
  survey_unit: string;
  display_status: string;
  work_category_label: string;
  work_types: string[];
  per_type_progress: { work_type_id: number; work_type: string; deadline: string | null; total: number; completed: number }[];
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

// v5.8.0 最終版：4 大類 — 顯示順序：已完成/交付 → 排程中 → 預警案件 → 闕漏紀錄
// legacy keys 保留歷史相容；新系統不產生
const STATUS_CONFIG: Record<string, { color: string; icon: React.ReactNode; order: number; hint: string }> = {
  '已完成/交付':  { color: 'green',   icon: <CheckCircleOutlined />,      order: 0, hint: '作業已完成、交付或結案' },
  '排程中':       { color: 'blue',    icon: <CalendarOutlined />,         order: 1, hint: '交付期限 > 7 天 — 等時間到即執行' },
  '預警案件':     { color: 'red',     icon: <ExclamationCircleOutlined />, order: 2, hint: '交付期限 ≤ 7 天（含已逾期）— 立即處理' },
  '闕漏紀錄':     { color: 'orange',  icon: <QuestionCircleOutlined />,   order: 3, hint: '缺律定期限或作業紀錄 — 需補建期限、事件或 work_record' },

  // legacy（歷史相容，新系統不產生）
  '已結案':       { color: 'green',   icon: <CheckCircleOutlined />,      order: 0, hint: '（舊狀態，等同「已完成/交付」）' },
  '已交付':       { color: 'green',   icon: <CheckCircleOutlined />,      order: 0, hint: '（舊狀態，等同「已完成/交付」）' },
  '待結案':       { color: 'green',   icon: <ClockCircleOutlined />,      order: 0, hint: '（舊狀態，等同「已完成/交付」）' },
  '逾期':         { color: 'red',     icon: <ExclamationCircleOutlined />, order: 2, hint: '（舊狀態，等同「預警案件」）' },
  '需處理':       { color: 'orange',  icon: <SyncOutlined />,             order: 3, hint: '（舊狀態，等同「闕漏紀錄」）' },
  '進行中':       { color: 'orange',  icon: <SyncOutlined />,             order: 3, hint: '（舊狀態，等同「闕漏紀錄」）' },
};

// v5.8.1：4 主類 → legacy 值映射（單一真理來源，供 filter 與卡片合計共用）
const CATEGORY_LEGACY_MAP: Record<string, string[]> = {
  '已完成/交付': ['已完成/交付', '已交付', '已結案', '待結案'],
  '排程中':      ['排程中'],
  '預警案件':    ['預警案件', '逾期'],
  '闕漏紀錄':    ['闕漏紀錄', '需處理', '進行中'],
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
  const { message } = App.useApp();
  const dispatchCache = useDispatchCacheInvalidator();
  const [filterStatus, setFilterStatus] = useState<string | undefined>(undefined);
  const [searchText, setSearchText] = useState('');

  const updateDeadlineMutation = useMutation({
    mutationFn: (params: { work_type_id: number; deadline: string | null }) =>
      apiClient.post(
        `${TAOYUAN_DISPATCH_ENDPOINTS.WORK_TYPE_UPDATE_DEADLINE}?work_type_id=${params.work_type_id}${params.deadline ? `&deadline=${params.deadline}` : ''}`,
        {},
      ),
    onSuccess: () => {
      message.success('交付期限已更新');
      dispatchCache.invalidateMorningStatusOnly();
    },
  });

  const items = useMemo(() => (data?.items ?? []) as MorningStatusItem[], [data]);
  const summary = useMemo(() => data?.summary ?? {}, [data]);

  // 合併外部 + 內部篩選
  const activeFilter = externalFilter || filterStatus;

  const filteredItems = useMemo(() => {
    let result = items;
    if (activeFilter) {
      // 4 主類：展開所含 legacy 值；非主類（例如外部直接傳 legacy 名）→ 精確比對
      const allowed = CATEGORY_LEGACY_MAP[activeFilter];
      if (allowed) {
        result = result.filter(i => allowed.includes(i.display_status));
      } else if (activeFilter === '__action_needed__') {
        // legacy 別名：動作需求合集（預警 + 闕漏）
        const merged = [
          ...(CATEGORY_LEGACY_MAP['預警案件'] ?? []),
          ...(CATEGORY_LEGACY_MAP['闕漏紀錄'] ?? []),
        ];
        result = result.filter(i => merged.includes(i.display_status));
      } else {
        result = result.filter(i => i.display_status === activeFilter);
      }
    }
    if (searchText) {
      const kw = searchText.toLowerCase();
      result = result.filter(i =>
        i.dispatch_no.toLowerCase().includes(kw) ||
        i.project_name.toLowerCase().includes(kw) ||
        i.handler.includes(kw) ||
        (i.survey_unit && i.survey_unit.toLowerCase().includes(kw))
      );
    }
    return result;
  }, [items, activeFilter, searchText]);

  const handlerOptions = useMemo(() => {
    const set = new Set(items.map(i => i.handler).filter(Boolean));
    return Array.from(set).sort().map(h => ({ text: h, value: h }));
  }, [items]);

  // v5.8.1：只列 4 主類（不再顯示 legacy 值避免篩選介面雜亂）
  const statusFilterOptions = useMemo(() => [
    { text: '已完成/交付', value: '已完成/交付' },
    { text: '排程中',      value: '排程中' },
    { text: '預警案件',    value: '預警案件' },
    { text: '闕漏紀錄',    value: '闕漏紀錄' },
  ], []);

  const categoryOptions = useMemo(() => {
    const set = new Set<string>();
    for (const item of items) {
      for (const t of item.work_types) set.add(t);
      if (item.work_category_label && item.work_category_label !== '-') {
        set.add(item.work_category_label);
      }
    }
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
      title: '查估單位',
      dataIndex: 'survey_unit',
      width: 100,
      ellipsis: true,
      filters: (() => {
        const set = new Set(items.map(i => i.survey_unit).filter(Boolean));
        return Array.from(set).sort().map(s => ({ text: s, value: s }));
      })(),
      onFilter: (value, record) => record.survey_unit === value,
    },
    {
      title: '作業類別',
      width: 160,
      filters: categoryOptions,
      onFilter: (value, record) =>
        record.work_types.some(t => t === value) || record.work_category_label === value,
      render: (_: unknown, record) => {
        if (record.work_types.length > 0) {
          return (
            <Space size={2} wrap>
              {record.work_types.map(t => (
                <Tag key={t} style={{ fontSize: 11, margin: 1 }}>{t}</Tag>
              ))}
            </Space>
          );
        }
        const label = record.work_category_label;
        return label && label !== '-' ? <Tag>{label}</Tag> : <Text type="secondary">-</Text>;
      },
    },
    {
      title: '狀態',
      dataIndex: 'display_status',
      width: 100,
      filters: statusFilterOptions,
      // v5.8.1：4 主類 filter 時，內部展開 legacy 值比對
      onFilter: (value, record) => {
        const allowed = CATEGORY_LEGACY_MAP[value as string];
        if (allowed) return allowed.includes(record.display_status);
        return record.display_status === value;
      },
      sorter: (a, b) =>
        (STATUS_CONFIG[a.display_status]?.order ?? 9) - (STATUS_CONFIG[b.display_status]?.order ?? 9),
      defaultSortOrder: 'ascend',
      render: (status: string) => {
        const cfg = STATUS_CONFIG[status] || { color: 'default', icon: null, hint: '' };
        const tagEl = <Tag color={cfg.color} icon={cfg.icon}>{status}</Tag>;
        return cfg.hint ? <Tooltip title={cfg.hint}>{tagEl}</Tooltip> : tagEl;
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
        scroll={{ x: 1050 }}
        expandable={{
          rowExpandable: (record) => record.per_type_progress.length >= 2,
          expandedRowRender: (record) => (
            <table style={{ width: '100%', marginLeft: 32, fontSize: 13 }}>
              <tbody>
                {record.per_type_progress.map((pt) => {
                  const pct = pt.total ? Math.round((pt.completed / pt.total) * 100) : 0;
                  const color = pct === 100 ? 'green' : pct >= 50 ? 'blue' : 'orange';
                  return (
                    <tr key={pt.work_type_id}>
                      <td style={{ padding: '4px 8px', width: 200 }}>
                        <Tag style={{ margin: 0 }}>{pt.work_type}</Tag>
                      </td>
                      <td style={{ padding: '4px 8px', width: 70 }}>
                        <Tag color={color} style={{ margin: 0 }}>{pt.completed}/{pt.total}</Tag>
                      </td>
                      <td style={{ padding: '4px 8px' }}>
                        <DatePicker
                          size="small"
                          value={pt.deadline ? dayjs(pt.deadline) : null}
                          placeholder="設定交付期限"
                          onChange={(d) => updateDeadlineMutation.mutate({
                            work_type_id: pt.work_type_id,
                            deadline: d ? d.format('YYYY-MM-DD') : null,
                          })}
                          style={{ width: 130 }}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ),
        }}
      />
    </Card>
  );
};
