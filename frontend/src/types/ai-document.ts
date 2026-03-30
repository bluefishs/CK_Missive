/**
 * AI 文件處理型別 (SSOT)
 *
 * 摘要、分類、關鍵字、機關匹配、健康檢查與配置
 *
 * @domain document-processing
 * @version 1.0.0
 * @date 2026-03-29
 */

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
