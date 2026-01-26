# AI Model Integration Patterns

> **版本**: 1.0.0
> **適用**: AI 整合專案
> **觸發**: AI 模型, LLM 整合, Claude API, OpenAI

---

## 概述

本 Skill 定義 AI 模型整合的架構模式與最佳實踐。

---

## 架構模式

### 1. 統一 AI 服務層

```
┌─────────────────────────────────────────┐
│             Application Layer            │
├─────────────────────────────────────────┤
│           AI Service Facade              │
│  ┌─────────┬─────────┬─────────┐       │
│  │ Claude  │ OpenAI  │ Local   │       │
│  │ Adapter │ Adapter │ Adapter │       │
│  └─────────┴─────────┴─────────┘       │
├─────────────────────────────────────────┤
│         Provider Abstraction             │
└─────────────────────────────────────────┘
```

### 2. 服務介面定義

```typescript
interface AIService {
  // 文字生成
  generate(prompt: string, options?: GenerateOptions): Promise<string>;

  // 串流生成
  stream(prompt: string, options?: StreamOptions): AsyncIterable<string>;

  // 嵌入向量
  embed(text: string): Promise<number[]>;

  // 對話
  chat(messages: Message[], options?: ChatOptions): Promise<Message>;
}
```

### 3. 配置管理

```typescript
interface AIConfig {
  provider: 'claude' | 'openai' | 'local';
  model: string;
  apiKey?: string;
  baseUrl?: string;
  maxTokens: number;
  temperature: number;
  timeout: number;
  retryConfig: RetryConfig;
}
```

---

## 實作範例

### Claude 整合

```typescript
class ClaudeAdapter implements AIService {
  private client: Anthropic;

  constructor(config: AIConfig) {
    this.client = new Anthropic({
      apiKey: config.apiKey,
    });
  }

  async generate(prompt: string, options?: GenerateOptions): Promise<string> {
    const response = await this.client.messages.create({
      model: options?.model || 'claude-3-sonnet-20240229',
      max_tokens: options?.maxTokens || 1024,
      messages: [{ role: 'user', content: prompt }],
    });

    return response.content[0].text;
  }
}
```

### 錯誤處理

```typescript
class AIError extends Error {
  constructor(
    message: string,
    public code: string,
    public provider: string,
    public retryable: boolean
  ) {
    super(message);
  }
}

// 重試邏輯
async function withRetry<T>(
  fn: () => Promise<T>,
  config: RetryConfig
): Promise<T> {
  let lastError: Error;

  for (let i = 0; i < config.maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      if (!isRetryable(error)) throw error;
      await delay(config.backoff * Math.pow(2, i));
    }
  }

  throw lastError;
}
```

---

## 最佳實踐

### 1. 請求限制
- 實作 rate limiting
- 使用請求佇列
- 監控 token 使用量

### 2. 快取策略
- 快取相同提示的回應
- 設定合理的 TTL
- 考慮語義快取

### 3. 成本控制
- 追蹤每次請求成本
- 設定預算警報
- 選擇適當的模型

---

## 檢查清單

- [ ] API 金鑰安全存儲
- [ ] 錯誤處理完整
- [ ] 重試機制實作
- [ ] 超時設定合理
- [ ] 日誌記錄完整

---

*版本：1.0.0 | 適用領域：AI 整合專案*
