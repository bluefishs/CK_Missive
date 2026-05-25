# CK_Missive 專案整體檢視報告

> **報告日期**: 2026-03-07
> **專案版本**: v1.79.0
> **技術棧**: FastAPI + PostgreSQL 16 + React 18.3 + TypeScript 5.9 + Ant Design
> **測試規模**: 2,782 tests (Backend 1,172 + Frontend 1,610)

---

## 總體評價

**CK_Missive 專案整體體質非常優秀**，具備嚴謹的文件規範、成熟的後端 FastAPI 非同步架構，以及前端 React 18 現代化堆疊。以下是三大改進方向的深度分析與具體建議。

| 維度 | 評分 | 說明 |
|------|------|------|
| 架構設計 | A | Service Factory + Repository + SSOT 三層分離優秀 |
| 文件規範 | B+ | 體系完整但存在版本漂移與覆蓋率追蹤缺口 |
| 後端品質 | B+ | 非同步模式正確，少量阻塞 I/O 與 Pydantic v1 殘留 |
| 前端品質 | A- | React 18 基礎紮實，缺少 Concurrent 進階特性 |
| 安全性 | A- | 無硬編碼密鑰，SQL 注入防護完善，少量 str(e) 殘留 |
| 系統效能 | B | 健康檢查與排程器存在擴展性瓶頸 |

---

## 方向一：文件規範嚴謹性

### 1.1 優勢

- **階層式文件架構**：CLAUDE.md (89 行索引) → `.claude/rules/` (9 規範) → `.claude/skills/` (24 領域知識) → `docs/` (規格文件)
- **SSOT 原則嚴格執行**：前端型別 `types/api.ts` 為唯一來源，後端 `schemas/` 為唯一 Pydantic 定義
- **強制檢查清單**：`MANDATORY_CHECKLIST.md` 涵蓋 10 類開發任務 (A-X)
- **18+ 驗證指令**：`/pre-dev-check`、`/api-check`、`/type-sync` 等自動化檢查

### 1.2 發現問題

| # | 問題 | 嚴重度 | 位置 |
|---|------|--------|------|
| D-1 | CLAUDE.md 版本標記 v1.61.0，實際已 v1.79.0（落後 11 天） | HIGH | `CLAUDE.md:5` |
| D-2 | 無 OpenAPI Schema 匯出，前端型別依賴手動同步 | HIGH | `docs/` 缺少 `openapi.json` |
| D-3 | 測試覆蓋率未追蹤，無法驗證 80% 強制要求 | HIGH | CI/CD 缺少覆蓋率報告 |
| D-4 | 6 份規格文件標記「規劃中」未完成 | MEDIUM | `docs/specifications/` |
| D-5 | 19 個 `.claude/` 檔案含未解決 TODO/FIXME | MEDIUM | 各 skills/commands |
| D-6 | 部分 Skills 缺少版本號（api-development, testing-guide, database-schema） | LOW | `.claude/skills/` |
| D-7 | `_archived/document_deprecated.py` 無遷移指引 | LOW | `backend/app/extended/models/_archived/` |

### 1.3 建議

#### 立即行動

```
1. 更新 CLAUDE.md 版本至 v1.79.0，同步最後更新日期
2. 建立 OpenAPI Schema 自動匯出腳本：
   python -c "from main import app; import json; print(json.dumps(app.openapi()))" > docs/openapi.json
3. 將 npm run type:sync:full 加入 CI/CD（GitHub Actions 或 Husky pre-commit hook）
   以嚴格阻擋型別不一致的 Commit
```

#### 中期規劃

```
4. 整合 pytest-cov + Codecov 至 CI/CD，強制 80% 門檻
5. 完成「規劃中」規格文件，特別是 TESTING_FRAMEWORK.md
6. 為所有 Skills 統一版本號標記
```

---

## 方向二：後端 FastAPI 非同步與 Pydantic 驗證

### 2.1 優勢

- **全端點 async def**：47 個端點檔案全部使用 `async def`，無同步處理器
- **Service Factory DI**：統一使用 `Depends(get_service(ServiceClass))` 注入模式
- **Repository 層**：34 個 Repository + QueryBuilder，查詢邏輯隔離良好
- **SQLAlchemy async**：主流程正確使用 `AsyncSession` + `await session.execute()`
- **Rate Limiting**：slowapi 全端點覆蓋，429 回應含 Retry-After header

### 2.2 發現問題

#### 非同步模式

| # | 問題 | 嚴重度 | 位置 |
|---|------|--------|------|
| B-1 | `subprocess.run()` 阻塞呼叫在 async 端點中 | HIGH | `deployment.py:374,387` |
| B-2 | 同步 `open()` 在 async 端點 | MEDIUM | `files/storage.py:98` |
| B-3 | 同步 `subprocess.run()` 在備份服務中 | MEDIUM | `backup/db_backup.py:38,164`、`backup/utils.py:136,151` |
| B-4 | `main.py` 承載大量 Scheduler（備份、行事曆同步、NER 提取等） | HIGH | `backend/main.py` |

#### Pydantic 驗證

| # | 問題 | 嚴重度 | 位置 |
|---|------|--------|------|
| B-5 | 3 處端點接受 `dict` 而非 Pydantic Model，繞過驗證 | HIGH | `project_notifications.py:35,185,239,283`、`admin.py:65`、`navigation.py:80` |
| B-6 | 2 個 Schema 檔案仍用 Pydantic v1 `class Config` | MEDIUM | `document_calendar.py:155`、`site_management.py:50,103` |
| B-7 | Email 欄位缺少格式驗證（`EmailStr` 或 `@field_validator`） | MEDIUM | `agency.py:42`、`auth.py:45` |
| B-8 | 字串日期欄位缺少格式驗證 | MEDIUM | `ai.py:36-37`（`date_from`/`date_to`） |
| B-9 | `agency_service.py:140-143` 保留 Pydantic v1 相容層 `.dict()` | LOW | `agency_service.py:140` |

### 2.3 建議

#### 立即行動

```python
# B-1: 將 subprocess.run() 改為 asyncio.create_subprocess_exec()
# ❌ 目前
result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=30)

# ✅ 建議
proc = await asyncio.create_subprocess_exec(
    *cmd.split(),
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)
stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
```

```python
# B-5: 將 dict 參數替換為 Pydantic Model
# ❌ 目前
@router.post("/notifications")
async def create_notification(request: dict): ...

# ✅ 建議
class NotificationCreateRequest(BaseModel):
    title: str = Field(..., max_length=200)
    content: str = Field(..., max_length=2000)
    target_users: list[int] = Field(default_factory=list)

@router.post("/notifications")
async def create_notification(request: NotificationCreateRequest): ...
```

```python
# B-7: 加入 Email 驗證
from pydantic import EmailStr
email: Optional[EmailStr] = Field(None, max_length=100)
```

#### 中期規劃 — Worker 架構

```
B-4: main.py 排程器分離

目前 main.py 承載：備份排程、行事曆同步、NER 實體提取等背景任務
在高負載/大檔案解析時可能影響主要 API 的延遲 (Latency)

建議引入外部 Worker（如 Celery / ARQ）專門處理背景與 AI 任務：
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  FastAPI     │────▶│  Redis Queue │────▶│  ARQ Worker   │
│  (API Only)  │     │  (Broker)    │     │  (Background) │
└─────────────┘     └──────────────┘     └───────────────┘
                                          ├── 備份排程
                                          ├── 行事曆同步
                                          ├── NER 提取
                                          └── Embedding 計算
```

---

## 方向三：前端 React 18 現代化

### 3.1 優勢

- **React 18.3.1 + createRoot**：正確使用 React 18 入口點，StrictMode 啟用
- **React Query v5**：集中式快取配置（`queryConfig.ts`），staleTime/gcTime 統一管理
- **Vite 手動分包**：react-vendor / antd-core / antd-icons / recharts / dayjs / state / xlsx 七層拆分
- **TypeScript 嚴謹**：極少 `any` 使用（僅 5 處），零 `@ts-ignore`
- **Tree-shakeable 匯入**：lodash 使用 `lodash/debounce` 具名匯入，antd 解構匯入
- **零 class component**：僅 `ErrorBoundary` 為 class（React 限制）
- **Logger 服務**：無 `console.log` 散落，統一使用 `logger.error()`

### 3.2 發現問題

| # | 問題 | 嚴重度 | 位置 |
|---|------|--------|------|
| F-1 | 未使用 React.lazy + Suspense 進行路由級 Code Splitting | HIGH | `AppRouter.tsx` |
| F-2 | 未使用 `useTransition` / `useDeferredValue` 處理非同步狀態更新 | MEDIUM | 全域搜尋/篩選操作 |
| F-3 | 缺少 `React.memo()` 包裝純元件 | MEDIUM | 高頻渲染元件 |
| F-4 | 缺少 `useMemo` 處理昂貴計算 | MEDIUM | 資料密集元件 |
| F-5 | Header.tsx 等元件含大量 inline style | LOW | `Header.tsx:86-96` |
| F-6 | `DatabaseManagementPage.tsx` 使用 `any[]` 型別 | LOW | `DatabaseManagementPage.tsx:30-32,59` |
| F-7 | `ContractCaseFormPage.tsx` 保留未使用狀態變數 | LOW | `ContractCaseFormPage.tsx:74-77` |

### 3.3 建議

#### 立即行動 — 路由級 Code Splitting (F-1)

```tsx
// ❌ 目前：所有頁面同步載入
import DocumentDetailPage from '../pages/DocumentDetailPage';
import KnowledgeGraphPage from '../pages/KnowledgeGraphPage';

// ✅ 建議：Suspense + lazy 按需載入
import { Suspense, lazy } from 'react';
import { Spin } from 'antd';

const DocumentDetailPage = lazy(() => import('../pages/DocumentDetailPage'));
const KnowledgeGraphPage = lazy(() => import('../pages/KnowledgeGraphPage'));

// 路由包裝
<Suspense fallback={<Spin size="large" />}>
  <Route path="/documents/:id" element={<DocumentDetailPage />} />
</Suspense>
```

**預期效果**：首次載入 bundle 減少 30-50%，知識圖譜/報表等重型頁面延遲載入。

#### 中期規劃 — Concurrent Features (F-2)

```tsx
// 搜尋/篩選操作使用 useTransition 避免阻塞 UI
import { useTransition } from 'react';

const [isPending, startTransition] = useTransition();

const handleSearch = (keyword: string) => {
  // 輸入框即時更新
  setSearchText(keyword);
  // 搜尋結果延遲更新，不阻塞輸入
  startTransition(() => {
    setFilteredResults(filterData(keyword));
  });
};
```

#### 性能優化 — Memoization (F-3, F-4)

```tsx
// 高頻渲染的純展示元件加入 React.memo
const KanbanCard = React.memo(({ record }: KanbanCardProps) => {
  // ...
});

// 昂貴計算使用 useMemo
const statistics = useMemo(() =>
  computeWorkflowStats(workRecords),
  [workRecords]
);
```

---

## 方向四：系統效能與架構擴展（補充）

### 4.1 健康檢查端點 SELECT COUNT(*) 問題

**現況**：`/health/detailed` 端點使用 `SELECT COUNT(*)` 對多張資料表進行全表掃描計數。

**風險**：隨著資料表變大（尤指 `documents`），全表掃描計數的效能會大幅下降。

**建議**：使用 PostgreSQL 系統表 `pg_class` 獲取預估值：

```sql
-- ❌ 目前：全表掃描（O(n)，隨資料量線性增長）
SELECT COUNT(*) FROM documents;

-- ✅ 建議：系統表預估值（O(1)，常數時間）
SELECT reltuples::bigint AS estimated_count
FROM pg_class
WHERE relname = 'documents';
```

> **適用場景**：健康檢查、儀表板統計等不需要精確值的場景。精確值需求（如分頁 total）仍用 COUNT(*)。

### 4.2 型別同步自動化

**現況**：前端依靠手動或特定指令（`/type-sync`）同步後端 Schema，若有變動容易遺漏。

**建議**：將 `npm run type:sync:full` 加入 CI/CD（GitHub Actions 或 Husky pre-commit hook），以嚴格阻擋型別不一致的 Commit。

```yaml
# .github/workflows/ci.yml 新增 job
type-sync-check:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: npm run type:sync:full
      working-directory: frontend
    - run: |
        if [ -n "$(git diff --name-only)" ]; then
          echo "::error::Type definitions out of sync with backend schemas"
          git diff
          exit 1
        fi
```

### 4.3 Scheduler 外部化

| 排程任務 | 目前位置 | 建議位置 |
|---------|----------|----------|
| 備份排程 | `main.py` startup | ARQ Worker |
| 行事曆同步 | `main.py` startup | ARQ Worker |
| NER 實體提取 | `main.py` startup | ARQ Worker |
| Embedding 計算 | `main.py` startup | ARQ Worker |
| 系統健康檢查 | `main.py` startup | 保留（輕量） |

**ARQ 選擇理由**：專為 Python asyncio 設計，與 FastAPI 天然相容，Redis 已在基礎設施中。

---

## 改進優先級總覽

### P0 — 立即行動（本週）

| # | 項目 | 預估工時 |
|---|------|---------|
| D-1 | 更新 CLAUDE.md 版本至 v1.79.0 | 15 min |
| B-5 | 將 3 處 `dict` 參數替換為 Pydantic Model | 1 hr |
| B-1 | `deployment.py` 阻塞 subprocess 改 async | 30 min |
| F-6 | `DatabaseManagementPage.tsx` 消除 `any` | 30 min |

### P1 — 短期（1-2 週）

| # | 項目 | 預估工時 |
|---|------|---------|
| F-1 | 路由級 Code Splitting（React.lazy + Suspense） | 2 hr |
| B-6 | 統一 Pydantic v2 `model_config`（3 檔案） | 30 min |
| B-7 | Email/日期欄位加入驗證器 | 1 hr |
| D-2 | OpenAPI Schema 匯出 + CI 整合 | 2 hr |
| D-3 | pytest-cov 覆蓋率追蹤整合至 CI | 2 hr |
| 4.1 | `/health/detailed` 改用 pg_class 預估值 | 30 min |
| 4.2 | type:sync:full 加入 CI/CD pre-commit | 1 hr |

### P2 — 中期（1 個月）

| # | 項目 | 預估工時 |
|---|------|---------|
| B-4 | Scheduler 外部化至 ARQ Worker | 1 week |
| F-2 | useTransition / useDeferredValue 導入 | 3 hr |
| F-3,4 | React.memo + useMemo 性能優化 | 4 hr |
| D-4 | 完成「規劃中」規格文件 | 4 hr |
| B-9 | 移除 Pydantic v1 相容層 | 1 hr |

### P3 — 長期待辦

| # | 項目 | 說明 |
|---|------|------|
| — | Repository 採用率提升 (18%→50%) | 漸進式遷移 Service 層直接查詢 |
| — | LLM 智慧路由 | 依任務複雜度自動選擇 Groq/Ollama |
| — | API 版本化 (`/api/v1/`) | 為未來向後相容做準備 |
| — | Neo4j 評估 | 知識圖譜重型查詢場景 |

---

## 附錄：分析方法

本報告基於以下分析維度：

1. **後端架構**：47 個端點檔案、34 個 Repository、140+ Python 檔案全量掃描
2. **前端現代化**：React 18 特性採用率、TypeScript 嚴謹度、Bundle 優化、狀態管理
3. **文件規範**：CLAUDE.md 體系、9 份 rules、24 份 skills、18 份 commands 一致性比對
4. **用戶補充觀點**：健康檢查效能、型別同步自動化、Scheduler 外部化

---

*報告生成：Claude Code | 專案：CK_Missive v1.79.0 | 日期：2026-03-07*
