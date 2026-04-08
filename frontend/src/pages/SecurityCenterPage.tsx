/**
 * 資安管理中心
 * 基於 OWASP Top 10 標準，參照 CK_Showcase 架構適配 CK_Missive
 *
 * Tab: OWASP 儀表板 / 問題追蹤 / 掃描記錄 / 通知管理 / 安全模式庫
 *
 * @version 1.0.0
 * @created 2026-03-27
 */

import React, { useState } from 'react';
import {
  Typography, Tabs, Card, Tag, Statistic, Row, Col, Empty, Spin,
  Button, Badge, Space, List, Alert,
} from 'antd';
import { EnhancedTable } from '../components/common/EnhancedTable';
import {
  SafetyCertificateOutlined, BugOutlined, ScanOutlined,
  BookOutlined, BellOutlined, ReloadOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';

const { Title, Text } = Typography;

// ── API 呼叫 ──

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ApiAny = any;
const fetchOwaspSummary = (): Promise<ApiAny> => apiClient.post(API_ENDPOINTS.SECURITY.OWASP_SUMMARY, {});
const fetchIssues = (params: Record<string, unknown> = {}): Promise<ApiAny> =>
  apiClient.post(API_ENDPOINTS.SECURITY.ISSUES_LIST, { page: 1, limit: 50, ...params });
const fetchScans = (): Promise<ApiAny> => apiClient.post(API_ENDPOINTS.SECURITY.SCANS_LIST, {});
const fetchNotifications = (): Promise<ApiAny> => apiClient.post(API_ENDPOINTS.SECURITY.NOTIFICATIONS_LIST, {});
const fetchPatterns = (): Promise<ApiAny> => apiClient.post(API_ENDPOINTS.SECURITY.PATTERNS, {});

// ── 常數 ──

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'red', high: 'volcano', medium: 'orange', low: 'blue', info: 'default',
};
const STATUS_COLORS: Record<string, string> = {
  open: 'error', in_progress: 'processing', resolved: 'success', wont_fix: 'default', false_positive: 'default',
};

// ── OWASP 儀表板 ──

const OwaspDashboardTab: React.FC = () => {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['security-owasp'],
    queryFn: fetchOwaspSummary,
    staleTime: 5 * 60_000,
  });

  if (isLoading) return <Spin />;
  if (!data) return <Empty />;

  const cats = data.owasp_categories || {};
  const stats = data.owasp_stats || {};

  const gradeColors: Record<string, string> = { A: '#52c41a', B: '#1890ff', C: '#faad14', D: '#ff4d4f' };
  const grade = data.security_grade || 'A';

  return (
    <div>
      {/* 安全概覽 */}
      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col span={4}>
          <Card size="small" style={{ textAlign: 'center' }}>
            <Statistic
              title={<span style={{ fontSize: 11 }}>安全等級 / 分數</span>}
              value={`${grade} ${data.security_score ?? 0}`}
              suffix="分"
              styles={{ content: { color: gradeColors[grade] || '#999', fontWeight: 'bold' } }}
            />
          </Card>
        </Col>
        <Col span={4}><Card size="small"><Statistic title="未解決" value={data.open_issues} styles={{ content: { color: data.open_issues > 0 ? '#ff4d4f' : '#52c41a' } }} /></Card></Col>
        <Col span={4}><Card size="small"><Statistic title="已修復" value={data.resolved_issues || 0} suffix={<Text type="secondary" style={{ fontSize: 10 }}>/ {data.total_issues || 0}</Text>} styles={{ content: { color: '#52c41a' } }} /></Card></Col>
        <Col span={4}><Card size="small"><Statistic title="Critical" value={data.severity_distribution?.critical || 0} styles={{ content: { color: '#f5222d' } }} /></Card></Col>
        <Col span={4}><Card size="small"><Statistic title="High" value={data.severity_distribution?.high || 0} styles={{ content: { color: '#fa541c' } }} /></Card></Col>
        <Col span={4}><Card size="small"><Statistic title="誤判" value={data.false_positive_issues || 0} styles={{ content: { color: '#999' } }} /></Card></Col>
      </Row>

      {/* 評分說明 */}
      <Alert
        type="success"
        style={{ marginBottom: 12, fontSize: 11 }}
        message={
          <Text style={{ fontSize: 11 }}>
            安全分數 = 100 − (Critical×25 + High×10 + Medium×3 + Low×1)，僅計算未解決問題。
            等級: A(≥90) B(≥70) C(≥50) D(&lt;50)。每日 02:00 自動掃描更新。
          </Text>
        }
      />

      {/* 掃描資訊 */}
      {data.last_scan && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          message={
            <span>
              <Text strong>最近掃描</Text>
              <Text type="secondary" style={{ marginLeft: 8 }}>
                {data.last_scan.created_at ? new Date(data.last_scan.created_at).toLocaleString('zh-TW') : '-'}
              </Text>
              <Tag style={{ marginLeft: 8 }}>{data.last_scan.scan_type}</Tag>
              <Text style={{ marginLeft: 8 }}>發現 {data.last_scan.total_issues} 個問題</Text>
              <Text type="secondary" style={{ marginLeft: 8 }}>
                | 標準: {data.owasp_standard || 'OWASP Top 10'} | 版本: {data.scanner_version || '1.0.0'} | {data.scan_schedule || ''}
              </Text>
            </span>
          }
        />
      )}

      <Card size="small" title="OWASP Top 10 分佈" extra={<Button size="small" icon={<ReloadOutlined />} onClick={() => refetch()} />}>
        <Row gutter={[8, 8]}>
          {Object.entries(cats as Record<string, Record<string, unknown>>).map(([code, info]) => {
            const stat = (stats as Record<string, Record<string, number>>)[code] || {};
            return (
              <Col xs={12} md={8} lg={6} key={code}>
                <Card size="small" style={{ borderLeft: `3px solid ${info.color as string}` }}>
                  <Text strong style={{ fontSize: 12 }}>{code}</Text>
                  <Text type="secondary" style={{ fontSize: 11, marginLeft: 4 }}>{info.nameZh as string}</Text>
                  <div style={{ marginTop: 4 }}>
                    <Tag>{(stat as Record<string, number>).total || 0} 筆</Tag>
                    {((stat as Record<string, number>).open || 0) > 0 && (
                      <Tag color="error">{(stat as Record<string, number>).open} 未解決</Tag>
                    )}
                  </div>
                </Card>
              </Col>
            );
          })}
        </Row>
      </Card>
    </div>
  );
};

// ── 問題追蹤 ──

const IssuesTab: React.FC = () => {
  const { data, isLoading, refetch } = useQuery({ queryKey: ['security-issues'], queryFn: () => fetchIssues() });
  const items = data?.items || [];

  const columns = [
    { title: '嚴重度', dataIndex: 'severity', width: 80,
      filters: [{ text: 'critical', value: 'critical' }, { text: 'high', value: 'high' }, { text: 'medium', value: 'medium' }, { text: 'low', value: 'low' }],
      onFilter: (value: unknown, record: Record<string, unknown>) => record.severity === value,
      sorter: (a: Record<string, unknown>, b: Record<string, unknown>) => {
        const order: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
        return (order[a.severity as string] ?? 5) - (order[b.severity as string] ?? 5);
      },
      render: (s: string) => <Tag color={SEVERITY_COLORS[s]}>{s}</Tag> },
    { title: '狀態', dataIndex: 'status', width: 90,
      filters: [{ text: 'open', value: 'open' }, { text: 'resolved', value: 'resolved' }, { text: 'false_positive', value: 'false_positive' }],
      onFilter: (value: unknown, record: Record<string, unknown>) => record.status === value,
      render: (s: string) => <Badge status={STATUS_COLORS[s] as 'error' | 'processing' | 'success' | 'default'} text={s} /> },
    { title: 'OWASP', dataIndex: 'owasp_category', width: 65,
      filters: ['A01','A02','A03','A04','A05','A06','A07','A08','A09','A10'].map(c => ({ text: c, value: c })),
      onFilter: (value: unknown, record: Record<string, unknown>) => record.owasp_category === value },
    { title: '標題', dataIndex: 'title', ellipsis: true, sorter: (a: Record<string, unknown>, b: Record<string, unknown>) => String(a.title || '').localeCompare(String(b.title || '')) },
    { title: '檔案', dataIndex: 'file_path', width: 180, ellipsis: true },
    { title: '負責人', dataIndex: 'assigned_to', width: 80 },
    { title: '建立時間', dataIndex: 'created_at', width: 100,
      sorter: (a: Record<string, unknown>, b: Record<string, unknown>) => String(a.created_at || '').localeCompare(String(b.created_at || '')),
      render: (d: string) => d ? new Date(d).toLocaleDateString('zh-TW') : '-' },
  ];

  return (
    <Card size="small" extra={<Button size="small" icon={<ReloadOutlined />} onClick={() => refetch()}>重新整理</Button>}>
      <EnhancedTable dataSource={items} columns={columns} rowKey="id" size="small" loading={isLoading}
        pagination={{ pageSize: 20, total: data?.total }} />
    </Card>
  );
};

// ── 掃描記錄 ──

const ScansTab: React.FC = () => {
  const { data, isLoading, refetch } = useQuery({ queryKey: ['security-scans'], queryFn: fetchScans });
  const queryClient = useQueryClient();
  const runScan = useMutation({
    mutationFn: () => apiClient.post(API_ENDPOINTS.SECURITY.SCANS_RUN, { project_name: 'CK_Missive', scan_type: 'quick' }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['security-scans'] }); },
  });

  const items = data?.items || [];
  const columns = [
    { title: '專案', dataIndex: 'project_name', width: 120 },
    { title: '類型', dataIndex: 'scan_type', width: 80 },
    { title: '狀態', dataIndex: 'status', width: 80,
      render: (s: string) => <Tag color={s === 'completed' ? 'green' : s === 'failed' ? 'red' : 'blue'}>{s}</Tag> },
    { title: '問題數', dataIndex: 'total_issues', width: 80 },
    { title: '安全分數', dataIndex: 'security_score', width: 100,
      render: (s: number | null) => s != null ? (
        <Tag color={s >= 90 ? 'green' : s >= 70 ? 'blue' : s >= 50 ? 'orange' : 'red'}>
          {Math.round(s)} / 100
        </Tag>
      ) : '-' },
    { title: '執行者', dataIndex: 'created_by', width: 80 },
    { title: '時間', dataIndex: 'created_at', width: 100,
      render: (d: string) => d ? new Date(d).toLocaleDateString('zh-TW') : '-' },
  ];

  return (
    <Card size="small" extra={
      <Space>
        <Button size="small" type="primary" icon={<ScanOutlined />} onClick={() => runScan.mutate()} loading={runScan.isPending}>執行掃描</Button>
        <Button size="small" icon={<ReloadOutlined />} onClick={() => refetch()} />
      </Space>
    }>
      <EnhancedTable dataSource={items} columns={columns} rowKey="id" size="small" loading={isLoading} pagination={false} />
    </Card>
  );
};

// ── 通知管理 ──

const NotificationsTab: React.FC = () => {
  const { data, isLoading } = useQuery({ queryKey: ['security-notifications'], queryFn: fetchNotifications });
  const items = data?.items || [];

  if (isLoading) return <Spin />;
  if (!items.length) return <Empty description="暫無資安通知" />;

  return (
    <List
      size="small"
      dataSource={items}
      renderItem={(item: Record<string, unknown>) => (
        <List.Item>
          <List.Item.Meta
            title={<><Tag color={SEVERITY_COLORS[item.severity as string] || 'default'}>{item.severity as string}</Tag> {item.title as string}</>}
            description={<><Text type="secondary" style={{ fontSize: 11 }}>{item.created_at ? new Date(item.created_at as string).toLocaleString('zh-TW') : ''}</Text> — {item.message as string}</>}
          />
        </List.Item>
      )}
    />
  );
};

// ── 安全模式庫 ──

const PatternsTab: React.FC = () => {
  const { data, isLoading } = useQuery({ queryKey: ['security-patterns'], queryFn: fetchPatterns });
  if (isLoading) return <Spin />;
  const patterns = data?.patterns || [];

  return (
    <Row gutter={[12, 12]}>
      {patterns.map((p: Record<string, string>, i: number) => (
        <Col xs={24} md={12} key={i}>
          <Card size="small" title={
            <Space>
              <Tag>{p.category}</Tag>
              <Tag color={SEVERITY_COLORS[p.severity || 'info'] || 'default'}>{p.severity || 'info'}</Tag>
              <Text strong style={{ fontSize: 13 }}>{p.title}</Text>
            </Space>
          }>
            <Text style={{ fontSize: 12 }}>{p.description}</Text>
            <Alert type="info" title={<code style={{ fontSize: 11 }}>{p.example}</code>} style={{ marginTop: 8 }} />
            {p.reference && (
              <Text type="secondary" style={{ fontSize: 10, display: 'block', marginTop: 4 }}>
                參考: {p.reference}
              </Text>
            )}
          </Card>
        </Col>
      ))}
    </Row>
  );
};

// ── 主頁面 ──

const SecurityCenterPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');

  const { data: owaspData } = useQuery({ queryKey: ['security-owasp'], queryFn: fetchOwaspSummary, staleTime: 60_000 });
  const openCount = owaspData?.open_issues || 0;

  return (
    <div style={{ padding: '0 0 24px' }}>
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          <SafetyCertificateOutlined /> 資安管理中心
        </Title>
        <Text type="secondary">基於 OWASP Top 10 標準 — 自動掃描 (每日 02:00) + 問題追蹤 + 安全模式庫</Text>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'dashboard',
            label: <span><SafetyCertificateOutlined /> OWASP 儀表板</span>,
            children: <OwaspDashboardTab />,
          },
          {
            key: 'issues',
            label: <span><BugOutlined /> 問題追蹤 {openCount > 0 && <Badge count={openCount} style={{ marginLeft: 4 }} />}</span>,
            children: <IssuesTab />,
          },
          {
            key: 'scans',
            label: <span><ScanOutlined /> 掃描記錄</span>,
            children: <ScansTab />,
          },
          {
            key: 'notifications',
            label: <span><BellOutlined /> 通知管理</span>,
            children: <NotificationsTab />,
          },
          {
            key: 'patterns',
            label: <span><BookOutlined /> 安全模式庫</span>,
            children: <PatternsTab />,
          },
        ]}
      />
    </div>
  );
};

export default SecurityCenterPage;
