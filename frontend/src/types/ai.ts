/**
 * AI 服務型別定義 (SSOT - Single Source of Truth)
 *
 * 所有 AI API 的 Request/Response/Entity 型別統一定義於此。
 * API 層 (api/aiApi.ts) 僅 re-export，不自行定義型別。
 *
 * @version 1.0.0
 * @ssot-location /frontend/src/types/ai.ts
 * @created 2026-02-24
 * @migrated-from api/ai/types.ts
 */

import type { AIStatsResponse } from './api';

// Re-export for convenience
export type { AIStatsResponse };

// ============================================================================
// 摘要生成
// ============================================================================

export interface SummaryRequest {
  subject: string;
  content?: string;
  sender?: string;
  max_length?: number;
}

export interface SummaryResponse {
  summary: string;
  confidence: number;
  source: 'ai' | 'fallback' | 'disabled' | 'rate_limited';
  error?: string;
}

// ============================================================================
// 分類建議
// ============================================================================

export interface ClassifyRequest {
  subject: string;
  content?: string;
  sender?: string;
}

export interface ClassifyResponse {
  doc_type: string;
  category: '收文' | '發文';
  doc_type_confidence: number;
  category_confidence: number;
  reasoning?: string;
  source: 'ai' | 'fallback' | 'disabled' | 'rate_limited';
  error?: string;
}

// ============================================================================
// 關鍵字提取
// ============================================================================

export interface KeywordsRequest {
  subject: string;
  content?: string;
  max_keywords?: number;
}

export interface KeywordsResponse {
  keywords: string[];
  confidence: number;
  source: 'ai' | 'fallback' | 'disabled' | 'rate_limited';
  error?: string;
}

// ============================================================================
// 機關匹配
// ============================================================================

export interface AgencyCandidate {
  id: number;
  name: string;
  short_name?: string;
}

export interface AgencyMatchRequest {
  agency_name: string;
  candidates?: AgencyCandidate[];
}

export interface AgencyMatchResult {
  id: number;
  name: string;
  score: number;
}

export interface AgencyMatchResponse {
  best_match: AgencyMatchResult | null;
  alternatives: AgencyMatchResult[];
  is_new: boolean;
  reasoning?: string;
  source: 'ai' | 'fallback' | 'disabled';
  error?: string;
}

// ============================================================================
// 健康檢查與配置
// ============================================================================

export interface AIHealthStatus {
  groq: {
    available: boolean;
    message: string;
  };
  ollama: {
    available: boolean;
    message: string;
  };
  rate_limit?: {
    can_proceed: boolean;
    current_requests: number;
    max_requests: number;
    window_seconds: number;
  };
}

export interface AIConfigResponse {
  enabled: boolean;
  providers: {
    groq: {
      name: string;
      description: string;
      priority: number;
      model: string;
      available: boolean;
    };
    ollama: {
      name: string;
      description: string;
      priority: number;
      model: string;
      url: string;
    };
  };
  rate_limit: {
    max_requests: number;
    window_seconds: number;
  };
  cache: {
    enabled: boolean;
    ttl_summary: number;
    ttl_classify: number;
    ttl_keywords: number;
  };
  features: {
    summary: { max_tokens: number; default_max_length: number };
    classify: { max_tokens: number; confidence_threshold: number };
    keywords: { max_tokens: number; default_max_keywords: number };
    agency_match: { score_threshold: number; max_alternatives: number };
  };
}

// ============================================================================
// 自然語言搜尋
// ============================================================================

export interface ParsedSearchIntent {
  keywords?: string[] | null;
  doc_type?: string | null;
  category?: string | null;
  sender?: string | null;
  receiver?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  status?: string | null;
  has_deadline?: boolean | null;
  contract_case?: string | null;
  related_entity?: 'dispatch_order' | 'project' | null;
  confidence: number;
}

export interface ParseIntentRequest {
  query: string;
}

export interface ParseIntentResponse {
  success: boolean;
  query: string;
  parsed_intent: ParsedSearchIntent;
  source: 'ai' | 'error';
  error?: string | null;
}

export interface NaturalSearchRequest {
  query: string;
  max_results?: number;
  include_attachments?: boolean;
  offset?: number;
}

export interface AttachmentInfo {
  id: number;
  file_name: string;
  original_name?: string | null;
  file_size?: number | null;
  mime_type?: string | null;
  created_at?: string | null;
}

export interface DocumentSearchResult {
  id: number;
  auto_serial?: string | null;
  doc_number: string;
  subject: string;
  doc_type?: string | null;
  category?: string | null;
  sender?: string | null;
  receiver?: string | null;
  doc_date?: string | null;
  status?: string | null;
  contract_project_name?: string | null;
  ck_note?: string | null;
  attachment_count: number;
  attachments: AttachmentInfo[];
  created_at?: string | null;
  updated_at?: string | null;
}

/** 搜尋結果中匹配到的正規化實體（橋接圖譜） */
export interface MatchedEntity {
  entity_id: number;
  canonical_name: string;
  entity_type: string;
  mention_count: number;
  match_source: 'sender' | 'receiver' | 'keyword';
}

export interface NaturalSearchResponse {
  success: boolean;
  query: string;
  parsed_intent: ParsedSearchIntent;
  results: DocumentSearchResult[];
  total: number;
  source: 'ai' | 'rule_engine' | 'merged' | 'vector' | 'fallback' | 'rate_limited' | 'error';
  search_strategy?: 'keyword' | 'similarity' | 'hybrid' | 'semantic' | null;
  synonym_expanded?: boolean;
  entity_expanded?: boolean;
  expanded_keywords?: string[] | null;
  history_id?: number | null;
  matched_entities?: MatchedEntity[];
  error?: string | null;
}

/** 搜尋回饋請求 */
export interface SearchFeedbackRequest {
  history_id: number;
  score: 1 | -1;
}

/** 搜尋回饋回應 */
export interface SearchFeedbackResponse {
  success: boolean;
  message: string;
}

// ============================================================================
// 搜尋建議
// ============================================================================

export interface QuerySuggestionRequest {
  prefix: string;
  limit?: number;
}

export interface QuerySuggestionItem {
  query: string;
  type: 'popular' | 'history' | 'related';
  count: number;
  avg_results: number;
}

export interface QuerySuggestionResponse {
  suggestions: QuerySuggestionItem[];
}

// ============================================================================
// 知識圖譜
// ============================================================================

export interface GraphNode {
  id: string;
  type: 'document' | 'project' | 'dispatch' | 'agency' | string;
  label: string;
  category?: string | null;
  doc_number?: string | null;
  status?: string | null;
  mention_count?: number | null;
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
// Embedding 管線
// ============================================================================

export interface EmbeddingStatsResponse {
  total_documents: number;
  with_embedding: number;
  without_embedding: number;
  coverage_percent: number;
  pgvector_enabled: boolean;
}

export interface EmbeddingBatchRequest {
  limit?: number;
  batch_size?: number;
}

export interface EmbeddingBatchResponse {
  success: boolean;
  message: string;
  success_count: number;
  error_count: number;
  skip_count: number;
  elapsed_seconds: number;
}

// ============================================================================
// 同義詞管理
// ============================================================================

export interface AISynonymItem {
  id: number;
  category: string;
  words: string;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AISynonymListRequest {
  category?: string | null;
  is_active?: boolean | null;
}

export interface AISynonymListResponse {
  items: AISynonymItem[];
  total: number;
  categories: string[];
}

export interface AISynonymCreateRequest {
  category: string;
  words: string;
  is_active?: boolean;
}

export interface AISynonymUpdateRequest {
  id: number;
  category?: string;
  words?: string;
  is_active?: boolean;
}

export interface AISynonymDeleteRequest {
  id: number;
}

export interface AISynonymReloadResponse {
  success: boolean;
  total_groups: number;
  total_words: number;
  message: string;
}

// ============================================================================
// Prompt 版本管理
// ============================================================================

export interface PromptVersionItem {
  id: number;
  feature: string;
  version: number;
  system_prompt: string;
  user_template?: string | null;
  is_active: boolean;
  description?: string | null;
  created_by?: string | null;
  created_at?: string | null;
}

export interface PromptListRequest {
  feature?: string | null;
}

export interface PromptListResponse {
  items: PromptVersionItem[];
  total: number;
  features: string[];
}

export interface PromptCreateRequest {
  feature: string;
  system_prompt: string;
  user_template?: string | null;
  description?: string | null;
  activate?: boolean;
}

export interface PromptCreateResponse {
  success: boolean;
  item: PromptVersionItem;
  message: string;
}

export interface PromptActivateRequest {
  id: number;
}

export interface PromptActivateResponse {
  success: boolean;
  message: string;
  activated: PromptVersionItem;
}

export interface PromptDiff {
  field: string;
  value_a?: string | null;
  value_b?: string | null;
  changed: boolean;
}

export interface PromptCompareRequest {
  id_a: number;
  id_b: number;
}

export interface PromptCompareResponse {
  version_a: PromptVersionItem;
  version_b: PromptVersionItem;
  diffs: PromptDiff[];
}

// ============================================================================
// 搜尋歷史
// ============================================================================

export interface SearchHistoryItem {
  id: number;
  user_id?: number | null;
  user_name?: string | null;
  query: string;
  parsed_intent?: Record<string, unknown> | null;
  results_count: number;
  search_strategy?: string | null;
  source?: string | null;
  synonym_expanded: boolean;
  related_entity?: string | null;
  latency_ms?: number | null;
  confidence?: number | null;
  created_at?: string | null;
}

export interface SearchHistoryListRequest {
  page?: number;
  page_size?: number;
  date_from?: string;
  date_to?: string;
  search_strategy?: string;
  source?: string;
  keyword?: string;
}

export interface SearchHistoryListResponse {
  items: SearchHistoryItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface DailyTrend {
  date: string;
  count: number;
}

export interface TopQuery {
  query: string;
  count: number;
  avg_results: number;
}

export interface SearchStatsResponse {
  total_searches: number;
  today_searches: number;
  rule_engine_hit_rate: number;
  avg_latency_ms: number;
  avg_confidence: number;
  daily_trend: DailyTrend[];
  top_queries: TopQuery[];
  strategy_distribution: Record<string, number>;
  source_distribution: Record<string, number>;
  entity_distribution: Record<string, number>;
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
}

export interface KGShortestPathResponse {
  success: boolean;
  found: boolean;
  depth: number;
  path: KGPathNode[];
  relations: string[];
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
// Ollama 管理
// ============================================================================

/** GPU 已載入模型資訊 */
export interface OllamaGpuLoadedModel {
  name: string;
  size: number;
  size_vram: number;
}

/** Ollama GPU 資訊 */
export interface OllamaGpuInfo {
  loaded_models: OllamaGpuLoadedModel[];
}

/** Ollama 詳細狀態回應 */
export interface OllamaStatusResponse {
  available: boolean;
  message: string;
  models: string[];
  required_models: string[];
  required_models_ready: boolean;
  missing_models: string[];
  gpu_info: OllamaGpuInfo | null;
  groq_available: boolean;
  groq_message: string;
}

/** Ollama 模型檢查與拉取回應 */
export interface OllamaEnsureModelsResponse {
  ollama_available: boolean;
  installed: string[];
  pulled: string[];
  failed: string[];
}

/** Ollama 模型預熱回應 */
export interface OllamaWarmupResponse {
  results: Record<string, boolean>;
  all_success: boolean;
}

// ============================================================================
// RAG 問答
// ============================================================================

export interface RAGQueryRequest {
  question: string;
  top_k?: number;
  similarity_threshold?: number;
}

export interface RAGSourceItem {
  document_id: number;
  doc_number: string;
  subject: string;
  doc_type: string;
  category: string;
  sender: string;
  receiver: string;
  doc_date: string;
  similarity: number;
}

export interface RAGQueryResponse {
  success: boolean;
  answer: string;
  sources: RAGSourceItem[];
  retrieval_count: number;
  latency_ms: number;
  model: string;
}

export interface RAGStreamRequest {
  question: string;
  top_k?: number;
  similarity_threshold?: number;
  history?: Array<{ role: string; content: string }>;
}

// ============================================================================
// AI 回饋
// ============================================================================

export interface AIFeedbackSubmitRequest {
  conversation_id: string;
  message_index: number;
  feature_type: 'agent' | 'rag';
  score: 1 | -1;
  question?: string;
  answer_preview?: string;
  feedback_text?: string;
  latency_ms?: number;
  model?: string;
}

export interface AIFeedbackSubmitResponse {
  success: boolean;
  message: string;
}

export interface AIFeedbackStatsResponse {
  success: boolean;
  total_feedback: number;
  positive_count: number;
  negative_count: number;
  positive_rate: number;
  by_feature: Record<string, {
    total: number;
    positive: number;
    negative: number;
    positive_rate: number;
  }>;
  recent_negative: Array<{
    id: number;
    question?: string;
    answer_preview?: string;
    feature_type: string;
    created_at?: string;
  }>;
}

export interface AIAnalyticsOverviewResponse {
  success: boolean;
  ai_feature_usage: Record<string, {
    count: number;
    cache_hits: number;
    errors: number;
    avg_latency_ms: number;
  }>;
  feedback_summary: {
    total_feedback: number;
    positive_count: number;
    negative_count: number;
    positive_rate: number;
    by_feature: Record<string, unknown>;
  };
  search_stats: Record<string, unknown>;
  unused_features: string[];
}
