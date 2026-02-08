/**
 * AI 服務 API
 *
 * 提供公文 AI 智慧功能的前端 API 介面
 *
 * @version 1.1.0
 * @created 2026-02-04
 * @updated 2026-02-05 - 新增自然語言公文搜尋
 */

import axios from 'axios';
import { apiClient, API_BASE_URL } from './client';
import { AI_ENDPOINTS } from './endpoints';
import { logger } from '../services/logger';
import type { AIStatsResponse } from '../types/api';

// ============================================================================
// 型別定義
// ============================================================================

/** 摘要生成請求 */
export interface SummaryRequest {
  subject: string;
  content?: string;
  sender?: string;
  max_length?: number;
}

/** 摘要生成回應 */
export interface SummaryResponse {
  summary: string;
  confidence: number;
  source: 'ai' | 'fallback' | 'disabled' | 'rate_limited';
  error?: string;
}

/** 分類建議請求 */
export interface ClassifyRequest {
  subject: string;
  content?: string;
  sender?: string;
}

/** 分類建議回應 */
export interface ClassifyResponse {
  doc_type: string;
  category: '收文' | '發文';
  doc_type_confidence: number;
  category_confidence: number;
  reasoning?: string;
  source: 'ai' | 'fallback' | 'disabled' | 'rate_limited';
  error?: string;
}

/** 關鍵字提取請求 */
export interface KeywordsRequest {
  subject: string;
  content?: string;
  max_keywords?: number;
}

/** 關鍵字提取回應 */
export interface KeywordsResponse {
  keywords: string[];
  confidence: number;
  source: 'ai' | 'fallback' | 'disabled' | 'rate_limited';
  error?: string;
}

/** 機關候選項 */
export interface AgencyCandidate {
  id: number;
  name: string;
  short_name?: string;
}

/** 機關匹配請求 */
export interface AgencyMatchRequest {
  agency_name: string;
  candidates?: AgencyCandidate[];
}

/** 機關匹配結果 */
export interface AgencyMatchResult {
  id: number;
  name: string;
  score: number;
}

/** 機關匹配回應 */
export interface AgencyMatchResponse {
  best_match: AgencyMatchResult | null;
  alternatives: AgencyMatchResult[];
  is_new: boolean;
  reasoning?: string;
  source: 'ai' | 'fallback' | 'disabled';
  error?: string;
}

/** AI 服務健康狀態 */
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

/** AI 服務配置 (從後端取得) */
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
// 自然語言搜尋相關型別 (v1.1.0 新增)
// ============================================================================

/** 解析的搜尋意圖 */
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
  confidence: number;
}

/** 意圖解析請求 */
export interface ParseIntentRequest {
  query: string;
}

/** 意圖解析回應 */
export interface ParseIntentResponse {
  success: boolean;
  query: string;
  parsed_intent: ParsedSearchIntent;
  source: 'ai' | 'error';
  error?: string | null;
}

/** 自然語言搜尋請求 */
export interface NaturalSearchRequest {
  query: string;
  max_results?: number;
  include_attachments?: boolean;
  offset?: number;
}

/** 附件資訊 */
export interface AttachmentInfo {
  id: number;
  file_name: string;
  original_name?: string | null;
  file_size?: number | null;
  mime_type?: string | null;
  created_at?: string | null;
}

/** 公文搜尋結果項目 */
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

/** 自然語言搜尋回應 */
export interface NaturalSearchResponse {
  success: boolean;
  query: string;
  parsed_intent: ParsedSearchIntent;
  results: DocumentSearchResult[];
  total: number;
  source: 'ai' | 'fallback' | 'rate_limited' | 'error';
  error?: string | null;
}

// ============================================================================
// 同義詞管理型別 (A4)
// ============================================================================

/** 同義詞群組 */
export interface AISynonymItem {
  id: number;
  category: string;
  words: string;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

/** 同義詞列表請求 */
export interface AISynonymListRequest {
  category?: string | null;
  is_active?: boolean | null;
}

/** 同義詞列表回應 */
export interface AISynonymListResponse {
  items: AISynonymItem[];
  total: number;
  categories: string[];
}

/** 同義詞建立請求 */
export interface AISynonymCreateRequest {
  category: string;
  words: string;
  is_active?: boolean;
}

/** 同義詞更新請求 */
export interface AISynonymUpdateRequest {
  id: number;
  category?: string;
  words?: string;
  is_active?: boolean;
}

/** 同義詞刪除請求 */
export interface AISynonymDeleteRequest {
  id: number;
}

/** 同義詞重新載入回應 */
export interface AISynonymReloadResponse {
  success: boolean;
  total_groups: number;
  total_words: number;
  message: string;
}

// ============================================================================
// Prompt 版本管理相關型別 (v1.1.0 新增)
// ============================================================================

/** Prompt 版本項目 */
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

/** Prompt 列表請求 */
export interface PromptListRequest {
  feature?: string | null;
}

/** Prompt 列表回應 */
export interface PromptListResponse {
  items: PromptVersionItem[];
  total: number;
  features: string[];
}

/** Prompt 新增請求 */
export interface PromptCreateRequest {
  feature: string;
  system_prompt: string;
  user_template?: string | null;
  description?: string | null;
  activate?: boolean;
}

/** Prompt 新增回應 */
export interface PromptCreateResponse {
  success: boolean;
  item: PromptVersionItem;
  message: string;
}

/** Prompt 啟用請求 */
export interface PromptActivateRequest {
  id: number;
}

/** Prompt 啟用回應 */
export interface PromptActivateResponse {
  success: boolean;
  message: string;
  activated: PromptVersionItem;
}

/** Prompt 版本差異 */
export interface PromptDiff {
  field: string;
  value_a?: string | null;
  value_b?: string | null;
  changed: boolean;
}

/** Prompt 比較請求 */
export interface PromptCompareRequest {
  id_a: number;
  id_b: number;
}

/** Prompt 比較回應 */
export interface PromptCompareResponse {
  version_a: PromptVersionItem;
  version_b: PromptVersionItem;
  diffs: PromptDiff[];
}

// ============================================================================
// 模組級變數：自然語言搜尋 AbortController
// ============================================================================

/** 當前自然語言搜尋的 AbortController（用於取消進行中的請求） */
let _naturalSearchController: AbortController | null = null;

/**
 * 取消進行中的自然語言搜尋
 *
 * 外部可呼叫此方法來主動取消搜尋（例如元件卸載時）
 */
export function abortNaturalSearch(): void {
  if (_naturalSearchController) {
    _naturalSearchController.abort();
    _naturalSearchController = null;
  }
}

// ============================================================================
// API 端點 — 統一從 endpoints.ts 匯入 (SSOT)
// ============================================================================

// AI_ENDPOINTS 已從 './endpoints' 匯入

// ============================================================================
// API 方法
// ============================================================================

export const aiApi = {
  /**
   * 生成公文摘要
   *
   * @param request 摘要生成請求
   * @returns 摘要生成回應
   */
  async generateSummary(request: SummaryRequest): Promise<SummaryResponse> {
    try {
      logger.log('AI 生成摘要:', request.subject.substring(0, 50));
      return await apiClient.post<SummaryResponse>(AI_ENDPOINTS.SUMMARY, request);
    } catch (error) {
      logger.error('AI 摘要生成失敗:', error);
      return {
        summary: request.subject.substring(0, request.max_length || 100),
        confidence: 0,
        source: 'fallback',
        error: error instanceof Error ? error.message : '未知錯誤',
      };
    }
  },

  /**
   * 串流生成公文摘要 (SSE)
   *
   * 使用 Server-Sent Events 逐字接收 AI 生成的摘要，
   * 降低使用者感知延遲。
   *
   * @param params 摘要生成請求
   * @param onToken 收到每個 token 時的回調
   * @param onDone 串流完成時的回調
   * @param onError 發生錯誤時的回調
   * @returns AbortController 供外部取消串流
   */
  streamSummary(
    params: SummaryRequest,
    onToken: (token: string) => void,
    onDone: () => void,
    onError?: (error: string) => void,
  ): AbortController {
    const controller = new AbortController();

    const baseUrl = API_BASE_URL;
    const url = `${baseUrl}${AI_ENDPOINTS.SUMMARY_STREAM}`;

    // 取得 token (向後相容)
    const accessToken = localStorage.getItem('access_token');

    (async () => {
      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
          },
          body: JSON.stringify(params),
          signal: controller.signal,
          credentials: 'include',
        });

        if (!response.ok) {
          const errorText = await response.text();
          onError?.(errorText || `HTTP ${response.status}`);
          onDone();
          return;
        }

        const reader = response.body?.getReader();
        if (!reader) {
          onError?.('ReadableStream not supported');
          onDone();
          return;
        }

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // 解析 SSE: 每個事件以 \n\n 分隔
          const parts = buffer.split('\n\n');
          buffer = parts.pop() || '';

          for (const part of parts) {
            const line = part.trim();
            if (!line.startsWith('data: ')) continue;

            const dataStr = line.slice(6);
            try {
              const data = JSON.parse(dataStr) as {
                token: string;
                done: boolean;
                error?: string;
              };

              if (data.error) {
                onError?.(data.error);
              }

              if (data.token) {
                onToken(data.token);
              }

              if (data.done) {
                onDone();
                return;
              }
            } catch {
              // 跳過無法解析的行
              logger.warn('SSE 解析失敗:', dataStr);
            }
          }
        }

        // reader 結束但沒收到 done 事件
        onDone();
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') {
          // 使用者主動取消，不算錯誤
          return;
        }
        const message = err instanceof Error ? err.message : '串流連線失敗';
        logger.error('SSE 串流錯誤:', message);
        onError?.(message);
        onDone();
      }
    })();

    return controller;
  },

  /**
   * 取得分類建議
   *
   * @param request 分類建議請求
   * @returns 分類建議回應
   */
  async suggestClassification(request: ClassifyRequest): Promise<ClassifyResponse> {
    try {
      logger.log('AI 分類建議:', request.subject.substring(0, 50));
      return await apiClient.post<ClassifyResponse>(AI_ENDPOINTS.CLASSIFY, request);
    } catch (error) {
      logger.error('AI 分類建議失敗:', error);
      return {
        doc_type: '函',
        category: '收文',
        doc_type_confidence: 0,
        category_confidence: 0,
        source: 'fallback',
        error: error instanceof Error ? error.message : '未知錯誤',
      };
    }
  },

  /**
   * 提取關鍵字
   *
   * @param request 關鍵字提取請求
   * @returns 關鍵字提取回應
   */
  async extractKeywords(request: KeywordsRequest): Promise<KeywordsResponse> {
    try {
      logger.log('AI 提取關鍵字:', request.subject.substring(0, 50));
      return await apiClient.post<KeywordsResponse>(AI_ENDPOINTS.KEYWORDS, request);
    } catch (error) {
      logger.error('AI 關鍵字提取失敗:', error);
      return {
        keywords: [],
        confidence: 0,
        source: 'fallback',
        error: error instanceof Error ? error.message : '未知錯誤',
      };
    }
  },

  /**
   * AI 機關匹配
   *
   * @param request 機關匹配請求
   * @returns 機關匹配回應
   */
  async matchAgency(request: AgencyMatchRequest): Promise<AgencyMatchResponse> {
    try {
      logger.log('AI 機關匹配:', request.agency_name);
      return await apiClient.post<AgencyMatchResponse>(AI_ENDPOINTS.AGENCY_MATCH, request);
    } catch (error) {
      logger.error('AI 機關匹配失敗:', error);
      return {
        best_match: null,
        alternatives: [],
        is_new: true,
        source: 'fallback',
        error: error instanceof Error ? error.message : '未知錯誤',
      };
    }
  },

  /**
   * 檢查 AI 服務健康狀態
   *
   * @returns AI 服務健康狀態
   */
  async checkHealth(): Promise<AIHealthStatus> {
    try {
      logger.log('檢查 AI 服務健康狀態');
      return await apiClient.post<AIHealthStatus>(AI_ENDPOINTS.HEALTH, {});
    } catch (error) {
      logger.error('AI 健康檢查失敗:', error);
      return {
        groq: { available: false, message: '無法連接' },
        ollama: { available: false, message: '無法連接' },
      };
    }
  },

  /**
   * 取得 AI 服務配置 (Feature Flag)
   *
   * @returns AI 服務配置
   */
  async getConfig(): Promise<AIConfigResponse | null> {
    try {
      logger.log('取得 AI 服務配置');
      return await apiClient.post<AIConfigResponse>(AI_ENDPOINTS.CONFIG, {});
    } catch (error) {
      logger.error('取得 AI 配置失敗:', error);
      return null;
    }
  },

  /**
   * 批次處理：生成摘要 + 分類建議
   *
   * @param subject 公文主旨
   * @param content 公文內容
   * @param sender 發文機關
   * @returns 摘要和分類建議
   */
  async analyzeDocument(
    subject: string,
    content?: string,
    sender?: string
  ): Promise<{
    summary: SummaryResponse;
    classification: ClassifyResponse;
  }> {
    const [summary, classification] = await Promise.all([
      this.generateSummary({ subject, content, sender }),
      this.suggestClassification({ subject, content, sender }),
    ]);

    return { summary, classification };
  },

  /**
   * 解析搜尋意圖（僅解析，不執行搜尋）
   *
   * 將自然語言查詢解析為結構化搜尋條件，供前端填充傳統篩選器。
   *
   * @param query 自然語言查詢
   * @returns 解析的搜尋意圖
   *
   * @example
   * const result = await aiApi.parseSearchIntent('找桃園市政府上個月的公文');
   * // result.parsed_intent.sender = '桃園市政府'
   */
  async parseSearchIntent(query: string): Promise<ParseIntentResponse> {
    try {
      logger.log('AI 意圖解析:', query.substring(0, 50));
      return await apiClient.post<ParseIntentResponse>(AI_ENDPOINTS.PARSE_INTENT, { query });
    } catch (error) {
      logger.error('AI 意圖解析失敗:', error);
      return {
        success: false,
        query,
        parsed_intent: { keywords: [query], confidence: 0 },
        source: 'error',
        error: error instanceof Error ? error.message : '未知錯誤',
      };
    }
  },

  /**
   * 自然語言公文搜尋 (v1.2.0)
   *
   * 使用 AI 解析自然語言查詢，搜尋相關公文並返回結果（含附件資訊）
   * - 自動取消上一次進行中的搜尋（競態防護）
   * - 30 秒超時自動取消
   * - 可透過 abortNaturalSearch() 從外部取消
   *
   * @param query 自然語言查詢
   * @param maxResults 最大結果數（預設 20）
   * @param includeAttachments 是否包含附件資訊（預設 true）
   * @returns 搜尋結果
   *
   * @example
   * // 搜尋範例
   * const result = await aiApi.naturalSearch('找桃園市政府上個月的公文');
   * const result = await aiApi.naturalSearch('有截止日的待處理公文', 10);
   * // 取消搜尋
   * abortNaturalSearch();
   */
  /**
   * 取得 AI 使用統計
   *
   * @returns AI 使用統計資料
   */
  async getStats(): Promise<AIStatsResponse | null> {
    try {
      logger.log('取得 AI 使用統計');
      return await apiClient.post<AIStatsResponse>(AI_ENDPOINTS.STATS, {});
    } catch (error) {
      logger.error('取得 AI 統計失敗:', error);
      return null;
    }
  },

  /**
   * 重設 AI 使用統計
   */
  async resetStats(): Promise<boolean> {
    try {
      logger.log('重設 AI 使用統計');
      await apiClient.post(AI_ENDPOINTS.STATS_RESET, {});
      return true;
    } catch (error) {
      logger.error('重設 AI 統計失敗:', error);
      return false;
    }
  },

  // ==========================================================================
  // 同義詞管理 API
  // ==========================================================================

  /**
   * 列出同義詞群組
   */
  async listSynonyms(request: AISynonymListRequest = {}): Promise<AISynonymListResponse> {
    try {
      logger.log('取得同義詞列表');
      return await apiClient.post<AISynonymListResponse>(AI_ENDPOINTS.SYNONYMS_LIST, request);
    } catch (error) {
      logger.error('取得同義詞列表失敗:', error);
      return { items: [], total: 0, categories: [] };
    }
  },

  /**
   * 新增同義詞群組
   */
  async createSynonym(request: AISynonymCreateRequest): Promise<AISynonymItem | null> {
    try {
      logger.log('新增同義詞群組:', request.category);
      return await apiClient.post<AISynonymItem>(AI_ENDPOINTS.SYNONYMS_CREATE, request);
    } catch (error) {
      logger.error('新增同義詞群組失敗:', error);
      throw error;
    }
  },

  /**
   * 更新同義詞群組
   */
  async updateSynonym(request: AISynonymUpdateRequest): Promise<AISynonymItem | null> {
    try {
      logger.log('更新同義詞群組:', request.id);
      return await apiClient.post<AISynonymItem>(AI_ENDPOINTS.SYNONYMS_UPDATE, request);
    } catch (error) {
      logger.error('更新同義詞群組失敗:', error);
      throw error;
    }
  },

  /**
   * 刪除同義詞群組
   */
  async deleteSynonym(id: number): Promise<boolean> {
    try {
      logger.log('刪除同義詞群組:', id);
      await apiClient.post(AI_ENDPOINTS.SYNONYMS_DELETE, { id });
      return true;
    } catch (error) {
      logger.error('刪除同義詞群組失敗:', error);
      throw error;
    }
  },

  /**
   * 重新載入同義詞到記憶體
   */
  async reloadSynonyms(): Promise<AISynonymReloadResponse> {
    try {
      logger.log('重新載入同義詞');
      return await apiClient.post<AISynonymReloadResponse>(AI_ENDPOINTS.SYNONYMS_RELOAD, {});
    } catch (error) {
      logger.error('重新載入同義詞失敗:', error);
      return {
        success: false,
        total_groups: 0,
        total_words: 0,
        message: error instanceof Error ? error.message : '重新載入失敗',
      };
    }
  },

  async naturalSearch(
    query: string,
    maxResults: number = 20,
    includeAttachments: boolean = true,
    offset: number = 0
  ): Promise<NaturalSearchResponse> {
    // 取消上一次進行中的搜尋
    _naturalSearchController?.abort();
    _naturalSearchController = new AbortController();

    const TIMEOUT_MS = 30000;
    const timeoutId = setTimeout(() => _naturalSearchController?.abort(), TIMEOUT_MS);

    try {
      logger.log('AI 自然語言搜尋:', query.substring(0, 50));
      const response = await apiClient.post<NaturalSearchResponse>(
        AI_ENDPOINTS.NATURAL_SEARCH,
        {
          query,
          max_results: maxResults,
          include_attachments: includeAttachments,
          offset,
        },
        { signal: _naturalSearchController.signal }
      );
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);

      // AbortError: 搜尋被取消或超時（Axios 使用 CanceledError，瀏覽器使用 DOMException）
      const isAborted = axios.isCancel(error) ||
        (error instanceof DOMException && error.name === 'AbortError');
      if (isAborted) {
        logger.log('AI 自然語言搜尋已取消或超時');
        return {
          success: false,
          query,
          parsed_intent: { keywords: [query], confidence: 0 },
          results: [],
          total: 0,
          source: 'error',
          error: '搜尋已取消或超時',
        };
      }

      logger.error('AI 自然語言搜尋失敗:', error);
      return {
        success: false,
        query,
        parsed_intent: { keywords: [query], confidence: 0 },
        results: [],
        total: 0,
        source: 'error',
        error: error instanceof Error ? error.message : '未知錯誤',
      };
    }
  },

  // ==========================================================================
  // Prompt 版本管理 API
  // ==========================================================================

  /**
   * 列出 Prompt 版本
   */
  async listPrompts(feature?: string): Promise<PromptListResponse> {
    try {
      logger.log('列出 Prompt 版本', feature ? `feature=${feature}` : '全部');
      return await apiClient.post<PromptListResponse>(AI_ENDPOINTS.PROMPTS_LIST, {
        feature: feature || null,
      });
    } catch (error) {
      logger.error('列出 Prompt 版本失敗:', error);
      throw error;
    }
  },

  /**
   * 新增 Prompt 版本
   */
  async createPrompt(request: PromptCreateRequest): Promise<PromptCreateResponse> {
    try {
      logger.log('新增 Prompt 版本:', request.feature);
      return await apiClient.post<PromptCreateResponse>(AI_ENDPOINTS.PROMPTS_CREATE, request);
    } catch (error) {
      logger.error('新增 Prompt 版本失敗:', error);
      throw error;
    }
  },

  /**
   * 啟用 Prompt 版本
   */
  async activatePrompt(id: number): Promise<PromptActivateResponse> {
    try {
      logger.log('啟用 Prompt 版本:', id);
      return await apiClient.post<PromptActivateResponse>(AI_ENDPOINTS.PROMPTS_ACTIVATE, { id });
    } catch (error) {
      logger.error('啟用 Prompt 版本失敗:', error);
      throw error;
    }
  },

  /**
   * 比較兩個 Prompt 版本
   */
  async comparePrompts(idA: number, idB: number): Promise<PromptCompareResponse> {
    try {
      logger.log('比較 Prompt 版本:', idA, 'vs', idB);
      return await apiClient.post<PromptCompareResponse>(AI_ENDPOINTS.PROMPTS_COMPARE, {
        id_a: idA,
        id_b: idB,
      });
    } catch (error) {
      logger.error('比較 Prompt 版本失敗:', error);
      throw error;
    }
  },
};

export default aiApi;
