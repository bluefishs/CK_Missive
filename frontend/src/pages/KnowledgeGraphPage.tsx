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
  Input,
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
  CodeOutlined,
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
import { getAllMergedConfigs, getMergedNodeConfig } from '../config/graphNodeConfig';
import { useAuthGuard } from '../hooks/utility/useAuthGuard';
import { KGAdminPanel } from './knowledgeGraph/KGAdminPanel';

/** Code Wiki 模式的實體類型選項 */
const CODE_WIKI_TYPE_OPTIONS = [
  { label: 'Python 模組', value: 'py_module' },
  { label: 'Python 類別', value: 'py_class' },
  { label: 'Python 函數', value: 'py_function' },
  { label: '資料表', value: 'db_table' },
  { label: 'TS 模組', value: 'ts_module' },
  { label: 'React 元件', value: 'ts_component' },
  { label: 'React Hook', value: 'ts_hook' },
] as const;

/** Code Wiki 模式的關聯類型篩選選項 */
const CODE_RELATION_OPTIONS = [
  { label: '定義類別', value: 'defines_class' },
  { label: '定義函數', value: 'defines_function' },
  { label: '方法', value: 'has_method' },
  { label: '匯入', value: 'imports' },
  { label: '繼承', value: 'inherits' },
  { label: 'FK 引用', value: 'references_table' },
  { label: '呼叫', value: 'calls' },
  { label: '定義元件', value: 'defines_component' },
  { label: '定義 Hook', value: 'defines_hook' },
] as const;

type GraphMode = 'document' | 'codeWiki';

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

export interface KnowledgeGraphPageProps {
  /** 預設圖譜模式，由路由決定 */
  defaultMode?: GraphMode;
}

const KnowledgeGraphPage: React.FC<KnowledgeGraphPageProps> = ({ defaultMode = 'document' }) => {
  const { message } = App.useApp();
  const { isAdmin } = useAuthGuard();

  // Graph mode
  const [graphMode, setGraphMode] = useState<GraphMode>(defaultMode);

  // 穩定引用：公文模式傳給 KnowledgeGraph 的空 documentIds（避免每次渲染產生新引用）
  const emptyDocumentIds = useMemo<number[]>(() => [], []);

  // Code Wiki state
  const [codeWikiData, setCodeWikiData] = useState<ExternalGraphData | null>(null);
  const [codeWikiLoading, setCodeWikiLoading] = useState(false);
  const [codeWikiTypes, setCodeWikiTypes] = useState<string[]>(['py_module']);
  const [codeWikiPrefix, setCodeWikiPrefix] = useState<string>('');
  const [codeWikiRelTypes, setCodeWikiRelTypes] = useState<string[]>([]);

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

  // Load Code Wiki graph
  const loadCodeWiki = useCallback(async () => {
    setCodeWikiLoading(true);
    try {
      const result = await aiApi.getCodeWikiGraph({
        entity_types: codeWikiTypes,
        module_prefix: codeWikiPrefix.trim() || null,
        limit: 500,
      });
      if (result?.success) {
        setCodeWikiData({ nodes: result.nodes, edges: result.edges });
      } else {
        setCodeWikiData({ nodes: [], edges: [] });
      }
    } catch {
      message.error('載入代碼圖譜失敗');
      setCodeWikiData({ nodes: [], edges: [] });
    } finally {
      setCodeWikiLoading(false);
    }
  }, [codeWikiTypes, codeWikiPrefix, message]);

  // Apply client-side edge type filter
  const filteredCodeWikiData = useMemo<ExternalGraphData | null>(() => {
    if (!codeWikiData) return null;
    if (codeWikiRelTypes.length === 0) return codeWikiData;
    const allowedTypes = new Set(codeWikiRelTypes);
    const filteredEdges = codeWikiData.edges.filter((e) => allowedTypes.has(e.type));
    // Keep only nodes that participate in filtered edges
    const nodeIds = new Set<string>();
    for (const e of filteredEdges) {
      nodeIds.add(e.source);
      nodeIds.add(e.target);
    }
    const filteredNodes = codeWikiData.nodes.filter((n) => nodeIds.has(n.id));
    return { nodes: filteredNodes, edges: filteredEdges };
  }, [codeWikiData, codeWikiRelTypes]);

  // Auto-load Code Wiki ONLY when switching to code wiki mode（篩選條件變更不自動重載，靠按鈕觸發）
  const loadCodeWikiRef = useRef(loadCodeWiki);
  loadCodeWikiRef.current = loadCodeWiki;
  useEffect(() => {
    if (graphMode === 'codeWiki') {
      loadCodeWikiRef.current();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graphMode]);

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
    <div style={{ display: 'flex', gap: 0, height: 'calc(100vh - 120px)', overflow: 'hidden' }}>
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
        {/* Title + Mode Switch */}
        <div style={{ marginBottom: 4 }}>
          <Title level={5} style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
            {graphMode === 'document' ? <ApartmentOutlined /> : <CodeOutlined />}
            <span>{graphMode === 'document' ? '知識圖譜探索' : '代碼圖譜'}</span>
          </Title>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {graphMode === 'document'
              ? '視覺化公文關聯網絡與正規化實體'
              : '視覺化程式碼結構與模組關聯'}
          </Text>
        </div>

        {/* Mode Toggle */}
        <Space size={4}>
          <Button
            size="small"
            type={graphMode === 'document' ? 'primary' : 'default'}
            icon={<ApartmentOutlined />}
            onClick={() => {
              setCodeWikiData(null); // 清除代碼圖譜殘留資料
              setGraphMode('document');
            }}
          >
            公文圖譜
          </Button>
          <Button
            size="small"
            type={graphMode === 'codeWiki' ? 'primary' : 'default'}
            icon={<CodeOutlined />}
            onClick={() => setGraphMode('codeWiki')}
          >
            代碼圖譜
          </Button>
        </Space>

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

        {/* Code Wiki Controls */}
        {graphMode === 'codeWiki' && (
          <Card
            size="small"
            title={
              <span style={{ fontSize: 13 }}>
                <CodeOutlined /> 代碼圖譜篩選
              </span>
            }
            styles={{ body: { padding: '8px 12px' } }}
          >
            <Space direction="vertical" style={{ width: '100%' }} size={8}>
              <div>
                <Text style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>實體類型</Text>
                <Select
                  mode="multiple"
                  size="small"
                  style={{ width: '100%' }}
                  value={codeWikiTypes}
                  onChange={setCodeWikiTypes}
                  options={CODE_WIKI_TYPE_OPTIONS.map((o) => ({ label: o.label, value: o.value }))}
                  placeholder="選擇要顯示的實體類型"
                />
              </div>
              <div>
                <Text style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>模組前綴</Text>
                <Input
                  size="small"
                  placeholder="如 app.services.ai"
                  value={codeWikiPrefix}
                  onChange={(e) => setCodeWikiPrefix(e.target.value)}
                  allowClear
                />
              </div>
              <div>
                <Text style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>關聯類型篩選</Text>
                <Select
                  mode="multiple"
                  size="small"
                  style={{ width: '100%' }}
                  value={codeWikiRelTypes}
                  onChange={setCodeWikiRelTypes}
                  options={CODE_RELATION_OPTIONS.map((o) => ({ label: o.label, value: o.value }))}
                  placeholder="全部（不篩選）"
                  allowClear
                />
              </div>
              <Button
                block
                size="small"
                type="primary"
                icon={<SyncOutlined spin={codeWikiLoading} />}
                loading={codeWikiLoading}
                onClick={loadCodeWiki}
                disabled={codeWikiTypes.length === 0}
              >
                載入代碼圖譜
              </Button>
              {codeWikiData && (
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {(filteredCodeWikiData ?? codeWikiData).nodes.length} 個節點 · {(filteredCodeWikiData ?? codeWikiData).edges.length} 條關聯
                  {codeWikiRelTypes.length > 0 && ` (已篩選)`}
                </Text>
              )}
            </Space>
          </Card>
        )}

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
        {graphMode === 'codeWiki' && (codeWikiLoading || !codeWikiData) ? (
          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <Spin size="large" />
            <div style={{ marginTop: 12, color: '#888' }}>載入代碼圖譜...</div>
          </div>
        ) : (
          <KnowledgeGraph
            documentIds={emptyDocumentIds}
            height={typeof window !== 'undefined' ? window.innerHeight - 120 : 700}
            externalGraphData={graphMode === 'codeWiki' ? filteredCodeWikiData : undefined}
            onExternalRefresh={graphMode === 'codeWiki' ? loadCodeWiki : undefined}
          />
        )}
      </div>

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
  );
};

export default KnowledgeGraphPage;
