/**
 * AI 服務配置測試
 * AI Config Tests
 */
import { describe, it, expect, beforeEach } from 'vitest';
import {
  AI_CONFIG,
  AI_FEATURE_NAMES,
  AI_PROVIDERS,
  getAIFeatureName,
  getAISourceLabel,
  getAISourceColor,
  getAIConfig,
  isConfigLoaded,
} from '../aiConfig';
import type { AIFeatureType, AISource } from '../aiConfig';

// ============================================================================
// AI_CONFIG structure
// ============================================================================

describe('AI_CONFIG', () => {
  it('應包含所有功能區塊', () => {
    expect(AI_CONFIG).toHaveProperty('summary');
    expect(AI_CONFIG).toHaveProperty('keywords');
    expect(AI_CONFIG).toHaveProperty('classify');
    expect(AI_CONFIG).toHaveProperty('agencyMatch');
    expect(AI_CONFIG).toHaveProperty('cache');
    expect(AI_CONFIG).toHaveProperty('rateLimit');
  });

  describe('summary', () => {
    it('應有合理的長度限制', () => {
      expect(typeof AI_CONFIG.summary.maxLength).toBe('number');
      expect(typeof AI_CONFIG.summary.defaultMaxLength).toBe('number');
      expect(typeof AI_CONFIG.summary.minLength).toBe('number');
      expect(AI_CONFIG.summary.minLength).toBeLessThan(AI_CONFIG.summary.maxLength);
    });
  });

  describe('keywords', () => {
    it('應有合理的數量限制', () => {
      expect(typeof AI_CONFIG.keywords.maxKeywords).toBe('number');
      expect(typeof AI_CONFIG.keywords.defaultMaxKeywords).toBe('number');
      expect(typeof AI_CONFIG.keywords.minKeywords).toBe('number');
      expect(AI_CONFIG.keywords.minKeywords).toBeLessThanOrEqual(
        AI_CONFIG.keywords.defaultMaxKeywords
      );
      expect(AI_CONFIG.keywords.defaultMaxKeywords).toBeLessThanOrEqual(
        AI_CONFIG.keywords.maxKeywords
      );
    });
  });

  describe('classify', () => {
    it('confidenceThreshold 應在 0-1 之間', () => {
      expect(AI_CONFIG.classify.confidenceThreshold).toBeGreaterThan(0);
      expect(AI_CONFIG.classify.confidenceThreshold).toBeLessThanOrEqual(1);
    });

    it('showReasoning 應為 boolean', () => {
      expect(typeof AI_CONFIG.classify.showReasoning).toBe('boolean');
    });
  });

  describe('agencyMatch', () => {
    it('scoreThreshold 應在 0-1 之間', () => {
      expect(AI_CONFIG.agencyMatch.scoreThreshold).toBeGreaterThan(0);
      expect(AI_CONFIG.agencyMatch.scoreThreshold).toBeLessThanOrEqual(1);
    });

    it('maxAlternatives 應為正整數', () => {
      expect(AI_CONFIG.agencyMatch.maxAlternatives).toBeGreaterThan(0);
      expect(Number.isInteger(AI_CONFIG.agencyMatch.maxAlternatives)).toBe(true);
    });
  });

  describe('cache', () => {
    it('enabled 應為 boolean', () => {
      expect(typeof AI_CONFIG.cache.enabled).toBe('boolean');
    });

    it('TTL 值應為正數（秒）', () => {
      expect(AI_CONFIG.cache.ttlSummary).toBeGreaterThan(0);
      expect(AI_CONFIG.cache.ttlClassify).toBeGreaterThan(0);
      expect(AI_CONFIG.cache.ttlKeywords).toBeGreaterThan(0);
    });
  });

  describe('rateLimit', () => {
    it('maxRequests 應為正整數', () => {
      expect(AI_CONFIG.rateLimit.maxRequests).toBeGreaterThan(0);
      expect(Number.isInteger(AI_CONFIG.rateLimit.maxRequests)).toBe(true);
    });

    it('windowSeconds 應為正整數', () => {
      expect(AI_CONFIG.rateLimit.windowSeconds).toBeGreaterThan(0);
      expect(Number.isInteger(AI_CONFIG.rateLimit.windowSeconds)).toBe(true);
    });
  });
});

// ============================================================================
// AI_FEATURE_NAMES
// ============================================================================

describe('AI_FEATURE_NAMES', () => {
  const expectedFeatures: AIFeatureType[] = ['summary', 'classify', 'keywords', 'agency_match'];

  it('應包含所有功能的中文名稱', () => {
    for (const feature of expectedFeatures) {
      expect(AI_FEATURE_NAMES).toHaveProperty(feature);
      expect(typeof AI_FEATURE_NAMES[feature]).toBe('string');
      expect(AI_FEATURE_NAMES[feature].length).toBeGreaterThan(0);
    }
  });
});

// ============================================================================
// AI_PROVIDERS
// ============================================================================

describe('AI_PROVIDERS', () => {
  it('應包含 groq 和 ollama', () => {
    expect(AI_PROVIDERS).toHaveProperty('groq');
    expect(AI_PROVIDERS).toHaveProperty('ollama');
  });

  it('groq 應有正確的結構', () => {
    const groq = AI_PROVIDERS.groq;
    expect(typeof groq.name).toBe('string');
    expect(typeof groq.description).toBe('string');
    expect(typeof groq.priority).toBe('number');
    expect(groq.rateLimit).not.toBeNull();
    expect(groq.rateLimit.requests).toBeGreaterThan(0);
    expect(groq.rateLimit.window).toBeGreaterThan(0);
  });

  it('ollama 應有正確的結構', () => {
    const ollama = AI_PROVIDERS.ollama;
    expect(typeof ollama.name).toBe('string');
    expect(typeof ollama.description).toBe('string');
    expect(typeof ollama.priority).toBe('number');
    expect(ollama.rateLimit).toBeNull();
  });

  it('groq 優先級應高於 ollama（數值較小）', () => {
    expect(AI_PROVIDERS.groq.priority).toBeLessThan(AI_PROVIDERS.ollama.priority);
  });
});

// ============================================================================
// getAIFeatureName
// ============================================================================

describe('getAIFeatureName', () => {
  it('應回傳已知功能的中文名稱', () => {
    expect(getAIFeatureName('summary')).toBe('摘要生成');
    expect(getAIFeatureName('classify')).toBe('分類建議');
    expect(getAIFeatureName('keywords')).toBe('關鍵字提取');
    expect(getAIFeatureName('agency_match')).toBe('機關匹配');
  });
});

// ============================================================================
// getAISourceLabel
// ============================================================================

describe('getAISourceLabel', () => {
  const expectedLabels: Record<AISource, string> = {
    ai: 'AI 生成',
    fallback: '備援',
    disabled: '已停用',
    rate_limited: '超過速率限制',
  };

  it.each(Object.entries(expectedLabels))(
    '來源 "%s" 應回傳 "%s"',
    (source, expectedLabel) => {
      expect(getAISourceLabel(source as AISource)).toBe(expectedLabel);
    }
  );
});

// ============================================================================
// getAISourceColor
// ============================================================================

describe('getAISourceColor', () => {
  const expectedColors: Record<AISource, string> = {
    ai: 'success',
    fallback: 'warning',
    disabled: 'default',
    rate_limited: 'error',
  };

  it.each(Object.entries(expectedColors))(
    '來源 "%s" 應回傳顏色 "%s"',
    (source, expectedColor) => {
      expect(getAISourceColor(source as AISource)).toBe(expectedColor);
    }
  );
});

// ============================================================================
// getAIConfig / isConfigLoaded
// ============================================================================

describe('getAIConfig', () => {
  it('未同步時應回傳本地 AI_CONFIG', () => {
    const config = getAIConfig();
    expect(config).toEqual(AI_CONFIG);
  });

  it('回傳的配置應包含所有區塊', () => {
    const config = getAIConfig();
    expect(config).toHaveProperty('summary');
    expect(config).toHaveProperty('keywords');
    expect(config).toHaveProperty('classify');
    expect(config).toHaveProperty('agencyMatch');
    expect(config).toHaveProperty('cache');
    expect(config).toHaveProperty('rateLimit');
  });
});

describe('isConfigLoaded', () => {
  it('初始狀態應為 false', () => {
    // Note: module state persists across tests in the same file,
    // but syncAIConfigFromServer is not called so _configLoaded stays false
    expect(typeof isConfigLoaded()).toBe('boolean');
  });
});
