/**
 * 系統監控頁 — G1 整合補接（2026-07-17）
 *
 * 背景：system_monitoring.py 後端有 9 端點（health-detailed/error-summary/recent-errors/
 *   log-files/system-metrics 等），原前端無入口（僅 review-dashboard 於 AI 面板被用）。
 *   「系統監控」選單原 redirect 到管理員面板（C5/G3 語意不符）。本頁補接後端監控能力。
 */
import React from 'react';
import { Card, Tabs, Row, Col, Statistic, Table, Alert, Progress, Tag, Empty } from 'antd';
import {
  DashboardOutlined, HeartOutlined, WarningOutlined, FileTextOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { SYSTEM_ENDPOINTS } from '../api/endpoints/core';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const post = async (url: string): Promise<any> => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const res = await apiClient.post(url, {}) as any;
  return res?.data;
};

const MetricsTab: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['system-metrics'],
    queryFn: () => post(SYSTEM_ENDPOINTS.SYSTEM_METRICS),
    refetchInterval: 10000,
  });
  const m = data?.metrics || data || {};
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} sm={8}>
        <Card loading={isLoading}>
          <Statistic title="CPU 使用率" value={m.cpu?.percent ?? '—'} suffix="%" />
          <Progress percent={Math.round(m.cpu?.percent ?? 0)} showInfo={false} status={m.cpu?.percent > 85 ? 'exception' : 'normal'} />
          <div style={{ color: '#888', fontSize: 12 }}>核心數：{m.cpu?.count ?? '—'}</div>
        </Card>
      </Col>
      <Col xs={24} sm={8}>
        <Card loading={isLoading}>
          <Statistic title="記憶體使用率" value={m.memory?.percent_used ?? '—'} suffix="%" />
          <Progress percent={Math.round(m.memory?.percent_used ?? 0)} showInfo={false} status={m.memory?.percent_used > 90 ? 'exception' : 'normal'} />
          <div style={{ color: '#888', fontSize: 12 }}>可用：{m.memory?.available_gb ?? '—'} / {m.memory?.total_gb ?? '—'} GB</div>
        </Card>
      </Col>
      <Col xs={24} sm={8}>
        <Card loading={isLoading}>
          <Statistic title="磁碟使用" value={m.disk?.used_gb ?? '—'} suffix={`/ ${m.disk?.total_gb ?? '—'} GB`} />
          {m.disk?.total_gb ? <Progress percent={Math.round((m.disk.used_gb / m.disk.total_gb) * 100)} showInfo={false} /> : null}
          <div style={{ color: '#888', fontSize: 12 }}>Python 物件數：{m.python?.object_count?.toLocaleString?.() ?? '—'}</div>
        </Card>
      </Col>
      <Col span={24}><div style={{ color: '#999', fontSize: 12 }}>更新時間：{m.timestamp ?? '—'}（每 10 秒自動刷新）</div></Col>
    </Row>
  );
};

const HealthTab: React.FC = () => {
  const { data, isLoading } = useQuery({ queryKey: ['system-health-detailed'], queryFn: () => post(SYSTEM_ENDPOINTS.HEALTH_DETAILED) });
  const checks = data?.checks || data?.components || {};
  const entries = Object.entries(checks as Record<string, unknown>);
  return (
    <Card loading={isLoading} title="詳細健康檢查">
      {entries.length === 0 ? <Empty description="無健康檢查資料" /> : (
        <Row gutter={[12, 12]}>
          {entries.map(([k, v]) => {
            const ok = typeof v === 'object' ? (v as { status?: string; ok?: boolean })?.status === 'healthy' || (v as { ok?: boolean })?.ok : !!v;
            return (
              <Col xs={12} sm={8} md={6} key={k}>
                <Tag color={ok ? 'green' : 'red'} style={{ width: '100%', padding: 8, textAlign: 'center' }}>
                  {ok ? '✓' : '✗'} {k}
                </Tag>
              </Col>
            );
          })}
        </Row>
      )}
    </Card>
  );
};

const ErrorsTab: React.FC = () => {
  const { data: summary } = useQuery({ queryKey: ['system-error-summary'], queryFn: () => post(SYSTEM_ENDPOINTS.ERROR_SUMMARY) });
  const { data: recent, isLoading } = useQuery({ queryKey: ['system-recent-errors'], queryFn: () => post(SYSTEM_ENDPOINTS.RECENT_ERRORS) });
  const errors = recent?.errors || recent?.recent_errors || [];
  return (
    <>
      {summary ? <Alert style={{ marginBottom: 16 }} type={(summary.total_errors ?? summary.total ?? 0) > 0 ? 'warning' : 'success'}
        message={`錯誤統計：總計 ${summary.total_errors ?? summary.total ?? 0} 筆`} showIcon /> : null}
      <Table
        loading={isLoading}
        rowKey={(_, i) => String(i)}
        size="small"
        locale={{ emptyText: '無最近錯誤' }}
        dataSource={Array.isArray(errors) ? errors : []}
        columns={[
          { title: '時間', dataIndex: 'timestamp', key: 'ts', width: 180 },
          { title: '等級', dataIndex: 'level', key: 'level', width: 90, render: (l) => <Tag color={l === 'ERROR' ? 'red' : 'orange'}>{l}</Tag> },
          { title: '訊息', dataIndex: 'message', key: 'msg', ellipsis: true },
        ]}
      />
    </>
  );
};

const LogsTab: React.FC = () => {
  const { data, isLoading } = useQuery({ queryKey: ['system-log-files'], queryFn: () => post(SYSTEM_ENDPOINTS.LOG_FILES) });
  const files: Record<string, unknown>[] = data?.log_files || data?.files || [];
  return (
    <Table<Record<string, unknown>>
      loading={isLoading}
      rowKey={(r, i) => String(r.name ?? i)}
      size="small"
      locale={{ emptyText: '無日誌檔案資料' }}
      dataSource={Array.isArray(files) ? files : []}
      columns={[
        { title: '檔案', dataIndex: 'name', key: 'name' },
        { title: '大小', dataIndex: 'size_mb', key: 'size', width: 120, render: (s, r) => (s != null ? `${s} MB` : r.size != null ? `${((r.size as number) / 1048576).toFixed(2)} MB` : '—') },
        { title: '最後修改', dataIndex: 'modified', key: 'modified', width: 200 },
      ]}
    />
  );
};

const SystemMonitoringPage: React.FC = () => {
  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 16 }}><DashboardOutlined /> 系統監控</h2>
      <Tabs
        items={[
          { key: 'metrics', label: <span><DashboardOutlined /> 系統指標</span>, children: <MetricsTab /> },
          { key: 'health', label: <span><HeartOutlined /> 健康檢查</span>, children: <HealthTab /> },
          { key: 'errors', label: <span><WarningOutlined /> 錯誤日誌</span>, children: <ErrorsTab /> },
          { key: 'logs', label: <span><FileTextOutlined /> 日誌檔案</span>, children: <LogsTab /> },
        ]}
      />
    </div>
  );
};

export default SystemMonitoringPage;
