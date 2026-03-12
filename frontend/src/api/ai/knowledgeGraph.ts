/**
 * 知識圖譜 Phase 2 API
 *
 * 正規化實體搜尋、鄰居、詳情、時間軸、入圖、合併等。
 *
 * @version 1.0.0
 * @created 2026-02-24
 */

import { apiClient } from '../client';
import { AI_ENDPOINTS } from '../endpoints';
import { logger } from '../../services/logger';
import type {
  KGEntitySearchRequest,
  KGEntitySearchResponse,
  KGNeighborsRequest,
  KGNeighborsResponse,
  KGShortestPathRequest,
  KGShortestPathResponse,
  KGEntityDetailRequest,
  KGEntityDetailResponse,
  KGTimelineRequest,
  KGTimelineResponse,
  KGTopEntitiesRequest,
  KGTopEntitiesResponse,
  KGGraphStatsResponse,
  KGIngestRequest,
  KGIngestResponse,
  KGMergeEntitiesRequest,
  KGMergeEntitiesResponse,
  GraphNode,
  GraphEdge,
} from './types';

/** 搜尋正規化實體 */
export async function searchGraphEntities(
  request: KGEntitySearchRequest,
): Promise<KGEntitySearchResponse> {
  return await apiClient.post<KGEntitySearchResponse>(
    AI_ENDPOINTS.GRAPH_ENTITY_SEARCH,
    request,
  );
}

/** 取得實體 K 跳鄰居 */
export async function getEntityNeighbors(
  request: KGNeighborsRequest,
): Promise<KGNeighborsResponse> {
  return await apiClient.post<KGNeighborsResponse>(
    AI_ENDPOINTS.GRAPH_ENTITY_NEIGHBORS,
    request,
  );
}

/** 查詢兩實體間最短路徑 */
export async function findShortestPath(
  request: KGShortestPathRequest,
): Promise<KGShortestPathResponse> {
  return await apiClient.post<KGShortestPathResponse>(
    AI_ENDPOINTS.GRAPH_SHORTEST_PATH,
    request,
  );
}

/** 取得實體詳情（別名、公文、關係） */
export async function getEntityDetail(
  request: KGEntityDetailRequest,
): Promise<KGEntityDetailResponse> {
  return await apiClient.post<KGEntityDetailResponse>(
    AI_ENDPOINTS.GRAPH_ENTITY_DETAIL,
    request,
  );
}

/** 取得實體關係時間軸 */
export async function getEntityTimeline(
  request: KGTimelineRequest,
): Promise<KGTimelineResponse> {
  return await apiClient.post<KGTimelineResponse>(
    AI_ENDPOINTS.GRAPH_ENTITY_TIMELINE,
    request,
  );
}

/** 高頻實體排名 */
export async function getTopEntities(
  request: KGTopEntitiesRequest,
): Promise<KGTopEntitiesResponse> {
  return await apiClient.post<KGTopEntitiesResponse>(
    AI_ENDPOINTS.GRAPH_ENTITY_TOP,
    request,
  );
}

/** 圖譜統計 */
export async function getGraphStats(): Promise<KGGraphStatsResponse> {
  return await apiClient.post<KGGraphStatsResponse>(
    AI_ENDPOINTS.GRAPH_STATS,
    {},
  );
}

/** 觸發入圖管線 */
export async function triggerGraphIngest(
  request: KGIngestRequest,
): Promise<KGIngestResponse> {
  return await apiClient.post<KGIngestResponse>(
    AI_ENDPOINTS.GRAPH_INGEST,
    request,
  );
}

/** 手動合併實體（管理員） */
export async function mergeGraphEntities(
  request: KGMergeEntitiesRequest,
): Promise<KGMergeEntitiesResponse> {
  try {
    return await apiClient.post<KGMergeEntitiesResponse>(
      AI_ENDPOINTS.GRAPH_MERGE_ENTITIES,
      request,
    );
  } catch (error) {
    logger.error('合併實體失敗', error);
    throw error;
  }
}

/** 取得實體中心公文知識圖譜 */
export async function getEntityGraph(
  params: { entity_types?: string[]; min_mentions?: number; limit?: number } = {},
): Promise<{ success: boolean; nodes: GraphNode[]; edges: GraphEdge[] } | null> {
  try {
    return await apiClient.post(
      AI_ENDPOINTS.GRAPH_ENTITY_GRAPH,
      params,
    );
  } catch (error) {
    logger.error('取得實體圖譜失敗:', error);
    return null;
  }
}

import type { CodeWikiRequest, CodeWikiResponse } from '../../types/ai';

/** 取得 Code Wiki 代碼圖譜 */
export async function getCodeWikiGraph(
  request: CodeWikiRequest = {},
): Promise<CodeWikiResponse> {
  return await apiClient.post<CodeWikiResponse>(
    AI_ENDPOINTS.GRAPH_CODE_WIKI,
    request,
  );
}

/** 觸發 Code Graph 入圖 (Admin) */
export interface CodeGraphIngestRequest {
  clean?: boolean;
  include_schema?: boolean;
  include_frontend?: boolean;
  incremental?: boolean;
}

export interface CodeGraphIngestResponse {
  success: boolean;
  message: string;
  modules: number;
  classes: number;
  functions: number;
  tables: number;
  ts_modules: number;
  ts_components: number;
  ts_hooks: number;
  relations: number;
  errors: number;
  skipped: number;
  elapsed_seconds: number;
}

export async function triggerCodeGraphIngest(
  request: CodeGraphIngestRequest = {},
): Promise<CodeGraphIngestResponse> {
  return await apiClient.post<CodeGraphIngestResponse>(
    AI_ENDPOINTS.GRAPH_CODE_INGEST,
    request,
  );
}

/** 循環依賴偵測結果 */
export interface CycleDetectionResponse {
  success: boolean;
  total_modules: number;
  total_import_edges: number;
  cycles_found: number;
  cycles: string[][];
}

/** 偵測模組循環匯入依賴 (Admin) */
export async function detectImportCycles(): Promise<CycleDetectionResponse> {
  return await apiClient.post<CycleDetectionResponse>(
    AI_ENDPOINTS.GRAPH_CYCLE_DETECTION,
    {},
  );
}

/** 架構分析結果 */
export interface ArchitectureAnalysisResponse {
  success: boolean;
  complexity_hotspots: Array<{ module: string; outgoing_deps: number }>;
  hub_modules: Array<{ module: string; imported_by: number }>;
  large_modules: Array<{ module: string; lines: number; type: string }>;
  orphan_modules: string[];
  god_classes: Array<{ class: string; method_count: number }>;
  summary: Record<string, number>;
}

/** 分析代碼架構 */
export async function analyzeArchitecture(): Promise<ArchitectureAnalysisResponse> {
  return await apiClient.post<ArchitectureAnalysisResponse>(
    AI_ENDPOINTS.GRAPH_ARCHITECTURE_ANALYSIS,
    {},
  );
}

/** JSON 圖譜匯入請求 */
export interface JsonImportRequest {
  file_path?: string;
  clean?: boolean;
}

/** JSON 圖譜匯入回應 */
export interface JsonImportResponse {
  success: boolean;
  message: string;
  nodes_imported: number;
  edges_imported: number;
  elapsed_seconds: number;
}

/** 模組架構概覽 — 按架構層分組 + DB ERD 摘要 */
export interface ModuleOverviewResponse {
  layers: Record<string, {
    modules: Array<{
      name: string;
      type: string;
      lines: number;
      functions: number;
      outgoing_deps: number;
      incoming_deps: number;
    }>;
    total_lines: number;
    total_functions: number;
  }>;
  db_tables: Array<{
    name: string;
    columns: number;
    foreign_keys: string[];
    indexes: number;
    has_primary_key: boolean;
    unique_constraints: number;
  }>;
  summary: {
    total_modules: number;
    total_tables: number;
    total_relations: number;
  };
}

export async function getModuleOverview(): Promise<ModuleOverviewResponse> {
  return await apiClient.post<ModuleOverviewResponse>(
    AI_ENDPOINTS.GRAPH_MODULE_OVERVIEW,
    {},
  );
}

/** DB Schema 圖譜回應 */
export interface DbSchemaGraphResponse {
  success: boolean;
  nodes: GraphNode[];
  edges: GraphEdge[];
  error?: string;
}

/** 取得資料庫 ER 圖譜（nodes + edges 格式） */
export async function getDbSchemaGraph(): Promise<DbSchemaGraphResponse> {
  return await apiClient.post<DbSchemaGraphResponse>(
    AI_ENDPOINTS.GRAPH_DB_GRAPH,
    {},
  );
}

/** DB Schema 完整反射回應（含欄位、索引、約束） */
export interface DbColumnInfo {
  name: string;
  type: string;
  nullable: boolean;
  primary_key: boolean;
}

export interface DbForeignKey {
  constrained_columns: string[];
  referred_table: string;
  referred_columns: string[];
}

export interface DbIndex {
  name: string;
  columns: string[];
  unique: boolean;
}

export interface DbTableInfo {
  name: string;
  columns: DbColumnInfo[];
  primary_key_columns: string[];
  foreign_keys: DbForeignKey[];
  indexes: DbIndex[];
  unique_constraints: DbIndex[];
}

export interface DbSchemaResponse {
  success: boolean;
  tables: DbTableInfo[];
  error?: string;
}

/** 取得完整資料庫 Schema（含欄位詳情） */
export async function getDbSchema(): Promise<DbSchemaResponse> {
  return await apiClient.post<DbSchemaResponse>(
    AI_ENDPOINTS.GRAPH_DB_SCHEMA,
    {},
  );
}

/** 動態模組映射回應 */
export interface ModuleMappingsResponse {
  success: boolean;
  enabled_keys: string[];
  disabled_keys: string[];
  total: number;
}

/** 取得動態模組映射（基於 site_navigation_items） */
export async function getModuleMappings(): Promise<ModuleMappingsResponse> {
  return await apiClient.post<ModuleMappingsResponse>(
    AI_ENDPOINTS.GRAPH_MODULE_MAPPINGS,
    {},
  );
}

/** 匯入本地 GitNexus 產生的 knowledge_graph.json (Admin) */
export async function importJsonGraph(
  request: JsonImportRequest = {},
): Promise<JsonImportResponse> {
  return await apiClient.post<JsonImportResponse>(
    AI_ENDPOINTS.GRAPH_JSON_IMPORT,
    request,
  );
}
