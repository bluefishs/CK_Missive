/**
 * AI 自然語言搜尋 API
 *
 * 包含 AbortController 管理、超時保護、競態防護。
 *
 * @version 1.0.0
 * @created 2026-02-11
 */

import axios from 'axios';
import { apiClient } from '../client';
import { AI_ENDPOINTS } from '../endpoints';
import { logger } from '../../services/logger';
import type { NaturalSearchResponse } from './types';

/** 當前自然語言搜尋的 AbortController */
let _naturalSearchController: AbortController | null = null;

/**
 * 取消進行中的自然語言搜尋
 */
export function abortNaturalSearch(): void {
  if (_naturalSearchController) {
    _naturalSearchController.abort();
    _naturalSearchController = null;
  }
}

/**
 * 自然語言公文搜尋
 *
 * - 自動取消上一次進行中的搜尋（競態防護）
 * - 30 秒超時自動取消
 * - 可透過 abortNaturalSearch() 從外部取消
 */
export async function naturalSearch(
  query: string,
  maxResults: number = 20,
  includeAttachments: boolean = true,
  offset: number = 0,
): Promise<NaturalSearchResponse> {
  _naturalSearchController?.abort();
  _naturalSearchController = new AbortController();

  const TIMEOUT_MS = 30000;
  const timeoutId = setTimeout(() => _naturalSearchController?.abort(), TIMEOUT_MS);

  try {
    logger.log('AI 自然語言搜尋:', query.substring(0, 50));
    const response = await apiClient.post<NaturalSearchResponse>(
      AI_ENDPOINTS.NATURAL_SEARCH,
      { query, max_results: maxResults, include_attachments: includeAttachments, offset },
      { signal: _naturalSearchController.signal },
    );
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);

    const isAborted =
      axios.isCancel(error) ||
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
}
