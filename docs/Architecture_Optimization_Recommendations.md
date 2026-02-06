# CK_Missive 架構優化建議

> **版本**: 2.0.0
> **建立日期**: 2026-02-06
> **最後更新**: 2026-02-06 (v13.0 全面架構檢視)
> **狀態**: 建議中 (待逐步實施)

---

## 目錄

1. [現況評估總覽](#1-現況評估總覽)
2. [響應式設計優化](#2-響應式設計優化)
3. [AI 助理 UI 架構優化](#3-ai-助理-ui-架構優化)
4. [AI 服務後端架構優化](#4-ai-服務後端架構優化)
5. [服務層遷移路線圖](#5-服務層遷移路線圖)
6. [實施優先級與路線圖](#6-實施優先級與路線圖)

---

## 1. 現況評估總覽

### 1.1 各模組成熟度

| 模組 | 當前評分 | 目標評分 | 關鍵缺口 |
|------|----------|----------|----------|
| 響應式設計 | 6.5/10 | 8.5/10 | AI 面板固定尺寸、硬編碼 px 寬度 |
| AI 助理 UI | 7.5/10 | 9.0/10 | 面板不響應、配置未自動同步 |
| AI 後端服務 | 8.3/10 | 9.5/10 | 快取非線程安全、統計非持久化 |
| 服務層架構 | 8.5/10 | 9.5/10 | Singleton 服務尚未全部遷移 |

### 1.2 v13.0 已完成項目

| 項目 | 說明 |
|------|------|
| GIN trigram 索引 | 新增 content, assignee, agency_short_name, agency_code 共 4 個索引 |
| 連線池調優 | pool_size=10, max_overflow=20 (容量 +100%) |
| PostgreSQL 配置 | shared_buffers=512MB, work_mem=16MB, random_page_cost=1.1 |
| Prompt 外部化 | 5 組模板移至 prompts.yaml |
| 同義詞擴展 | 53 組同義詞字典 + _post_process_intent() |
| AI 使用統計 | POST /ai/stats 端點 + 類別層級追蹤 |
| 全端點 POST 化 | AI 模組 10 個端點全部改為 POST |
| N+1 預載入 | 公文附件 + 專案人員 selectinload |
| similarity 排序 | pg_trgm similarity() 相關性排序 |

---

## 2. 響應式設計優化

### 2.1 現況問題

**問題 A: AI 助手面板固定尺寸**

```tsx
// 目前: 固定 320x400px，小螢幕可能超出視窗
width: 320,
height: isMinimized ? 'auto' : 400,
```

**問題 B: NaturalSearchPanel 固定高度**

```tsx
// 目前: height 由 prop 傳入但預設為固定 280px
<NaturalSearchPanel height={280} />
```

**問題 C: 搜尋結果項附件名稱截斷寬度固定**

```tsx
// 目前: maxWidth: 150 不響應螢幕寬度
<Text ellipsis style={{ fontSize: 12, maxWidth: 150 }}>
```

### 2.2 建議方案

#### A. AI 面板響應式尺寸

```tsx
// 建議: 使用 CSS clamp() 函數
const panelWidth = `clamp(280px, 90vw, 400px)`;
const panelHeight = `clamp(300px, 60vh, 500px)`;

// 或搭配 useResponsive Hook
const { isMobile } = useResponsive();
const panelWidth = isMobile ? 'calc(100vw - 32px)' : 320;
const panelHeight = isMobile ? 'calc(100vh - 120px)' : 400;
```

**手機版行為**:
- 面板佔滿螢幕寬度 (左右各留 16px margin)
- 高度佔視窗 80% (底部保留返回操作空間)
- 拖曳功能在手機版停用 (改為全螢幕覆蓋)
- 浮動按鈕縮小至 48x48px

#### B. NaturalSearchPanel 彈性高度

```tsx
// 建議: 使用 flex 佈局取代固定 height
<NaturalSearchPanel
  style={{ flex: 1, minHeight: 200 }}
  // 移除固定 height prop，改為繼承容器高度
/>
```

#### C. 統一 RWD 常數

```typescript
// 建議新增: frontend/src/constants/responsive.ts
export const AI_PANEL = {
  width: { mobile: 'calc(100vw - 32px)', tablet: 320, desktop: 360 },
  height: { mobile: 'calc(100vh - 120px)', tablet: 400, desktop: 450 },
  buttonSize: { mobile: 48, desktop: 56 },
  buttonPosition: { mobile: { right: 16, bottom: 16 }, desktop: { right: 24, bottom: 24 } },
} as const;
```

### 2.3 待優化元件清單

| 元件 | 問題 | 優先級 | 工作量 |
|------|------|--------|--------|
| `AIAssistantButton.tsx` | 面板 320x400 固定 | 高 | 2h |
| `NaturalSearchPanel.tsx` | height=280 固定 | 高 | 1h |
| `AISummaryPanel.tsx` | maxLength 配置未響應 | 中 | 1h |
| `AIClassifyPanel.tsx` | 面板內容未響應 | 中 | 1h |
| `ReportsPage.tsx` | RWD 尚未完成 | 低 | 3h |

### 2.4 拖曳機制優化

```tsx
// 目前: 邊界計算使用固定面板尺寸
const newRight = Math.max(0, Math.min(window.innerWidth - 320, ...));
const newBottom = Math.max(0, Math.min(window.innerHeight - 400, ...));

// 建議: 動態計算面板實際尺寸
const panelRef = useRef<HTMLDivElement>(null);
const handleDragMove = useCallback((e: MouseEvent) => {
  const rect = panelRef.current?.getBoundingClientRect();
  const panelW = rect?.width ?? 320;
  const panelH = rect?.height ?? 400;
  const newRight = Math.max(0, Math.min(window.innerWidth - panelW, ...));
  const newBottom = Math.max(0, Math.min(window.innerHeight - panelH, ...));
  setPosition({ right: newRight, bottom: newBottom });
}, [isDragging]);
```

---

## 3. AI 助理 UI 架構優化

### 3.1 現況分析

| 元件 | 版本 | 行數 | 職責 |
|------|------|------|------|
| `AIAssistantButton.tsx` | 2.1.0 | 442 | Portal 渲染、拖曳、Tab 切換、健康檢查 |
| `NaturalSearchPanel.tsx` | 1.0.0 | 454 | 搜尋、結果顯示、附件下載/預覽 |
| `AISummaryPanel.tsx` | - | ~150 | 摘要生成 |
| `AIClassifyPanel.tsx` | - | ~150 | 分類建議 |

**評估**: `AIAssistantButton` 職責合理 (442 行含 Portal 邏輯)，暫不需拆分。`NaturalSearchPanel` 搜尋+結果+附件職責較多，建議後續提取 `SearchResultItem` 子元件。

### 3.2 配置自動同步

**現況**: `aiConfig.ts` 提供 `syncAIConfigFromServer()`，但需手動呼叫。

```typescript
// 建議: 在 App 啟動時自動同步
// frontend/src/App.tsx 或 providers/AppProvider.tsx
useEffect(() => {
  syncAIConfigFromServer().catch(() => {
    // 靜默失敗，使用本地預設配置
    console.warn('AI 配置同步失敗，使用本地預設');
  });
}, []);
```

### 3.3 搜尋結果分類群組

**現況**: 搜尋結果以平鋪列表顯示。

**建議**: 當結果數量 > 10 時，按 category (收文/發文) 分組顯示。

```tsx
// 建議: 分組顯示搜尋結果
const groupedResults = useMemo(() => {
  if (results.length <= 10) return null;
  return {
    received: results.filter(r => r.category === '收文'),
    sent: results.filter(r => r.category === '發文'),
    other: results.filter(r => r.category !== '收文' && r.category !== '發文'),
  };
}, [results]);
```

### 3.4 搜尋體驗增強 (建議項)

| 功能 | 說明 | 優先級 |
|------|------|--------|
| 搜尋歷史 | localStorage 儲存最近 10 筆搜尋 | 中 |
| 快捷鍵 | Ctrl+K 開啟/關閉 AI 面板 | 低 |
| 搜尋結果快取 | 相同查詢 5 分鐘內不重複請求 | 中 |
| 結果高亮 | 匹配關鍵字在結果中高亮顯示 | 低 |

---

## 4. AI 服務後端架構優化

### 4.1 SimpleCache 線程安全

**現況問題**:
- `SimpleCache` 使用普通 `dict`，在 async 環境下可能有併發問題
- uvicorn 使用 asyncio 事件循環，同一時刻只有一個協程執行，所以**目前不會產生真正的 race condition**
- 但如果未來切換到 multi-worker 模式，每個 worker 有獨立的快取實例，等於快取失效

**風險等級**: 低 (目前 single worker)

**長期建議**:

```python
# 方案 A: asyncio.Lock (最小改動，適合 single worker)
import asyncio

class SimpleCache:
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            # ... existing logic
            pass

    async def set(self, key: str, value: Any, ttl: int) -> None:
        async with self._lock:
            # ... existing logic
            pass

# 方案 B: Redis 快取 (適合 multi-worker 部署)
# 專案已有 Redis 服務，可直接使用
import redis.asyncio as redis

class RedisCache:
    def __init__(self, redis_url: str = "redis://redis:6379/1"):
        self._redis = redis.from_url(redis_url)

    async def get(self, key: str) -> Optional[str]:
        return await self._redis.get(f"ai:{key}")

    async def set(self, key: str, value: str, ttl: int) -> None:
        await self._redis.setex(f"ai:{key}", ttl, value)
```

**建議**: 短期維持現狀 (single worker 下 asyncio 本身保證串行)，中期遷移到 Redis 快取以支援 multi-worker。

### 4.2 統計資料持久化

**現況問題**:
- `_stats` 為類別變數 (class-level dict)，服務重啟後歸零
- 生產環境的使用統計無法跨部署追蹤

**建議**: 使用 Redis 持久化統計

```python
# 方案: Redis HINCRBY 原子操作
class AIStatsManager:
    """AI 使用統計管理器 (Redis 持久化)"""

    PREFIX = "ai:stats"

    def __init__(self, redis_client):
        self._redis = redis_client

    async def record(self, feature: str, *, cache_hit=False, error=False, latency_ms=0.0):
        pipe = self._redis.pipeline()
        pipe.hincrby(f"{self.PREFIX}:total", "requests", 1)
        pipe.hincrby(f"{self.PREFIX}:feature:{feature}", "count", 1)
        if cache_hit:
            pipe.hincrby(f"{self.PREFIX}:feature:{feature}", "cache_hits", 1)
        if error:
            pipe.hincrby(f"{self.PREFIX}:feature:{feature}", "errors", 1)
        pipe.hincrbyfloat(f"{self.PREFIX}:feature:{feature}", "latency_ms", latency_ms)
        await pipe.execute()

    async def get_stats(self) -> Dict[str, Any]:
        # 從 Redis 讀取所有統計
        ...

    async def reset(self):
        keys = await self._redis.keys(f"{self.PREFIX}:*")
        if keys:
            await self._redis.delete(*keys)
```

**優先級**: 中 (目前 in-memory 統計已能滿足開發需求)

### 4.3 AI 回應輸出驗證

**現況問題**:
- `_call_ai_with_cache()` 直接返回 AI 原始字串，未驗證格式
- `document_ai_service.py` 各方法自行 try/except 解析 JSON
- 若 AI 返回非預期格式，錯誤訊息不夠明確

**建議**: 新增統一的回應驗證層

```python
# 建議: 在 BaseAIService 新增驗證方法
class BaseAIService:
    async def _call_ai_with_validation(
        self,
        cache_key: str,
        ttl: int,
        system_prompt: str,
        user_content: str,
        response_schema: Optional[Type[BaseModel]] = None,
        **kwargs,
    ) -> Union[str, Dict]:
        """呼叫 AI 並驗證回應格式"""
        raw = await self._call_ai_with_cache(
            cache_key, ttl, system_prompt, user_content, **kwargs
        )

        if response_schema is None:
            return raw

        # 嘗試 JSON 解析 + Pydantic 驗證
        try:
            data = json.loads(raw)
            validated = response_schema.model_validate(data)
            return validated.model_dump()
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"AI 回應格式驗證失敗: {e}")
            # 返回原始字串，交由呼叫端處理
            return raw
```

**優先級**: 中 (可大幅減少各服務方法中的重複解析程式碼)

### 4.4 Prompt 載入容錯

**現況**: `DocumentAIService.__init__()` 載入 `prompts.yaml`，若檔案缺失或格式錯誤會直接拋異常。

**建議**: 新增 fallback 預設值

```python
class DocumentAIService(BaseAIService):
    # 內建預設 prompt (當 YAML 載入失敗時使用)
    _DEFAULT_PROMPTS = {
        "summary": {
            "system": "你是一個文件摘要助手，請用繁體中文生成摘要。",
        },
        "classify": {
            "system": "你是一個文件分類助手，請分析文件類型。",
        },
        # ...
    }

    def _load_prompts(self) -> Dict:
        try:
            yaml_path = Path(__file__).parent / "prompts.yaml"
            with open(yaml_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Prompt YAML 載入失敗，使用預設值: {e}")
            return self._DEFAULT_PROMPTS
```

**優先級**: 高 (防止 YAML 損壞導致整個 AI 服務不可用)

---

## 5. 服務層遷移路線圖

### 5.1 Singleton -> 工廠模式遷移現況

| 服務 | 模式 | 狀態 | 遷移目標 |
|------|------|------|----------|
| `VendorService` | Singleton (deprecated) | 待遷移 | 工廠模式 |
| `AgencyService` | Singleton (deprecated) | 待遷移 | 工廠模式 |
| `ProjectService` | Singleton (deprecated) | 待遷移 | 工廠模式 |
| `DocumentService` | 工廠模式 | 完成 | - |
| `DispatchOrderService` | 工廠模式 | 完成 | - |
| `DocumentAIService` | 無狀態 Singleton | 合理 | 維持現狀 |

### 5.2 遷移步驟 (每個服務)

```
1. 建立新版 Service (工廠模式)
   |- __init__(self, db: AsyncSession)
   |- 整合對應 Repository
   |- 移除方法中的 db 參數

2. 更新 dependencies.py
   |- 新增 get_service_with_db(NewService) 工廠函數

3. 逐一更新 API 端點
   |- 移除 db: Depends(get_async_db)
   |- 改用新版 Service Depends

4. 更新/新增測試

5. 移除舊版 Service (待所有端點遷移完成)
```

### 5.3 Repository 層擴展規劃

| Repository | 狀態 | 說明 |
|------------|------|------|
| `DocumentRepository` | 完成 | filter_documents, get_statistics |
| `ProjectRepository` | 完成 | filter_projects, check_user_access |
| `AgencyRepository` | 完成 | match_agency, suggest_agencies |
| `VendorRepository` | 完成 | CRUD + 搜尋 |
| `UserRepository` | 完成 | 基礎 CRUD |
| `ConfigurationRepository` | 完成 | 系統配置 CRUD |
| `NavigationRepository` | 完成 | 導航項目管理 |
| `CalendarEventRepository` | 待建立 | 行事曆事件查詢、提醒管理 |
| `NotificationRepository` | 待建立 | 通知查詢、已讀標記 |
| `AuditLogRepository` | 待建立 | 審計日誌查詢 (目前無 ORM 模型) |

### 5.4 直接 ORM 查詢端點 (長期遷移目標)

以下端點仍有直接 ORM 查詢，屬長期遷移目標：

| 端點模組 | 直接 ORM 查詢數 | 優先級 |
|----------|-----------------|--------|
| `documents/` | 5 | 高 (核心模組) |
| `taoyuan_dispatch/` | 6 | 中 |
| `document_calendar/` | 4 | 中 |
| `health.py` | 3 | 低 (系統端點) |
| `navigation.py` | 3 | 低 |
| 其他 | 6 | 低 |

---

## 6. 實施優先級與路線圖

### 6.1 短期 (1-2 週)

| # | 項目 | 影響 | 工作量 |
|---|------|------|--------|
| S1 | Prompt 載入容錯 (4.4) | 高 - 防止服務不可用 | 1h |
| S2 | AI 面板響應式 (2.2A) | 高 - 手機版無法使用 | 2h |
| S3 | AI 配置自動同步 (3.2) | 中 - 減少手動操作 | 0.5h |
| S4 | NaturalSearchPanel 彈性高度 (2.2B) | 中 - 改善顯示 | 1h |

### 6.2 中期 (2-4 週)

| # | 項目 | 影響 | 工作量 |
|---|------|------|--------|
| M1 | SimpleCache 遷移至 Redis (4.1) | 中 - 支援 multi-worker | 4h |
| M2 | 統計資料 Redis 持久化 (4.2) | 中 - 跨部署追蹤 | 3h |
| M3 | AI 回應驗證層 (4.3) | 中 - 減少重複程式碼 | 3h |
| M4 | VendorService 工廠遷移 (5.2) | 中 - 架構統一 | 4h |
| M5 | AgencyService 工廠遷移 (5.2) | 中 - 架構統一 | 4h |
| M6 | ProjectService 工廠遷移 (5.2) | 中 - 架構統一 | 4h |
| M7 | 搜尋歷史 + 結果快取 (3.4) | 低 - 改善體驗 | 2h |

### 6.3 長期 (1-3 月)

| # | 項目 | 影響 | 工作量 |
|---|------|------|--------|
| L1 | pgvector 語意搜尋 | 高 - 搜尋品質飛躍 | 20h |
| L2 | 27 個端點 Repository 遷移 | 中 - 架構完全統一 | 30h |
| L3 | CalendarEvent Repository | 中 - 行事曆查詢優化 | 6h |
| L4 | WebSocket 即時推送 | 中 - 即時通知 | 15h |
| L5 | AI 串流回應前端整合 | 低 - 體驗提升 | 8h |

### 6.4 不做的事項

| 項目 | 原因 |
|------|------|
| D3.js 機關關係圖 | 需引入新依賴，ROI 低 |
| PWA 支援 | 長期項目，現階段無需求 |
| 甘特圖 | 需專門套件，另開 session |
| 微服務拆分 | 目前單體架構足夠，過早拆分增加複雜度 |
| GraphQL | REST API 已滿足需求，切換成本高 |

---

## 附錄 A: AI 助理 UI 架構圖

```
Portal Container (#ai-assistant-portal)
z-index: 9999, position: fixed

  AIAssistantButton.tsx (v2.1.0)
  |
  +-- FloatButton (56x56px, gradient bg, fixed right:24 bottom:24)
  |
  +-- Card Panel (320x400px, 需改為響應式)
      |
      +-- [Tab: Search] NaturalSearchPanel (height:280, 需改為 flex)
      |   +-- Search Input (自然語言)
      |   +-- Intent Tags (AI 解析結果)
      |   +-- Result List (公文列表+附件)
      |   +-- Load More Button
      |
      +-- [Tab: AI Tools]
          +-- Service Status (Groq/Ollama Tags)
          +-- Rate Limit Info
          +-- Feature Buttons (摘要/分類/關鍵字)
          +-- Health Check Button
```

## 附錄 B: AI 後端服務架構圖

```
                    API Layer
                       |
            +----------+----------+
            |          |          |
     document_ai.py  ai_stats.py  (future endpoints)
            |          |
            +----------+----------+
                       |
              DocumentAIService (v2.2.0)
              +-- prompts.yaml (5 templates)
              +-- synonyms.yaml (53 groups)
              +-- _post_process_intent()
              |   +-- 同義詞擴展
              |   +-- 縮寫轉全稱
              |   +-- 低信心度策略
              +-- extends BaseAIService
                         |
                  +------+------+
                  |      |      |
            RateLimiter  |  SimpleCache
            30 req/min   |  LRU 1000, TTL 1h
                         |
                   AIConnector
                   +-- Groq API (主要)
                   +-- Ollama (備援)
                   +-- Fallback (預設回應)
                         |
                   DocumentQueryBuilder
                   +-- with_keywords_full()
                   +-- with_relevance_order()
                   |   +-- pg_trgm similarity()
                   +-- paginate()
```

## 附錄 C: 服務層遷移進度

```
Singleton (deprecated)          Factory (推薦)
+-------------------+          +-------------------+
| VendorService     | --待遷移-> | VendorService     |
| AgencyService     | --待遷移-> | AgencyService     |
| ProjectService    | --待遷移-> | ProjectService    |
+-------------------+          +-------------------+

                    已完成
                    +--------------------------+
                    | DocumentService          | OK
                    | DispatchOrderService     | OK
                    | CalendarIntegrationSvc   | OK
                    | DocumentAIService        | OK (無狀態)
                    +--------------------------+
```

---

*文件維護: Claude Code Assistant*
*版本: 2.0.0*
*最後更新: 2026-02-06*
