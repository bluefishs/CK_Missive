# AI 功能開發規範

> **版本**: 1.0.0
> **建立日期**: 2026-02-05
> **觸發關鍵字**: AI, Groq, Ollama, 語意, 摘要, 分類
> **適用範圍**: AI 相關功能開發與維護

---

## 架構概述

CK_Missive 採用混合 AI 架構：

```
用戶請求
    ↓
┌─────────────────┐
│   RateLimiter   │ ← 30 req/min (Groq 免費方案)
└────────┬────────┘
         ↓
┌─────────────────┐
│   SimpleCache   │ ← 記憶體快取 (TTL 1 小時)
└────────┬────────┘
         ↓
┌─────────────────┐     ┌─────────────────┐
│   Groq API      │ ──→ │    Ollama       │ ← 自動備援
│   (主要)        │  失敗 │    (本地)        │
└─────────────────┘     └─────────────────┘
```

---

## 核心元件

### 後端

| 元件 | 位置 | 說明 |
|------|------|------|
| `AIConfig` | `app/services/ai/ai_config.py` | AI 配置管理 |
| `AIConnector` | `app/core/ai_connector.py` | 混合 AI 連接器 |
| `DocumentAIService` | `app/services/ai/document_ai_service.py` | 公文 AI 服務 |
| `RateLimiter` | `app/services/ai/base_ai_service.py` | 速率限制器 |
| `SimpleCache` | `app/services/ai/base_ai_service.py` | 記憶體快取 |

### 前端

| 元件 | 位置 | 說明 |
|------|------|------|
| `aiApi` | `src/api/aiApi.ts` | AI API 服務 |
| `AI_CONFIG` | `src/config/aiConfig.ts` | AI 前端配置 |
| `AIAssistantButton` | `src/components/ai/` | AI 浮動按鈕 |

---

## 開發規範

### 1. 所有 AI 呼叫必須經過 RateLimiter

```python
# ✅ 正確 - 使用 RateLimiter
async def generate_summary(self, ...):
    if not await self.rate_limiter.acquire():
        return {"summary": "", "source": "rate_limited"}
    # 執行 AI 呼叫

# ❌ 禁止 - 直接呼叫
async def generate_summary(self, ...):
    return await self.ai_connector.chat_completion(...)
```

### 2. AI 結果必須快取

```python
# ✅ 正確 - 檢查快取
cache_key = f"summary:{hash(content)}"
cached = await self.cache.get(cache_key)
if cached:
    return cached

result = await self._generate(...)
await self.cache.set(cache_key, result, ttl=3600)
return result
```

### 3. 必須實作降級策略

```python
# ✅ 正確 - 完整的降級流程
async def generate_summary(self, subject: str) -> dict:
    # 1. 檢查速率限制
    if not await self.rate_limiter.acquire():
        return self._fallback_summary(subject)

    # 2. 檢查快取
    cached = await self.cache.get(cache_key)
    if cached:
        return cached

    # 3. 嘗試 AI 生成
    try:
        result = await self._generate_with_ai(subject)
        return result
    except Exception as e:
        # 4. 降級到預設回應
        return self._fallback_summary(subject)
```

### 4. 回應必須包含來源標識

```python
# ✅ 正確 - 明確標識來源
return {
    "summary": "...",
    "confidence": 0.95,
    "source": "ai"  # ai | fallback | rate_limited | disabled
}
```

---

## API 端點規範

### 端點列表

| 端點 | 方法 | 說明 |
|------|------|------|
| `/ai/document/summary` | POST | 生成公文摘要 |
| `/ai/document/classify` | POST | 分類建議 |
| `/ai/document/keywords` | POST | 關鍵字提取 |
| `/ai/agency/match` | POST | 機關匹配 |
| `/ai/health` | GET | 健康檢查 |
| `/ai/config` | GET | 取得配置 |

### 回應格式

```json
{
  "result": "...",
  "confidence": 0.95,
  "source": "ai",
  "error": null
}
```

---

## 環境變數

```bash
# Groq API (主要)
GROQ_API_KEY=gsk_...          # API 金鑰
AI_ENABLED=true               # 功能開關
AI_DEFAULT_MODEL=llama-3.3-70b-versatile

# Ollama (備援)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# 速率限制
AI_RATE_LIMIT_REQUESTS=30     # 請求數
AI_RATE_LIMIT_WINDOW=60       # 時間窗口 (秒)

# 快取
AI_CACHE_ENABLED=true
AI_CACHE_TTL_SUMMARY=3600     # 摘要快取 TTL
AI_CACHE_TTL_CLASSIFY=3600    # 分類快取 TTL
AI_CACHE_TTL_KEYWORDS=3600    # 關鍵字快取 TTL
```

---

## 錯誤處理

### 錯誤類型

| 錯誤 | 處理方式 |
|------|----------|
| API 逾時 | 自動切換到 Ollama |
| 速率限制 | 返回 `rate_limited` 狀態 |
| 服務不可用 | 返回降級回應 |
| 無效輸入 | 返回 400 錯誤 |

### 錯誤回應格式

```json
{
  "detail": "AI 服務暫時不可用",
  "source": "fallback",
  "error_code": "AI_SERVICE_UNAVAILABLE"
}
```

---

## 測試要求

### 單元測試

```python
# 必須測試的情境
- AI 正常回應
- 速率限制觸發
- 快取命中
- 服務降級
- 錯誤處理
```

### 整合測試

```python
# 必須驗證
- Groq API 連接 (需要 API key)
- Ollama 備援切換
- 端點回應格式
```

---

## 前端整合

### 使用 AI API

```typescript
import { aiApi } from '../api/aiApi';

// 生成摘要
const result = await aiApi.generateSummary({
  subject: '公文主旨',
  content: '公文內容',
  max_length: 100,
});

if (result.source === 'rate_limited') {
  message.warning('AI 服務繁忙，請稍後再試');
}
```

### 配置同步

```typescript
import { syncAIConfigFromServer, getAIConfig } from '../config/aiConfig';

// 應用程式啟動時同步配置
await syncAIConfigFromServer();

// 取得配置
const config = getAIConfig();
```

---

## 最佳實踐

1. **開發環境**: 優先使用 Ollama，避免消耗 Groq 額度
2. **生產環境**: 主要依賴 Groq，Ollama 作為備援
3. **測試**: Mock AI 服務，避免依賴外部 API
4. **監控**: 追蹤 AI 呼叫次數與成功率

---

## 相關文件

| 文件 | 說明 |
|------|------|
| `docs/OLLAMA_SETUP_GUIDE.md` | Ollama 部署指南 |
| `scripts/check-ollama.ps1` | Ollama 健康檢查腳本 |
| `.env.example` | 環境變數範例 |
