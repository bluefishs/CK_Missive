import React, { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Space,
  Button,
  Typography,
  App,
  Tag,
  Tooltip,
  Input,
  Collapse,
  List,
  Spin,
} from 'antd';
import {
  RobotOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SearchOutlined,
  FileTextOutlined,
} from '@ant-design/icons';

import { aiApi } from '../api/aiApi';
import type { SmartGraphSearchResult } from '../api/ai';
import type {
  KGEntityItem,
  KGShortestPathResponse,
} from '../types/ai';
import { KnowledgeGraph } from '../components/ai/KnowledgeGraph';
import type { ExternalGraphData } from '../components/ai/KnowledgeGraph';
import { RAGChatPanel } from '../components/ai/RAGChatPanel';
import { GraphAgentBridgeProvider } from '../components/ai/knowledgeGraph/GraphAgentBridge';
import { ErrorBoundary } from '../components/common/ErrorBoundary';
import { getMergedNodeConfig } from '../config/graphNodeConfig';
import type { ColorByMode } from '../components/ai/knowledgeGraph/useGraphTransform';
import { useAuthGuard } from '../hooks/utility/useAuthGuard';
import GraphLeftPanel from './knowledgeGraph/GraphLeftPanel';
import MergeEntitiesModal from './knowledgeGraph/MergeEntitiesModal';

const { Text } = Typography;

import type { CoverageStats } from './knowledgeGraph/CoveragePanel';

const KnowledgeGraphPage: React.FC = () => {
  const { message } = App.useApp();
  const { isAdmin } = useAuthGuard();

  const emptyDocumentIds = useMemo<number[]>(() => [], []);

  const [selectedYear, setSelectedYear] = useState<number | undefined>(undefined);
  const yearOptions = useMemo(() => {
    const currentRocYear = new Date().getFullYear() - 1911;
    const options = [{ label: '全部年度', value: 0 }];
    for (let y = currentRocYear; y >= currentRocYear - 4; y--) {
      options.push({ label: `${y} 年`, value: y });
    }
    return options;
  }, []);

  const [collapseAgency, setCollapseAgency] = useState(true);
  const [colorBy, setColorBy] = useState<ColorByMode>('type');
  const [visibleSourceProjects, setVisibleSourceProjects] = useState<Set<string>>(new Set());

  const queryClient = useQueryClient();

  const {
    data: statsData,
    isLoading: statsLoading,
    refetch: refetchStats,
  } = useQuery({
    queryKey: ['kg-coverage-stats'],
    queryFn: async () => {
      const [embedding, entity, graph, topEnt] = await Promise.allSettled([
        aiApi.getEmbeddingStats(),
        aiApi.getEntityStats(),
        aiApi.getGraphStats(),
        aiApi.getTopEntities({ limit: 10 }),
      ]);
      return {
        coverageStats: {
          embedding: embedding.status === 'fulfilled' ? embedding.value : null,
          entity: entity.status === 'fulfilled' ? entity.value : null,
          graph: graph.status === 'fulfilled' ? graph.value : null,
        } as CoverageStats,
        topEntities:
          topEnt.status === 'fulfilled' && topEnt.value?.entities
            ? topEnt.value.entities
            : ([] as KGEntityItem[]),
      };
    },
    staleTime: 5 * 60 * 1000,  // 統計資料 5 分鐘快取
    gcTime: 10 * 60 * 1000,
  });
  const coverageStats = statsData?.coverageStats ?? { embedding: null, entity: null, graph: null };
  const topEntities = statsData?.topEntities ?? [];

  const { data: entityGraphData, refetch: refetchEntityGraph } = useQuery({
    queryKey: ['kg-entity-graph', selectedYear, collapseAgency],
    queryFn: async () => {
      const params: { min_mentions: number; limit: number; year?: number; collapse_agency?: boolean } = {
        min_mentions: 2,
        limit: 150,
        collapse_agency: collapseAgency,
      };
      if (selectedYear && selectedYear > 0) {
        params.year = selectedYear;
      }
      const result = await aiApi.getEntityGraph(params);
      if (result?.success && result.nodes.length > 0) {
        return { nodes: result.nodes, edges: result.edges } as ExternalGraphData;
      }
      return null;
    },
    staleTime: 5 * 60 * 1000,  // 圖譜資料 5 分鐘快取
    gcTime: 10 * 60 * 1000,
    placeholderData: (prev) => prev,  // 切換篩選時保留舊資料避免閃爍
  });

  const [pathSourceId, setPathSourceId] = useState<number | null>(null);
  const [pathTargetId, setPathTargetId] = useState<number | null>(null);
  const [pathResult, setPathResult] = useState<KGShortestPathResponse | null>(null);

  const [chatPanelOpen, setChatPanelOpen] = useState(true);

  const graphContainerRef = useRef<HTMLDivElement>(null);
  const [graphWidth, setGraphWidth] = useState(0);

  useEffect(() => {
    const el = graphContainerRef.current;
    if (!el) return;
    const measure = () => {
      const w = el.clientWidth;
      if (w > 0) setGraphWidth(w);
    };
    measure();
    const observer = new ResizeObserver(() => measure());
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const [mergeModalOpen, setMergeModalOpen] = useState(false);
  const [mergeKeepId, setMergeKeepId] = useState<number | null>(null);
  const [mergeMergeId, setMergeMergeId] = useState<number | null>(null);

  const searchTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const [entityOptions, setEntityOptions] = useState<Array<{ label: string; value: number }>>([]);

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

  const [pathTrigger, setPathTrigger] = useState(0);
  const pathQueryEnabled = !!(pathSourceId && pathTargetId && pathTrigger > 0);

  const findPathQuery = useQuery({
    queryKey: ['kg-cross-domain-path', pathSourceId, pathTargetId],
    queryFn: () => aiApi.findCrossDomainPath({
      source_id: pathSourceId!,
      target_id: pathTargetId!,
    }),
    enabled: pathQueryEnabled,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });

  useEffect(() => {
    if (findPathQuery.data) {
      setPathResult(findPathQuery.data);
      if (!findPathQuery.data.found) {
        message.info('未找到兩實體間的路徑');
      }
    }
  }, [findPathQuery.data, message]);

  useEffect(() => {
    if (findPathQuery.error) {
      message.error('路徑查詢失敗');
    }
  }, [findPathQuery.error, message]);

  const handleFindPath = useCallback(() => {
    if (!pathSourceId || !pathTargetId) return;
    setPathResult(null);
    setPathTrigger((t) => t + 1);
  }, [pathSourceId, pathTargetId]);

  const mergeMutation = useMutation({
    mutationFn: (params: { keep_id: number; merge_id: number }) =>
      aiApi.mergeGraphEntities(params),
    onSuccess: (result) => {
      if (result?.success) {
        message.success(result.message || '合併成功');
        setMergeModalOpen(false);
        setMergeKeepId(null);
        setMergeMergeId(null);
        queryClient.invalidateQueries({ queryKey: ['kg-coverage-stats'] });
        queryClient.invalidateQueries({ queryKey: ['kg-entity-graph'] });
      } else {
        message.error(result?.message || '合併失敗');
      }
    },
    onError: () => {
      message.error('合併請求失敗');
    },
  });

  const handleMerge = useCallback(() => {
    if (!mergeKeepId || !mergeMergeId) return;
    mergeMutation.mutate({ keep_id: mergeKeepId, merge_id: mergeMergeId });
  }, [mergeKeepId, mergeMergeId, mergeMutation]);

  const handleSourceChange = useCallback((val: number | null) => {
    setPathSourceId(val);
    setPathResult(null);
  }, []);

  const handleTargetChange = useCallback((val: number | null) => {
    setPathTargetId(val);
    setPathResult(null);
  }, []);

  // --- NL Smart Search ---
  const [nlSearchText, setNlSearchText] = useState('');
  const [nlSearchResult, setNlSearchResult] = useState<SmartGraphSearchResult | null>(null);
  const [nlSearchLoading, setNlSearchLoading] = useState(false);

  const handleNlSearch = useCallback(async (value: string) => {
    const q = value.trim();
    if (!q) return;
    setNlSearchLoading(true);
    try {
      const result = await aiApi.smartGraphSearch(q);
      setNlSearchResult(result);
      if (result.success && result.data?.count === 0) {
        message.info('未找到相關實體');
      }
    } catch {
      message.error('搜尋失敗');
    } finally {
      setNlSearchLoading(false);
    }
  }, [message]);

  const graphTypeDistribution = coverageStats.graph?.entity_type_distribution;
  const sourceProjectDistribution = coverageStats.graph?.source_project_distribution;

  return (
    <GraphAgentBridgeProvider>
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', overflow: 'hidden' }}>
      <div style={{ display: 'flex', gap: 0, flex: 1, overflow: 'hidden', position: 'relative' }}>
      <GraphLeftPanel
        selectedYear={selectedYear}
        onYearChange={setSelectedYear}
        yearOptions={yearOptions}
        collapseAgency={collapseAgency}
        onCollapseAgencyChange={setCollapseAgency}
        coverageStats={coverageStats}
        statsLoading={statsLoading}
        onRefetchStats={() => refetchStats()}
        isAdmin={isAdmin}
        withoutExtraction={coverageStats.entity?.without_extraction ?? 1}
        onOpenMergeModal={() => setMergeModalOpen(true)}
        graphTypeDistribution={graphTypeDistribution}
        sourceProjectDistribution={sourceProjectDistribution}
        topEntities={topEntities}
        pathSourceId={pathSourceId}
        pathTargetId={pathTargetId}
        pathResult={pathResult}
        entityOptions={entityOptions}
        onSourceChange={handleSourceChange}
        onTargetChange={handleTargetChange}
        onEntitySearch={handleEntitySearch}
        onFindPath={handleFindPath}
        findPathLoading={findPathQuery.isFetching}
        colorBy={colorBy}
        onColorByChange={setColorBy}
        visibleSourceProjects={visibleSourceProjects}
        onVisibleSourceProjectsChange={setVisibleSourceProjects}
      />

      <div style={{ flex: 1, minWidth: 0, overflow: 'hidden', background: '#fafafa', display: 'flex', flexDirection: 'column' }}>
        {/* NL Smart Search */}
        <div style={{ padding: '8px 12px', borderBottom: '1px solid #f0f0f0', background: '#fff', flexShrink: 0 }}>
          <Input.Search
            placeholder="自然語言搜尋知識圖譜..."
            allowClear
            enterButton={<><SearchOutlined /> 搜尋</>}
            value={nlSearchText}
            onChange={(e) => setNlSearchText(e.target.value)}
            onSearch={handleNlSearch}
            loading={nlSearchLoading}
            style={{ maxWidth: 500 }}
          />
          {nlSearchLoading && <Spin size="small" style={{ marginLeft: 8 }} />}
        </div>
        {nlSearchResult?.success && nlSearchResult.data && (
          <div style={{ flexShrink: 0, maxHeight: 260, overflow: 'auto', borderBottom: '1px solid #f0f0f0' }}>
            <Collapse
              defaultActiveKey={['entities']}
              size="small"
              items={[
                {
                  key: 'entities',
                  label: `搜尋結果 (${nlSearchResult.data.count} 個實體)`,
                  children: (
                    <List
                      size="small"
                      dataSource={nlSearchResult.data.entities}
                      renderItem={(item) => (
                        <List.Item>
                          <List.Item.Meta
                            title={<span>{item.canonical_name} <Tag>{item.entity_type}</Tag></span>}
                            description={`提及次數: ${item.mention_count}${item.description ? ` — ${item.description}` : ''}`}
                          />
                        </List.Item>
                      )}
                    />
                  ),
                },
                ...(nlSearchResult.data.related_documents?.length
                  ? [{
                      key: 'documents',
                      label: `相關公文 (${nlSearchResult.data.related_documents.length})`,
                      children: (
                        <List
                          size="small"
                          dataSource={nlSearchResult.data.related_documents}
                          renderItem={(doc) => (
                            <List.Item>
                              <List.Item.Meta
                                avatar={<FileTextOutlined />}
                                title={doc.subject}
                                description={`${doc.doc_number || ''}${doc.doc_date ? ` | ${doc.doc_date}` : ''}`}
                              />
                            </List.Item>
                          )}
                        />
                      ),
                    }]
                  : []),
              ]}
            />
          </div>
        )}
        <div ref={graphContainerRef} style={{ flex: 1, minWidth: 0, overflow: 'hidden' }}>
        <ErrorBoundary>
          <KnowledgeGraph
            documentIds={emptyDocumentIds}
            externalGraphData={entityGraphData ?? undefined}
            onExternalRefresh={() => refetchEntityGraph()}
            height={typeof window !== 'undefined' ? window.innerHeight - 120 : 700}
            width={graphWidth || undefined}
            colorBy={colorBy}
            visibleSourceProjects={visibleSourceProjects}
          />
        </ErrorBoundary>
      </div>
      </div>

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
          <RAGChatPanel embedded agentMode context="knowledge-graph" />
        </div>
      )}

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

      <MergeEntitiesModal
        open={mergeModalOpen}
        onCancel={() => { setMergeModalOpen(false); setMergeKeepId(null); setMergeMergeId(null); }}
        onOk={handleMerge}
        keepId={mergeKeepId}
        mergeId={mergeMergeId}
        onKeepChange={(val) => setMergeKeepId(val)}
        onMergeChange={(val) => setMergeMergeId(val)}
        entityOptions={entityOptions}
        onSearch={handleEntitySearch}
        isLoading={mergeMutation.isPending}
      />
    </div>
    </div>
    </GraphAgentBridgeProvider>
  );
};

export default KnowledgeGraphPage;
