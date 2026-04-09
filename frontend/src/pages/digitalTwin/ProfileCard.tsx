/**
 * Agent 身份卡片 — Self-Profile 展示
 *
 * 支援兩種模式：
 * - compact=false (預設)：完整版，含個性提示、對話摘要、回饋品質
 * - compact=true：精簡版，含 dashboard snapshot 統計、品質、學習畢業率
 */
import React from 'react';
import {
  Button, Card, Row, Col, Typography, Spin, Tag, Statistic,
  Progress, Space, Badge, Divider, Skeleton, Alert,
} from 'antd';
import {
  RobotOutlined, CloudServerOutlined, TrophyOutlined,
  ThunderboltOutlined, BookOutlined, HeartOutlined, BranchesOutlined,
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;

export interface AgentSelfProfile {
  success: boolean;
  identity: string;
  total_queries: number;
  top_domains: Array<{ domain: string; count: number }>;
  favorite_tools: Array<{ tool: string; count: number }>;
  avg_score: number;
  learnings_count: number;
  conversation_summaries: number;
  recent_summaries?: Array<{ content: string; created_at: string | null }>;
  rated_queries?: number;
  personality_hint: string;
}

// eslint-disable-next-line react-refresh/only-export-components
export const defaultProfile: AgentSelfProfile = {
  success: false, identity: '乾坤智能體', total_queries: 0,
  top_domains: [], favorite_tools: [], avg_score: 0,
  learnings_count: 0, conversation_summaries: 0, personality_hint: '',
};

export interface DashboardSnapshot {
  profile: { total_queries: number; avg_score: number; learnings_count: number } | null;
  capability: { strengths: string[]; weaknesses: string[] } | null;
  daily: { today_queries: number; avg_latency_ms: number; tool_distribution: Record<string, number> } | null;
  quality: { avg_score: number; total_evaluated: number } | null;
  recent_traces: Array<{ query: string; latency_ms: number; tool_count: number; created_at: string }> | null;
  health: { available: boolean; systems_count: number } | null;
}

interface ProfileCardProps {
  profile: AgentSelfProfile;
  loading: boolean;
  error?: boolean;
  onRetry?: () => void;
  compact?: boolean;
  dashboardData?: DashboardSnapshot | null;
  dashboardLoading?: boolean;
}

/* ── Compact Mode (精簡版：AgentSidebar) ─────────────────── */

const CompactProfile: React.FC<ProfileCardProps> = ({
  profile, loading, error, dashboardData, dashboardLoading,
}) => {
  if (loading) {
    return (
      <Card styles={{ body: { padding: '20px 16px' } }}>
        <Skeleton active avatar={{ shape: 'circle', size: 52 }} paragraph={{ rows: 6 }} />
      </Card>
    );
  }
  if (error) {
    return (
      <Card>
        <Alert type="warning" showIcon message="智能體檔案載入失敗" />
      </Card>
    );
  }

  const scorePercent = Math.min(100, Math.round((profile.avg_score ?? 0) * 20));
  const daily = dashboardData?.daily;
  const capability = dashboardData?.capability;
  const learningsCount = profile.learnings_count ?? 0;
  const graduationRate = learningsCount > 0
    ? Math.min(100, Math.round((learningsCount / Math.max(learningsCount + 5, 1)) * 100)) : 0;

  return (
    <Card styles={{ body: { padding: '20px 16px' } }}>
      {/* Identity */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <div style={{
          width: 52, height: 52, borderRadius: '50%',
          background: 'linear-gradient(135deg, #722ed1 0%, #13c2c2 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        }}>
          <RobotOutlined style={{ fontSize: 26, color: '#fff' }} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Title level={5} style={{ margin: 0 }}>{profile.identity || '乾坤智能體'}</Title>
          <Text type="secondary" style={{ fontSize: 11 }}>v5.5.0 | gemma4-8b-q4</Text>
        </div>
        <Badge status="success" text="" />
      </div>

      <Divider style={{ margin: '12px 0' }} />

      {/* 30-day Stats */}
      <div style={{ marginBottom: 16 }}>
        <Text strong style={{ fontSize: 12, color: '#8c8c8c' }}>
          <ThunderboltOutlined /> 30 日統計
        </Text>
        <Row gutter={8} style={{ marginTop: 8 }}>
          <Col span={12}>
            <Statistic title={<span style={{ fontSize: 11 }}>查詢次數</span>}
              value={profile.total_queries ?? 0} valueStyle={{ fontSize: 20 }} />
          </Col>
          <Col span={12}>
            <Statistic title={<span style={{ fontSize: 11 }}>平均延遲</span>}
              value={daily?.avg_latency_ms ?? 0} suffix="ms"
              valueStyle={{ fontSize: 20 }} loading={dashboardLoading} />
          </Col>
        </Row>
      </div>

      <Divider style={{ margin: '12px 0' }} />

      {/* Quality Score */}
      <div style={{ marginBottom: 16 }}>
        <Text strong style={{ fontSize: 12, color: '#8c8c8c' }}><TrophyOutlined /> 品質評分</Text>
        <Progress percent={scorePercent}
          strokeColor={scorePercent >= 80 ? '#52c41a' : scorePercent >= 60 ? '#faad14' : '#ff4d4f'}
          format={() => `${(profile.avg_score ?? 0).toFixed(1)}/5`}
          style={{ marginTop: 8 }} />
      </div>

      {/* Learning Graduation */}
      <div style={{ marginBottom: 16 }}>
        <Text strong style={{ fontSize: 12, color: '#8c8c8c' }}><BookOutlined /> 學習畢業率</Text>
        <Progress percent={graduationRate} strokeColor="#722ed1"
          format={() => `${learningsCount} 條`} style={{ marginTop: 8 }} />
      </div>

      <Divider style={{ margin: '12px 0' }} />

      {/* Strengths / Weaknesses */}
      {capability && (
        <div>
          {(capability.strengths ?? []).length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <Text style={{ fontSize: 11, color: '#8c8c8c' }}>擅長領域</Text>
              <div style={{ marginTop: 4 }}>
                <Space wrap size={[4, 4]}>
                  {capability.strengths.slice(0, 5).map(s => (
                    <Tag key={s} color="green" style={{ fontSize: 11 }}>{s}</Tag>
                  ))}
                </Space>
              </div>
            </div>
          )}
          {(capability.weaknesses ?? []).length > 0 && (
            <div>
              <Text style={{ fontSize: 11, color: '#8c8c8c' }}>待加強</Text>
              <div style={{ marginTop: 4 }}>
                <Space wrap size={[4, 4]}>
                  {capability.weaknesses.slice(0, 5).map(w => (
                    <Tag key={w} color="orange" style={{ fontSize: 11 }}>{w}</Tag>
                  ))}
                </Space>
              </div>
            </div>
          )}
        </div>
      )}

      <Divider style={{ margin: '12px 0' }} />

      {/* Top Domains */}
      {profile.top_domains?.length > 0 && (
        <div>
          <Text style={{ fontSize: 11, color: '#8c8c8c' }}>熱門領域</Text>
          <div style={{ marginTop: 4 }}>
            <Space wrap size={[4, 4]}>
              {profile.top_domains.slice(0, 4).map(d => (
                <Tag key={d.domain} style={{ fontSize: 11 }}>{d.domain} ({d.count})</Tag>
              ))}
            </Space>
          </div>
        </div>
      )}
    </Card>
  );
};

/* ── Full Mode (完整版) ──────────────────────────────────── */

const FullProfile: React.FC<ProfileCardProps> = ({ profile, loading, error, onRetry }) => {
  if (loading) {
    return (
      <Card style={{ textAlign: 'center', padding: 32 }}>
        <Spin size="large" />
        <div style={{ marginTop: 12 }}><Text type="secondary">載入智能體檔案...</Text></div>
      </Card>
    );
  }
  if (error) {
    return (
      <Card style={{ textAlign: 'center', padding: 32 }}>
        <Text type="danger">載入失敗</Text>
        {onRetry && <div style={{ marginTop: 8 }}><Button size="small" onClick={onRetry}>重新載入</Button></div>}
      </Card>
    );
  }

  const scorePercent = Math.min(100, Math.round((profile.avg_score ?? 0) * 20));

  return (
    <Card styles={{ body: { padding: '20px 24px' } }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
        <div style={{
          width: 56, height: 56, borderRadius: '50%',
          background: 'linear-gradient(135deg, #722ed1 0%, #13c2c2 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        }}>
          <RobotOutlined style={{ fontSize: 28, color: '#fff' }} />
        </div>
        <div style={{ flex: 1 }}>
          <Title level={4} style={{ margin: 0 }}>{profile.identity || '乾坤智能體'}</Title>
          <Text type="secondary" style={{ fontSize: 12 }}>自覺型 AI 助理 — 問答、自省、進化</Text>
        </div>
        <Badge status="success" text="運行中" />
      </div>

      {profile.personality_hint && (
        <Paragraph type="secondary" style={{ fontSize: 13, margin: '0 0 16px', fontStyle: 'italic' }}>
          {profile.personality_hint}
        </Paragraph>
      )}

      <Divider style={{ margin: '12px 0' }} />

      <Row gutter={[16, 12]}>
        <Col span={8}>
          <Statistic title={<span style={{ fontSize: 11 }}>累計問答</span>} value={profile.total_queries}
            prefix={<ThunderboltOutlined style={{ fontSize: 12 }} />} styles={{ content: { fontSize: 20 } }} />
        </Col>
        <Col span={8}>
          <Statistic title={<span style={{ fontSize: 11 }}>學習記錄</span>} value={profile.learnings_count}
            prefix={<BookOutlined style={{ fontSize: 12 }} />} styles={{ content: { fontSize: 20 } }} />
        </Col>
        <Col span={8}>
          <Statistic title={<span style={{ fontSize: 11 }}>對話摘要</span>} value={profile.conversation_summaries}
            prefix={<CloudServerOutlined style={{ fontSize: 12 }} />} styles={{ content: { fontSize: 20 } }} />
        </Col>
      </Row>

      <Divider style={{ margin: '12px 0' }} />

      <div style={{ marginBottom: 12 }}>
        <Text strong style={{ fontSize: 12, display: 'block', marginBottom: 6 }}><TrophyOutlined /> 擅長領域</Text>
        <Space wrap size={[4, 4]}>
          {(profile.top_domains ?? []).slice(0, 6).map((d) => <Tag key={d.domain} color="purple">{d.domain} ({d.count})</Tag>)}
          {(!profile.top_domains || profile.top_domains.length === 0) && <Text type="secondary" style={{ fontSize: 11 }}>尚無足夠資料</Text>}
        </Space>
      </div>

      <div>
        <Text strong style={{ fontSize: 12, display: 'block', marginBottom: 6 }}><BranchesOutlined /> 常用工具</Text>
        <Space wrap size={[4, 4]}>
          {(profile.favorite_tools ?? []).slice(0, 6).map((t) => <Tag key={t.tool} color="cyan">{t.tool} ({t.count})</Tag>)}
          {(!profile.favorite_tools || profile.favorite_tools.length === 0) && <Text type="secondary" style={{ fontSize: 11 }}>尚無足夠資料</Text>}
        </Space>
      </div>

      {(profile.rated_queries ?? 0) > 0 && (
        <>
          <Divider style={{ margin: '12px 0' }} />
          <div>
            <Text strong style={{ fontSize: 12, display: 'block', marginBottom: 6 }}><HeartOutlined /> 回饋品質</Text>
            <Row gutter={8}>
              <Col span={12}>
                <Text type="secondary" style={{ fontSize: 11 }}>平均評分</Text>
                <Progress percent={scorePercent} size="small"
                  format={() => `${(profile.avg_score ?? 0).toFixed(1)}/5`}
                  status={scorePercent >= 80 ? 'success' : scorePercent >= 50 ? 'normal' : 'exception'} />
              </Col>
              <Col span={12}>
                <Text type="secondary" style={{ fontSize: 11 }}>已評分查詢</Text>
                <div style={{ fontSize: 16, fontWeight: 600, marginTop: 4 }}>
                  {profile.rated_queries} <Text type="secondary" style={{ fontSize: 11 }}>/ {profile.total_queries}</Text>
                </div>
              </Col>
            </Row>
          </div>
        </>
      )}

      {profile.conversation_summaries > 0 && (
        <>
          <Divider style={{ margin: '12px 0' }} />
          <div>
            <Text strong style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
              <BookOutlined /> 對話摘要 ({profile.conversation_summaries})
            </Text>
            {(profile.recent_summaries ?? []).map((s, idx) => (
              <div key={idx} style={{ background: '#fafafa', borderRadius: 6, padding: '6px 10px', marginBottom: 4, fontSize: 11, lineHeight: 1.5 }}>
                <Text style={{ fontSize: 11 }}>{s.content}</Text>
                {s.created_at && <Text type="secondary" style={{ fontSize: 10, display: 'block', marginTop: 2 }}>{new Date(s.created_at).toLocaleDateString('zh-TW')}</Text>}
              </div>
            ))}
          </div>
        </>
      )}
    </Card>
  );
};

/* ── Exported Component ──────────────────────────────────── */

export const ProfileCard: React.FC<ProfileCardProps> = (props) => {
  return props.compact ? <CompactProfile {...props} /> : <FullProfile {...props} />;
};
