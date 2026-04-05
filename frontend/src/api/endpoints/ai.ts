/**
 * AI 服務端點
 */

/** AI 服務 API 端點 */
export const AI_ENDPOINTS = {
  /** 公文摘要 POST /ai/document/summary */
  SUMMARY: '/ai/document/summary',
  /** 串流摘要 POST /ai/document/summary/stream */
  SUMMARY_STREAM: '/ai/document/summary/stream',
  /** 分類建議 POST /ai/document/classify */
  CLASSIFY: '/ai/document/classify',
  /** 關鍵字提取 POST /ai/document/keywords */
  KEYWORDS: '/ai/document/keywords',
  /** 自然語言搜尋 POST /ai/document/natural-search */
  NATURAL_SEARCH: '/ai/document/natural-search',
  /** 意圖解析 POST /ai/document/parse-intent */
  PARSE_INTENT: '/ai/document/parse-intent',
  /** 機關匹配 POST /ai/agency/match */
  AGENCY_MATCH: '/ai/agency/match',
  /** 健康檢查 POST /ai/health */
  HEALTH: '/ai/health',
  /** AI 配置 POST /ai/config */
  CONFIG: '/ai/config',
  /** AI 統計 POST /ai/stats */
  STATS: '/ai/stats',
  /** 重設統計 POST /ai/stats/reset */
  STATS_RESET: '/ai/stats/reset',
  /** 同義詞列表 POST /ai/synonyms/list */
  SYNONYMS_LIST: '/ai/synonyms/list',
  /** 新增同義詞 POST /ai/synonyms/create */
  SYNONYMS_CREATE: '/ai/synonyms/create',
  /** 更新同義詞 POST /ai/synonyms/update */
  SYNONYMS_UPDATE: '/ai/synonyms/update',
  /** 刪除同義詞 POST /ai/synonyms/delete */
  SYNONYMS_DELETE: '/ai/synonyms/delete',
  /** 重新載入同義詞 POST /ai/synonyms/reload */
  SYNONYMS_RELOAD: '/ai/synonyms/reload',
  /** Prompt 版本列表 POST /ai/prompts/list */
  PROMPTS_LIST: '/ai/prompts/list',
  /** 新增 Prompt 版本 POST /ai/prompts/create */
  PROMPTS_CREATE: '/ai/prompts/create',
  /** 啟用 Prompt 版本 POST /ai/prompts/activate */
  PROMPTS_ACTIVATE: '/ai/prompts/activate',
  /** Prompt 版本比較 POST /ai/prompts/compare */
  PROMPTS_COMPARE: '/ai/prompts/compare',
  /** 搜尋歷史列表 POST /ai/search-history/list */
  SEARCH_HISTORY_LIST: '/ai/search-history/list',
  /** 搜尋統計 POST /ai/search-history/stats */
  SEARCH_HISTORY_STATS: '/ai/search-history/stats',
  /** 清除搜尋歷史 POST /ai/search-history/clear */
  SEARCH_HISTORY_CLEAR: '/ai/search-history/clear',
  /** 搜尋回饋 POST /ai/search-history/feedback */
  SEARCH_HISTORY_FEEDBACK: '/ai/search-history/feedback',
  /** 搜尋建議 POST /ai/search-history/suggestions */
  SEARCH_HISTORY_SUGGESTIONS: '/ai/search-history/suggestions',
  /** 關聯圖譜 POST /ai/document/relation-graph */
  RELATION_GRAPH: '/ai/document/relation-graph',
  /** Embedding 統計 POST /ai/embedding/stats */
  EMBEDDING_STATS: '/ai/embedding/stats',
  /** Embedding 批次 POST /ai/embedding/batch */
  EMBEDDING_BATCH: '/ai/embedding/batch',
  /** 語意相似推薦 POST /ai/document/semantic-similar */
  SEMANTIC_SIMILAR: '/ai/document/semantic-similar',
  /** 實體提取 POST /ai/entity/extract */
  ENTITY_EXTRACT: '/ai/entity/extract',
  /** 實體批次提取 POST /ai/entity/batch */
  ENTITY_BATCH: '/ai/entity/batch',
  /** 實體提取統計 POST /ai/entity/stats */
  ENTITY_STATS: '/ai/entity/stats',
  // --- 知識圖譜 Phase 2: 正規化實體查詢 ---
  /** 正規化實體搜尋 POST /ai/graph/entity/search */
  GRAPH_ENTITY_SEARCH: '/ai/graph/entity/search',
  /** 實體鄰居查詢 POST /ai/graph/entity/neighbors */
  GRAPH_ENTITY_NEIGHBORS: '/ai/graph/entity/neighbors',
  /** 實體詳情 POST /ai/graph/entity/detail */
  GRAPH_ENTITY_DETAIL: '/ai/graph/entity/detail',
  /** 最短路徑 POST /ai/graph/entity/shortest-path */
  GRAPH_SHORTEST_PATH: '/ai/graph/entity/shortest-path',
  /** 實體時間軸 POST /ai/graph/entity/timeline */
  GRAPH_ENTITY_TIMELINE: '/ai/graph/entity/timeline',
  /** 高頻實體排名 POST /ai/graph/entity/top */
  GRAPH_ENTITY_TOP: '/ai/graph/entity/top',
  /** 實體中心圖譜 POST /ai/graph/entity/graph */
  GRAPH_ENTITY_GRAPH: '/ai/graph/entity/graph',
  /** 圖譜統計 POST /ai/graph/stats */
  GRAPH_STATS: '/ai/graph/stats',
  /** 聯邦健康指標 POST /ai/graph/federation-health */
  GRAPH_FEDERATION_HEALTH: '/ai/graph/federation-health',
  /** 跨專案路徑查詢 POST /ai/graph/cross-domain-path */
  GRAPH_CROSS_DOMAIN_PATH: '/ai/graph/cross-domain-path',
  /** Agent 自我檔案 POST /ai/agent/self-profile */
  AGENT_SELF_PROFILE: '/ai/agent/self-profile',
  /** 時序聚合 POST /ai/graph/timeline/aggregate */
  GRAPH_TIMELINE_AGGREGATE: '/ai/graph/timeline/aggregate',
  /** 圖譜入圖管線 POST /ai/graph/ingest */
  GRAPH_INGEST: '/ai/graph/ingest',
  /** Code Wiki 代碼圖譜 POST /ai/graph/code-wiki */
  GRAPH_CODE_WIKI: '/ai/graph/code-wiki',
  /** Code Graph 入圖觸發 POST /ai/graph/admin/code-ingest */
  GRAPH_CODE_INGEST: '/ai/graph/admin/code-ingest',
  /** 循環依賴偵測 POST /ai/graph/admin/cycle-detection */
  GRAPH_CYCLE_DETECTION: '/ai/graph/admin/cycle-detection',
  /** 架構分析 POST /ai/graph/admin/architecture-analysis */
  GRAPH_ARCHITECTURE_ANALYSIS: '/ai/graph/admin/architecture-analysis',
  /** JSON 圖譜匯入 POST /ai/graph/admin/json-import */
  GRAPH_JSON_IMPORT: '/ai/graph/admin/json-import',
  /** Diff 影響分析 POST /ai/graph/admin/diff-impact */
  GRAPH_DIFF_IMPACT: '/ai/graph/admin/diff-impact',
  /** 實體合併 POST /ai/graph/admin/merge-entities */
  GRAPH_MERGE_ENTITIES: '/ai/graph/admin/merge-entities',
  /** 模組架構概覽 POST /ai/graph/module-overview */
  GRAPH_MODULE_OVERVIEW: '/ai/graph/module-overview',
  /** 動態模組映射 GET /ai/graph/module-mappings */
  GRAPH_MODULE_MAPPINGS: '/ai/graph/module-mappings',
  /** 資料庫 Schema 反射 POST /ai/graph/db-schema */
  GRAPH_DB_SCHEMA: '/ai/graph/db-schema',
  /** 資料庫 ER 圖譜 POST /ai/graph/db-graph */
  GRAPH_DB_GRAPH: '/ai/graph/db-graph',
  /** 跨圖譜統一搜尋 POST /ai/graph/unified-search */
  GRAPH_UNIFIED_SEARCH: '/ai/graph/unified-search',
  /** 自然語言知識圖譜搜尋 POST /ai/graph/smart-search */
  GRAPH_SMART_SEARCH: '/ai/graph/smart-search',
  /** 跨域橋接觸發 POST /ai/graph/cross-domain-link (Admin) */
  GRAPH_CROSS_DOMAIN_LINK: '/ai/graph/cross-domain-link',
  /** Embedding 批次回填 POST /ai/graph/embedding-backfill (Admin) */
  GRAPH_EMBEDDING_BACKFILL: '/ai/graph/embedding-backfill',
  // --- RAG 問答 ---
  /** RAG 問答 POST /ai/rag/query */
  RAG_QUERY: '/ai/rag/query',
  /** RAG 串流問答 POST /ai/rag/query/stream */
  RAG_QUERY_STREAM: '/ai/rag/query/stream',
  // --- Agentic 問答 ---
  /** Agentic 串流問答 POST /ai/agent/query/stream */
  AGENT_QUERY_STREAM: '/ai/agent/query/stream',
  /** 清除 Agent 對話記憶 POST /ai/agent/conversation/{session_id}/delete */
  AGENT_CONVERSATION_CLEAR: (sessionId: string) => `/ai/agent/conversation/${sessionId}/delete` as const,
  // --- 語音轉文字 ---
  /** 語音轉文字 POST /ai/voice/transcribe (multipart/form-data) */
  VOICE_TRANSCRIBE: '/ai/voice/transcribe',
  // --- Ollama 管理 ---
  /** Ollama 詳細狀態 POST /ai/ollama/status */
  OLLAMA_STATUS: '/ai/ollama/status',
  /** Ollama 模型檢查與拉取 POST /ai/ollama/ensure-models */
  OLLAMA_ENSURE_MODELS: '/ai/ollama/ensure-models',
  /** Ollama 模型預熱 POST /ai/ollama/warmup */
  OLLAMA_WARMUP: '/ai/ollama/warmup',
  // --- AI 回饋 + 分析 ---
  /** 提交 AI 回答回饋 POST /ai/feedback */
  FEEDBACK: '/ai/feedback',
  /** AI 回饋統計 POST /ai/feedback/stats */
  FEEDBACK_STATS: '/ai/feedback/stats',
  /** 系統使用分析總覽 POST /ai/analytics/overview */
  ANALYTICS_OVERVIEW: '/ai/analytics/overview',
  // --- AI 分析持久化 ---
  /** 取得公文 AI 分析結果 POST /ai/analysis/{document_id} */
  ANALYSIS_GET: (documentId: number) => `/ai/analysis/${documentId}` as const,
  /** 觸發公文 AI 分析 POST /ai/analysis/{document_id}/analyze */
  ANALYSIS_TRIGGER: (documentId: number) => `/ai/analysis/${documentId}/analyze` as const,
  /** 批次 AI 分析 POST /ai/analysis/batch */
  ANALYSIS_BATCH: '/ai/analysis/batch',
  /** AI 分析覆蓋率統計 POST /ai/analysis/stats */
  ANALYSIS_STATS: '/ai/analysis/stats',
  // --- Phase 3A 統計端點 ---
  /** 工具成功率統計 POST /ai/stats/tool-success-rates */
  STATS_TOOL_SUCCESS_RATES: '/ai/stats/tool-success-rates',
  /** Agent 追蹤記錄 POST /ai/stats/agent-traces */
  STATS_AGENT_TRACES: '/ai/stats/agent-traces',
  /** 單筆 Trace 詳情 GET /ai/stats/agent-traces/{id} (V-1.2 Timeline) */
  STATS_AGENT_TRACE_DETAIL: (traceId: number) => `/ai/stats/agent-traces/${traceId}`,
  /** 學習模式統計 POST /ai/stats/patterns */
  STATS_PATTERNS: '/ai/stats/patterns',
  /** 持久化學習統計 POST /ai/stats/learnings */
  STATS_LEARNINGS: '/ai/stats/learnings',
  /** 每日趨勢統計 POST /ai/stats/daily-trend */
  STATS_DAILY_TREND: '/ai/stats/daily-trend',
  /** 主動觸發警報 POST /ai/proactive/alerts */
  PROACTIVE_ALERTS: '/ai/proactive/alerts',
  /** 工具註冊清單 POST /ai/stats/tool-registry */
  STATS_TOOL_REGISTRY: '/ai/stats/tool-registry',
  /** Skills 能力圖譜 POST /ai/graph/skills-map */
  GRAPH_SKILLS_MAP: '/ai/graph/skills-map',
  /** 技能演化樹 POST /ai/graph/skill-evolution */
  GRAPH_SKILL_EVOLUTION: '/ai/graph/skill-evolution',
  /** 進化指標 POST /ai/stats/evolution/metrics */
  STATS_EVOLUTION_METRICS: '/ai/stats/evolution/metrics',
} as const;

/** 數位分身 API 端點 — 透過 Missive 後端代理至 NemoClaw Gateway */
export const DIGITAL_TWIN_ENDPOINTS = {
  /** 串流查詢 POST /ai/digital-twin/query/stream (SSE) */
  QUERY_STREAM: '/ai/digital-twin/query/stream',
  /** 健康檢查 POST /ai/digital-twin/health */
  HEALTH: '/ai/digital-twin/health',
  /** 任務狀態 POST /ai/digital-twin/tasks/{jobId} */
  TASK_STATUS: (jobId: string) => `/ai/digital-twin/tasks/${jobId}`,
  /** 任務核准 POST /ai/digital-twin/tasks/{jobId}/approve */
  TASK_APPROVE: (jobId: string) => `/ai/digital-twin/tasks/${jobId}/approve`,
  /** 任務拒絕 POST /ai/digital-twin/tasks/{jobId}/reject */
  TASK_REJECT: (jobId: string) => `/ai/digital-twin/tasks/${jobId}/reject`,
  /** 即時轉播 GET /ai/digital-twin/live-activity/stream (SSE 例外) */
  LIVE_ACTIVITY_STREAM: '/ai/digital-twin/live-activity/stream',
  /** Agent 組織圖 POST /ai/digital-twin/agent-topology */
  AGENT_TOPOLOGY: '/ai/digital-twin/agent-topology',
  /** QA 影響分析 POST /ai/digital-twin/qa-impact */
  QA_IMPACT: '/ai/digital-twin/qa-impact',
  /** 聚合儀表板 POST /ai/digital-twin/dashboard */
  DASHBOARD: '/ai/digital-twin/dashboard',
  /** 跨域自動委派 POST /ai/digital-twin/delegate/auto (E-6) */
  DELEGATE_AUTO: '/ai/digital-twin/delegate/auto',
  /** 智能洞察 POST /ai/digital-twin/insights */
  INSIGHTS: '/ai/digital-twin/insights',
} as const;

/** 知識庫瀏覽器 API 端點 */
export const KNOWLEDGE_BASE_ENDPOINTS = {
  TREE: '/knowledge-base/tree',
  FILE: '/knowledge-base/file',
  ADR_LIST: '/knowledge-base/adr/list',
  DIAGRAMS_LIST: '/knowledge-base/diagrams/list',
  SEARCH: '/knowledge-base/search',
  /** 知識卡片摘要 POST /knowledge-base/summarize-card */
  SUMMARIZE_CARD: '/knowledge-base/summarize-card',
} as const;
