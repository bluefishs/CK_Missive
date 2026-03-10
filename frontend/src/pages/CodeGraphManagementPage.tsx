/**
 * CodeGraphManagementPage - 代碼圖譜管理頁面
 *
 * 獨立的開發者工具頁面，從 KnowledgeGraphPage 拆分出代碼圖譜管理功能：
 * - 代碼圖譜入圖（Python AST + TypeScript + DB Schema）
 * - JSON 圖譜匯入
 * - 循環依賴偵測
 * - 架構分析報告
 * - 代碼圖譜視覺化預覽
 *
 * @version 1.0.0
 * @created 2026-03-10
 */

import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import {
  Card,
  Space,
  Button,
  Popconfirm,
  Modal,
  Tag,
  Divider,
  Typography,
  App,
  Select,
  Input,
  Row,
  Col,
  Statistic,
  Spin,
  Switch,
  Alert,
} from 'antd';
import {
  CodeOutlined,
  ForkOutlined,
  DatabaseOutlined,
  UploadOutlined,
  SyncOutlined,
  NodeIndexOutlined,
  ApartmentOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

import { aiApi } from '../api/aiApi';
import { KnowledgeGraph } from '../components/ai/KnowledgeGraph';
import type { ExternalGraphData } from '../components/ai/KnowledgeGraph';
import { useAuthGuard } from '../hooks/utility/useAuthGuard';
import { ROUTES } from '../router/types';

const { Title, Text } = Typography;

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

const CodeGraphManagementPage: React.FC = () => {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const { isAdmin } = useAuthGuard();

  // =========================================================================
  // Admin action loading states
  // =========================================================================
  const [codeIngestLoading, setCodeIngestLoading] = useState(false);
  const [cycleLoading, setCycleLoading] = useState(false);
  const [archLoading, setArchLoading] = useState(false);
  const [jsonImportLoading, setJsonImportLoading] = useState(false);

  // Ingest options
  const [ingestIncremental, setIngestIncremental] = useState(true);
  const [ingestClean, setIngestClean] = useState(false);
  const [jsonClean, setJsonClean] = useState(true);

  // =========================================================================
  // Code Wiki visualization state
  // =========================================================================
  const [codeWikiData, setCodeWikiData] = useState<ExternalGraphData | null>(null);
  const [codeWikiLoading, setCodeWikiLoading] = useState(false);
  const [codeWikiTypes, setCodeWikiTypes] = useState<string[]>(['py_module']);
  const [codeWikiPrefix, setCodeWikiPrefix] = useState<string>('');
  const [codeWikiRelTypes, setCodeWikiRelTypes] = useState<string[]>([]);

  // Stats
  const [stats, setStats] = useState<{
    totalEntities: number;
    totalRelationships: number;
    typeDistribution: Record<string, number>;
  } | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);

  // Stable empty array for KnowledgeGraph
  const emptyDocumentIds = useMemo<number[]>(() => [], []);

  // =========================================================================
  // Load stats
  // =========================================================================
  const loadStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const graphStats = await aiApi.getGraphStats();
      if (graphStats) {
        // Filter only code-related entity types for display
        const codeTypes = new Set(['py_module', 'py_class', 'py_function', 'db_table', 'ts_module', 'ts_component', 'ts_hook']);
        const codeDist: Record<string, number> = {};
        let codeEntityCount = 0;
        if (graphStats.entity_type_distribution) {
          for (const [type, count] of Object.entries(graphStats.entity_type_distribution)) {
            if (codeTypes.has(type)) {
              codeDist[type] = count;
              codeEntityCount += count;
            }
          }
        }
        setStats({
          totalEntities: codeEntityCount,
          totalRelationships: graphStats.total_relationships ?? 0,
          typeDistribution: codeDist,
        });
      }
    } catch {
      // silent
    } finally {
      setStatsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  // =========================================================================
  // Code Wiki visualization
  // =========================================================================
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

  // Auto-load on mount
  const loadCodeWikiRef = useRef(loadCodeWiki);
  loadCodeWikiRef.current = loadCodeWiki;
  useEffect(() => {
    loadCodeWikiRef.current();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Apply client-side edge type filter
  const filteredCodeWikiData = useMemo<ExternalGraphData | null>(() => {
    if (!codeWikiData) return null;
    if (codeWikiRelTypes.length === 0) return codeWikiData;
    const allowedTypes = new Set(codeWikiRelTypes);
    const filteredEdges = codeWikiData.edges.filter((e) => allowedTypes.has(e.type));
    const nodeIds = new Set<string>();
    for (const e of filteredEdges) {
      nodeIds.add(e.source);
      nodeIds.add(e.target);
    }
    const filteredNodes = codeWikiData.nodes.filter((n) => nodeIds.has(n.id));
    return { nodes: filteredNodes, edges: filteredEdges };
  }, [codeWikiData, codeWikiRelTypes]);

  // =========================================================================
  // Admin handlers
  // =========================================================================

  const handleCodeGraphIngest = useCallback(async () => {
    setCodeIngestLoading(true);
    try {
      const result = await aiApi.triggerCodeGraphIngest({
        incremental: ingestIncremental,
        clean: ingestClean,
      });
      if (result?.success) {
        const parts = [result.message];
        if (result.elapsed_seconds > 0) parts.push(`（耗時 ${result.elapsed_seconds.toFixed(1)}s）`);
        message.success(parts.join(''));
        loadCodeWiki();
        loadStats();
      } else {
        message.error(result?.message || '代碼圖譜入圖失敗');
      }
    } catch {
      message.error('代碼圖譜入圖請求失敗');
    } finally {
      setCodeIngestLoading(false);
    }
  }, [message, ingestIncremental, ingestClean, loadCodeWiki, loadStats]);

  const handleCycleDetection = useCallback(async () => {
    setCycleLoading(true);
    try {
      const result = await aiApi.detectImportCycles();
      if (result?.success) {
        if (result.cycles_found === 0) {
          message.success(`掃描 ${result.total_modules} 個模組、${result.total_import_edges} 條匯入，未發現循環依賴`);
        } else {
          Modal.warning({
            title: `發現 ${result.cycles_found} 個循環依賴`,
            width: 600,
            content: (
              <div style={{ maxHeight: 400, overflow: 'auto' }}>
                {result.cycles.slice(0, 20).map((cycle: string[], i: number) => (
                  <div key={i} style={{ marginBottom: 8, fontSize: 12, fontFamily: 'monospace' }}>
                    <Tag color="red">Cycle {i + 1}</Tag>
                    {cycle.join(' → ')}
                  </div>
                ))}
                {result.cycles_found > 20 && (
                  <Text type="secondary">...還有 {result.cycles_found - 20} 個循環</Text>
                )}
              </div>
            ),
          });
        }
      } else {
        message.error('循環偵測失敗');
      }
    } catch {
      message.error('循環偵測請求失敗');
    } finally {
      setCycleLoading(false);
    }
  }, [message]);

  const handleArchAnalysis = useCallback(async () => {
    setArchLoading(true);
    try {
      const result = await aiApi.analyzeArchitecture();
      if (result?.success) {
        Modal.info({
          title: '架構分析報告',
          width: 700,
          content: (
            <div style={{ maxHeight: 500, overflow: 'auto', fontSize: 12 }}>
              <Divider orientation="left" style={{ fontSize: 13 }}>概要</Divider>
              <Space wrap>
                {Object.entries(result.summary || {}).map(([k, v]) => (
                  <Tag key={k}>{k}: {String(v)}</Tag>
                ))}
              </Space>

              {result.complexity_hotspots.length > 0 && (
                <>
                  <Divider orientation="left" style={{ fontSize: 13 }}>高耦合模組 (出向依賴最多)</Divider>
                  {result.complexity_hotspots.map((h: { module: string; outgoing_deps: number }, i: number) => (
                    <div key={i} style={{ fontFamily: 'monospace', marginBottom: 2 }}>
                      <Tag color="red">{h.outgoing_deps}</Tag> {h.module}
                    </div>
                  ))}
                </>
              )}

              {result.hub_modules.length > 0 && (
                <>
                  <Divider orientation="left" style={{ fontSize: 13 }}>樞紐模組 (被匯入最多)</Divider>
                  {result.hub_modules.map((h: { module: string; imported_by: number }, i: number) => (
                    <div key={i} style={{ fontFamily: 'monospace', marginBottom: 2 }}>
                      <Tag color="blue">{h.imported_by}</Tag> {h.module}
                    </div>
                  ))}
                </>
              )}

              {result.large_modules.length > 0 && (
                <>
                  <Divider orientation="left" style={{ fontSize: 13 }}>大型模組 (行數最多)</Divider>
                  {result.large_modules.map((h: { module: string; lines: number }, i: number) => (
                    <div key={i} style={{ fontFamily: 'monospace', marginBottom: 2 }}>
                      <Tag color="orange">{h.lines} 行</Tag> {h.module}
                    </div>
                  ))}
                </>
              )}

              {result.god_classes.length > 0 && (
                <>
                  <Divider orientation="left" style={{ fontSize: 13 }}>巨型類別 (方法數最多)</Divider>
                  {result.god_classes.map((h: { class: string; method_count: number }, i: number) => (
                    <div key={i} style={{ fontFamily: 'monospace', marginBottom: 2 }}>
                      <Tag color="purple">{h.method_count} 方法</Tag> {h.class}
                    </div>
                  ))}
                </>
              )}

              {result.orphan_modules.length > 0 && (
                <>
                  <Divider orientation="left" style={{ fontSize: 13 }}>孤立模組 (無入向匯入) — 前 {result.orphan_modules.length} 個</Divider>
                  <div style={{ fontFamily: 'monospace', lineHeight: 1.8 }}>
                    {result.orphan_modules.map((m: string, i: number) => (
                      <Tag key={i} style={{ marginBottom: 2 }}>{m}</Tag>
                    ))}
                  </div>
                </>
              )}
            </div>
          ),
        });
      } else {
        message.error('架構分析失敗');
      }
    } catch {
      message.error('架構分析請求失敗');
    } finally {
      setArchLoading(false);
    }
  }, [message]);

  const handleJsonImport = useCallback(async () => {
    setJsonImportLoading(true);
    try {
      const result = await aiApi.importJsonGraph({ clean: jsonClean });
      if (result?.success) {
        message.success(`${result.message}（耗時 ${result.elapsed_seconds.toFixed(1)}s）`);
        loadCodeWiki();
        loadStats();
      } else {
        message.error(result?.message || 'JSON 圖譜匯入失敗');
      }
    } catch {
      message.error('JSON 圖譜匯入請求失敗');
    } finally {
      setJsonImportLoading(false);
    }
  }, [message, jsonClean, loadCodeWiki, loadStats]);

  // =========================================================================
  // Render
  // =========================================================================

  if (!isAdmin) {
    return (
      <div style={{ padding: 24 }}>
        <Alert type="warning" message="此頁面需要管理員權限" showIcon />
      </div>
    );
  }

  const TYPE_LABELS: Record<string, string> = {
    py_module: 'Python 模組',
    py_class: 'Python 類別',
    py_function: 'Python 函數',
    db_table: '資料表',
    ts_module: 'TS 模組',
    ts_component: 'React 元件',
    ts_hook: 'React Hook',
  };

  return (
    <div style={{ display: 'flex', gap: 0, height: 'calc(100vh - 120px)', overflow: 'hidden' }}>
      {/* Left Panel */}
      <div
        style={{
          width: 300,
          minWidth: 300,
          background: '#fff',
          borderRight: '1px solid #f0f0f0',
          overflow: 'auto',
          padding: 16,
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}
      >
        {/* Header */}
        <div>
          <Button
            type="text"
            size="small"
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate(ROUTES.CODE_WIKI)}
            style={{ marginBottom: 4 }}
          >
            返回代碼圖譜
          </Button>
          <Title level={5} style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
            <CodeOutlined /> 代碼圖譜管理
          </Title>
          <Text type="secondary" style={{ fontSize: 12 }}>
            程式碼結構分析、入圖、匯入與品質檢測
          </Text>
        </div>

        <Divider style={{ margin: '4px 0' }} />

        {/* Stats */}
        <Card
          size="small"
          title={<span style={{ fontSize: 13 }}><DatabaseOutlined /> 圖譜統計</span>}
          extra={
            <Button size="small" type="text" icon={<SyncOutlined spin={statsLoading} />} onClick={loadStats} />
          }
          styles={{ body: { padding: '8px 12px' } }}
        >
          {statsLoading ? (
            <Spin size="small" />
          ) : stats ? (
            <>
              <Row gutter={[8, 8]}>
                <Col span={12}>
                  <Statistic
                    title={<span style={{ fontSize: 11 }}>程式碼實體</span>}
                    value={stats.totalEntities}
                    prefix={<NodeIndexOutlined style={{ fontSize: 12 }} />}
                    valueStyle={{ fontSize: 18 }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title={<span style={{ fontSize: 11 }}>關係數量</span>}
                    value={stats.totalRelationships}
                    prefix={<ApartmentOutlined style={{ fontSize: 12 }} />}
                    valueStyle={{ fontSize: 18 }}
                  />
                </Col>
              </Row>
              {Object.keys(stats.typeDistribution).length > 0 && (
                <div style={{ marginTop: 8 }}>
                  {Object.entries(stats.typeDistribution).map(([type, count]) => (
                    <div key={type} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, padding: '2px 0' }}>
                      <span>{TYPE_LABELS[type] || type}</span>
                      <Text type="secondary">{count}</Text>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <Text type="secondary" style={{ fontSize: 12 }}>無資料</Text>
          )}
        </Card>

        {/* Admin Actions */}
        <Card
          size="small"
          title={<span style={{ fontSize: 13 }}><CodeOutlined /> 管理動作</span>}
          styles={{ body: { padding: '8px 12px' } }}
        >
          <Space direction="vertical" style={{ width: '100%' }} size={8}>
            {/* Code Graph Ingest */}
            <div>
              <div style={{ display: 'flex', gap: 12, marginBottom: 4 }}>
                <label style={{ fontSize: 11, display: 'flex', alignItems: 'center', gap: 4 }}>
                  <Switch size="small" checked={ingestIncremental} onChange={setIngestIncremental} />
                  增量模式
                </label>
                <label style={{ fontSize: 11, display: 'flex', alignItems: 'center', gap: 4 }}>
                  <Switch size="small" checked={ingestClean} onChange={setIngestClean} />
                  清除重建
                </label>
              </div>
              <Popconfirm
                title={`確定要${ingestClean ? '清除並重新' : ingestIncremental ? '增量' : '全量'}掃描代碼圖譜？`}
                onConfirm={handleCodeGraphIngest}
              >
                <Button block size="small" icon={<CodeOutlined />} loading={codeIngestLoading}>
                  代碼圖譜入圖
                </Button>
              </Popconfirm>
            </div>

            <Divider style={{ margin: '4px 0' }} />

            {/* JSON Import */}
            <div>
              <label style={{ fontSize: 11, display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
                <Switch size="small" checked={jsonClean} onChange={setJsonClean} />
                匯入前清除舊資料
              </label>
              <Popconfirm
                title={`匯入本地 knowledge_graph.json？${jsonClean ? '將清除現有代碼圖譜資料後重新匯入。' : ''}`}
                onConfirm={handleJsonImport}
              >
                <Button block size="small" icon={<UploadOutlined />} loading={jsonImportLoading}>
                  JSON 圖譜匯入
                </Button>
              </Popconfirm>
            </div>

            <Divider style={{ margin: '4px 0' }} />

            {/* Analysis Tools */}
            <Button
              block
              size="small"
              icon={<ForkOutlined />}
              loading={cycleLoading}
              onClick={handleCycleDetection}
            >
              循環依賴偵測
            </Button>
            <Button
              block
              size="small"
              icon={<DatabaseOutlined />}
              loading={archLoading}
              onClick={handleArchAnalysis}
            >
              架構分析報告
            </Button>
          </Space>
        </Card>

        {/* Code Wiki Filters */}
        <Card
          size="small"
          title={<span style={{ fontSize: 13 }}><CodeOutlined /> 圖譜篩選</span>}
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
                {codeWikiRelTypes.length > 0 && ' (已篩選)'}
              </Text>
            )}
          </Space>
        </Card>
      </div>

      {/* Center: Graph Visualization */}
      <div style={{ flex: 1, minWidth: 0, overflow: 'hidden', background: '#fafafa' }}>
        {codeWikiLoading || !codeWikiData ? (
          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <Spin size="large" />
            <div style={{ marginTop: 12, color: '#888' }}>載入代碼圖譜...</div>
          </div>
        ) : (
          <KnowledgeGraph
            documentIds={emptyDocumentIds}
            height={typeof window !== 'undefined' ? window.innerHeight - 120 : 700}
            externalGraphData={filteredCodeWikiData}
            onExternalRefresh={loadCodeWiki}
          />
        )}
      </div>
    </div>
  );
};

export default CodeGraphManagementPage;
