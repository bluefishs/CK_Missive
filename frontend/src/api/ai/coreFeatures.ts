/**
 * AI 核心功能 API
 *
 * 摘要生成、分類建議、關鍵字提取、機關匹配、健康檢查、統計
 *
 * @version 1.0.0
 * @created 2026-02-11
 */

import { apiClient, API_BASE_URL } from '../client';
import { AI_ENDPOINTS } from '../endpoints';
import { logger } from '../../services/logger';
import type {
  SummaryRequest,
  SummaryResponse,
  ClassifyRequest,
  ClassifyResponse,
  KeywordsRequest,
  KeywordsResponse,
  AgencyMatchRequest,
  AgencyMatchResponse,
  AIHealthStatus,
  AIConfigResponse,
  AIStatsResponse,
} from './types';

export async function generateSummary(request: SummaryRequest): Promise<SummaryResponse> {
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
}

export function streamSummary(
  params: SummaryRequest,
  onToken: (token: string) => void,
  onDone: () => void,
  onError?: (error: string) => void,
): AbortController {
  const controller = new AbortController();
  const baseUrl = API_BASE_URL;
  const url = `${baseUrl}${AI_ENDPOINTS.SUMMARY_STREAM}`;
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

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
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

            if (data.error) onError?.(data.error);
            if (data.token) onToken(data.token);
            if (data.done) { onDone(); return; }
          } catch {
            logger.warn('SSE 解析失敗:', dataStr);
          }
        }
      }
      onDone();
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      const message = err instanceof Error ? err.message : '串流連線失敗';
      logger.error('SSE 串流錯誤:', message);
      onError?.(message);
      onDone();
    }
  })();

  return controller;
}

export async function suggestClassification(request: ClassifyRequest): Promise<ClassifyResponse> {
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
}

export async function extractKeywords(request: KeywordsRequest): Promise<KeywordsResponse> {
  try {
    logger.log('AI 提取關鍵字:', request.subject.substring(0, 50));
    return await apiClient.post<KeywordsResponse>(AI_ENDPOINTS.KEYWORDS, request);
  } catch (error) {
    logger.error('AI 關鍵字提取失敗:', error);
    return { keywords: [], confidence: 0, source: 'fallback', error: error instanceof Error ? error.message : '未知錯誤' };
  }
}

export async function matchAgency(request: AgencyMatchRequest): Promise<AgencyMatchResponse> {
  try {
    logger.log('AI 機關匹配:', request.agency_name);
    return await apiClient.post<AgencyMatchResponse>(AI_ENDPOINTS.AGENCY_MATCH, request);
  } catch (error) {
    logger.error('AI 機關匹配失敗:', error);
    return { best_match: null, alternatives: [], is_new: true, source: 'fallback', error: error instanceof Error ? error.message : '未知錯誤' };
  }
}

export async function checkHealth(): Promise<AIHealthStatus> {
  try {
    logger.log('檢查 AI 服務健康狀態');
    return await apiClient.post<AIHealthStatus>(AI_ENDPOINTS.HEALTH, {});
  } catch (error) {
    logger.error('AI 健康檢查失敗:', error);
    return { groq: { available: false, message: '無法連接' }, ollama: { available: false, message: '無法連接' } };
  }
}

export async function getConfig(): Promise<AIConfigResponse | null> {
  try {
    logger.log('取得 AI 服務配置');
    return await apiClient.post<AIConfigResponse>(AI_ENDPOINTS.CONFIG, {});
  } catch (error) {
    logger.error('取得 AI 配置失敗:', error);
    return null;
  }
}

export async function analyzeDocument(
  subject: string,
  content?: string,
  sender?: string,
): Promise<{ summary: SummaryResponse; classification: ClassifyResponse }> {
  const [summary, classification] = await Promise.all([
    generateSummary({ subject, content, sender }),
    suggestClassification({ subject, content, sender }),
  ]);
  return { summary, classification };
}

export async function getStats(): Promise<AIStatsResponse | null> {
  try {
    logger.log('取得 AI 使用統計');
    return await apiClient.post<AIStatsResponse>(AI_ENDPOINTS.STATS, {});
  } catch (error) {
    logger.error('取得 AI 統計失敗:', error);
    return null;
  }
}

export async function resetStats(): Promise<boolean> {
  try {
    logger.log('重設 AI 使用統計');
    await apiClient.post(AI_ENDPOINTS.STATS_RESET, {});
    return true;
  } catch (error) {
    logger.error('重設 AI 統計失敗:', error);
    return false;
  }
}

export async function parseSearchIntent(query: string): Promise<import('./types').ParseIntentResponse> {
  try {
    logger.log('AI 意圖解析:', query.substring(0, 50));
    return await apiClient.post(AI_ENDPOINTS.PARSE_INTENT, { query });
  } catch (error) {
    logger.error('AI 意圖解析失敗:', error);
    return { success: false, query, parsed_intent: { keywords: [query], confidence: 0 }, source: 'error', error: error instanceof Error ? error.message : '未知錯誤' };
  }
}
