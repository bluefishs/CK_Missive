/**
 * AI 知識圖譜型別 (SSOT)
 *
 * 圖譜節點/邊、語意相似、實體提取、KG Phase 2、統一圖譜搜尋、
 * Code Graph、DB Schema
 *
 * @domain knowledge-graph
 * @version 1.0.0
 * @date 2026-03-29
 */

// ============================================================================
// 知識圖譜 — 基礎結構
// ============================================================================

export interface GraphNode {
  id: string;
  type: 'document' | 'project' | 'dispatch' | 'agency' | string;
  label: string;
  fullLabel?: string | null;
  category?: string | null;
  doc_number?: string | null;
  status?: string | null;
  mention_count?: number | null;
  dispatch_nos?: string[] | null;
  source_project?: string | null;
}

export interface GraphEdge {
  source: string;
  target: string;
  label: string;
  type: string;
  weight?: number | null;
}

export interface RelationGraphRequest {
  document_ids: number[];
}

export interface RelationGraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ============================================================================
// 語意相似推薦
// ============================================================================

export interface SemanticSimilarRequest {
  document_id: number;
  limit?: number;
}

export interface SemanticSimilarItem {
  id: number;
  doc_number?: string | null;
  subject?: string | null;
  category?: string | null;
  sender?: string | null;
  doc_date?: string | null;
  similarity: number;
}

export interface SemanticSimilarResponse {
  source_id: number;
  similar_documents: SemanticSimilarItem[];
}

// ============================================================================
// 實體提取 (Entity Extraction)
// ============================================================================

export interface EntityExtractRequest {
  document_id: number;
  force?: boolean;
}

export interface EntityExtractResponse {
  success: boolean;
  document_id: number;
  entities_count: number;
  relations_count: number;
  skipped: boolean;
  reason?: string | null;
  error?: string | null;
}

export interface EntityBatchRequest {
  limit?: number;
  force?: boolean;
}

export interface EntityBatchResponse {
  success: boolean;
  message: string;
  total_processed: number;
  success_count: number;
  skip_count: number;
  error_count: number;
}

export interface EntityStatsResponse {
  total_documents: number;
  extracted_documents: number;
  without_extraction: number;
  coverage_percent: number;
  total_entities: number;
  total_relations: number;
  entity_type_stats: Record<string, number>;
}

// ============================================================================
// 知識圖譜 Phase 2: 正規化實體查詢
// ============================================================================

export interface KGEntitySearchRequest {
  query: string;
  entity_type?: string | null;
  limit?: number;
}

export interface KGEntityItem {
  id: number;
  canonical_name: string;
  entity_type: string;
  mention_count: number;
  alias_count: number;
  description?: string | null;
  first_seen_at?: string | null;
  last_seen_at?: string | null;
}

export interface KGEntitySearchResponse {
  success: boolean;
  results: KGEntityItem[];
  total: number;
}

export interface KGNeighborsRequest {
  entity_id: number;
  max_hops?: number;
  limit?: number;
}

export interface KGGraphNode {
  id: number;
  name: string;
  type: string;
  mention_count: number;
  hop: number;
}

export interface KGGraphEdge {
  source_id: number;
  target_id: number;
  relation_type: string;
  relation_label?: string | null;
  weight: number;
}

export interface KGNeighborsResponse {
  success: boolean;
  nodes: KGGraphNode[];
  edges: KGGraphEdge[];
}

export interface KGShortestPathRequest {
  source_id: number;
  target_id: number;
  max_hops?: number;
}

export interface KGPathNode {
  id: number;
  name: string;
  type: string;
  source_project?: string;
}

export interface KGShortestPathResponse {
  success: boolean;
  found: boolean;
  depth: number;
  path: KGPathNode[];
  relations: string[];
  source_projects_traversed?: string[];
  is_cross_project?: boolean;
}

export interface KGEntityDetailRequest {
  entity_id: number;
}

export interface KGEntityDocument {
  document_id: number;
  mention_text: string;
  confidence: number;
  subject?: string | null;
  doc_number?: string | null;
  doc_date?: string | null;
}

export interface KGEntityRelationship {
  id: number;
  direction: 'outgoing' | 'incoming';
  relation_type: string;
  relation_label?: string | null;
  target_name?: string;
  target_type?: string;
  target_id?: number;
  source_name?: string;
  source_type?: string;
  source_id?: number;
  weight: number;
  valid_from?: string | null;
  valid_to?: string | null;
  document_count: number;
}

export interface KGEntityDetailResponse {
  success: boolean;
  id: number;
  canonical_name: string;
  entity_type: string;
  description?: string | null;
  alias_count: number;
  mention_count: number;
  first_seen_at?: string | null;
  last_seen_at?: string | null;
  aliases: string[];
  documents: KGEntityDocument[];
  relationships: KGEntityRelationship[];
}

export interface KGTimelineRequest {
  entity_id: number;
}

export interface KGTimelineItem {
  id: number;
  direction: 'outgoing' | 'incoming';
  relation_type: string;
  relation_label?: string | null;
  other_name: string;
  other_type: string;
  weight: number;
  valid_from?: string | null;
  valid_to?: string | null;
  invalidated_at?: string | null;
  document_count: number;
}

export interface KGTimelineResponse {
  success: boolean;
  entity_id: number;
  timeline: KGTimelineItem[];
}

export interface KGTopEntitiesRequest {
  entity_type?: string | null;
  sort_by?: 'mention_count' | 'alias_count';
  limit?: number;
}

export interface KGTopEntitiesResponse {
  success: boolean;
  entities: KGEntityItem[];
}

export interface KGGraphStatsResponse {
  success: boolean;
  total_entities: number;
  total_aliases: number;
  total_mentions: number;
  total_relationships: number;
  total_ingestion_events: number;
  entity_type_distribution: Record<string, number>;
  source_project_distribution?: Record<string, number>;
  entities_with_embedding?: number;
  embedding_coverage_percent?: number;
  entities_without_embedding?: number;
  embedding_backfill_needed?: boolean;
}

export interface KGFederationProjectHealth {
  source_project: string;
  entity_count: number;
  last_updated: string | null;
}

export interface KGFederationEmbeddingCoverage {
  total: number;
  with_embedding: number;
  coverage_pct: number;
}

export interface KGFederationHealthResponse {
  success: boolean;
  projects: KGFederationProjectHealth[];
  cross_project_relations: number;
  total_projects: number;
  embedding_coverage?: Record<string, KGFederationEmbeddingCoverage>;
}

export interface KGIngestRequest {
  document_id?: number | null;
  limit?: number;
  force?: boolean;
}

export interface KGIngestResponse {
  success: boolean;
  status: string;
  document_id?: number;
  entities_found?: number;
  entities_new?: number;
  entities_merged?: number;
  relations_found?: number;
  processing_ms?: number;
  total_processed?: number;
  success_count?: number;
  skip_count?: number;
  error_count?: number;
  message?: string;
}

export interface KGMergeEntitiesRequest {
  keep_id: number;
  merge_id: number;
}

export interface KGMergeEntitiesResponse {
  success: boolean;
  message: string;
  entity_id: number;
}

// ============================================================================
// 跨圖譜統一搜尋
// ============================================================================

export interface UnifiedGraphSearchRequest {
  query: string;
  include_kg?: boolean;
  include_code?: boolean;
  include_db?: boolean;
  limit_per_graph?: number;
}

export interface UnifiedGraphResult {
  source: string;
  entity_type: string;
  name: string;
  description: string;
  relevance: number;
}

export interface UnifiedGraphSearchResponse {
  success: boolean;
  results: UnifiedGraphResult[];
  total: number;
  sources_queried: string[];
}

// ============================================================================
// Code Wiki 代碼圖譜
// ============================================================================

export interface CodeWikiRequest {
  entity_types?: string[];
  module_prefix?: string | null;
  limit?: number;
}

export interface CodeWikiResponse {
  success: boolean;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ============================================================================
// Code Graph API
// ============================================================================

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

export interface CycleDetectionResponse {
  success: boolean;
  total_modules: number;
  total_import_edges: number;
  cycles_found: number;
  cycles: string[][];
}

export interface ArchitectureAnalysisResponse {
  success: boolean;
  complexity_hotspots: Array<{ module: string; outgoing_deps: number }>;
  hub_modules: Array<{ module: string; imported_by: number }>;
  large_modules: Array<{ module: string; lines: number; type: string }>;
  orphan_modules: string[];
  god_classes: Array<{ class: string; method_count: number }>;
  summary: Record<string, number>;
}

export interface JsonImportRequest {
  file_path?: string;
  clean?: boolean;
}

export interface JsonImportResponse {
  success: boolean;
  message: string;
  nodes_imported: number;
  edges_imported: number;
  elapsed_seconds: number;
}

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

export interface DbSchemaGraphResponse {
  success: boolean;
  nodes: GraphNode[];
  edges: GraphEdge[];
  error?: string;
}

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

export interface ModuleMappingsResponse {
  success: boolean;
  enabled_keys: string[];
  disabled_keys: string[];
  total: number;
}
