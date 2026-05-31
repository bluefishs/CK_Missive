/**
 * Scheduler Events + Retrospective Reports Page (v6.13, 2026-05-31)
 *
 * Owner: 前端需提供專案排程紀錄追溯表 + 覆盤紀錄
 *
 * 路徑: /admin/scheduler-events
 * 包含 3 tabs:
 *   1. Cron Events 歷史
 *   2. Job 統計摘要
 *   3. Daily Retrospective 報告
 */
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Tabs, Table, Tag, Card, Typography, Space, Drawer, Spin } from 'antd';
import { ClockCircleOutlined, BarChartOutlined, FileTextOutlined } from '@ant-design/icons';
import { apiClient } from '../api/client';

const { Title, Text } = Typography;

interface CronEvent {
  ts: string;
  job_id: string;
  status: 'success' | 'failure';
  duration_ms?: number;
  error?: string;
}

interface JobStat {
  job_id: string;
  success_count: number;
  failure_count: number;
  total_count: number;
  success_rate_pct: number;
  avg_duration_ms: number;
  last_event: CronEvent | null;
}

interface ReportSummary {
  date: string;
  filename: string;
  size_bytes: number;
  mtime: string;
  overall: string;
  summary: string;
}

interface EventsResp { events: CronEvent[]; total: number; }
interface StatsResp { jobs: JobStat[]; total_events: number; total_jobs: number; }
interface ReportsResp { reports: ReportSummary[]; total: number; }

const useCronEvents = (limit = 100) =>
  useQuery<EventsResp>({
    queryKey: ['scheduler-events', limit],
    queryFn: async () => {
      return await apiClient.get<EventsResp>(`/api/admin/scheduler/events?limit=${limit}`);
    },
    refetchInterval: 60000,
  });

const useJobStats = () =>
  useQuery<StatsResp>({
    queryKey: ['scheduler-stats'],
    queryFn: async () => {
      return await apiClient.get<StatsResp>('/api/admin/scheduler/events/stats');
    },
    refetchInterval: 60000,
  });

const useRetrospectiveReports = () =>
  useQuery<ReportsResp>({
    queryKey: ['retrospective-reports'],
    queryFn: async () => {
      return await apiClient.get<ReportsResp>('/api/admin/retrospective/reports?limit=30');
    },
  });

export const SchedulerEventsPage: React.FC = () => {
  const [selectedReport, setSelectedReport] = useState<string | null>(null);
  const [reportContent, setReportContent] = useState<string>('');
  const [reportLoading, setReportLoading] = useState(false);

  const eventsQ = useCronEvents();
  const statsQ = useJobStats();
  const reportsQ = useRetrospectiveReports();

  const openReport = async (date: string) => {
    setSelectedReport(date);
    setReportLoading(true);
    try {
      const data = await apiClient.get<{ markdown: string }>(`/api/admin/retrospective/reports/${date}`);
      setReportContent(data.markdown);
    } catch (e) {
      setReportContent('讀取失敗');
    } finally {
      setReportLoading(false);
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 1400, margin: '0 auto' }}>
      <Space direction="vertical" size={4} style={{ marginBottom: 16 }}>
        <Title level={2}>排程紀錄追溯 + 覆盤報告</Title>
        <Text type="secondary">
          v6.13 owner: 紀錄變文件化與架構 / 真活大於規劃
        </Text>
      </Space>

      <Tabs
        defaultActiveKey="events"
        size="large"
        items={[
          {
            key: 'events',
            label: <span><ClockCircleOutlined /> Cron Events 歷史</span>,
            children: (
              <Card title={`最近 ${eventsQ.data?.events.length ?? 0} 事件 / 總計 ${eventsQ.data?.total ?? 0}`}>
                <Table
                  size="small"
                  loading={eventsQ.isLoading}
                  dataSource={eventsQ.data?.events ?? []}
                  rowKey={(r) => `${r.ts}-${r.job_id}`}
                  columns={[
                    { title: '時間', dataIndex: 'ts', width: 160, render: (v) => v?.slice(0, 19) },
                    { title: 'Job ID', dataIndex: 'job_id', ellipsis: true },
                    { title: '狀態', dataIndex: 'status', width: 90,
                      render: (v) => <Tag color={v === 'success' ? 'green' : 'red'}>{v}</Tag> },
                    { title: '耗時 (ms)', dataIndex: 'duration_ms', width: 100,
                      render: (v) => v?.toFixed(0) },
                    { title: 'Error', dataIndex: 'error', ellipsis: true,
                      render: (v) => v ? <Text type="danger">{v}</Text> : '-' },
                  ]}
                />
              </Card>
            ),
          },
          {
            key: 'stats',
            label: <span><BarChartOutlined /> Job 統計</span>,
            children: (
              <Card title={`${statsQ.data?.total_jobs ?? 0} jobs / ${statsQ.data?.total_events ?? 0} events`}>
                <Table
                  size="small"
                  loading={statsQ.isLoading}
                  dataSource={statsQ.data?.jobs ?? []}
                  rowKey="job_id"
                  columns={[
                    { title: 'Job ID', dataIndex: 'job_id', ellipsis: true },
                    { title: '成功', dataIndex: 'success_count', width: 80, sorter: (a, b) => a.success_count - b.success_count },
                    { title: '失敗', dataIndex: 'failure_count', width: 80, sorter: (a, b) => a.failure_count - b.failure_count },
                    { title: '成功率', dataIndex: 'success_rate_pct', width: 100, sorter: (a, b) => a.success_rate_pct - b.success_rate_pct,
                      render: (v) => <Tag color={v === 100 ? 'green' : v >= 80 ? 'orange' : 'red'}>{v}%</Tag> },
                    { title: '平均耗時 (ms)', dataIndex: 'avg_duration_ms', width: 120,
                      render: (v) => v?.toFixed(0) },
                  ]}
                />
              </Card>
            ),
          },
          {
            key: 'reports',
            label: <span><FileTextOutlined /> Daily Retrospective</span>,
            children: (
              <Card title={`${reportsQ.data?.total ?? 0} 份報告`}>
                <Table
                  size="small"
                  loading={reportsQ.isLoading}
                  dataSource={reportsQ.data?.reports ?? []}
                  rowKey="date"
                  onRow={(r) => ({ onClick: () => openReport(r.date), style: { cursor: 'pointer' } })}
                  columns={[
                    { title: '日期', dataIndex: 'date', width: 120 },
                    { title: 'Overall', dataIndex: 'overall', width: 100,
                      render: (v) => <Tag color={v === 'GREEN' ? 'green' : v === 'YELLOW' ? 'orange' : v === 'RED' ? 'red' : 'default'}>{v}</Tag> },
                    { title: '檔案大小', dataIndex: 'size_bytes', width: 100,
                      render: (v) => `${(v / 1024).toFixed(1)} KB` },
                    { title: '修改時間', dataIndex: 'mtime', width: 180, render: (v) => v?.slice(0, 19) },
                    { title: '摘要', dataIndex: 'summary', ellipsis: true },
                  ]}
                />
              </Card>
            ),
          },
        ]}
      />

      <Drawer
        title={`Retrospective Report: ${selectedReport}`}
        width={800}
        open={!!selectedReport}
        onClose={() => setSelectedReport(null)}
      >
        {reportLoading ? <Spin /> : (
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>{reportContent}</pre>
        )}
      </Drawer>
    </div>
  );
};

export default SchedulerEventsPage;
