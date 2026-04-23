/**
 * CrystalEvolutionTab（原「進化史」）— 坤哥「結晶進化」視角
 *
 * 呈現史萊姆式成長軌跡：
 *   - 成功 pattern 進度（hit 累積 → 結晶候選 → 結晶提案 → 正式結晶）
 *   - Crystal 已套用歷史（intent_rule 加速路由）
 *   - 等待批准的結晶提案
 *
 * 資料來源：
 *   - /ai/memory/patterns/list
 *   - /ai/memory/proposals/list
 *   - /ai/memory/crystals/list
 *
 * ADR-0031 Phase 5：與以下兩者職責分工明確，不應混為一談：
 *   - UnifiedAgent 的「健康進化」Tab = Agent journal / tool-health 監控
 *   - /ai/skill-evolution 的「技能族譜」= DB skill 節點演化樹
 *
 * @version 1.1.0 — ADR-0031 命名正名
 */

import React from 'react';
import {
  Card,
  Typography,
  Row,
  Col,
  Tag,
  Space,
  Progress,
  Timeline,
  Button,
  Empty,
  List,
  Tooltip,
} from 'antd';
import { useNavigate } from 'react-router-dom';
import {
  RiseOutlined,
  BranchesOutlined,
  CrownOutlined,
  NodeIndexOutlined,
  ArrowRightOutlined,
  FireOutlined,
} from '@ant-design/icons';
import { usePatternsList, useProposalsList, useCrystalsList } from '../../hooks/useMemoryData';
import type { PatternSummary, ProposalSummary, CrystalSummary } from '../../types/memory';

const { Title, Paragraph, Text } = Typography;

const CRYSTAL_HIT_THRESHOLD = 5;
const CRYSTAL_SUCCESS_THRESHOLD = 0.95;

const toArray = (seq: string | string[] | undefined): string[] => {
  if (!seq) return [];
  if (Array.isArray(seq)) return seq;
  try {
    const parsed = JSON.parse(seq);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

const PatternRow: React.FC<{ p: PatternSummary }> = ({ p }) => {
  const meta = p.meta ?? {};
  const hit = meta.hit_count ?? 0;
  const rate = meta.success_rate ?? 0;
  const tools = toArray(meta.tool_sequence);
  const hitProgress = Math.min(100, (hit / CRYSTAL_HIT_THRESHOLD) * 100);
  const isCandidate = !!meta.crystallization_candidate;
  const isCrystallized = !!meta.crystallized;
  const patternId = meta.pattern_id ?? p.filename;

  return (
    <Card size="small" style={{ marginBottom: 8 }}>
      <Space direction="vertical" size={4} style={{ width: '100%' }}>
        <Space wrap>
          <Text strong style={{ fontSize: 13 }}>
            #{String(patternId).slice(0, 16)}
          </Text>
          {tools.map((t) => (
            <Tag key={t} style={{ fontSize: 11 }}>{t}</Tag>
          ))}
          {isCrystallized && <Tag color="gold" icon={<NodeIndexOutlined />}>已結晶</Tag>}
          {!isCrystallized && isCandidate && <Tag color="orange" icon={<FireOutlined />}>結晶候選</Tag>}
        </Space>
        <Space size={16} wrap>
          <Tooltip title={`hit ${hit} / 門檻 ${CRYSTAL_HIT_THRESHOLD}`}>
            <div style={{ width: 220 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                累積觸發 {hit} / {CRYSTAL_HIT_THRESHOLD}
              </Text>
              <Progress
                percent={hitProgress}
                size="small"
                strokeColor={hit >= CRYSTAL_HIT_THRESHOLD ? '#52c41a' : '#1677ff'}
                showInfo={false}
              />
            </div>
          </Tooltip>
          <Text style={{ fontSize: 12 }}>
            成功率 <Text strong style={{ color: rate >= CRYSTAL_SUCCESS_THRESHOLD ? '#52c41a' : '#fa8c16' }}>
              {(rate * 100).toFixed(0)}%
            </Text>
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            最新：{meta.last_seen ?? '—'}
          </Text>
        </Space>
      </Space>
    </Card>
  );
};

const ProposalRow: React.FC<{ p: ProposalSummary }> = ({ p }) => {
  const meta = p.meta ?? {};
  return (
    <List.Item>
      <Space direction="vertical" size={2} style={{ width: '100%' }}>
        <Space wrap>
          <Tag color="orange">{meta.status ?? 'pending'}</Tag>
          <Tag color="blue">{meta.proposal_kind ?? 'unknown'}</Tag>
          <Text code style={{ fontSize: 12 }}>{meta.proposal_id}</Text>
        </Space>
        <Text style={{ fontSize: 12 }}>
          → 目標檔 <code>{meta.target_file ?? '—'}</code> · 來源 pattern{' '}
          <code>{meta.source_pattern ?? '—'}</code>
        </Text>
        {meta.reason && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            {meta.reason}
          </Text>
        )}
      </Space>
    </List.Item>
  );
};

const CrystalRow: React.FC<{ c: CrystalSummary }> = ({ c }) => {
  const meta = c.meta ?? {};
  return (
    <List.Item>
      <Space direction="vertical" size={2} style={{ width: '100%' }}>
        <Space wrap>
          <Tag color="gold" icon={<NodeIndexOutlined />}>crystal</Tag>
          <Text code style={{ fontSize: 12 }}>{meta.crystal_id}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {meta.approved_at ?? '—'}
          </Text>
        </Space>
        <Text style={{ fontSize: 12 }}>
          已套用到 <code>{meta.target_file ?? '—'}</code>
          （source pattern <code>{meta.source_pattern ?? '—'}</code>，批准者 {meta.approved_by ?? '—'}）
        </Text>
      </Space>
    </List.Item>
  );
};

export const EvolutionTab: React.FC = () => {
  const navigate = useNavigate();
  const { data: patterns, isLoading: lp } = usePatternsList({ limit: 20 });
  const { data: proposals, isLoading: lpr } = useProposalsList({ limit: 20 });
  const { data: crystals, isLoading: lc } = useCrystalsList({ limit: 20 });

  const proposalList: ProposalSummary[] = proposals ?? [];
  const patternList: PatternSummary[] = patterns ?? [];
  const crystalList: CrystalSummary[] = crystals ?? [];
  const pendingProposals = proposalList.filter(
    (x) => (x.meta?.status ?? 'pending') === 'pending',
  );
  const crystalCount = crystalList.length;
  const candidates = patternList.filter(
    (p) => p.meta?.crystallization_candidate && !p.meta?.crystallized,
  );

  return (
    <div>
      <Card bordered={false}>
        <Title level={3} style={{ marginTop: 0 }}>
          <RiseOutlined /> 進化史
        </Title>
        <Paragraph type="secondary" style={{ fontSize: 15 }}>
          我以<Text strong>史萊姆模式</Text>成長 — 吞噬經驗、累積 hit、達門檻結晶為 intent_rule，
          讓下次類似問題走快速通道。下圖是當前進化階段。
        </Paragraph>
      </Card>

      <Row gutter={[12, 12]} style={{ marginTop: 16 }}>
        <Col xs={24} md={8}>
          <Card
            size="small"
            title={<Space><BranchesOutlined /> 結晶候選</Space>}
            extra={<Tag color="orange">{candidates.length}</Tag>}
            loading={lp}
            style={{ height: '100%' }}
          >
            {candidates.length === 0 ? (
              <Empty description="尚無候選" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              candidates.map((p) => (
                <PatternRow key={p.meta?.pattern_id ?? p.filename} p={p} />
              ))
            )}
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card
            size="small"
            title={<Space><CrownOutlined /> 待批提案</Space>}
            extra={<Tag color="orange">{pendingProposals.length}</Tag>}
            loading={lpr}
            style={{ height: '100%' }}
          >
            {pendingProposals.length === 0 ? (
              <Empty description="無待批" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <List<ProposalSummary>
                size="small"
                dataSource={pendingProposals}
                renderItem={(p) => <ProposalRow p={p} />}
              />
            )}
            {pendingProposals.length > 0 && (
              <Button
                type="link"
                size="small"
                style={{ padding: 0, marginTop: 4 }}
                onClick={() => navigate('/ai/memory')}
              >
                前往批准 <ArrowRightOutlined />
              </Button>
            )}
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card
            size="small"
            title={<Space><NodeIndexOutlined /> 已套用結晶</Space>}
            extra={<Tag color="gold">{crystalCount}</Tag>}
            loading={lc}
            style={{ height: '100%' }}
          >
            {crystalCount === 0 ? (
              <Empty description="等待首次結晶" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <List<CrystalSummary>
                size="small"
                dataSource={crystalList}
                renderItem={(c) => <CrystalRow c={c} />}
              />
            )}
          </Card>
        </Col>
      </Row>

      <Card
        bordered={false}
        style={{ marginTop: 16 }}
        title={<Space><FireOutlined /> 成長時間軸</Space>}
      >
        <Timeline
          items={[
            {
              color: 'green',
              children: (
                <>
                  <Text strong>2026-04-20</Text>
                  <div>Memory Wiki 7-Phase 上線（v5.7.0）— 日記、成功模式、結晶提案、週自傳機制全交付</div>
                </>
              ),
            },
            {
              color: 'green',
              children: (
                <>
                  <Text strong>2026-04-20</Text>
                  <div>v5.7.1 覆盤：四層 silent failure 全清 + Phase 7 SOUL/Memory/Wiki 三層橋接</div>
                </>
              ),
            },
            {
              color: 'blue',
              children: (
                <>
                  <Text strong>2026-04-21</Text>
                  <div>
                    D1-A · SOUL.md v2.0 升級為「坤哥」人格 — 身份宣言、三信念、反迴聲室、倫理紅線
                  </div>
                </>
              ),
            },
            {
              color: 'blue',
              children: (
                <>
                  <Text strong>2026-04-21</Text>
                  <div>
                    D3-A · 首批 pattern 達結晶候選門檻（hit=9/6，success=100%）並產出 2 個 intent_rule proposal
                  </div>
                </>
              ),
            },
            {
              color: 'blue',
              children: (
                <>
                  <Text strong>2026-04-21</Text>
                  <div>
                    D2-A · 修 60s silent gap → tool/synthesis start-end 觀測性齊全 · extract_daily 同日 dedup
                  </div>
                </>
              ),
            },
            {
              color: 'gray',
              children: (
                <>
                  <Text type="secondary">待發生</Text>
                  <div>
                    D5+ · 反迴聲室協議實作 · Autobiography 首篇 · 首次結晶 apply 到 intent_rules.yaml
                  </div>
                </>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
};

export default EvolutionTab;
