/**
 * 能力雷達 Tab — Recharts RadarChart 呈現領域能力 + 今日觀察
 */
import React from 'react';
import { Row, Col, Card, Typography, Space, Tag, Empty, Spin, Alert, Statistic } from 'antd';
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer } from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { DIGITAL_TWIN_ENDPOINTS } from '../../api/endpoints';

const { Text } = Typography;

interface DashboardData {
  capability: {
    domains?: Array<{ domain: string; score: number; query_count: number; level: string }>;
    strengths?: Array<{ domain: string; score: number }>;
    weaknesses?: Array<{ domain: string; score: number }>;
    overall_score?: number;
  } | null;
  daily: {
    today_queries?: number;
    avg_score?: number;
    avg_latency_ms?: number;
    route_distribution?: Record<string, number>;
    tool_distribution?: Array<{ tool: string; count: number }>;
    self_observation?: string;
  } | null;
}

const DOMAIN_LABELS: Record<string, string> = {
  doc: '公文', dispatch: '派工', graph: '圖譜',
  pm: '專案', erp: '財務', analysis: '分析', general: '通用',
};

export const CapabilityRadarTab: React.FC = () => {
  const { data, isLoading, isError } = useQuery<DashboardData>({
    queryKey: ['dt-dashboard'],
    queryFn: () => apiClient.post(DIGITAL_TWIN_ENDPOINTS.DASHBOARD, {}),
    staleTime: 5 * 60_000,
  });

  if (isLoading) return <Spin tip="載入能力分析..." style={{ display: 'block', padding: 40, textAlign: 'center' }} />;
  if (isError) return <Alert type="warning" showIcon title="能力資料載入失敗" />;

  const capability = data?.capability;
  const daily = data?.daily;

  // 雷達圖資料
  const radarData = (capability?.domains ?? []).map(d => ({
    domain: DOMAIN_LABELS[d.domain] ?? d.domain,
    score: Math.round(d.score * 100),
    fullMark: 100,
  }));

  return (
    <Row gutter={[16, 16]}>
      {/* 雷達圖 */}
      <Col xs={24} md={14}>
        <Card title="領域能力雷達" size="small">
          {radarData.length >= 3 ? (
            <ResponsiveContainer width="100%" height={300}>
              <RadarChart data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="domain" tick={{ fontSize: 12 }} />
                <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
                <Radar name="能力" dataKey="score" stroke="#722ed1" fill="#722ed1" fillOpacity={0.3} />
              </RadarChart>
            </ResponsiveContainer>
          ) : (
            <Empty description="需要至少 3 個領域的查詢資料才能繪製雷達圖" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}

          {/* 強弱項標籤 */}
          {capability?.strengths && capability.strengths.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <Text strong style={{ fontSize: 12, color: '#52c41a' }}>強項：</Text>
              <Space wrap size={[4, 4]} style={{ marginLeft: 8 }}>
                {capability.strengths.map(s => (
                  <Tag key={s.domain} color="green">{DOMAIN_LABELS[s.domain] ?? s.domain} ({(s.score * 100).toFixed(0)}%)</Tag>
                ))}
              </Space>
            </div>
          )}
          {capability?.weaknesses && capability.weaknesses.length > 0 && (
            <div style={{ marginTop: 6 }}>
              <Text strong style={{ fontSize: 12, color: '#faad14' }}>待加強：</Text>
              <Space wrap size={[4, 4]} style={{ marginLeft: 8 }}>
                {capability.weaknesses.map(w => (
                  <Tag key={w.domain} color="orange">{DOMAIN_LABELS[w.domain] ?? w.domain} ({(w.score * 100).toFixed(0)}%)</Tag>
                ))}
              </Space>
            </div>
          )}
        </Card>
      </Col>

      {/* 今日觀察 */}
      <Col xs={24} md={10}>
        <Card title="今日觀察" size="small">
          {daily ? (
            <>
              <Row gutter={[8, 12]}>
                <Col span={8}>
                  <Statistic title={<span style={{ fontSize: 11 }}>查詢數</span>}
                    value={daily.today_queries ?? 0} styles={{ content: { fontSize: 20 } }} />
                </Col>
                <Col span={8}>
                  <Statistic title={<span style={{ fontSize: 11 }}>平均分</span>}
                    value={(daily.avg_score ?? 0).toFixed(2)} styles={{ content: { fontSize: 20 } }} />
                </Col>
                <Col span={8}>
                  <Statistic title={<span style={{ fontSize: 11 }}>延遲(ms)</span>}
                    value={daily.avg_latency_ms ?? 0} styles={{ content: { fontSize: 20 } }} />
                </Col>
              </Row>

              {/* 工具使用排行 */}
              {daily.tool_distribution && daily.tool_distribution.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <Text strong style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>常用工具</Text>
                  <Space wrap size={[4, 4]}>
                    {daily.tool_distribution.slice(0, 8).map(t => (
                      <Tag key={t.tool} color="blue">{t.tool} ({t.count})</Tag>
                    ))}
                  </Space>
                </div>
              )}

              {/* 自我觀察 */}
              {daily.self_observation && (
                <div style={{ marginTop: 16, background: '#f6ffed', borderRadius: 6, padding: '8px 12px', fontSize: 12, fontStyle: 'italic' }}>
                  {daily.self_observation}
                </div>
              )}
            </>
          ) : (
            <Empty description="今日尚無查詢資料" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>
      </Col>
    </Row>
  );
};
