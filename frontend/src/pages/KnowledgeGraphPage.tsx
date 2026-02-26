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

import React, { useEffect, useState, useCallback, useRef } from 'react';
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
  Popconfirm,
  App,
  Select,
  Modal,
  Tag,
} from 'antd';
import {
  ApartmentOutlined,
  RocketOutlined,
  SyncOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  NodeIndexOutlined,
  FileTextOutlined,
  CrownOutlined,
  SwapOutlined,
  ForkOutlined,
} from '@ant-design/icons';

import { aiApi } from '../api/aiApi';
import type {
  EmbeddingStatsResponse,
  EntityStatsResponse,
  KGGraphStatsResponse,
  EntityBatchResponse,
  KGIngestResponse,
  KGEntityItem,
  KGShortestPathResponse,
} from '../types/ai';
import { KnowledgeGraph } from '../components/ai/KnowledgeGraph';
import { getAllMergedConfigs, getMergedNodeConfig } from '../config/graphNodeConfig';
import { useAuthGuard } from '../hooks/utility/useAuthGuard';

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

  // Coverage stats
  const [coverageStats, setCoverageStats] = useState<CoverageStats>({
    embedding: null,
    entity: null,
    graph: null,
  });
  const [statsLoading, setStatsLoading] = useState(true);

  // Admin action loading states
  const [entityBatchLoading, setEntityBatchLoading] = useState(false);
  const [graphIngestLoading, setGraphIngestLoading] = useState(false);

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

  // Admin actions
  const handleEntityBatch = useCallback(async () => {
    setEntityBatchLoading(true);
    try {
      const result: EntityBatchResponse | null = await aiApi.runEntityBatch({ limit: 200 });
      if (result?.success) {
        message.success(result.message);
        loadStats();
      } else {
        message.error(result?.message || '批次提取失敗');
      }
    } catch {
      message.error('批次提取請求失敗');
    } finally {
      setEntityBatchLoading(false);
    }
  }, [message, loadStats]);

  const handleGraphIngest = useCallback(async () => {
    setGraphIngestLoading(true);
    try {
      const result: KGIngestResponse | null = await aiApi.triggerGraphIngest({ limit: 200 });
      if (result?.success) {
        message.success(result.message || `入圖完成：處理 ${result.total_processed ?? 0} 筆`);
        loadStats();
      } else {
        message.error(result?.message || '批次入圖失敗');
      }
    } catch {
      message.error('批次入圖請求失敗');
    } finally {
      setGraphIngestLoading(false);
    }
  }, [message, loadStats]);

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
        {/* Title */}
        <div style={{ marginBottom: 4 }}>
          <Title level={5} style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
            <ApartmentOutlined />
            <span>知識圖譜探索</span>
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
          <Card
            size="small"
            title={
              <span style={{ fontSize: 13 }}>
                <RocketOutlined /> 管理動作
              </span>
            }
            styles={{ body: { padding: '8px 12px' } }}
          >
            <Space direction="vertical" style={{ width: '100%' }} size={8}>
              <Popconfirm
                title="確定要批次提取實體？將處理最多 200 筆公文。"
                onConfirm={handleEntityBatch}
              >
                <Button
                  block
                  size="small"
                  icon={<ExperimentOutlined />}
                  loading={entityBatchLoading}
                  disabled={
                    (coverageStats.entity?.without_extraction ?? 1) === 0
                  }
                >
                  批次提取實體
                </Button>
              </Popconfirm>
              <Popconfirm
                title="確定要批次入圖？將處理最多 200 筆已提取公文。"
                onConfirm={handleGraphIngest}
              >
                <Button
                  block
                  size="small"
                  icon={<ApartmentOutlined />}
                  loading={graphIngestLoading}
                >
                  批次入圖
                </Button>
              </Popconfirm>
              <Button
                block
                size="small"
                icon={<SwapOutlined />}
                onClick={() => setMergeModalOpen(true)}
              >
                合併實體
              </Button>
            </Space>
          </Card>
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
      <div style={{ flex: 1, overflow: 'hidden', background: '#fafafa' }}>
        <KnowledgeGraph
          documentIds={[]}
          height={typeof window !== 'undefined' ? window.innerHeight - 120 : 700}
        />
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
