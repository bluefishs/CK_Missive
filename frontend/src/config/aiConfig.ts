/**
 * AI 服務配置
 *
 * 集中管理 AI 相關的前端配置，減少重複設定
 * 支援從後端 API 同步配置 (Feature Flag)
 *
 * @version 1.1.0
 * @created 2026-02-05
 * @updated 2026-02-05 - 新增後端配置同步支援
 * @reference CK_lvrland_Webmap AI 配置架構
 */

// ============================================================================
// AI 功能配置
// ============================================================================

export const AI_CONFIG = {
  /** 摘要生成 */
  summary: {
    maxLength: 100,
    defaultMaxLength: 100,
    minLength: 20,
  },

  /** 關鍵字提取 */
  keywords: {
    maxKeywords: 10,
    defaultMaxKeywords: 5,
    minKeywords: 1,
  },

  /** 分類建議 */
  classify: {
    confidenceThreshold: 0.7,  // 信心度閾值
    showReasoning: true,       // 是否顯示判斷理由
  },

  /** 機關匹配 */
  agencyMatch: {
    scoreThreshold: 0.7,       // 匹配分數閾值
    maxAlternatives: 3,        // 最多顯示幾個替代建議
  },

  /** 快取設定 */
  cache: {
    enabled: true,
    ttlSummary: 3600,          // 摘要快取 1 小時
    ttlClassify: 3600,         // 分類快取 1 小時
    ttlKeywords: 3600,         // 關鍵字快取 1 小時
  },

  /** 速率限制 */
  rateLimit: {
    maxRequests: 30,           // Groq 免費方案限制
    windowSeconds: 60,
  },
};

// ============================================================================
// AI 功能類型定義
// ============================================================================

export type AIFeatureType = 'summary' | 'classify' | 'keywords' | 'agency_match';

export type AISource = 'ai' | 'fallback' | 'disabled' | 'rate_limited';

// ============================================================================
// AI 功能名稱中文化
// ============================================================================

export const AI_FEATURE_NAMES: Record<AIFeatureType, string> = {
  summary: '摘要生成',
  classify: '分類建議',
  keywords: '關鍵字提取',
  agency_match: '機關匹配',
};

// ============================================================================
// AI 服務提供者配置
// ============================================================================

export const AI_PROVIDERS = {
  groq: {
    name: 'Groq',
    description: '主要 AI 服務（雲端）',
    priority: 1,
    rateLimit: { requests: 30, window: 60 },
  },
  ollama: {
    name: 'Ollama',
    description: '本地 AI 備援服務',
    priority: 2,
    rateLimit: null, // 無限制
  },
};

// ============================================================================
// 工具函數
// ============================================================================

/**
 * 取得 AI 功能的中文名稱
 */
export const getAIFeatureName = (feature: AIFeatureType): string => {
  return AI_FEATURE_NAMES[feature] || feature;
};

/**
 * 取得 AI 來源的顯示文字
 */
export const getAISourceLabel = (source: AISource): string => {
  const labels: Record<AISource, string> = {
    ai: 'AI 生成',
    fallback: '備援',
    disabled: '已停用',
    rate_limited: '超過速率限制',
  };
  return labels[source] || source;
};

/**
 * 取得 AI 來源的顏色
 */
export const getAISourceColor = (source: AISource): string => {
  const colors: Record<AISource, string> = {
    ai: 'success',
    fallback: 'warning',
    disabled: 'default',
    rate_limited: 'error',
  };
  return colors[source] || 'default';
};

// ============================================================================
// 配置同步狀態
// ============================================================================

let _serverConfig: typeof AI_CONFIG | null = null;
let _configLoaded = false;

/**
 * 從後端同步 AI 配置
 * 用於實現 Feature Flag 模式
 */
export const syncAIConfigFromServer = async (): Promise<boolean> => {
  try {
    // 動態導入避免循環依賴
    const { aiApi } = await import('../api/aiApi');
    const serverConfig = await aiApi.getConfig();

    if (serverConfig) {
      // 合併後端配置到本地配置
      _serverConfig = {
        ...AI_CONFIG,
        cache: {
          ...AI_CONFIG.cache,
          enabled: serverConfig.cache.enabled,
          ttlSummary: serverConfig.cache.ttl_summary,
          ttlClassify: serverConfig.cache.ttl_classify,
          ttlKeywords: serverConfig.cache.ttl_keywords,
        },
        rateLimit: {
          maxRequests: serverConfig.rate_limit.max_requests,
          windowSeconds: serverConfig.rate_limit.window_seconds,
        },
        classify: {
          ...AI_CONFIG.classify,
          confidenceThreshold: serverConfig.features.classify.confidence_threshold,
        },
        agencyMatch: {
          ...AI_CONFIG.agencyMatch,
          scoreThreshold: serverConfig.features.agency_match.score_threshold,
          maxAlternatives: serverConfig.features.agency_match.max_alternatives,
        },
      };
      _configLoaded = true;
      return true;
    }
    return false;
  } catch {
    return false;
  }
};

/**
 * 取得目前的 AI 配置
 * 優先使用後端同步的配置，否則使用本地預設
 */
export const getAIConfig = (): typeof AI_CONFIG => {
  return _serverConfig || AI_CONFIG;
};

/**
 * 檢查配置是否已從後端載入
 */
export const isConfigLoaded = (): boolean => {
  return _configLoaded;
};

export default AI_CONFIG;
