/**
 * 模組圖譜配置 — 選單模組到程式碼的映射
 *
 * 定義每個功能模組（對應網站選單）關聯的：
 * - 前端頁面 (pages)
 * - API 端點群組 (apiGroups)
 * - 後端服務 (backendServices)
 * - 資料庫表 (dbTables)
 *
 * 管理員可透過前端設定面板修改此映射（覆蓋存入 localStorage）。
 *
 * @version 1.0.0
 * @created 2026-03-11
 */

export interface ModuleMapping {
  /** 模組唯一 key (對應 navigation key) */
  key: string;
  /** 中文顯示名稱 */
  title: string;
  /** 模組圖示 (Ant Design icon name) */
  icon: string;
  /** 模組分類顏色 */
  color: string;
  /** 關聯的前端頁面 */
  pages: string[];
  /** 關聯的 API 端點群組名 */
  apiGroups: string[];
  /** 關聯的後端服務類名 */
  backendServices: string[];
  /** 關聯的資料庫表名 */
  dbTables: string[];
}

/** 預設模組映射（可由管理員覆蓋） */
export const DEFAULT_MODULE_MAPPINGS: ModuleMapping[] = [
  {
    key: 'dashboard',
    title: '儀表板',
    icon: 'DashboardOutlined',
    color: '#1890ff',
    pages: ['DashboardPage'],
    apiGroups: ['DASHBOARD'],
    backendServices: ['DashboardService'],
    dbTables: ['documents', 'contract_projects', 'calendar_events'],
  },
  {
    key: 'documents',
    title: '公文管理',
    icon: 'FileTextOutlined',
    color: '#1976d2',
    pages: ['DocumentPage', 'DocumentDetailPage', 'DocumentEditPage', 'DocumentNumbersPage'],
    apiGroups: ['DOCUMENTS', 'DOCUMENT_NUMBERS'],
    backendServices: ['DocumentService', 'DocumentImportService', 'DocumentStatisticsService'],
    dbTables: ['documents', 'attachments', 'doc_number_sequences'],
  },
  {
    key: 'contract-cases',
    title: '承攬案件',
    icon: 'ProjectOutlined',
    color: '#52c41a',
    pages: ['ContractCasePage', 'ContractCaseDetailPage', 'ContractCaseFormPage'],
    apiGroups: ['PROJECTS', 'PROJECT_STAFF', 'PROJECT_VENDORS'],
    backendServices: ['ProjectService'],
    dbTables: ['contract_projects', 'project_vendor_association', 'project_user_association'],
  },
  {
    key: 'agencies',
    title: '機關管理',
    icon: 'BankOutlined',
    color: '#13c2c2',
    pages: ['AgenciesPage'],
    apiGroups: ['AGENCIES'],
    backendServices: ['AgencyService', 'AgencyMatchingService'],
    dbTables: ['government_agencies', 'agency_contacts'],
  },
  {
    key: 'vendors',
    title: '廠商管理',
    icon: 'ShopOutlined',
    color: '#eb2f96',
    pages: ['VendorPage'],
    apiGroups: ['VENDORS'],
    backendServices: ['VendorService'],
    dbTables: ['partner_vendors', 'project_vendor_association'],
  },
  {
    key: 'staff',
    title: '人員管理',
    icon: 'TeamOutlined',
    color: '#722ed1',
    pages: ['StaffPage', 'StaffDetailPage', 'StaffCreatePage'],
    apiGroups: ['PROJECT_STAFF', 'CERTIFICATIONS'],
    backendServices: [],
    dbTables: ['project_user_association', 'certifications'],
  },
  {
    key: 'calendar',
    title: '行事曆',
    icon: 'CalendarOutlined',
    color: '#fa8c16',
    pages: ['CalendarPage'],
    apiGroups: ['CALENDAR'],
    backendServices: ['DocumentCalendarService', 'EventAutoBuilder'],
    dbTables: ['calendar_events', 'calendar_reminders', 'calendar_sync_logs'],
  },
  {
    key: 'taoyuan-dispatch',
    title: '桃園派工',
    icon: 'EnvironmentOutlined',
    color: '#f5222d',
    pages: ['TaoyuanDispatchPage', 'TaoyuanDispatchCreatePage', 'TaoyuanDispatchDetailPage', 'TaoyuanProjectDetailPage', 'WorkRecordFormPage'],
    apiGroups: ['TAOYUAN_DISPATCH'],
    backendServices: ['DispatchOrderService', 'DispatchImportService', 'PaymentService', 'WorkRecordService'],
    dbTables: ['taoyuan_projects', 'taoyuan_dispatch_orders', 'taoyuan_work_records', 'taoyuan_payments'],
  },
  {
    key: 'reports',
    title: '統計報表',
    icon: 'BarChartOutlined',
    color: '#faad14',
    pages: ['ReportsPage'],
    apiGroups: ['DASHBOARD'],
    backendServices: ['DocumentStatisticsService'],
    dbTables: ['documents', 'contract_projects', 'taoyuan_dispatch_orders'],
  },
  {
    key: 'ai-features',
    title: 'AI 智慧功能',
    icon: 'ExperimentOutlined',
    color: '#2f54eb',
    pages: ['KnowledgeGraphPage', 'CodeGraphManagementPage', 'DatabaseGraphPage', 'AISynonymManagementPage', 'AIAssistantManagementPage'],
    apiGroups: ['AI'],
    backendServices: ['DocumentAIService', 'RAGQueryService', 'AgentOrchestrator', 'GraphQueryService', 'EmbeddingManager', 'SynonymExpander'],
    dbTables: ['canonical_entities', 'entity_aliases', 'entity_mentions', 'entity_relations', 'prompt_templates', 'search_history'],
  },
  {
    key: 'system-management',
    title: '系統管理',
    icon: 'SettingOutlined',
    color: '#595959',
    pages: ['AdminDashboardPage', 'UserManagementPage', 'PermissionManagementPage', 'DatabaseManagementPage', 'SiteManagementPage', 'BackupManagementPage', 'DeploymentManagementPage'],
    apiGroups: ['ADMIN', 'ADMIN_USER_MANAGEMENT', 'ADMIN_DATABASE', 'SITE_MANAGEMENT', 'BACKUP', 'DEPLOYMENT'],
    backendServices: ['AdminService', 'SystemHealthService', 'BackupService'],
    dbTables: ['users', 'user_sessions', 'site_configurations', 'site_navigation_items', 'system_notifications'],
  },
];

const STORAGE_KEY = 'ck_module_graph_config';

/** 檢查單一項目是否符合 ModuleMapping 結構 */
function isValidModuleMapping(item: unknown): item is ModuleMapping {
  if (typeof item !== 'object' || item === null) return false;
  const obj = item as Record<string, unknown>;
  return (
    typeof obj.key === 'string' &&
    typeof obj.title === 'string' &&
    typeof obj.color === 'string' &&
    Array.isArray(obj.pages) &&
    Array.isArray(obj.apiGroups) &&
    Array.isArray(obj.backendServices) &&
    Array.isArray(obj.dbTables)
  );
}

/** 讀取模組映射（優先使用 localStorage 覆蓋，含 schema 驗證） */
export function getModuleMappings(): ModuleMapping[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed: unknown = JSON.parse(stored);
      if (Array.isArray(parsed) && parsed.length > 0 && parsed.every(isValidModuleMapping)) {
        return parsed;
      }
      // 資料格式無效，清除損壞的 localStorage 資料
      localStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    // JSON 解析失敗，清除損壞資料
    localStorage.removeItem(STORAGE_KEY);
  }
  return DEFAULT_MODULE_MAPPINGS;
}

/** 儲存模組映射覆蓋 */
export function saveModuleMappings(mappings: ModuleMapping[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(mappings));
}

/** 重置為預設映射 */
export function resetModuleMappings(): void {
  localStorage.removeItem(STORAGE_KEY);
}

/** 將模組映射轉為圖譜 nodes + edges (符合 GraphNode/GraphEdge 介面) */
export function buildModuleGraphData(mappings: ModuleMapping[]): {
  nodes: Array<{ id: string; label: string; type: string; category?: string }>;
  edges: Array<{ source: string; target: string; label: string; type: string }>;
} {
  const nodes: Array<{ id: string; label: string; type: string; category?: string }> = [];
  const edges: Array<{ source: string; target: string; label: string; type: string }> = [];
  const addedNodes = new Set<string>();

  const addNode = (id: string, label: string, type: string, category?: string) => {
    if (!addedNodes.has(id)) {
      addedNodes.add(id);
      nodes.push({ id, label, type, category });
    }
  };

  for (const mod of mappings) {
    // Module node (center)
    const modId = `mod_${mod.key}`;
    addNode(modId, mod.title, 'menu_module', mod.key);

    // Page nodes
    for (const page of mod.pages) {
      const pageId = `page_${page}`;
      addNode(pageId, page, 'ts_component', 'page');
      edges.push({ source: modId, target: pageId, label: '前端頁面', type: 'has_page' });
    }

    // API group nodes
    for (const api of mod.apiGroups) {
      const apiId = `api_${api}`;
      addNode(apiId, api, 'api_group', 'api');
      edges.push({ source: modId, target: apiId, label: 'API 端點', type: 'has_api' });
    }

    // Backend service nodes
    for (const svc of mod.backendServices) {
      const svcId = `svc_${svc}`;
      addNode(svcId, svc, 'py_class', 'service');
      edges.push({ source: modId, target: svcId, label: '後端服務', type: 'has_service' });
    }

    // DB table nodes
    for (const tbl of mod.dbTables) {
      const tblId = `tbl_${tbl}`;
      addNode(tblId, tbl, 'db_table', 'table');
      edges.push({ source: modId, target: tblId, label: '資料表', type: 'has_table' });
    }

    // Cross-layer edges: pages → API groups
    for (const page of mod.pages) {
      for (const api of mod.apiGroups) {
        edges.push({ source: `page_${page}`, target: `api_${api}`, label: '呼叫', type: 'calls' });
      }
    }

    // Cross-layer edges: API groups → services
    for (const api of mod.apiGroups) {
      for (const svc of mod.backendServices) {
        edges.push({ source: `api_${api}`, target: `svc_${svc}`, label: '委派', type: 'delegates' });
      }
    }

    // Cross-layer edges: services → tables
    for (const svc of mod.backendServices) {
      for (const tbl of mod.dbTables) {
        edges.push({ source: `svc_${svc}`, target: `tbl_${tbl}`, label: '存取', type: 'accesses' });
      }
    }
  }

  return { nodes, edges };
}
