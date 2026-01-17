# /performance-check - 效能檢查

> **版本**: 1.0.0
> **建立日期**: 2026-01-15
> **用途**: 系統效能診斷與優化建議

---

## 執行項目

執行此指令時，請依序完成以下效能檢查：

### 1. N+1 查詢偵測

**後端檢查**:
```python
# 搜尋可能的 N+1 查詢模式
# 在 for 迴圈中執行資料庫查詢
grep -rn "for.*in.*:" backend/app/services/ --include="*.py" -A 5 | grep -E "db\.|session\.|query"
```

**正確模式**:
```python
# ✅ 使用 joinedload 預載入關聯
from sqlalchemy.orm import joinedload

query = session.query(Document).options(
    joinedload(Document.agency),
    joinedload(Document.project)
)
```

**錯誤模式**:
```python
# ❌ N+1 查詢
documents = session.query(Document).all()
for doc in documents:
    agency = session.query(Agency).get(doc.agency_id)  # 每次迴圈都查詢
```

### 2. 慢查詢識別

**資料庫層面**:
```sql
-- 檢查 PostgreSQL 慢查詢日誌
-- 在 postgresql.conf 中設定:
-- log_min_duration_statement = 1000  -- 記錄超過 1 秒的查詢
```

**應用層面**:
```python
# 檢查是否有缺少索引的查詢
# backend/app/api/endpoints/*.py
# 搜尋 filter 條件中使用的欄位
grep -rn "\.filter\(" backend/app/ --include="*.py" | grep -v "test"
```

**索引建議檢查**:
- [ ] `documents.doc_date` - 日期範圍查詢
- [ ] `documents.status` - 狀態篩選
- [ ] `documents.doc_type` - 類型篩選
- [ ] `projects.status` - 案件狀態
- [ ] `agencies.agency_name` - 機關名稱搜尋

### 3. 前端 Bundle 大小分析

```bash
# 分析前端打包大小
cd frontend && npm run build -- --report

# 或使用 vite-bundle-visualizer
npx vite-bundle-visualizer
```

**檢查項目**:
- [ ] 總 bundle 大小 < 2MB (gzipped < 500KB)
- [ ] 主要 chunk 已正確分割
- [ ] 未使用的依賴已移除
- [ ] 圖片已壓縮

**當前分割配置** (`vite.config.ts`):
```javascript
manualChunks: {
  'react-vendor': ['react', 'react-dom', 'react-router-dom'],
  'antd': ['antd', '@ant-design/icons'],
  'recharts': ['recharts'],
  'dayjs': ['dayjs'],
  'state': ['zustand', '@tanstack/react-query'],
}
```

### 4. API 回應時間監控

**健康檢查端點**:
```bash
# 測試 API 回應時間
curl -w "\nTime: %{time_total}s\n" http://localhost:8001/health

# 測試業務 API
curl -X POST -w "\nTime: %{time_total}s\n" \
  -H "Content-Type: application/json" \
  -d '{"page": 1, "limit": 20}' \
  http://localhost:8001/api/documents-enhanced/list
```

**效能基準**:
| 端點類型 | 目標回應時間 |
|---------|-------------|
| 健康檢查 | < 50ms |
| 列表查詢 (20筆) | < 200ms |
| 詳情查詢 | < 100ms |
| 統計查詢 | < 500ms |
| 匯出操作 | < 5s |

### 5. 記憶體使用檢查

**後端**:
```python
# 檢查是否有記憶體洩漏風險
# 搜尋未關閉的資源
grep -rn "open\(" backend/app/ --include="*.py" | grep -v "with "
```

**前端**:
```javascript
// 檢查 useEffect 清理函數
// 搜尋未清理的訂閱或計時器
grep -rn "useEffect" frontend/src/ --include="*.tsx" -A 10 | grep -v "return"
```

### 6. 快取效率檢查

**後端快取** (`backend/app/core/cache.py`):
- [ ] Redis 連線正常
- [ ] 快取命中率 > 80%
- [ ] TTL 設定合理

**前端快取** (TanStack Query):
```typescript
// 檢查 staleTime 和 cacheTime 設定
const { data } = useQuery({
  queryKey: ['documents'],
  queryFn: fetchDocuments,
  staleTime: 5 * 60 * 1000,  // 5 分鐘
  cacheTime: 30 * 60 * 1000, // 30 分鐘
});
```

### 7. 並發處理能力

```bash
# 簡易壓力測試
# 使用 Apache Bench 或 wrk
ab -n 100 -c 10 http://localhost:8001/health

# 或使用 Python
python -c "
import asyncio
import aiohttp
import time

async def test():
    async with aiohttp.ClientSession() as session:
        tasks = [session.get('http://localhost:8001/health') for _ in range(100)]
        start = time.time()
        await asyncio.gather(*tasks)
        print(f'100 requests in {time.time()-start:.2f}s')

asyncio.run(test())
"
```

---

## 輸出格式

執行完成後，輸出效能檢查報告：

```markdown
## 效能檢查報告 - [日期]

### 檢查結果摘要

| 項目 | 狀態 | 數值 | 建議 |
|------|------|------|------|
| N+1 查詢 | ✅/⚠️/❌ | [數量] | [建議] |
| 慢查詢 | ✅/⚠️/❌ | [數量] | [建議] |
| Bundle 大小 | ✅/⚠️/❌ | [大小] | [建議] |
| API 回應時間 | ✅/⚠️/❌ | [平均] | [建議] |
| 記憶體使用 | ✅/⚠️/❌ | [使用量] | [建議] |
| 快取效率 | ✅/⚠️/❌ | [命中率] | [建議] |

### 效能瓶頸

[列出發現的效能問題]

### 優化建議

[提供具體優化步驟]

### 優先處理項目

1. [最高優先級項目]
2. [次優先級項目]
3. ...
```

---

## 相關文件

- `docs/FILTER_OPTIMIZATION.md` - 篩選優化說明
- `docs/architecture-optimization-report.md` - 架構優化報告
- `backend/database_indexes_optimization.sql` - 資料庫索引優化

---

*此指令建議在重大功能上線前執行*
