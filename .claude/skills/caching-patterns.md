---
trigger_keywords: [快取, cache, Redis, TTL, stale-while-revalidate, React Query, SimpleCache, 快取策略]
version: "1.0.0"
date: "2026-02-21"
---

# 快取策略規範

## 三層快取架構

| 層級 | 技術 | TTL | 用途 |
|------|------|-----|------|
| L1 | React Query | 5min stale / 30min gc | 前端 API 快取 |
| L2 | Redis | 1h | 後端 AI/運算結果快取 |
| L3 | SimpleCache (記憶體) | 1h | Redis 降級備援 |

## L1: React Query (前端)

### 基礎配置

```typescript
// providers/QueryProvider.tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,      // 5 分鐘後標記為 stale
      gcTime: 30 * 60 * 1000,         // 30 分鐘後回收
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});
```

### stale-while-revalidate 模式

```typescript
// hooks/useDocuments.ts
export function useDocuments(params: DocumentListParams) {
  return useQuery({
    queryKey: ['documents', params],
    queryFn: () => documentApi.getList(params),
    staleTime: 5 * 60 * 1000,        // 5 分鐘內直接用快取
    placeholderData: keepPreviousData, // 分頁切換保留舊資料
  });
}
```

### 快取失效策略

```typescript
// 建立/更新/刪除後失效
const createMutation = useMutation({
  mutationFn: documentApi.create,
  onSuccess: () => {
    // 精確失效相關查詢
    queryClient.invalidateQueries({ queryKey: ['documents'] });
    // 不失效統計（除非統計會變）
  },
});

// 樂觀更新（即時 UI 反應）
const updateMutation = useMutation({
  mutationFn: documentApi.update,
  onMutate: async (newData) => {
    await queryClient.cancelQueries({ queryKey: ['documents', newData.id] });
    const previous = queryClient.getQueryData(['documents', newData.id]);
    queryClient.setQueryData(['documents', newData.id], newData);
    return { previous };
  },
  onError: (err, newData, context) => {
    queryClient.setQueryData(['documents', newData.id], context?.previous);
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: ['documents'] });
  },
});
```

### Query Key 規範

```typescript
// 階層式 key 設計
['documents']                    // 所有公文查詢
['documents', 'list', params]    // 公文列表（含篩選）
['documents', id]                // 單一公文詳情
['documents', id, 'attachments'] // 公文附件
['documents', 'stats']           // 公文統計

// invalidateQueries 會失效所有子 key
queryClient.invalidateQueries({ queryKey: ['documents'] }); // 失效全部
```

## L2: Redis 快取 (後端)

### 連線管理

```python
# backend/app/core/redis_client.py
import redis.asyncio as redis

_redis_client: redis.Redis | None = None

async def get_redis() -> redis.Redis | None:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=5,
                decode_responses=True,
            )
            await _redis_client.ping()
        except Exception:
            logger.warning("Redis 連線失敗，降級至記憶體快取")
            _redis_client = None
    return _redis_client
```

### Graceful Fallback 模式

```python
# ⚠️ Redis 操作永遠不應阻斷核心業務流程

class RedisCache:
    def __init__(self, prefix: str = "cache"):
        self.prefix = prefix
        self._fallback = SimpleCache()  # 記憶體備援

    async def get(self, key: str) -> str | None:
        r = await get_redis()
        if r:
            try:
                return await r.get(f"{self.prefix}:{key}")
            except Exception:
                pass
        return self._fallback.get(key)

    async def set(self, key: str, value: str, ttl: int = 3600) -> None:
        r = await get_redis()
        if r:
            try:
                await r.set(f"{self.prefix}:{key}", value, ex=ttl)
                return
            except Exception:
                pass
        self._fallback.set(key, value, ttl)
```

### AI 快取策略

```python
# TTL 配置 (from ai_config.py)
AI_CACHE_TTL_SUMMARY  = 3600   # 摘要 1 小時
AI_CACHE_TTL_CLASSIFY = 3600   # 分類 1 小時
AI_CACHE_TTL_KEYWORDS = 3600   # 關鍵字 1 小時

# Cache Key 設計
cache_key = f"ai:summary:{doc_id}:{hash(content[:500])}"
```

### 統計持久化

```python
# 使用 Redis HINCRBY 原子操作
async def increment_stat(self, key: str, field: str, amount: int = 1):
    r = await get_redis()
    if r:
        await r.hincrby(f"ai:stats:{key}", field, amount)
```

## L3: SimpleCache (記憶體備援)

### LRU 淘汰機制

```python
class SimpleCache:
    def __init__(self, max_size: int = 1000):
        self._cache: dict[str, tuple[Any, float]] = {}
        self._max_size = max_size

    def get(self, key: str) -> Any | None:
        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                return value
            del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        # LRU 淘汰：超過上限時移除最舊的 20%
        if len(self._cache) >= self._max_size:
            sorted_keys = sorted(
                self._cache, key=lambda k: self._cache[k][1]
            )
            for k in sorted_keys[:self._max_size // 5]:
                del self._cache[k]
        self._cache[key] = (value, time.time() + ttl)
```

## 快取失效策略

### 主動失效 (Write-Through)

```python
# 更新資料時同步清除快取
async def update_document(self, doc_id: int, data: dict):
    result = await self.repository.update(doc_id, data)

    # 清除相關快取
    cache = RedisCache("ai")
    await cache.delete(f"summary:{doc_id}")
    await cache.delete(f"classify:{doc_id}")

    return result
```

### 被動失效 (TTL)

- 短 TTL（5 分鐘）：頻繁變動的列表資料
- 中 TTL（1 小時）：AI 分析結果
- 長 TTL（24 小時）：靜態配置、機關列表

### 不快取的場景

- 使用者認證/權限資料
- 即時統計（dashboard 計數器）
- 含有個人資料的查詢結果

## CK_Missive 現有實作

| 快取 | 位置 | 說明 |
|------|------|------|
| React Query | `providers/QueryProvider.tsx` | 前端 API 快取 |
| Redis AI Cache | `services/ai/base_ai_service.py` | AI 結果快取 + graceful fallback |
| SimpleCache | `services/ai/base_ai_service.py` | Redis 降級備援 |
| SearchCache | `components/ai/NaturalSearchPanel.tsx` | 搜尋結果前端快取 (5min TTL) |
| RequestThrottler | `api/client.ts` | 請求熔斷器 (防重複請求) |
