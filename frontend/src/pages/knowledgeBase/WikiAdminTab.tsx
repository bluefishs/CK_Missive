/**
 * Wiki 管理 Tab（含 SchedulerPanel / TokenUsagePanel）— 從 WikiPage.tsx 拆分（v1.0 2026-04-18）
 */
import React from 'react';
import {
  Typography, Card, Button, Tag, Space, Row, Col, Statistic, App, Descriptions,
} from 'antd';
import {
  SettingOutlined, SyncOutlined, CheckCircleOutlined, WarningOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';
import type { WikiStats, WikiLintResult, SchedulerJob, TokenProvider } from './wikiTypes';

// ── Scheduler Panel ──

const SchedulerPanel: React.FC = () => {
  const { data: jobs } = useQuery<SchedulerJob[]>({
    queryKey: ['scheduler-health'],
    queryFn: async () => {
      const resp = await apiClient.post<{
        success: boolean;
        scheduler: { jobs: SchedulerJob[] };
      }>('/health/scheduler', {});
      return resp.scheduler?.jobs || [];
    },
    staleTime: 30_000,
  });

  if (!jobs || jobs.length === 0) return null;

  // 只顯示 wiki 相關 + 月度覆盤
  const wikiJobs = jobs.filter((j) =>
    j.id.includes('wiki') || j.id.includes('arch_review')
  );

  return (
    <Card title={`排程器 (${jobs.length} jobs, 顯示 wiki 相關)`} size="small" style={{ marginTop: 16 }}>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #f0f0f0', textAlign: 'left' }}>
              <th style={{ padding: 4 }}>任務</th>
              <th style={{ padding: 4 }}>上次執行</th>
              <th style={{ padding: 4 }}>狀態</th>
              <th style={{ padding: 4 }}>耗時</th>
              <th style={{ padding: 4 }}>成功/失敗</th>
            </tr>
          </thead>
          <tbody>
            {wikiJobs.map((j) => (
              <tr key={j.id} style={{ borderBottom: '1px solid #f5f5f5' }}>
                <td style={{ padding: 4 }}>{j.name || j.id}</td>
                <td style={{ padding: 4, color: '#888' }}>
                  {j.last_run ? new Date(j.last_run).toLocaleString('zh-TW') : '—'}
                </td>
                <td style={{ padding: 4 }}>
                  <Tag color={j.last_status === 'success' ? 'green' : j.last_status === 'failure' ? 'red' : 'default'}>
                    {j.last_status || 'pending'}
                  </Tag>
                </td>
                <td style={{ padding: 4 }}>{j.last_duration_ms ? `${j.last_duration_ms}ms` : '—'}</td>
                <td style={{ padding: 4 }}>{j.success_count}/{j.failure_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
};

// ── Token Usage Panel ──

const TokenUsagePanel: React.FC = () => {
  const { data } = useQuery<{ providers: TokenProvider[]; daily_total: { input: number; output: number; cost: number } }>({
    queryKey: ['token-usage'],
    queryFn: async () => {
      const resp = await apiClient.post<{ success: boolean; data: { providers: TokenProvider[]; daily_total: { input: number; output: number; cost: number } } }>(
        '/ai/stats/token-usage', {},
      );
      return resp.data;
    },
    staleTime: 60_000,
  });

  if (!data?.providers || data.providers.length === 0) return null;

  return (
    <Card title="Token 用量 (今日)" size="small" style={{ marginTop: 16 }}>
      <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #f0f0f0', textAlign: 'left' }}>
            <th style={{ padding: 4 }}>Provider</th>
            <th style={{ padding: 4 }}>Input</th>
            <th style={{ padding: 4 }}>Output</th>
            <th style={{ padding: 4 }}>Requests</th>
            <th style={{ padding: 4 }}>Cost (USD)</th>
          </tr>
        </thead>
        <tbody>
          {data.providers.map((p) => (
            <tr key={p.provider} style={{ borderBottom: '1px solid #f5f5f5' }}>
              <td style={{ padding: 4 }}><Tag>{p.provider}</Tag></td>
              <td style={{ padding: 4 }}>{p.total_input.toLocaleString()}</td>
              <td style={{ padding: 4 }}>{p.total_output.toLocaleString()}</td>
              <td style={{ padding: 4 }}>{p.request_count}</td>
              <td style={{ padding: 4 }}>${p.total_cost_usd.toFixed(4)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {data.daily_total && (
        <div style={{ marginTop: 8, fontSize: 12, color: '#888' }}>
          今日合計: {data.daily_total.input.toLocaleString()} input + {data.daily_total.output.toLocaleString()} output = ${data.daily_total.cost.toFixed(4)} USD
        </div>
      )}
    </Card>
  );
};

// ── Admin Tab ──

const WikiAdminTab: React.FC = () => {
  const { message } = App.useApp();
  const qc = useQueryClient();

  const { data: stats } = useQuery<WikiStats>({
    queryKey: ['wiki-stats'],
    queryFn: async () => {
      const resp = await apiClient.post<{ success: boolean; data: WikiStats }>(
        API_ENDPOINTS.WIKI.STATS, {},
      );
      return resp.data;
    },
  });

  const { data: lint } = useQuery<WikiLintResult>({
    queryKey: ['wiki-lint'],
    queryFn: async () => {
      const resp = await apiClient.post<{ success: boolean; data: WikiLintResult }>(
        API_ENDPOINTS.WIKI.LINT, {},
      );
      return resp.data;
    },
  });

  const compileMutation = useMutation({
    mutationFn: async (mode: string) => {
      const resp = await apiClient.post<{ success: boolean; data: Record<string, unknown> }>(
        `${API_ENDPOINTS.WIKI.COMPILE}?mode=${mode}`, {},
      );
      return resp.data;
    },
    onSuccess: (_data, mode) => {
      message.success(`Wiki ${mode} 編譯完成`);
      qc.invalidateQueries({ queryKey: ['wiki-stats'] });
      qc.invalidateQueries({ queryKey: ['wiki-lint'] });
      qc.invalidateQueries({ queryKey: ['wiki-graph'] });
    },
    onError: () => message.error('編譯失敗'),
  });

  const healthColor = lint?.health === 'good' ? '#52c41a' : '#faad14';
  const healthIcon = lint?.health === 'good' ? <CheckCircleOutlined /> : <WarningOutlined />;

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="健康狀態"
              value={lint?.health || 'unknown'}
              prefix={healthIcon}
              valueStyle={{ color: healthColor }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic title="總頁數" value={lint?.total_pages ?? stats?.total ?? 0} />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="孤立 / 斷裂"
              value={`${lint?.orphan_pages?.length ?? 0} / ${lint?.broken_links?.length ?? 0}`}
              valueStyle={{ color: (lint?.orphan_pages?.length || 0) > 5 ? '#faad14' : undefined }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="Wiki 編譯" size="small" style={{ marginBottom: 16 }}>
        <Space>
          <Button
            type="primary"
            icon={<SyncOutlined />}
            loading={compileMutation.isPending}
            onClick={() => compileMutation.mutate('incremental')}
          >
            增量編譯
          </Button>
          <Button
            icon={<SyncOutlined />}
            loading={compileMutation.isPending}
            onClick={() => compileMutation.mutate('full')}
          >
            全量編譯
          </Button>
        </Space>
        <Typography.Text type="secondary" style={{ marginLeft: 16 }}>
          增量: 只重編有新公文的機關/案件 | 全量: 全部重新編譯
        </Typography.Text>
      </Card>

      {lint && (
        <Card title="Lint 詳情" size="small">
          <Descriptions column={2} size="small">
            <Descriptions.Item label="entities">{lint.page_count?.entities ?? 0}</Descriptions.Item>
            <Descriptions.Item label="topics">{lint.page_count?.topics ?? 0}</Descriptions.Item>
            <Descriptions.Item label="sources">{lint.page_count?.sources ?? 0}</Descriptions.Item>
            <Descriptions.Item label="synthesis">{lint.page_count?.synthesis ?? 0}</Descriptions.Item>
          </Descriptions>
          {lint.orphan_pages && lint.orphan_pages.length > 0 && (
            <>
              <Typography.Text type="secondary" style={{ display: 'block', marginTop: 12 }}>
                孤立頁面 (無入站連結):
              </Typography.Text>
              {lint.orphan_pages.slice(0, 10).map((p) => (
                <Tag key={p} style={{ margin: 2 }}>{decodeURIComponent(p.split('/').pop() || p)}</Tag>
              ))}
              {lint.orphan_pages.length > 10 && <Tag>+{lint.orphan_pages.length - 10} more</Tag>}
            </>
          )}
        </Card>
      )}

      {/* 排程器狀態 */}
      <SchedulerPanel />

      {/* Token 用量 */}
      <TokenUsagePanel />
    </div>
  );
};

export { SettingOutlined };
export default WikiAdminTab;
