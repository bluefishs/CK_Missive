/**
 * 數位分身儀表板 Tab — 聚合快照
 *
 * 消費 GET /ai/digital-twin/dashboard API
 * 顯示：品質指標 / 今日統計 / 最近查詢 / Gateway 狀態
 *
 * @version 1.0.0
 * @created 2026-03-25
 */

import React from 'react';
import { Card, Row, Col, Statistic, Progress, Tag, Timeline, Alert, Spin, Typography, Space, Empty } from 'antd';
import {
  CheckCircleOutlined, ClockCircleOutlined,
  ThunderboltOutlined, ToolOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { DIGITAL_TWIN_ENDPOINTS } from '../../api/endpoints';

const { Text } = Typography;

interface DashboardSnapshot {
  profile: { total_queries: number; avg_score: number; learnings_count: number } | null;
  capability: { strengths: string[]; weaknesses: string[] } | null;
  daily: { today_queries: number; avg_latency_ms: number; tool_distribution: Record<string, number> } | null;
  quality: { avg_score: number; total_evaluated: number } | null;
  recent_traces: Array<{ query: string; latency_ms: number; tool_count: number; created_at: string }> | null;
  health: { available: boolean; systems_count: number } | null;
}

const DashboardTab: React.FC = () => {
  const { data, isLoading, isError } = useQuery<DashboardSnapshot>({
    queryKey: ['dt-dashboard'],
    queryFn: () => apiClient.post(DIGITAL_TWIN_ENDPOINTS.DASHBOARD, {}),
    staleTime: 5 * 60_000,
  });

  if (isLoading) return <Spin tip="載入儀表板..." style={{ display: 'block', padding: 40, textAlign: 'center' }} />;
  if (isError) return <Alert type="warning" showIcon title="儀表板資料載入失敗" />;
  if (!data) return <Empty description="暫無資料" />;

  const profile = data.profile;
  const daily = data.daily;
  const quality = data.quality;
  const health = data.health;
  const traces = data.recent_traces;
  const capability = data.capability;

  const avgScore = quality?.avg_score ?? profile?.avg_score ?? 0;
  const scorePercent = Math.min(100, (avgScore / 5) * 100);

  return (
    <div>
      {/* 頂部指標卡片 */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="總查詢次數"
              value={profile?.total_queries ?? 0}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="今日查詢"
              value={daily?.today_queries ?? 0}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="平均延遲"
              value={daily?.avg_latency_ms ?? 0}
              suffix="ms"
              precision={0}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="學習筆數"
              value={profile?.learnings_count ?? 0}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[12, 12]}>
        {/* 品質分數 */}
        <Col xs={24} md={8}>
          <Card size="small" title="品質評分">
            <div style={{ textAlign: 'center', padding: '8px 0' }}>
              <Progress
                type="dashboard"
                percent={Math.round(scorePercent)}
                format={() => `${avgScore.toFixed(1)}/5`}
                strokeColor={scorePercent >= 80 ? '#52c41a' : scorePercent >= 60 ? '#faad14' : '#ff4d4f'}
                size={120}
              />
              <div style={{ marginTop: 8 }}>
                <Text type="secondary">共 {quality?.total_evaluated ?? 0} 次評估</Text>
              </div>
            </div>
          </Card>
        </Col>

        {/* 能力概覽 */}
        <Col xs={24} md={8}>
          <Card size="small" title="能力概覽">
            {capability ? (
              <div>
                <div style={{ marginBottom: 8 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>強項</Text>
                  <div>
                    <Space wrap size={[4, 4]}>
                      {(capability.strengths ?? []).slice(0, 5).map(s => (
                        <Tag color="green" key={s}>{s}</Tag>
                      ))}
                    </Space>
                  </div>
                </div>
                <div>
                  <Text type="secondary" style={{ fontSize: 12 }}>待加強</Text>
                  <div>
                    <Space wrap size={[4, 4]}>
                      {(capability.weaknesses ?? []).slice(0, 5).map(w => (
                        <Tag color="orange" key={w}>{w}</Tag>
                      ))}
                    </Space>
                  </div>
                </div>
              </div>
            ) : <Empty description="無能力分析" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
          </Card>
        </Col>

        {/* Gateway 狀態 */}
        <Col xs={24} md={8}>
          <Card size="small" title="系統狀態">
            <div style={{ marginBottom: 12 }}>
              <Tag color={health?.available ? 'green' : 'red'}>
                {health?.available ? 'Gateway 連線正常' : 'Gateway 離線'}
              </Tag>
              <Text type="secondary" style={{ marginLeft: 8 }}>
                {health?.systems_count ?? 0} 個已註冊系統
              </Text>
            </div>
            {daily?.tool_distribution && (
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>今日工具使用</Text>
                <div style={{ marginTop: 4 }}>
                  <Space wrap size={[4, 4]}>
                    {Object.entries(daily.tool_distribution).slice(0, 6).map(([tool, count]) => (
                      <Tag key={tool} icon={<ToolOutlined />}>{tool}: {count}</Tag>
                    ))}
                  </Space>
                </div>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* 最近查詢 */}
      <Card size="small" title="最近查詢" style={{ marginTop: 12 }}>
        {traces && traces.length > 0 ? (
          <Timeline
            items={traces.map((t, i) => ({
              key: i,
              color: t.latency_ms < 3000 ? 'green' : t.latency_ms < 8000 ? 'blue' : 'red',
              children: (
                <div>
                  <Text style={{ fontSize: 13 }}>{t.query?.slice(0, 60)}</Text>
                  <div>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      {t.latency_ms}ms · {t.tool_count} tools · {t.created_at?.slice(0, 16)}
                    </Text>
                  </div>
                </div>
              ),
            }))}
          />
        ) : <Empty description="暫無查詢記錄" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
      </Card>
    </div>
  );
};

export { DashboardTab };
