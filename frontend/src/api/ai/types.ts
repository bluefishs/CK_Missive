/**
 * AI 服務型別定義
 *
 * 所有 AI API 的 Request/Response 型別集中定義。
 *
 * @version 1.0.0
 * @created 2026-02-11
 * @extracted-from aiApi.ts
 */

import type { AIStatsResponse } from '../../types/api';

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

export interface NaturalSearchResponse {
  success: boolean;
  query: string;
  parsed_intent: ParsedSearchIntent;
  results: DocumentSearchResult[];
  total: number;
  source: 'ai' | 'rule_engine' | 'merged' | 'vector' | 'fallback' | 'rate_limited' | 'error';
  search_strategy?: 'keyword' | 'similarity' | 'hybrid' | 'semantic' | null;
  synonym_expanded?: boolean;
  history_id?: number | null;
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
  type: 'document' | 'project' | 'dispatch' | 'agency';
  label: string;
  category?: string | null;
  doc_number?: string | null;
  status?: string | null;
}

export interface GraphEdge {
  source: string;
  target: string;
  label: string;
  type: string;
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
