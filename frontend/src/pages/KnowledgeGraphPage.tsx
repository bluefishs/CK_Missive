/**
 * KnowledgeGraphPage - 知識圖譜探索頁面
 *
 * 獨立全螢幕的知識圖譜探索器，包含：
 * - 左側面板：搜尋、過濾、覆蓋率儀表板、管理動作
 * - 中央：KnowledgeGraph 力導向視覺化元件
 * - 右側：EntityDetailSidebar（點擊實體節點時展開）
 *
 * @version 1.0.0
 * @created 2026-02-25
 */

import React, { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import {
  Card,
  Progress,
  Statistic,
  Space,
  Button,
  Typography,
  Spin,
  Row,
  Col,
  Divider,
  App,
  Select,
  Modal,
  Tag,
  Tooltip,
} from 'antd';
import {
  ApartmentOutlined,
  SyncOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  NodeIndexOutlined,
  FileTextOutlined,
  CrownOutlined,
  SwapOutlined,
  ForkOutlined,
  RobotOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';

import { aiApi } from '../api/aiApi';
import type {
  EmbeddingStatsResponse,
  EntityStatsResponse,
  KGGraphStatsResponse,
  KGEntityItem,
  KGShortestPathResponse,
} from '../types/ai';
import { KnowledgeGraph } from '../components/ai/KnowledgeGraph';
import type { ExternalGraphData } from '../components/ai/KnowledgeGraph';
import { RAGChatPanel } from '../components/ai/RAGChatPanel';
import { GraphAgentBridgeProvider } from '../components/ai/knowledgeGraph/GraphAgentBridge';
import { getAllMergedConfigs, getMergedNodeConfig } from '../config/graphNodeConfig';
import { useAuthGuard } from '../hooks/utility/useAuthGuard';
import { KGAdminPanel } from './knowledgeGraph/KGAdminPanel';

const { Title, Text } = Typography;

// ============================================================================
// 左側面板：覆蓋率儀表板
// ============================================================================

interface CoverageStats {
  embedding: EmbeddingStatsResponse | null;
  entity: EntityStatsResponse | null;
  graph: KGGraphStatsResponse | null;
}

const CoveragePanel: React.FC<{
  stats: CoverageStats;
  loading: boolean;
}> = ({ stats, loading }) => {
  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 16 }}>
        <Spin size="small" />
        <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
          載入統計...
        </div>
      </div>
    );
  }

  const embCoverage = stats.embedding?.coverage_percent ?? 0;
  const nerCoverage = stats.entity?.coverage_percent ?? 0;
  const canonicalEntities = stats.graph?.total_entities ?? 0;
  const totalRelationships = stats.graph?.total_relationships ?? 0;

  return (
    <div>
      {/* NER Coverage */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <Text style={{ fontSize: 12 }}>NER 實體提取</Text>
          <Text style={{ fontSize: 12 }} type="secondary">
            {stats.entity?.extracted_documents ?? 0}/{stats.entity?.total_documents ?? 0}
          </Text>
        </div>
        <Progress
          percent={nerCoverage}
          size="small"
          status={nerCoverage >= 80 ? 'success' : nerCoverage >= 50 ? 'normal' : 'exception'}
          format={(p) => `${(p ?? 0).toFixed(1)}%`}
        />
      </div>

      {/* Embedding Coverage */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <Text style={{ fontSize: 12 }}>Embedding 覆蓋</Text>
          <Text style={{ fontSize: 12 }} type="secondary">
            {stats.embedding?.with_embedding ?? 0}/{stats.embedding?.total_documents ?? 0}
          </Text>
        </div>
        <Progress
          percent={embCoverage}
          size="small"
          status={embCoverage >= 80 ? 'success' : embCoverage >= 50 ? 'normal' : 'exception'}
          format={(p) => `${(p ?? 0).toFixed(1)}%`}
        />
      </div>

      {/* Graph Stats */}
      <Row gutter={[8, 8]}>
        <Col span={12}>
          <Statistic
            title={<span style={{ fontSize: 11 }}>正規化實體</span>}
            value={canonicalEntities}
            prefix={<NodeIndexOutlined style={{ fontSize: 12 }} />}
            valueStyle={{ fontSize: 18 }}
          />
        </Col>
        <Col span={12}>
          <Statistic
            title={<span style={{ fontSize: 11 }}>關係數量</span>}
            value={totalRelationships}
            prefix={<ApartmentOutlined style={{ fontSize: 12 }} />}
            valueStyle={{ fontSize: 18 }}
          />
        </Col>
      </Row>

      {stats.entity && (
        <div style={{ marginTop: 12 }}>
          <Row gutter={[8, 8]}>
            <Col span={12}>
              <Statistic
                title={<span style={{ fontSize: 11 }}>NER 實體</span>}
                value={stats.entity.total_entities}
                prefix={<ExperimentOutlined style={{ fontSize: 12 }} />}
                valueStyle={{ fontSize: 18 }}
              />
            </Col>
            <Col span={12}>
              <Statistic
                title={<span style={{ fontSize: 11 }}>NER 關係</span>}
                value={stats.entity.total_relations}
                prefix={<FileTextOutlined style={{ fontSize: 12 }} />}
                valueStyle={{ fontSize: 18 }}
              />
            </Col>
          </Row>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// 主頁面
// ============================================================================

const KnowledgeGraphPage: React.FC = () => {
  const { message } = App.useApp();
  const { isAdmin } = useAuthGuard();

  // 穩定引用：傳給 KnowledgeGraph 的空 documentIds（避免每次渲染產生新引用）
  const emptyDocumentIds = useMemo<number[]>(() => [], []);

  // Entity graph state
  const [entityGraphData, setEntityGraphData] = useState<ExternalGraphData | null>(null);
  const [, setEntityGraphLoading] = useState(false);

  // Coverage stats
  const [coverageStats, setCoverageStats] = useState<CoverageStats>({
    embedding: null,
    entity: null,
    graph: null,
  });
  const [statsLoading, setStatsLoading] = useState(true);

  // Top entities
  const [topEntities, setTopEntities] = useState<KGEntityItem[]>([]);

  // Shortest path
  const [pathSourceId, setPathSourceId] = useState<number | null>(null);
  const [pathTargetId, setPathTargetId] = useState<number | null>(null);
  const [pathResult, setPathResult] = useState<KGShortestPathResponse | null>(null);
  const [pathLoading, setPathLoading] = useState(false);

  // AI Chat 面板
  const [chatPanelOpen, setChatPanelOpen] = useState(true);

  // Merge entities (admin)
  const [mergeModalOpen, setMergeModalOpen] = useState(false);
  const [mergeKeepId, setMergeKeepId] = useState<number | null>(null);
  const [mergeMergeId, setMergeMergeId] = useState<number | null>(null);
  const [mergeLoading, setMergeLoading] = useState(false);

  // Shared entity search options (for Select components)
  const searchTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const [entityOptions, setEntityOptions] = useState<Array<{ label: string; value: number }>>([]);

  // Load coverage stats
  const loadStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const [embedding, entity, graph, topEnt] = await Promise.allSettled([
        aiApi.getEmbeddingStats(),
        aiApi.getEntityStats(),
        aiApi.getGraphStats(),
        aiApi.getTopEntities({ limit: 10 }),
      ]);

      setCoverageStats({
        embedding: embedding.status === 'fulfilled' ? embedding.value : null,
        entity: entity.status === 'fulfilled' ? entity.value : null,
        graph: graph.status === 'fulfilled' ? graph.value : null,
      });
      setTopEntities(
        topEnt.status === 'fulfilled' && topEnt.value?.entities
          ? topEnt.value.entities
          : [],
      );
    } finally {
      setStatsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  // Load entity graph — 以實體為中心的公文知識圖譜
  const loadEntityGraph = useCallback(async () => {
    setEntityGraphLoading(true);
    try {
      const result = await aiApi.getEntityGraph({ min_mentions: 2, limit: 200 });
      if (result?.success && result.nodes.length > 0) {
        setEntityGraphData({ nodes: result.nodes, edges: result.edges });
      } else {
        setEntityGraphData(null);
      }
    } catch {
      setEntityGraphData(null);
    } finally {
      setEntityGraphLoading(false);
    }
  }, []);

  // Auto-load entity graph on mount
  useEffect(() => {
    loadEntityGraph();
  }, [loadEntityGraph]);

  // Admin actions
  // Entity search for Select (debounced)
  const handleEntitySearch = useCallback((query: string) => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    if (!query.trim()) {
      setEntityOptions([]);
      return;
    }
    searchTimerRef.current = setTimeout(async () => {
      try {
        const result = await aiApi.searchGraphEntities({ query, limit: 10 });
        if (result?.results) {
          setEntityOptions(result.results.map((e) => ({
            label: `${e.canonical_name} (${getMergedNodeConfig(e.entity_type).label})`,
            value: e.id,
          })));
        }
      } catch { /* silent */ }
    }, 300);
  }, []);

  // Shortest path
  const handleFindPath = useCallback(async () => {
    if (!pathSourceId || !pathTargetId) return;
    setPathLoading(true);
    setPathResult(null);
    try {
      const result = await aiApi.findShortestPath({
        source_id: pathSourceId,
        target_id: pathTargetId,
      });
      setPathResult(result);
      if (!result?.found) {
        message.info('未找到兩實體間的路徑');
      }
    } catch {
      message.error('路徑查詢失敗');
    } finally {
      setPathLoading(false);
    }
  }, [pathSourceId, pathTargetId, message]);

  // Merge entities (admin)
  const handleMerge = useCallback(async () => {
    if (!mergeKeepId || !mergeMergeId) return;
    setMergeLoading(true);
    try {
      const result = await aiApi.mergeGraphEntities({
        keep_id: mergeKeepId,
        merge_id: mergeMergeId,
      });
      if (result?.success) {
        message.success(result.message || '合併成功');
        setMergeModalOpen(false);
        setMergeKeepId(null);
        setMergeMergeId(null);
        loadStats();
      } else {
        message.error(result?.message || '合併失敗');
      }
    } catch {
      message.error('合併請求失敗');
    } finally {
      setMergeLoading(false);
    }
  }, [mergeKeepId, mergeMergeId, message, loadStats]);

  // Graph entity type distribution for the left panel
  const graphTypeDistribution = coverageStats.graph?.entity_type_distribution;

  return (
    <GraphAgentBridgeProvider>
    <div style={{ display: 'flex', gap: 0, height: 'calc(100vh - 120px)', overflow: 'hidden', position: 'relative' }}>
      {/* Left Panel */}
      <div
        style={{
          width: 280,
          minWidth: 280,
          background: '#fff',
          borderRight: '1px solid #f0f0f0',
          overflow: 'auto',
          padding: 16,
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}
      >
        {/* Title */}
        <div style={{ marginBottom: 4 }}>
          <Title level={5} style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
            <ApartmentOutlined />
            <span>公文圖譜</span>
          </Title>
          <Text type="secondary" style={{ fontSize: 12 }}>
            視覺化公文關聯網絡與正規化實體
          </Text>
        </div>

        <Divider style={{ margin: '4px 0' }} />

        {/* Coverage Dashboard */}
        <Card
          size="small"
          title={
            <span style={{ fontSize: 13 }}>
              <DatabaseOutlined /> 覆蓋率儀表板
            </span>
          }
          extra={
            <Button
              size="small"
              type="text"
              icon={<SyncOutlined spin={statsLoading} />}
              onClick={loadStats}
            />
          }
          styles={{ body: { padding: '8px 12px' } }}
        >
          <CoveragePanel stats={coverageStats} loading={statsLoading} />
        </Card>

        {/* Admin Actions */}
        {isAdmin && (
          <KGAdminPanel
            withoutExtraction={coverageStats.entity?.without_extraction ?? 1}
            onReloadStats={loadStats}
            onOpenMergeModal={() => setMergeModalOpen(true)}
          />
        )}

        {/* Entity Type Distribution */}
        {graphTypeDistribution && Object.keys(graphTypeDistribution).length > 0 && (
          <Card
            size="small"
            title={
              <span style={{ fontSize: 13 }}>
                <NodeIndexOutlined /> 實體類型分佈
              </span>
            }
            styles={{ body: { padding: '8px 12px' } }}
          >
            {Object.entries(graphTypeDistribution).map(([type, count]) => {
              const configs = getAllMergedConfigs();
              const cfg = configs[type] || configs[type];
              const label = cfg?.label || type;
              const color = cfg?.color || '#999';
              return (
                <div
                  key={type}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '3px 0',
                    fontSize: 12,
                  }}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: color,
                        display: 'inline-block',
                      }}
                    />
                    {label}
                  </span>
                  <Text type="secondary" style={{ fontSize: 12 }}>{count}</Text>
                </div>
              );
            })}
          </Card>
        )}

        {/* Top Entities Ranking */}
        {topEntities.length > 0 && (
          <Card
            size="small"
            title={
              <span style={{ fontSize: 13 }}>
                <CrownOutlined /> 高頻實體排行
              </span>
            }
            styles={{ body: { padding: '4px 12px' } }}
          >
            {topEntities.map((entity, idx) => {
              const cfg = getMergedNodeConfig(entity.entity_type);
              return (
                <div
                  key={entity.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '3px 0',
                    fontSize: 12,
                  }}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Text type="secondary" style={{ fontSize: 11, width: 16 }}>
                      {idx + 1}.
                    </Text>
                    <span
                      style={{
                        width: 8, height: 8, borderRadius: '50%',
                        background: cfg.color, display: 'inline-block',
                      }}
                    />
                    <span style={{ maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {entity.canonical_name}
                    </span>
                  </span>
                  <Tag style={{ fontSize: 10, margin: 0, lineHeight: '16px' }}>
                    {entity.mention_count}
                  </Tag>
                </div>
              );
            })}
          </Card>
        )}

        {/* Shortest Path Finder */}
        <Card
          size="small"
          title={
            <span style={{ fontSize: 13 }}>
              <ForkOutlined /> 最短路徑
            </span>
          }
          styles={{ body: { padding: '8px 12px' } }}
        >
          <Space direction="vertical" style={{ width: '100%' }} size={6}>
            <Select
              showSearch
              allowClear
              placeholder="起點實體"
              filterOption={false}
              onSearch={handleEntitySearch}
              onChange={(val) => { setPathSourceId(val ?? null); setPathResult(null); }}
              options={entityOptions}
              size="small"
              style={{ width: '100%' }}
              notFoundContent={null}
            />
            <Select
              showSearch
              allowClear
              placeholder="終點實體"
              filterOption={false}
              onSearch={handleEntitySearch}
              onChange={(val) => { setPathTargetId(val ?? null); setPathResult(null); }}
              options={entityOptions}
              size="small"
              style={{ width: '100%' }}
              notFoundContent={null}
            />
            <Button
              block
              size="small"
              type="primary"
              icon={<ForkOutlined />}
              loading={pathLoading}
              disabled={!pathSourceId || !pathTargetId || pathSourceId === pathTargetId}
              onClick={handleFindPath}
            >
              查找路徑
            </Button>
            {pathResult?.found && (
              <div style={{ fontSize: 12, padding: '4px 0' }}>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  路徑深度: {pathResult.depth} 跳
                </Text>
                <div style={{ marginTop: 4 }}>
                  {pathResult.path.map((node, idx) => (
                    <span key={node.id}>
                      <Tag color={getMergedNodeConfig(node.type).color} style={{ fontSize: 11, marginBottom: 2 }}>
                        {node.name}
                      </Tag>
                      {idx < pathResult.path.length - 1 && (
                        <span style={{ fontSize: 10, color: '#999', margin: '0 2px' }}>
                          —{pathResult.relations[idx] || ''}→{' '}
                        </span>
                      )}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </Space>
        </Card>
      </div>

      {/* Center: Knowledge Graph */}
      <div style={{ flex: 1, minWidth: 0, overflow: 'hidden', background: '#fafafa' }}>
        <KnowledgeGraph
          documentIds={emptyDocumentIds}
          height={typeof window !== 'undefined' ? window.innerHeight - 120 : 700}
          externalGraphData={entityGraphData ?? undefined}
          onExternalRefresh={entityGraphData ? loadEntityGraph : undefined}
        />
      </div>

      {/* Right Panel: AI Agent Chat */}
      {chatPanelOpen && (
        <div
          style={{
            width: 360,
            minWidth: 360,
            background: '#fff',
            borderLeft: '1px solid #f0f0f0',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '8px 12px',
              borderBottom: '1px solid #f0f0f0',
              flexShrink: 0,
            }}
          >
            <Space size={6}>
              <RobotOutlined style={{ color: '#722ed1' }} />
              <Text strong style={{ fontSize: 13 }}>AI 智能助理</Text>
              <Tag color="purple" style={{ fontSize: 10, lineHeight: '16px', margin: 0 }}>Agent</Tag>
            </Space>
            <Button
              type="text"
              size="small"
              icon={<MenuFoldOutlined />}
              onClick={() => setChatPanelOpen(false)}
            />
          </div>
          <RAGChatPanel embedded agentMode />
        </div>
      )}

      {/* AI Panel Toggle (when closed) — 固定在右上角確保不被裁掉 */}
      {!chatPanelOpen && (
        <Tooltip title="開啟 AI 助理">
          <Button
            type="primary"
            shape="circle"
            icon={<MenuUnfoldOutlined />}
            onClick={() => setChatPanelOpen(true)}
            style={{
              position: 'absolute', right: 12, bottom: 56, zIndex: 100,
              background: '#722ed1', borderColor: '#722ed1',
              boxShadow: '0 2px 8px rgba(114, 46, 209, 0.4)',
            }}
          />
        </Tooltip>
      )}

      {/* Merge Entities Modal */}
      <Modal
        title={<><SwapOutlined /> 合併實體</>}
        open={mergeModalOpen}
        onCancel={() => { setMergeModalOpen(false); setMergeKeepId(null); setMergeMergeId(null); }}
        onOk={handleMerge}
        okText="確定合併"
        cancelText="取消"
        confirmLoading={mergeLoading}
        okButtonProps={{ disabled: !mergeKeepId || !mergeMergeId || mergeKeepId === mergeMergeId }}
      >
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            將「被合併實體」的所有別名、提及、關係轉移至「保留實體」，然後刪除被合併實體。
          </Text>
          <div>
            <Text style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>保留實體</Text>
            <Select
              showSearch
              allowClear
              placeholder="搜尋要保留的實體"
              filterOption={false}
              onSearch={handleEntitySearch}
              onChange={(val) => setMergeKeepId(val ?? null)}
              options={entityOptions}
              style={{ width: '100%' }}
              notFoundContent={null}
            />
          </div>
          <div>
            <Text style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>被合併實體</Text>
            <Select
              showSearch
              allowClear
              placeholder="搜尋要合併（刪除）的實體"
              filterOption={false}
              onSearch={handleEntitySearch}
              onChange={(val) => setMergeMergeId(val ?? null)}
              options={entityOptions}
              style={{ width: '100%' }}
              notFoundContent={null}
            />
          </div>
        </Space>
      </Modal>
    </div>
    </GraphAgentBridgeProvider>
  );
};

export default KnowledgeGraphPage;
