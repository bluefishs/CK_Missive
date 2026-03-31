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
  KGFederationHealthResponse,
  UnifiedGraphSearchRequest,
  UnifiedGraphSearchResponse,
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

/** 跨專案路徑查詢 — 回傳含 source_project 標記的路徑 */
export async function findCrossDomainPath(
  request: KGShortestPathRequest,
): Promise<KGShortestPathResponse> {
  return await apiClient.post<KGShortestPathResponse>(
    AI_ENDPOINTS.GRAPH_CROSS_DOMAIN_PATH,
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

/** 時序聚合：按月/季/年統計關係趨勢 */
export async function getTimelineAggregate(
  request: { relation_type?: string; entity_type?: string; granularity?: string },
): Promise<{
  success: boolean;
  granularity: string;
  buckets: { period: string; count: number; total_weight: number; entity_count: number }[];
  total_relationships: number;
}> {
  return await apiClient.post(
    AI_ENDPOINTS.GRAPH_TIMELINE_AGGREGATE,
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

/** 聯邦健康指標 */
export async function getFederationHealth(): Promise<KGFederationHealthResponse> {
  return await apiClient.post<KGFederationHealthResponse>(
    AI_ENDPOINTS.GRAPH_FEDERATION_HEALTH,
    {},
  );
}

/** 跨圖譜統一搜尋 (KG + Code + DB) */
export async function unifiedGraphSearch(
  request: UnifiedGraphSearchRequest,
): Promise<UnifiedGraphSearchResponse> {
  return await apiClient.post<UnifiedGraphSearchResponse>(
    AI_ENDPOINTS.GRAPH_UNIFIED_SEARCH,
    request,
  );
}

/** 跨域橋接觸發 (Admin) — 執行 4 條 CrossDomainLinker 規則 */
export async function triggerCrossDomainLink(): Promise<{
  success: boolean;
  links_created: number;
  links_skipped: number;
  rules_applied: string[];
}> {
  return await apiClient.post(
    AI_ENDPOINTS.GRAPH_CROSS_DOMAIN_LINK,
    {},
  );
}

/** Embedding 批次回填 (Admin) — 回填缺少向量的實體 */
export async function triggerEmbeddingBackfill(
  batchSize = 100,
): Promise<{ success: boolean; processed?: number; skipped?: number; error?: string }> {
  return await apiClient.post(
    AI_ENDPOINTS.GRAPH_EMBEDDING_BACKFILL,
    {},
    { params: { batch_size: batchSize } },
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
  params: { entity_types?: string[]; min_mentions?: number; limit?: number; year?: number; collapse_agency?: boolean } = {},
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

import type {
  CodeWikiRequest,
  CodeWikiResponse,
  CodeGraphIngestRequest,
  CodeGraphIngestResponse,
  CycleDetectionResponse,
  ArchitectureAnalysisResponse,
  JsonImportRequest,
  JsonImportResponse,
  ModuleOverviewResponse,
  DbSchemaGraphResponse,
  DbColumnInfo,
  DbForeignKey,
  DbIndex,
  DbTableInfo,
  DbSchemaResponse,
  ModuleMappingsResponse,
} from '../../types/ai';

// Re-export types for backward compatibility
export type {
  CodeGraphIngestRequest,
  CodeGraphIngestResponse,
  CycleDetectionResponse,
  ArchitectureAnalysisResponse,
  JsonImportRequest,
  JsonImportResponse,
  ModuleOverviewResponse,
  DbSchemaGraphResponse,
  DbColumnInfo,
  DbForeignKey,
  DbIndex,
  DbTableInfo,
  DbSchemaResponse,
  ModuleMappingsResponse,
};

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
export async function triggerCodeGraphIngest(
  request: CodeGraphIngestRequest = {},
): Promise<CodeGraphIngestResponse> {
  return await apiClient.post<CodeGraphIngestResponse>(
    AI_ENDPOINTS.GRAPH_CODE_INGEST,
    request,
  );
}

/** 偵測模組循環匯入依賴 (Admin) */
export async function detectImportCycles(): Promise<CycleDetectionResponse> {
  return await apiClient.post<CycleDetectionResponse>(
    AI_ENDPOINTS.GRAPH_CYCLE_DETECTION,
    {},
  );
}

/** 分析代碼架構 */
export async function analyzeArchitecture(): Promise<ArchitectureAnalysisResponse> {
  return await apiClient.post<ArchitectureAnalysisResponse>(
    AI_ENDPOINTS.GRAPH_ARCHITECTURE_ANALYSIS,
    {},
  );
}

export async function getModuleOverview(): Promise<ModuleOverviewResponse> {
  return await apiClient.post<ModuleOverviewResponse>(
    AI_ENDPOINTS.GRAPH_MODULE_OVERVIEW,
    {},
  );
}

/** 取得資料庫 ER 圖譜（nodes + edges 格式） */
export async function getDbSchemaGraph(): Promise<DbSchemaGraphResponse> {
  return await apiClient.post<DbSchemaGraphResponse>(
    AI_ENDPOINTS.GRAPH_DB_GRAPH,
    {},
  );
}

/** 取得完整資料庫 Schema（含欄位詳情） */
export async function getDbSchema(): Promise<DbSchemaResponse> {
  return await apiClient.post<DbSchemaResponse>(
    AI_ENDPOINTS.GRAPH_DB_SCHEMA,
    {},
  );
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

/** Diff 影響分析 (Admin) */
export async function analyzeDiffImpact(): Promise<{
  success: boolean;
  data: {
    changed_files: string[];
    affected_entities: number;
    affected_by_type: Record<string, number>;
    downstream_dependents: number;
    downstream: Array<{
      entity: string;
      type: string;
      relation: string;
      depends_on: string;
    }>;
    summary: string;
    error?: string;
  };
}> {
  return await apiClient.post(AI_ENDPOINTS.GRAPH_DIFF_IMPACT, {});
}

/** 取得 Skills 能力圖譜（靜態資料） */
export async function getSkillsMap(): Promise<{
  success: boolean;
  nodes: GraphNode[];
  edges: GraphEdge[];
} | null> {
  try {
    return await apiClient.post(
      AI_ENDPOINTS.GRAPH_SKILLS_MAP,
      {},
    );
  } catch (error) {
    logger.error('取得 Skills 能力圖譜失敗:', error);
    return null;
  }
}
