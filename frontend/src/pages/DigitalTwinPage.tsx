/**
 * 數位分身展示頁面
 *
 * 整合 Agent Self-Profile 身份卡片 + DualModeChatPanel 雙模式問答，
 * 展示 NemoClaw 數位分身的能力與互動體驗。
 *
 * @version 1.0.0
 * @created 2026-03-23
 */

import React from 'react';
import {
  Button,
  Card,
  Row,
  Col,
  Typography,
  Spin,
  Tag,
  Statistic,
  Progress,
  Space,
  Badge,
  Divider,
} from 'antd';
import {
  RobotOutlined,
  CloudServerOutlined,
  TrophyOutlined,
  ThunderboltOutlined,
  BookOutlined,
  HeartOutlined,
  BranchesOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { AI_ENDPOINTS } from '../api/endpoints';
import { checkGatewayHealth } from '../api/digitalTwin';
import { DualModeChatPanel } from '../components/ai/DualModeChatPanel';

const { Title, Text, Paragraph } = Typography;

// ---------------------------------------------------------------------------
// Agent Self-Profile API
// ---------------------------------------------------------------------------

interface AgentSelfProfile {
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

async function fetchSelfProfile(): Promise<AgentSelfProfile> {
  return apiClient.post<AgentSelfProfile>(AI_ENDPOINTS.AGENT_SELF_PROFILE, {});
}

// ---------------------------------------------------------------------------
// ProfileCard — 身份卡片
// ---------------------------------------------------------------------------

const ProfileCard: React.FC<{
  profile: AgentSelfProfile;
  loading: boolean;
  error?: boolean;
  onRetry?: () => void;
}> = ({
  profile,
  loading,
  error,
  onRetry,
}) => {
  if (loading) {
    return (
      <Card style={{ textAlign: 'center', padding: 32 }}>
        <Spin size="large" />
        <div style={{ marginTop: 12 }}>
          <Text type="secondary">載入數位分身檔案...</Text>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card style={{ textAlign: 'center', padding: 32 }}>
        <Text type="danger">載入失敗</Text>
        {onRetry && (
          <div style={{ marginTop: 8 }}>
            <Button size="small" onClick={onRetry}>重新載入</Button>
          </div>
        )}
      </Card>
    );
  }

  const scorePercent = Math.min(100, Math.round((profile.avg_score ?? 0) * 20));

  return (
    <Card
      styles={{ body: { padding: '20px 24px' } }}
    >
      {/* 頭部: 身份 + 個性 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #722ed1 0%, #13c2c2 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <RobotOutlined style={{ fontSize: 28, color: '#fff' }} />
        </div>
        <div style={{ flex: 1 }}>
          <Title level={4} style={{ margin: 0 }}>
            {profile.identity || '乾坤智能體'}
          </Title>
          <Text type="secondary" style={{ fontSize: 12 }}>
            NemoClaw 數位分身 — 跨專案協作引擎
          </Text>
        </div>
        <Badge status="success" text="運行中" />
      </div>

      {/* 個性描述 */}
      {profile.personality_hint && (
        <Paragraph
          type="secondary"
          style={{ fontSize: 13, margin: '0 0 16px', fontStyle: 'italic' }}
        >
          「{profile.personality_hint}」
        </Paragraph>
      )}

      <Divider style={{ margin: '12px 0' }} />

      {/* 統計指標 */}
      <Row gutter={[16, 12]}>
        <Col span={8}>
          <Statistic
            title={<span style={{ fontSize: 11 }}>累計問答</span>}
            value={profile.total_queries}
            prefix={<ThunderboltOutlined style={{ fontSize: 12 }} />}
            styles={{ content: { fontSize: 20 } }}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title={<span style={{ fontSize: 11 }}>學習記錄</span>}
            value={profile.learnings_count}
            prefix={<BookOutlined style={{ fontSize: 12 }} />}
            styles={{ content: { fontSize: 20 } }}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title={<span style={{ fontSize: 11 }}>對話摘要</span>}
            value={profile.conversation_summaries}
            prefix={<CloudServerOutlined style={{ fontSize: 12 }} />}
            styles={{ content: { fontSize: 20 } }}
          />
        </Col>
      </Row>

      <Divider style={{ margin: '12px 0' }} />

      {/* 擅長領域 */}
      <div style={{ marginBottom: 12 }}>
        <Text strong style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
          <TrophyOutlined /> 擅長領域
        </Text>
        <Space wrap size={[4, 4]}>
          {(profile.top_domains ?? []).slice(0, 6).map((d) => (
            <Tag key={d.domain} color="purple">
              {d.domain} ({d.count})
            </Tag>
          ))}
          {(!profile.top_domains || profile.top_domains.length === 0) && (
            <Text type="secondary" style={{ fontSize: 11 }}>尚無足夠資料</Text>
          )}
        </Space>
      </div>

      {/* 常用工具 */}
      <div>
        <Text strong style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
          <BranchesOutlined /> 常用工具
        </Text>
        <Space wrap size={[4, 4]}>
          {(profile.favorite_tools ?? []).slice(0, 6).map((t) => (
            <Tag key={t.tool} color="cyan">
              {t.tool} ({t.count})
            </Tag>
          ))}
          {(!profile.favorite_tools || profile.favorite_tools.length === 0) && (
            <Text type="secondary" style={{ fontSize: 11 }}>尚無足夠資料</Text>
          )}
        </Space>
      </div>

      {/* 品質指標 */}
      {(profile.rated_queries ?? 0) > 0 && (
        <>
          <Divider style={{ margin: '12px 0' }} />
          <div>
            <Text strong style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
              <HeartOutlined /> 回饋品質
            </Text>
            <Row gutter={8}>
              <Col span={12}>
                <Text type="secondary" style={{ fontSize: 11 }}>平均評分</Text>
                <Progress
                  percent={scorePercent}
                  size="small"
                  format={() => `${(profile.avg_score ?? 0).toFixed(1)}/5`}
                  status={scorePercent >= 80 ? 'success' : scorePercent >= 50 ? 'normal' : 'exception'}
                />
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

      {/* 對話摘要 */}
      {profile.conversation_summaries > 0 && (
        <>
          <Divider style={{ margin: '12px 0' }} />
          <div>
            <Text strong style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
              <BookOutlined /> 對話摘要 ({profile.conversation_summaries})
            </Text>
            {(profile.recent_summaries ?? []).map((s, idx) => (
              <div
                key={idx}
                style={{
                  background: '#fafafa',
                  borderRadius: 6,
                  padding: '6px 10px',
                  marginBottom: 4,
                  fontSize: 11,
                  lineHeight: 1.5,
                }}
              >
                <Text style={{ fontSize: 11 }}>{s.content}</Text>
                {s.created_at && (
                  <Text type="secondary" style={{ fontSize: 10, display: 'block', marginTop: 2 }}>
                    {new Date(s.created_at).toLocaleDateString('zh-TW')}
                  </Text>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </Card>
  );
};

// ---------------------------------------------------------------------------
// GatewayHealthBadge — Gateway 連線狀態
// ---------------------------------------------------------------------------

const GatewayHealthBadge: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['dt-gateway-health'],
    queryFn: checkGatewayHealth,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  if (isLoading) return <Badge status="processing" text="檢測中..." />;
  if (!data) return <Badge status="default" text="未知" />;

  return (
    <Badge
      status={data.available ? 'success' : 'error'}
      text={
        data.available
          ? `Gateway 連線正常 (${data.latencyMs}ms)`
          : `Gateway 離線: ${data.message ?? '無回應'}`
      }
    />
  );
};

// ---------------------------------------------------------------------------
// 主頁面
// ---------------------------------------------------------------------------

const DigitalTwinPage: React.FC = () => {
  const { data: profile, isLoading: profileLoading, isError: profileError, refetch: refetchProfile } = useQuery({
    queryKey: ['agent-self-profile'],
    queryFn: fetchSelfProfile,
    staleTime: 5 * 60_000,
    retry: 1,
  });

  const defaultProfile: AgentSelfProfile = {
    success: false,
    identity: '乾坤智能體',
    total_queries: 0,
    top_domains: [],
    favorite_tools: [],
    avg_score: 0,
    learnings_count: 0,
    conversation_summaries: 0,
    personality_hint: '',
  };

  return (
    <div style={{ padding: '0 0 24px' }}>
      {/* 頁面標題 */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={4} style={{ margin: 0 }}>
            <CloudServerOutlined /> 數位分身
          </Title>
          <Text type="secondary">
            NemoClaw 跨專案智能協作引擎 — 即時問答與能力展示
          </Text>
        </div>
        <GatewayHealthBadge />
      </div>

      <Row gutter={[16, 16]}>
        {/* 左側: 身份卡片 */}
        <Col xs={24} lg={8}>
          <ProfileCard
            profile={profile ?? defaultProfile}
            loading={profileLoading}
            error={profileError}
            onRetry={() => refetchProfile()}
          />
        </Col>

        {/* 右側: 雙模式問答 */}
        <Col xs={24} lg={16}>
          <DualModeChatPanel />
        </Col>
      </Row>
    </div>
  );
};

export default DigitalTwinPage;
