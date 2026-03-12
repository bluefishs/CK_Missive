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

import React, { useState, useCallback, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
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
  Input,
  Row,
  Col,
  Statistic,
  Spin,
  Switch,
  Alert,
  Tabs,
  Table,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  CodeOutlined,
  ForkOutlined,
  DatabaseOutlined,
  UploadOutlined,
  SyncOutlined,
  NodeIndexOutlined,
  ApartmentOutlined,
  SearchOutlined,
  DownloadOutlined,
} from '@ant-design/icons';

import { aiApi } from '../api/aiApi';
import { KnowledgeGraph } from '../components/ai/KnowledgeGraph';
import type { ExternalGraphData } from '../components/ai/KnowledgeGraph';
import { CodeWikiFiltersCard } from '../components/ai/CodeWikiFiltersCard';
import { CODE_TYPE_LABELS } from '../constants/codeGraphOptions';
import {
  getModuleMappings,
  saveModuleMappings,
  resetModuleMappings,
  buildModuleGraphData,
  type ModuleMapping,
} from '../config/moduleGraphConfig';
import { useCodeWikiGraph } from '../hooks/useCodeWikiGraph';
import { useAuthGuard } from '../hooks/utility/useAuthGuard';

const { Title, Text } = Typography;

const CodeGraphManagementPage: React.FC = () => {
  const { message } = App.useApp();
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

  // Code Wiki (shared hook)
  const codeWiki = useCodeWikiGraph();

  const queryClient = useQueryClient();

  // Module overview state
  const [erdSearchText, setErdSearchText] = useState('');

  // Active tab
  const [activeTab, setActiveTab] = useState<string>('modules');

  // Stable empty array for KnowledgeGraph
  const emptyDocumentIds = useMemo<number[]>(() => [], []);

  // Module graph state
  const [moduleMappings, setModuleMappings] = useState<ModuleMapping[]>(() => getModuleMappings());
  const [editingModule, setEditingModule] = useState<ModuleMapping | null>(null);
  const [editFieldValues, setEditFieldValues] = useState<Record<string, string>>({});

  // Dynamic module visibility from site management
  const { data: navMappings } = useQuery({
    queryKey: ['module-mappings-nav'],
    queryFn: () => aiApi.getModuleMappings(),
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });

  // Filter module mappings by navigation enabled state
  const effectiveMappings = useMemo(() => {
    if (!navMappings?.success || navMappings.enabled_keys.length === 0) {
      return moduleMappings;
    }
    const enabledSet = new Set(navMappings.enabled_keys);
    return moduleMappings.filter((m) => enabledSet.has(m.key));
  }, [moduleMappings, navMappings]);

  const moduleGraphData = useMemo<ExternalGraphData>(() => {
    const data = buildModuleGraphData(effectiveMappings);
    return { nodes: data.nodes, edges: data.edges };
  }, [effectiveMappings]);

  // =========================================================================
  // Load stats via React Query
  // =========================================================================
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['code-graph-stats'],
    queryFn: async () => {
      const graphStats = await aiApi.getGraphStats();
      if (!graphStats) return null;
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
      return {
        totalEntities: codeEntityCount,
        totalRelationships: graphStats.total_relationships ?? 0,
        typeDistribution: codeDist,
      };
    },
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const loadStats = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['code-graph-stats'] });
  }, [queryClient]);

  // =========================================================================
  // Load module overview via React Query (lazy: only when architecture tab active)
  // =========================================================================
  const { data: moduleOverview, isLoading: moduleOverviewLoading } = useQuery({
    queryKey: ['code-module-overview'],
    queryFn: () => aiApi.getModuleOverview(),
    enabled: activeTab === 'architecture',
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const loadModuleOverview = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['code-module-overview'] });
  }, [queryClient]);

  // Code wiki auto-loads via React Query in useCodeWikiGraph

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
        codeWiki.loadCodeWiki();
        loadStats();
      } else {
        message.error(result?.message || '代碼圖譜入圖失敗');
      }
    } catch {
      message.error('代碼圖譜入圖請求失敗');
    } finally {
      setCodeIngestLoading(false);
    }
  }, [message, ingestIncremental, ingestClean, codeWiki, loadStats]);

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
        codeWiki.loadCodeWiki();
        loadStats();
      } else {
        message.error(result?.message || 'JSON 圖譜匯入失敗');
      }
    } catch {
      message.error('JSON 圖譜匯入請求失敗');
    } finally {
      setJsonImportLoading(false);
    }
  }, [message, jsonClean, codeWiki, loadStats]);

  // =========================================================================
  // Architecture layer table data
  // =========================================================================
  interface LayerRow {
    key: string;
    layer: string;
    moduleCount: number;
    totalLines: number;
    totalFunctions: number;
    modules: Array<{
      key: string;
      name: string;
      lines: number;
      outgoing_deps: number;
      incoming_deps: number;
    }>;
  }

  const layerTableData = useMemo<LayerRow[]>(() => {
    if (!moduleOverview) return [];
    return Object.entries(moduleOverview.layers).map(([layerName, layerData]) => ({
      key: layerName,
      layer: layerName,
      moduleCount: layerData.modules.length,
      totalLines: layerData.total_lines,
      totalFunctions: layerData.total_functions,
      modules: layerData.modules.map((m) => ({
        key: `${layerName}-${m.name}`,
        name: m.name,
        lines: m.lines,
        outgoing_deps: m.outgoing_deps,
        incoming_deps: m.incoming_deps,
      })),
    }));
  }, [moduleOverview]);

  const layerColumns: ColumnsType<LayerRow> = [
    { title: '架構層', dataIndex: 'layer', key: 'layer', width: 200 },
    { title: '模組數', dataIndex: 'moduleCount', key: 'moduleCount', width: 100, sorter: (a, b) => a.moduleCount - b.moduleCount },
    { title: '程式碼行數', dataIndex: 'totalLines', key: 'totalLines', width: 140, sorter: (a, b) => a.totalLines - b.totalLines, render: (v: number) => v.toLocaleString() },
    { title: '函數數', dataIndex: 'totalFunctions', key: 'totalFunctions', width: 100, sorter: (a, b) => a.totalFunctions - b.totalFunctions },
  ];

  const moduleColumns: ColumnsType<LayerRow['modules'][number]> = [
    { title: '模組名稱', dataIndex: 'name', key: 'name' },
    { title: '行數', dataIndex: 'lines', key: 'lines', width: 100, sorter: (a, b) => a.lines - b.lines, render: (v: number) => v.toLocaleString() },
    { title: '出向依賴', dataIndex: 'outgoing_deps', key: 'outgoing_deps', width: 100, sorter: (a, b) => a.outgoing_deps - b.outgoing_deps },
    { title: '入向依賴', dataIndex: 'incoming_deps', key: 'incoming_deps', width: 100, sorter: (a, b) => a.incoming_deps - b.incoming_deps },
  ];

  // DB ERD table data
  interface DbTableRow {
    key: string;
    name: string;
    columns: number;
    has_primary_key: boolean;
    foreign_keys: string[];
    indexes: number;
    unique_constraints: number;
  }

  const erdTableData = useMemo<DbTableRow[]>(() => {
    if (!moduleOverview) return [];
    return moduleOverview.db_tables.map((t) => ({
      key: t.name,
      name: t.name,
      columns: t.columns,
      has_primary_key: t.has_primary_key,
      foreign_keys: t.foreign_keys,
      indexes: t.indexes,
      unique_constraints: t.unique_constraints,
    }));
  }, [moduleOverview]);

  const filteredErdData = useMemo(() => {
    if (!erdSearchText) return erdTableData;
    const lower = erdSearchText.toLowerCase();
    return erdTableData.filter((row) => row.name.toLowerCase().includes(lower));
  }, [erdTableData, erdSearchText]);

  const erdColumns: ColumnsType<DbTableRow> = [
    { title: '資料表', dataIndex: 'name', key: 'name', width: 240, sorter: (a, b) => a.name.localeCompare(b.name) },
    { title: '欄位數', dataIndex: 'columns', key: 'columns', width: 90, sorter: (a, b) => a.columns - b.columns },
    { title: '主鍵', dataIndex: 'has_primary_key', key: 'has_primary_key', width: 70, render: (v: boolean) => (v ? '\u2713' : '\u2717'), align: 'center' },
    { title: '外鍵', dataIndex: 'foreign_keys', key: 'foreign_keys', width: 300, render: (fks: string[]) => fks.length > 0 ? fks.join(', ') : '-' },
    { title: '索引數', dataIndex: 'indexes', key: 'indexes', width: 90, sorter: (a, b) => a.indexes - b.indexes },
    { title: '唯一約束', dataIndex: 'unique_constraints', key: 'unique_constraints', width: 100, sorter: (a, b) => a.unique_constraints - b.unique_constraints },
  ];

  // =========================================================================
  // Module graph handlers
  // =========================================================================
  const handleModuleEdit = useCallback((mod: ModuleMapping) => {
    setEditingModule({ ...mod });
    setEditFieldValues({});
  }, []);

  const handleModuleSave = useCallback(() => {
    if (!editingModule) return;
    const updated = moduleMappings.map((m) => m.key === editingModule.key ? editingModule : m);
    setModuleMappings(updated);
    saveModuleMappings(updated);
    setEditingModule(null);
    message.success(`模組「${editingModule.title}」已儲存`);
  }, [editingModule, moduleMappings, message]);

  const handleModuleReset = useCallback(() => {
    resetModuleMappings();
    const defaults = getModuleMappings();
    setModuleMappings(defaults);
    message.success('已重置為預設映射');
  }, [message]);

  // =========================================================================
  // A4: Export functions
  // =========================================================================
  const exportArchitectureLayers = useCallback(async () => {
    if (!moduleOverview) return;
    try {
      const XLSX = await import('xlsx');
      const layerRows = Object.entries(moduleOverview.layers).flatMap(([layer, data]) =>
        data.modules.map((m) => ({
          '架構層': layer,
          '模組名稱': m.name,
          '類型': m.type,
          '行數': m.lines,
          '函數數': m.functions,
          '出向依賴': m.outgoing_deps,
          '入向依賴': m.incoming_deps,
        })),
      );
      const ws = XLSX.utils.json_to_sheet(layerRows);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, '架構層統計');
      const date = new Date().toISOString().slice(0, 10).replace(/-/g, '');
      XLSX.writeFile(wb, `架構層統計_${date}.xlsx`);
      message.success('匯出成功');
    } catch {
      message.error('匯出失敗');
    }
  }, [moduleOverview, message]);

  const exportDbErd = useCallback(async () => {
    if (!filteredErdData.length) return;
    try {
      const XLSX = await import('xlsx');
      const rows = filteredErdData.map((t) => ({
        '資料表': t.name,
        '欄位數': t.columns,
        '主鍵': t.has_primary_key ? 'Y' : 'N',
        '外鍵關聯': t.foreign_keys.join(', '),
        '索引數': t.indexes,
        '唯一約束': t.unique_constraints,
      }));
      const ws = XLSX.utils.json_to_sheet(rows);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'DB ERD');
      const date = new Date().toISOString().slice(0, 10).replace(/-/g, '');
      XLSX.writeFile(wb, `DB_ERD_${date}.xlsx`);
      message.success('匯出成功');
    } catch {
      message.error('匯出失敗');
    }
  }, [filteredErdData, message]);

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

  const TYPE_LABELS = CODE_TYPE_LABELS;

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
          <Title level={5} style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
            <CodeOutlined /> 代碼圖譜
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
        <CodeWikiFiltersCard graph={codeWiki} title="圖譜篩選" />
      </div>

      {/* Center: Tabs */}
      <div style={{ flex: 1, minWidth: 0, overflow: 'hidden', background: '#fafafa', display: 'flex', flexDirection: 'column' }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
          tabBarStyle={{ paddingLeft: 16, marginBottom: 0, background: '#fff', borderBottom: '1px solid #f0f0f0' }}
          items={[
            {
              key: 'modules',
              label: '模組總覽',
              children: (
                <div style={{ display: 'flex', height: 'calc(100vh - 168px)', overflow: 'hidden' }}>
                  {/* Module Graph Visualization */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <KnowledgeGraph
                      documentIds={emptyDocumentIds}
                      height={typeof window !== 'undefined' ? window.innerHeight - 168 : 650}
                      externalGraphData={moduleGraphData}
                      onNodeClickExternal={(node) => {
                        // Click module node → show edit panel
                        if (node.type === 'menu_module') {
                          const mod = moduleMappings.find((m) => m.key === node.id.replace('mod_', ''));
                          if (mod) handleModuleEdit(mod);
                        }
                      }}
                    />
                  </div>
                  {/* Module Config Panel */}
                  <div style={{ width: 320, minWidth: 320, background: '#fff', borderLeft: '1px solid #f0f0f0', overflow: 'auto', padding: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <Title level={5} style={{ margin: 0, fontSize: 14 }}>模組配置</Title>
                      <Button size="small" onClick={handleModuleReset}>重置預設</Button>
                    </div>
                    <Divider style={{ margin: '8px 0' }} />

                    {editingModule ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Tag color={editingModule.color} style={{ fontSize: 13 }}>{editingModule.title}</Tag>
                          <Space size="small">
                            <Button size="small" type="primary" onClick={handleModuleSave}>儲存</Button>
                            <Button size="small" onClick={() => setEditingModule(null)}>取消</Button>
                          </Space>
                        </div>

                        {/* Editable arrays */}
                        {(['pages', 'apiGroups', 'backendServices', 'dbTables'] as const).map((field) => {
                          const labels: Record<string, string> = {
                            pages: '前端頁面',
                            apiGroups: 'API 端點群組',
                            backendServices: '後端服務',
                            dbTables: '資料庫表',
                          };
                          return (
                            <Card key={field} size="small" title={<span style={{ fontSize: 12 }}>{labels[field]}</span>} styles={{ body: { padding: 8 } }}>
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                                {editingModule[field].map((item, idx) => (
                                  <Tag
                                    key={idx}
                                    closable
                                    onClose={() => {
                                      const updated = { ...editingModule, [field]: editingModule[field].filter((_: string, i: number) => i !== idx) };
                                      setEditingModule(updated);
                                    }}
                                    style={{ fontSize: 11 }}
                                  >
                                    {item}
                                  </Tag>
                                ))}
                              </div>
                              <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
                                <Input
                                  size="small"
                                  placeholder={`新增${labels[field]}...`}
                                  value={editFieldValues[field] || ''}
                                  onChange={(e) => setEditFieldValues((prev) => ({ ...prev, [field]: e.target.value }))}
                                  onPressEnter={() => {
                                    const val = (editFieldValues[field] || '').trim();
                                    if (val) {
                                      const updated = { ...editingModule, [field]: [...editingModule[field], val] };
                                      setEditingModule(updated);
                                      setEditFieldValues((prev) => ({ ...prev, [field]: '' }));
                                    }
                                  }}
                                  style={{ flex: 1 }}
                                />
                              </div>
                            </Card>
                          );
                        })}
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        <Text type="secondary" style={{ fontSize: 12, marginBottom: 4 }}>
                          點擊圖譜中的模組節點進行編輯
                        </Text>
                        {moduleMappings.map((mod) => (
                          <Card
                            key={mod.key}
                            size="small"
                            hoverable
                            onClick={() => handleModuleEdit(mod)}
                            styles={{ body: { padding: '6px 10px' } }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <span>
                                <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: mod.color, marginRight: 6 }} />
                                <Text strong style={{ fontSize: 12 }}>{mod.title}</Text>
                              </span>
                              <Space size={2}>
                                <Tag style={{ fontSize: 10 }}>{mod.pages.length} 頁面</Tag>
                                <Tag style={{ fontSize: 10 }}>{mod.dbTables.length} 表</Tag>
                              </Space>
                            </div>
                          </Card>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ),
            },
            {
              key: 'graph',
              label: '程式碼圖譜',
              children: (
                <div style={{ flex: 1, height: 'calc(100vh - 168px)', overflow: 'hidden' }}>
                  {codeWiki.loading || !codeWiki.codeWikiData ? (
                    <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                      <Spin size="large" />
                      <div style={{ marginTop: 12, color: '#888' }}>載入代碼圖譜...</div>
                    </div>
                  ) : (
                    <KnowledgeGraph
                      documentIds={emptyDocumentIds}
                      height={typeof window !== 'undefined' ? window.innerHeight - 168 : 650}
                      externalGraphData={codeWiki.filteredData}
                      onExternalRefresh={codeWiki.loadCodeWiki}
                      onNodeClickExternal={(node) => {
                        if (node.type === 'db_table') {
                          setActiveTab('architecture');
                          setErdSearchText(node.label);
                          if (!moduleOverview) loadModuleOverview();
                        }
                      }}
                    />
                  )}
                </div>
              ),
            },
            {
              key: 'architecture',
              label: '架構總覽',
              children: (
                <div style={{ padding: 16, height: 'calc(100vh - 168px)', overflow: 'auto' }}>
                  {moduleOverviewLoading ? (
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
                      <Spin size="large" />
                    </div>
                  ) : moduleOverview ? (
                    <Space direction="vertical" style={{ width: '100%' }} size={16}>
                      {/* Summary stats */}
                      <Row gutter={16}>
                        <Col span={8}>
                          <Card size="small">
                            <Statistic title="總模組數" value={moduleOverview.summary.total_modules} prefix={<CodeOutlined />} />
                          </Card>
                        </Col>
                        <Col span={8}>
                          <Card size="small">
                            <Statistic title="資料表數" value={moduleOverview.summary.total_tables} prefix={<DatabaseOutlined />} />
                          </Card>
                        </Col>
                        <Col span={8}>
                          <Card size="small">
                            <Statistic title="關係總數" value={moduleOverview.summary.total_relations} prefix={<ApartmentOutlined />} />
                          </Card>
                        </Col>
                      </Row>

                      {/* Architecture Layer Table */}
                      <Card
                        title={<><ApartmentOutlined /> 架構層統計</>}
                        size="small"
                        extra={
                          <Space size="small">
                            <Button size="small" type="text" icon={<DownloadOutlined />} onClick={exportArchitectureLayers} title="匯出 Excel" />
                            <Button size="small" type="text" icon={<SyncOutlined spin={moduleOverviewLoading} />} onClick={loadModuleOverview} />
                          </Space>
                        }
                      >
                        <Table<LayerRow>
                          columns={layerColumns}
                          dataSource={layerTableData}
                          pagination={false}
                          size="small"
                          expandable={{
                            expandedRowRender: (record) => (
                              <Table
                                columns={moduleColumns}
                                dataSource={record.modules}
                                pagination={false}
                                size="small"
                              />
                            ),
                            rowExpandable: (record) => record.modules.length > 0,
                          }}
                        />
                      </Card>

                      {/* DB ERD Table */}
                      <Card
                        title={<><DatabaseOutlined /> 資料庫 ERD</>}
                        size="small"
                        extra={
                          <Space size="small">
                            <Input
                              placeholder="搜尋資料表..."
                              prefix={<SearchOutlined />}
                              size="small"
                              style={{ width: 200 }}
                              value={erdSearchText}
                              onChange={(e) => setErdSearchText(e.target.value)}
                              allowClear
                            />
                            <Button size="small" icon={<DownloadOutlined />} onClick={exportDbErd} title="匯出 Excel" />
                          </Space>
                        }
                      >
                        <Table<DbTableRow>
                          columns={erdColumns}
                          dataSource={filteredErdData}
                          pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => `共 ${total} 張資料表` }}
                          size="small"
                          scroll={{ x: 900 }}
                        />
                      </Card>
                    </Space>
                  ) : (
                    <Alert type="info" message="無模組概覽資料，請先執行代碼圖譜入圖。" showIcon />
                  )}
                </div>
              ),
            },
          ]}
        />
      </div>
    </div>
  );
};

export default CodeGraphManagementPage;
