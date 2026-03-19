import React, { useState, useCallback, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  App,
  Spin,
  Alert,
  Tabs,
} from 'antd';

import { aiApi } from '../api/aiApi';
import { KnowledgeGraph } from '../components/ai/KnowledgeGraph';
import type { ExternalGraphData } from '../components/ai/KnowledgeGraph';
import {
  getModuleMappings,
  saveModuleMappings,
  resetModuleMappings,
  buildModuleGraphData,
  type ModuleMapping,
} from '../config/moduleGraphConfig';
import { useCodeWikiGraph } from '../hooks/useCodeWikiGraph';
import { useAuthGuard } from '../hooks/utility/useAuthGuard';
import { CodeGraphSidebar, ModuleConfigPanel, ArchitectureOverviewTab } from './codeGraph';
import type { LayerRow, DbTableRow } from './codeGraph';
import { useCodeGraphHandlers } from './useCodeGraphHandlers';

const CodeGraphManagementPage: React.FC = () => {
  const { message } = App.useApp();
  const { isAdmin } = useAuthGuard();

  const codeWiki = useCodeWikiGraph();
  const queryClient = useQueryClient();

  const [erdSearchText, setErdSearchText] = useState('');
  const [activeTab, setActiveTab] = useState<string>('modules');
  const emptyDocumentIds = useMemo<number[]>(() => [], []);

  const [moduleMappings, setModuleMappings] = useState<ModuleMapping[]>(() => getModuleMappings());
  const [editingModule, setEditingModule] = useState<ModuleMapping | null>(null);
  const [editFieldValues, setEditFieldValues] = useState<Record<string, string>>({});

  const { data: navMappings } = useQuery({
    queryKey: ['module-mappings-nav'],
    queryFn: () => aiApi.getModuleMappings(),
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });

  const effectiveMappings = useMemo(() => {
    if (!navMappings?.success || navMappings.enabled_keys.length === 0) return moduleMappings;
    const enabledSet = new Set(navMappings.enabled_keys);
    return moduleMappings.filter((m) => enabledSet.has(m.key));
  }, [moduleMappings, navMappings]);

  const moduleGraphData = useMemo<ExternalGraphData>(() => {
    const data = buildModuleGraphData(effectiveMappings);
    return { nodes: data.nodes, edges: data.edges };
  }, [effectiveMappings]);

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
          if (codeTypes.has(type)) { codeDist[type] = count; codeEntityCount += count; }
        }
      }
      return { totalEntities: codeEntityCount, totalRelationships: graphStats.total_relationships ?? 0, typeDistribution: codeDist };
    },
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const loadStats = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['code-graph-stats'] });
  }, [queryClient]);

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

  // Admin handlers (extracted hook)
  const handlers = useCodeGraphHandlers({ codeWiki, loadStats });

  // Architecture tab data
  const layerTableData = useMemo<LayerRow[]>(() => {
    if (!moduleOverview) return [];
    return Object.entries(moduleOverview.layers).map(([layerName, layerData]) => ({
      key: layerName, layer: layerName, moduleCount: layerData.modules.length,
      totalLines: layerData.total_lines, totalFunctions: layerData.total_functions,
      modules: layerData.modules.map((m) => ({
        key: `${layerName}-${m.name}`, name: m.name, lines: m.lines,
        outgoing_deps: m.outgoing_deps, incoming_deps: m.incoming_deps,
      })),
    }));
  }, [moduleOverview]);

  const erdTableData = useMemo<DbTableRow[]>(() => {
    if (!moduleOverview) return [];
    return moduleOverview.db_tables.map((t) => ({
      key: t.name, name: t.name, columns: t.columns, has_primary_key: t.has_primary_key,
      foreign_keys: t.foreign_keys, indexes: t.indexes, unique_constraints: t.unique_constraints,
    }));
  }, [moduleOverview]);

  const filteredErdData = useMemo(() => {
    if (!erdSearchText) return erdTableData;
    const lower = erdSearchText.toLowerCase();
    return erdTableData.filter((row) => row.name.toLowerCase().includes(lower));
  }, [erdTableData, erdSearchText]);

  // Export functions
  const exportArchitectureLayers = useCallback(async () => {
    if (!moduleOverview) return;
    try {
      const XLSX = await import('xlsx');
      const layerRows = Object.entries(moduleOverview.layers).flatMap(([layer, data]) =>
        data.modules.map((m) => ({ '架構層': layer, '模組名稱': m.name, '類型': m.type, '行數': m.lines, '函數數': m.functions, '出向依賴': m.outgoing_deps, '入向依賴': m.incoming_deps })),
      );
      const ws = XLSX.utils.json_to_sheet(layerRows);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, '架構層統計');
      XLSX.writeFile(wb, `架構層統計_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}.xlsx`);
    } catch { /* noop */ }
  }, [moduleOverview]);

  const exportDbErd = useCallback(async () => {
    if (!filteredErdData.length) return;
    try {
      const XLSX = await import('xlsx');
      const rows = filteredErdData.map((t) => ({ '資料表': t.name, '欄位數': t.columns, '主鍵': t.has_primary_key ? 'Y' : 'N', '外鍵關聯': t.foreign_keys.join(', '), '索引數': t.indexes, '唯一約束': t.unique_constraints }));
      const ws = XLSX.utils.json_to_sheet(rows);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'DB ERD');
      XLSX.writeFile(wb, `DB_ERD_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}.xlsx`);
    } catch { /* noop */ }
  }, [filteredErdData]);

  // Module graph handlers
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
    setModuleMappings(getModuleMappings());
    message.success('已重置為預設映射');
  }, [message]);

  if (!isAdmin) {
    return (
      <div style={{ padding: 24 }}>
        <Alert type="warning" title="此頁面需要管理員權限" showIcon />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', gap: 0, height: 'calc(100vh - 120px)', overflow: 'hidden' }}>
      <CodeGraphSidebar
        stats={stats} statsLoading={statsLoading} loadStats={loadStats}
        codeIngestLoading={handlers.codeIngestLoading} cycleLoading={handlers.cycleLoading}
        archLoading={handlers.archLoading} jsonImportLoading={handlers.jsonImportLoading}
        ingestIncremental={handlers.ingestIncremental} setIngestIncremental={handlers.setIngestIncremental}
        ingestClean={handlers.ingestClean} setIngestClean={handlers.setIngestClean}
        jsonClean={handlers.jsonClean} setJsonClean={handlers.setJsonClean}
        handleCodeGraphIngest={handlers.handleCodeGraphIngest} handleJsonImport={handlers.handleJsonImport}
        handleCycleDetection={handlers.handleCycleDetection} handleArchAnalysis={handlers.handleArchAnalysis}
        codeWiki={codeWiki}
      />

      <div style={{ flex: 1, minWidth: 0, overflow: 'hidden', background: '#fafafa', display: 'flex', flexDirection: 'column' }}>
        <Tabs
          activeKey={activeTab} onChange={setActiveTab}
          style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
          tabBarStyle={{ paddingLeft: 16, marginBottom: 0, background: '#fff', borderBottom: '1px solid #f0f0f0' }}
          items={[
            {
              key: 'modules', label: '模組總覽',
              children: (
                <div style={{ display: 'flex', height: 'calc(100vh - 168px)', overflow: 'hidden' }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <KnowledgeGraph
                      documentIds={emptyDocumentIds}
                      height={typeof window !== 'undefined' ? window.innerHeight - 168 : 650}
                      externalGraphData={moduleGraphData}
                      onNodeClickExternal={(node) => {
                        if (node.type === 'menu_module') {
                          const mod = moduleMappings.find((m) => m.key === node.id.replace('mod_', ''));
                          if (mod) handleModuleEdit(mod);
                        }
                      }}
                    />
                  </div>
                  <ModuleConfigPanel
                    editingModule={editingModule} setEditingModule={setEditingModule}
                    moduleMappings={moduleMappings} editFieldValues={editFieldValues}
                    setEditFieldValues={setEditFieldValues} handleModuleEdit={handleModuleEdit}
                    handleModuleSave={handleModuleSave} handleModuleReset={handleModuleReset}
                  />
                </div>
              ),
            },
            {
              key: 'graph', label: '程式碼圖譜',
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
              key: 'architecture', label: '架構總覽',
              children: (
                <ArchitectureOverviewTab
                  moduleOverview={moduleOverview} moduleOverviewLoading={moduleOverviewLoading}
                  loadModuleOverview={loadModuleOverview} layerTableData={layerTableData}
                  erdSearchText={erdSearchText} setErdSearchText={setErdSearchText}
                  filteredErdData={filteredErdData} exportArchitectureLayers={exportArchitectureLayers}
                  exportDbErd={exportDbErd}
                />
              ),
            },
          ]}
        />
      </div>
    </div>
  );
};

export default CodeGraphManagementPage;
