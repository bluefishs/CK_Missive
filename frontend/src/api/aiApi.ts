/**
 * AI 服務 API
 *
 * 提供公文 AI 智慧功能的前端 API 介面
 *
 * @version 1.0.0
 * @created 2026-02-04
 */

import { apiClient } from './client';
import { logger } from '../services/logger';

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

// ============================================================================
// API 端點
// ============================================================================

const AI_ENDPOINTS = {
  SUMMARY: '/ai/document/summary',
  CLASSIFY: '/ai/document/classify',
  KEYWORDS: '/ai/document/keywords',
  AGENCY_MATCH: '/ai/agency/match',
  HEALTH: '/ai/health',
};

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
      return await apiClient.get<AIHealthStatus>(AI_ENDPOINTS.HEALTH);
    } catch (error) {
      logger.error('AI 健康檢查失敗:', error);
      return {
        groq: { available: false, message: '無法連接' },
        ollama: { available: false, message: '無法連接' },
      };
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
};

export default aiApi;
