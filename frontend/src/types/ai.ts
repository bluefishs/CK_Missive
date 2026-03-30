/**
 * AI 服務型別定義 (SSOT - Barrel Re-export)
 *
 * 所有 AI 型別按領域拆分為 4 個子檔案，此處統一 re-export。
 * 既有 import { ... } from 'types/ai' 無需修改。
 *
 * @version 2.0.0
 * @ssot-location /frontend/src/types/ai.ts
 * @created 2026-02-24
 * @refactored 2026-03-29 — 拆分為 ai-document / ai-search / ai-knowledge-graph / ai-services
 */

import type { AIStatsResponse } from './api';

// Re-export from api.ts
export type { AIStatsResponse };

// Domain: 文件處理 (摘要、分類、關鍵字、機關匹配、健康/配置)
export * from './ai-document';

// Domain: 搜尋與知識管理 (意圖解析、自然搜尋、Embedding、同義詞、Prompt、搜尋歷史)
export * from './ai-search';

// Domain: 知識圖譜 (圖譜結構、語意相似、實體提取、KG Phase 2、統一搜尋、Code Graph、DB Schema)
export * from './ai-knowledge-graph';

// Domain: AI 服務 (Ollama、RAG、回饋、分析、Agent、數位分身、統計)
export * from './ai-services';
