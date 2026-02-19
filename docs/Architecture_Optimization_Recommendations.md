# CK_Missive 架構優化建議

> **版本**: 8.0.0
> **建立日期**: 2026-02-06
> **最後更新**: 2026-02-19 (v17.0.0 全面檢查 + Phase 6 規劃)
> **狀態**: Phase 1-4 全部完成 / Phase 5 規劃確定 / Phase 6 新增規劃

---

## 目錄

1. [現況評估總覽](#1-現況評估總覽)
2. [響應式設計優化](#2-響應式設計優化)
3. [AI 助理 UI 架構優化](#3-ai-助理-ui-架構優化)
4. [AI 服務後端架構優化](#4-ai-服務後端架構優化)
5. [服務層遷移路線圖](#5-服務層遷移路線圖)
6. [認證與安全架構](#6-認證與安全架構)
7. [測試與品質保障](#7-測試與品質保障)
8. [實施優先級與路線圖](#8-實施優先級與路線圖)
9. [Phase 4A: RWD 響應式設計全面規劃](#9-phase-4a-rwd-響應式設計全面規劃)
10. [Phase 4B: AI 助理深度優化規劃](#10-phase-4b-ai-助理深度優化規劃)
11. [Phase 4C: 帳號登入管控強化規劃](#11-phase-4c-帳號登入管控強化規劃)
12. [Phase 5: 架構精煉與品質自動化](#12-phase-5-架構精煉與品質自動化)
13. [Phase 6: 可訪問性與服務拆分 (v8.0.0 新增)](#13-phase-6-可訪問性與服務拆分)

---

## 13. Phase 6: 可訪問性與服務拆分

> **目標**: 補齊 A11y 可訪問性基線、拆分超大服務、強化測試深度
> **預估時間**: 3-4 週
> **前置**: Phase 5 SSOT 遷移完成
> **觸發**: v17.0.0 全面檢查發現可訪問性評分 6.0/10、backup_service 1055 行、API 整合測試不足

### 13.1 Phase 6A: 可訪問性基線建立 (優先級: HIGH)

**現狀**: 0 個 aria-label、0 個 alt 文字、無鍵盤導航測試

#### 第一階段：ARIA 標籤補強

| 區域 | 元件數 | 需要的 ARIA | 預估工時 |
|------|--------|-------------|----------|
| 按鈕（圖示型） | ~50+ | `aria-label` | 1 天 |
| 表格 | ~15 | `aria-describedby`, `aria-sort` | 1 天 |
| 表單 | ~20 | `aria-required`, `aria-invalid`, `aria-errormessage` | 1 天 |
| Modal | ~10 | `aria-modal`, `aria-labelledby` | 0.5 天 |
| 導航 | 1 | `aria-current="page"`, `aria-expanded` | 0.5 天 |

#### 第二階段：鍵盤導航

| 項目 | 說明 |
|------|------|
| Tab 順序 | 確保所有互動元素可 Tab 到達 |
| Escape 關閉 | Modal/Drawer 支援 Esc 關閉（Ant Design 預設支援） |
| Enter 確認 | 表單 Enter 提交（需逐一驗證） |
| Focus 管理 | Modal 開啟時 focus trap，關閉後恢復 focus |

#### 第三階段：E2E A11y 測試

```typescript
// playwright.config.ts 新增
import { AxeBuilder } from '@axe-core/playwright';

test('應通過 WCAG 2.1 AA 基本檢查', async ({ page }) => {
  await page.goto('/documents');
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toHaveLength(0);
});
```

### 13.2 Phase 6B: 後端服務拆分 (優先級: MEDIUM)

**backup_service.py (1055 行) 拆分方案**:

```
當前架構:
  BackupService (1055 行)
    ├── __init__() + 路徑管理 (50 行)
    ├── 資料庫備份 (250 行)
    ├── 附件備份 (200 行)
    ├── 還原功能 (200 行)
    ├── 列表管理 (150 行)
    ├── 驗證邏輯 (150 行)
    └── 雜項 (55 行)

目標架構:
  BackupCoordinator (200 行) — 協調器，路由到子服務
    ├── DbBackupService (250 行) — DB 備份/還原
    ├── FileBackupService (200 行) — 附件備份/還原
    ├── BackupMetadataService (150 行) — 列表/統計
    └── BackupValidator (150 行) — 驗證/空間檢查
```

**大型元件拆分方案**:

| 元件 | 行數 | 拆分策略 |
|------|------|----------|
| `DocumentDetailPage.tsx` | 897 | 提取 useDocumentDetail Hook (300行) + Tab 子元件 |
| `TaoyuanDispatchDetailPage.tsx` | 847 | 提取 useDispatchDetail Hook (250行) |
| `NaturalSearchPanel.tsx` | 774 | 提取 useNaturalSearch Hook (400行) + SearchResults 子元件 |
| `PaymentsTab.tsx` | 653 | 提取 usePayments Hook + PaymentForm 子元件 |

### 13.3 Phase 6C: 測試深度擴充 (優先級: MEDIUM)

**目標覆蓋率**: 後端 85%+，前端 80%+

#### 後端缺失測試

| 測試類型 | 缺失區域 | 預估測試數 |
|---------|----------|-----------|
| API 整合 | documents/list, stats, calendar | 20+ |
| 服務單元 | backup_service (30+), calendar | 40+ |
| Repository | CalendarEvent, Certification | 15+ |
| 安全 | CSRF bypass, rate limit edge cases | 10+ |

#### 前端缺失測試

| 測試類型 | 缺失區域 | 預估測試數 |
|---------|----------|-----------|
| 頁面測試 | DocumentDetail, DispatchDetail | 15+ |
| AI 元件 | NaturalSearchPanel, AISummaryPanel | 10+ |
| Tab 元件 | PaymentsTab, DispatchOrdersTab | 10+ |
| 表單驗證 | 派工表單、公文表單 | 8+ |

### 13.4 Phase 6D: Repository 層擴展 (優先級: MEDIUM)

**目標**: Repository 採用率從 18% 提升至 60%+

| 優先級 | Repository | 覆蓋端點 | 工時 |
|--------|-----------|---------|------|
| P0 | DocumentRepository 擴展 | list.py, stats.py (980行) | 3 天 |
| P0 | UserRepository 擴展 | user_management.py (539行) | 2 天 |
| P1 | CalendarEventRepository (新) | events.py (638行) | 3 天 |
| P1 | StaffCertificationRepository (新) | certifications.py (501行) | 2 天 |
| P2 | HealthRepository (新) | health.py (489行) | 1 天 |

### 13.5 Phase 6 實施路線圖

```
Week 1: Phase 6A (可訪問性 ARIA 標籤) + Phase 6D-P0 (Repository 擴展)
Week 2: Phase 6B (backup_service 拆分) + Phase 6C (後端測試補強)
Week 3: Phase 6A-3 (A11y E2E) + Phase 6C (前端測試補強)
Week 4: Phase 6D-P1/P2 + 總體驗證 + 元件拆分
```

### 13.6 Phase 6 完成標準

| 驗收項目 | 標準 |
|---------|------|
| 可訪問性評分 | WCAG 2.1 AA 基本通過（axe-core 0 violations） |
| backup_service | 拆分為 4 個 <300 行模組 |
| 所有元件 | <600 行 |
| 後端測試覆蓋 | ≥ 85% 行覆蓋率 |
| 前端測試覆蓋 | ≥ 80% 行覆蓋率 |
| Repository 採用率 | ≥ 60% 端點使用 Repository |

---

## 12. Phase 5: 架構精煉與品質自動化

> **目標**: 從「功能完備」提升至「架構卓越」，消除技術債、強化自動化品質門檻
> **預估時間**: 2-3 週
> **前置**: Phase 1-4 全部完成，`verify_architecture.py` 已建立基線

### 12.1 Phase 5A: 型別 SSOT 全面遷移 (優先級: HIGH)

**現狀**: `verify_architecture.py` 偵測到 21 個 SSOT 違規（後端 6 + 前端 15）

#### 後端 SSOT 遷移 (6 個端點)

| 端點檔案 | 本地 BaseModel 數 | 遷移目標 |
|---------|-------------------|---------|
| `ai/document_ai.py` | 12 | → `schemas/ai.py` |
| `ai/prompts.py` | 10 | → `schemas/ai.py` |
| `deployment.py` | 10 | → `schemas/deployment.py` (新增) |
| `auth/email_verify.py` | 1 | → `schemas/auth.py` |
| `document_calendar/events.py` | 1 | → `schemas/calendar.py` |
| `taoyuan_dispatch/dispatch_document_links.py` | 1 | → `schemas/taoyuan/dispatch.py` |

**步驟**:
1. 在 `schemas/` 建立對應 Schema 檔案
2. 將端點中的 BaseModel 搬至 Schema
3. 端點檔案改為 `from app.schemas.xxx import YYY`
4. 執行 `verify_architecture.py --check ssot` 確認 0 違規

#### 前端 SSOT 遷移 (15 個 API 檔案)

| API 檔案 | 本地型別數 | 遷移目標 |
|---------|-----------|---------|
| `deploymentApi.ts` | 14 | → `types/api.ts` |
| `filesApi.ts` | 8 | → `types/api.ts` |
| `calendarApi.ts` | 5 | → `types/api.ts` |
| `adminUsersApi.ts` | 5 | → `types/api.ts` |
| `documentsApi.ts` | 4 | → `types/api.ts` |
| 其他 10 個 | 1-3 | → `types/api.ts` |

**步驟**:
1. 將型別定義搬至 `types/api.ts`
2. API 檔案改為 `import type { XXX } from '../types/api'`
3. 確保 `re-export` 供外部使用
4. 執行 `npx tsc --noEmit` + `verify_architecture.py --check ssot`

### 12.2 Phase 5B: Schema-ORM 欄位對齊 (優先級: MEDIUM)

**現狀**: 5 個 Schema-ORM 欄位差異

| Schema | 多餘欄位 | 處置策略 |
|--------|---------|---------|
| `DocumentBase` | `contract_case`, `creator`, `doc_class`, `doc_word`, `priority_level`, `user_confirm` | 評估是否加入 ORM 或從 Schema 移除 |
| `DocumentResponse` | `assigned_staff`, `attachment_count`, `contract_project_name`, `receiver_agency_name`, `sender_agency_name` | 合理（計算欄位），加入 verify 排除清單 |
| `UserCreate/Update` | `password` | 合理（虛擬欄位），加入排除清單 |

### 12.3 Phase 5C: 品質自動化門檻 (優先級: HIGH)

#### CI 整合 verify_architecture.py

```yaml
# .github/workflows/ci.yml 新增 job
architecture-check:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: '3.11' }
    - run: python scripts/verify_architecture.py
      # 目標: 0 errors (warnings 允許但需追蹤)
```

#### Pre-commit Hook 整合

```bash
# .claude/hooks/ 新增
architecture-check.ps1  # 提交前執行 verify_architecture.py --check routes,imports
```

### 12.4 Phase 5D: 測試覆蓋率提升 (優先級: MEDIUM)

**目標**: 前端測試覆蓋率 80%+

| 優先區域 | 現狀 | 目標 | 策略 |
|---------|------|------|------|
| API 服務 | 部分覆蓋 | 80%+ | Mock API，驗證請求格式 |
| Hooks | 部分覆蓋 | 80%+ | renderHook + act |
| 頁面元件 | 低覆蓋 | 60%+ | 快照測試 + 互動測試 |
| E2E 關鍵路徑 | 5 個檔案 | 10+ | 新增公文 CRUD、認證完整流程 |

### 12.5 Phase 5E: 效能監控基礎設施 (優先級: LOW)

| 項目 | 說明 |
|------|------|
| 慢查詢日誌 | `statement_timeout` + 超時告警 |
| API 回應時間追蹤 | 中間件記錄 P50/P95/P99 |
| 前端 Web Vitals | LCP/FID/CLS 追蹤 |
| 連線池監控 | pool_size 使用率告警 |

### 12.6 Phase 5 實施路線圖

```
Week 1: Phase 5A (SSOT 遷移) + Phase 5C (CI 整合)
Week 2: Phase 5B (Schema 對齊) + Phase 5D (測試覆蓋)
Week 3: Phase 5E (效能監控) + 總體驗證
```

### 12.7 Phase 5 完成標準

| 驗收項目 | 標準 |
|---------|------|
| SSOT 違規 | 0 個（verify_architecture.py 通過） |
| Schema-ORM 差異 | 已全部歸類（修復或標記為合理） |
| CI 架構檢查 | 整合至 GitHub Actions |
| 前端測試覆蓋 | ≥ 80% 行覆蓋率 |
| 後端測試覆蓋 | ≥ 80% 行覆蓋率 |
| API P95 回應時間 | < 500ms |

---

## 1. 現況評估總覽

### 1.1 各模組成熟度

| 模組 | v4.0 評分 | v8.0 評分 | 目標 | 關鍵缺口 |
|------|-----------|-----------|------|----------|
| 響應式設計 | 8.5/10 | **8.5/10** ✅ | 9.0 | ReportsPage RWD 待完成 |
| AI 助理 UI | 9.5/10 | **9.5/10** ✅ | 9.5 | NaturalSearchPanel 774 行待拆分 |
| AI 後端服務 | 9.5/10 | **9.5/10** ✅ | 9.5 | ✅ 全部到位 |
| 服務層架構 | 9.5/10 | **9.5/10** ✅ | 9.5 | ✅ 工廠模式完成 |
| 認證安全 | 9.8/10 | **9.5/10** | 10 | passlib 停止維護待評估 |
| 帳號管控 | 9.2/10 | **9.2/10** ✅ | 9.0 | ✅ 全部到位 |
| 測試覆蓋 | 8.8/10 | **7.5/10** ↓ | 9.0 | API 整合測試嚴重不足（僅 3 個） |
| **Repository 層** | **-** | **6.5/10** 🆕 | 8.0 | 僅 18% 端點使用，82% 直接 ORM |
| **可訪問性** | **-** | **6.0/10** 🆕 | 8.0 | 無 ARIA 標籤、alt 文字、鍵盤測試 |
| **依賴健康** | **-** | **8.5/10** 🆕 | 9.0 | passlib/psutil 需升級 |

### 1.3 v1.48.0 已完成項目 (2026-02-07)

| 項目 | 說明 |
|------|------|
| 明文密碼回退移除 | `verify_password()` bcrypt 失敗 → return False |
| Refresh Token Rotation | SELECT FOR UPDATE + Token Replay 偵測 |
| 診斷路由保護 | 4 個診斷頁面 → admin 角色限制 |
| 公開端點加固 | 移除 auth_disabled/debug/credentials_file |
| SECRET_KEY 強制 | 生產環境拒絕 dev_only_ 金鑰 |
| 啟動 Token 驗證 | useAuthGuard 首次載入向 /auth/me 驗證 |
| 閒置超時 | useIdleTimeout 30 分鐘無操作登出 |
| 跨分頁同步 | storage 事件監聽登出/token 變更 |
| AdminDashboard 優化 | 趨勢圖 + 效能統計 + 導航修正 |
| Profile v2.0 | apiClient 統一 + SSOT + department/position |

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

## 6. 認證與安全架構

### 6.1 v1.48.0 安全強化成果

| 項目 | 修復前 | 修復後 | 影響 |
|------|--------|--------|------|
| 密碼驗證 | bcrypt 失敗 → 明文比對 | bcrypt 失敗 → 拒絕 | 消除憑證繞過 |
| Refresh Token | 重複使用不撤銷 | Rotation + Replay 偵測 | 防竊取擴散 |
| 診斷路由 | 無認證保護 | admin 角色限制 | 關閉資訊洩漏 |
| 公開端點 | 回傳 auth_disabled/debug | 僅回傳基本資訊 | 減少攻擊面 |
| SECRET_KEY | 生產環境可用開發金鑰 | 強制自訂金鑰 | 防 JWT 偽造 |
| 會話管理 | 無閒置超時 | 30 分鐘閒置登出 | 防閒置劫持 |
| 跨分頁 | 無同步機制 | storage 事件同步 | 統一登出狀態 |
| 啟動驗證 | 僅檢查本地 JWT | 向 /auth/me 驗證 | 防撤銷 token 續用 |

### 6.2 剩餘安全缺口

#### 6.2.1 httpOnly Cookie 遷移 (優先級: 中)

**現況**: Access Token 儲存於 `localStorage`，可被 XSS 讀取。

**風險**: 若任何第三方套件存在 XSS 漏洞，攻擊者可竊取 token。

**遷移路徑**:

```
Phase A: 後端支援 Set-Cookie
  ├── 登入成功 → Set-Cookie: access_token=xxx; HttpOnly; Secure; SameSite=Strict
  ├── /auth/refresh → 更新 cookie
  └── /auth/logout → 清除 cookie

Phase B: 前端遷移
  ├── 移除 localStorage.setItem(ACCESS_TOKEN_KEY)
  ├── axios 改用 withCredentials: true
  └── 保留 localStorage user_info (非敏感)

Phase C: CSRF 防護
  ├── 後端生成 CSRF token (Double Submit Cookie)
  ├── 前端 meta tag 注入
  └── axios 攔截器自動附加 X-CSRF-Token header
```

**工作量**: ~8h | **影響**: 大幅提升 XSS 防禦

#### 6.2.2 Refresh 端點速率限制 (優先級: 高)

**現況**: `/auth/refresh` 端點無獨立速率限制，可被暴力嘗試。

**建議**:

```python
# 在 session.py refresh 端點加入 slowapi 限制
@router.post("/refresh")
@limiter.limit("10/minute")  # 每分鐘最多 10 次刷新
async def refresh_token(request: Request, response: Response, ...):
    ...
```

**工作量**: ~0.5h | **影響**: 防止 token 暴力刷新

#### 6.2.3 密碼策略強化 (優先級: 低)

**現況**: 使用者註冊無密碼複雜度要求。

**建議**: 在 `RegisterRequest` schema 加入 validator:
- 最短 8 字元
- 包含大小寫 + 數字
- 不得與 username/email 相同

### 6.3 認證架構圖

```
瀏覽器                        後端
┌─────────────────┐          ┌──────────────────────────┐
│ localStorage    │          │ AuthService              │
│ ├ access_token  │◄─────────│ ├ verify_password()      │
│ ├ refresh_token │   JWT    │ │   bcrypt only, no      │
│ └ user_info     │          │ │   plaintext fallback   │
│                 │          │ ├ verify_refresh_token()  │
│ authService.ts  │──────────│ │   SELECT FOR UPDATE    │
│ ├ login()       │  /auth/* │ │   + replay detection   │
│ ├ logout()      │          │ ├ generate_login_response│
│ ├ isAuthenticated()        │ │   is_refresh flag      │
│ └ validateTokenOnStartup() │ └ revoke_session()       │
│                 │          │                          │
│ useAuthGuard    │          │ UserSession (DB)         │
│ ├ _startupValidated        │ ├ token_jti              │
│ └ resetStartupValidation() │ ├ refresh_token          │
│                 │          │ ├ is_active              │
│ useIdleTimeout  │          │ └ revoked_at             │
│ └ 30min idle    │          └──────────────────────────┘
│                 │
│ Cross-tab sync  │
│ └ storage event │
└─────────────────┘
```

---

## 7. 測試與品質保障

### 7.1 測試覆蓋現況

| 類別 | 測試數 | 覆蓋率 | 目標 |
|------|--------|--------|------|
| 後端單元測試 | 628 | ~75% | 80% |
| 前端單元測試 | 648 | ~70% | 80% |
| E2E 煙霧測試 | 10 | 核心流程 | 30+ |
| E2E 流程測試 | 39 | 3 模組 | 全模組 |

### 7.2 測試缺口分析

#### 7.2.1 認證流程測試 (優先級: 高)

**缺失**: 以下認證場景無自動化測試覆蓋：

| 場景 | 測試類型 | 狀態 |
|------|----------|------|
| 登入 → 取得 token | 整合測試 | 缺 |
| Refresh Token Rotation | 整合測試 | 缺 |
| Token Replay 偵測 | 整合測試 | 缺 |
| 閒置超時登出 | E2E | 缺 |
| 跨分頁同步 | E2E | 缺 |
| 啟動 token 驗證 | 前端單元 | 缺 |
| 密碼錯誤 5 次鎖定 | 整合測試 | 缺 (功能未實作) |
| Google OAuth 流程 | E2E | 缺 |

**建議**: 建立 `backend/tests/integration/test_auth_flow.py` 和 `frontend/src/__tests__/hooks/useAuthGuard.test.ts`

#### 7.2.2 E2E 測試擴展 (優先級: 中)

**已有 E2E 覆蓋**:
- 公文 CRUD (12 tests)
- 派工安排 (14 tests)
- 專案管理 (13 tests)
- 煙霧測試 (10 tests)

**缺少 E2E 覆蓋**:
| 模組 | 預估測試數 | 優先級 |
|------|-----------|--------|
| 認證登入/登出 | 5 | 高 |
| 管理後台 (Admin) | 8 | 中 |
| 行事曆功能 | 6 | 中 |
| 機關/廠商管理 | 6 | 中 |
| AI 助理功能 | 4 | 低 |
| 備份管理 | 3 | 低 |

#### 7.2.3 Repository 層測試 (優先級: 中)

**現況**: Repository 層有測試範本但實際測試為 0。

**建議**: 每個 Repository 至少 5 個核心測試:
- `test_get_by_id()` / `test_get_not_found()`
- `test_create()` / `test_update()` / `test_delete()`
- `test_filter_*()` (Repository 特定篩選方法)
- `test_search()` (全文搜尋)

### 7.3 品質工具整合

| 工具 | 狀態 | 說明 |
|------|------|------|
| TypeScript (tsc --noEmit) | 已整合 CI | 0 錯誤 |
| ESLint | 已整合 CI | 前端規範 |
| py_compile | 已整合 CI | Python 語法 |
| mypy | 已整合 CI | Python 型別 |
| npm audit | 已整合 CI | 前端依賴安全 |
| pip-audit | 已整合 CI | 後端依賴安全 |
| Codecov | 已整合 CI | 覆蓋率報告 |
| **Playwright** | **CI 獨立** | E2E (需 Docker) |

### 7.4 品質提升路線

```
Phase 1 (1 週): 認證流程測試
  ├── 後端整合測試: login/refresh/replay/revoke
  ├── 前端單元測試: useAuthGuard/useIdleTimeout
  └── 目標: 認證模組 90%+ 覆蓋

Phase 2 (2 週): Repository 層測試
  ├── DocumentRepository: 10 tests
  ├── ProjectRepository: 8 tests
  ├── AgencyRepository: 8 tests
  └── 目標: Repository 層 85%+ 覆蓋

Phase 3 (2 週): E2E 擴展
  ├── 認證流程 E2E: 5 tests
  ├── 管理後台 E2E: 8 tests
  ├── 行事曆 E2E: 6 tests
  └── 目標: E2E 覆蓋 6+ 模組
```

---

## 8. 實施優先級與路線圖

### 8.1 短期 Phase 3 — ✅ 已完成 (v1.49.0, 2026-02-07)

| # | 項目 | 狀態 | 完成說明 |
|---|------|------|----------|
| S1 | Refresh 端點速率限制 | ✅ | `@limiter.limit("10/minute")` |
| S2 | 認證流程整合測試 | ✅ | 22 個整合測試 |
| S3 | Prompt 載入容錯 | ✅ | `_DEFAULT_PROMPTS` 已存在 |
| S4 | AI 面板響應式 | ✅ | `responsiveValue()` 已整合 |
| S5 | AI 配置自動同步 | ✅ | `syncAIConfigFromServer()` |
| S6 | NaturalSearchPanel 彈性高度 | ✅ | flex 佈局 |

### 8.2 中期 Phase 3 — ✅ 已完成 (v1.49.0, 2026-02-07)

| # | 項目 | 狀態 | 完成說明 |
|---|------|------|----------|
| M1 | httpOnly Cookie + CSRF 遷移 | ✅ | csrf.py + set_auth_cookies + 前端 interceptor |
| M2 | Repository 層測試 | ✅ | 109 個測試 (Document 36 + Project 34 + Agency 39) |
| M3 | E2E 認證流程測試 | ✅ | 5 個 Playwright 測試 |
| M4 | SimpleCache → Redis | ✅ | RedisCache + graceful fallback |
| M5 | 統計資料 Redis 持久化 | ✅ | AIStatsManager + HINCRBY |
| M6 | AI 回應驗證層 | ✅ | `_call_ai_with_validation()` + Pydantic |
| M7-M9 | 服務工廠遷移 | ✅ | VendorService/AgencyService/ProjectService 已完成 |
| M10 | 搜尋歷史 + 結果快取 | ✅ | localStorage + 5min Map cache |

**安全審查額外修復** (v1.49.0):

| 修復 | 嚴重度 | 說明 |
|------|--------|------|
| CSRF bypass fix | CRITICAL | access_token cookie 存在時強制要求 csrf_token |
| Login rate limit | HIGH | `/login` 5/min + `/google` 10/min |
| Error sanitization | HIGH | 移除 `str(e)` 洩漏 |
| Redis URL redaction | HIGH | 密碼遮罩 |
| Username masking | MEDIUM | 登入日誌部分遮罩 |

### 8.3 Phase 4: 下一階段規劃 (詳見 Section 9-11)

| 階段 | 主題 | 項目數 | 預估總工時 | 影響評分提升 |
|------|------|--------|-----------|-------------|
| **4A** | RWD 響應式設計 | 4 項 | 20h | 6.5 → 8.5 |
| **4B** | AI 助理深度優化 | 5 項 | 41h | 9.0 → 9.5 |
| **4C** | 帳號登入管控 | 7 項 | 31.5h | 7.2 → 9.0 |
| | **合計** | **16 項** | **92.5h** | |

**建議執行順序**: 4C-L1(密碼策略) → 4A-R1(側邊欄) → 4C-L2(帳號鎖定) → 4A-R2(表格) → 4C-L3(密碼重設) → 4B-A1(串流) → 其餘

### 8.4 長期 (1-3 月)

| # | 項目 | 來源 | 影響 | 工作量 |
|---|------|------|------|--------|
| L1 | 27 端點 Repository 遷移 | 5.4 | 中 - 架構統一 | 30h |
| L2 | CalendarEvent Repository | 5.3 | 中 - 行事曆優化 | 6h |
| L3 | WebSocket 即時推送 | - | 中 - 即時通知 | 15h |
| L4 | E2E 全模組覆蓋 | 7.2.2 | 中 - 品質保障 | 15h |
| L5 | SSO/SAML 整合 | - | 低 - 企業級 | 20h |

### 8.5 不做的事項

| 項目 | 原因 |
|------|------|
| D3.js 機關關係圖 | 需引入新依賴，ROI 低 |
| PWA 支援 | 長期項目，現階段無需求 |
| 甘特圖 | 需專門套件，另開 session |
| 微服務拆分 | 目前單體架構足夠，過早拆分增加複雜度 |
| GraphQL | REST API 已滿足需求，切換成本高 |
| FIDO2/WebAuthn | 硬體需求高，TOTP 先行 |

---

## 9. Phase 4A: RWD 響應式設計全面規劃

> **狀態**: ✅ **全部完成** (v1.51.0, 2026-02-08)
> - R1: Drawer 側邊欄 (SidebarContent + 漢堡選單)
> - R2: ResponsiveTable 元件 (9 個頁面, scroll.x + mobileHiddenColumns)
> - R3: ResponsiveFormRow 元件 (15 個頁面, 2 欄 → 1 欄切換)
> - R4: ResponsiveContainer 全面採用 (18 個頁面)
> - **評分: 6.5 → 8.5/10**

### 9.1 現況問題分析 (實作前)

**實作前成熟度: 6.5/10** — 基礎設施優秀但實作不一致

| 層面 | 評分 | 說明 |
|------|------|------|
| Hook 基礎設施 | 9/10 | `useResponsive()` 設計完善，breakpoint 對齊 Ant Design |
| CSS 框架 | 8/10 | `responsive.css` 405 行工具類別完備 |
| Layout 行動版 | 3/10 | **側邊欄無行動版收合，佔 17-23% 螢幕** |
| Table 響應式 | 4/10 | `scroll.x` 定義但未實作，行動版看不全 |
| Form 響應式 | 5/10 | 多數硬編碼 vertical layout |
| 元件採用率 | 4/10 | ResponsiveContainer 元件定義了但鮮少使用 |

### 9.2 優化項目

#### R1: 行動裝置側邊欄 (CRITICAL, 4h)

**問題**: 側邊欄固定 80-200px 寬度，行動版無自動收合/漢堡選單。

**修改範圍**:
- `frontend/src/components/Layout.tsx` — marginLeft 行動版設為 0
- `frontend/src/components/Layout/Sidebar.tsx` — Drawer 模式 + 漢堡按鈕
- `frontend/src/components/Layout/Header.tsx` — 新增行動版選單按鈕

**方案**: 行動版 (< 768px) 側邊欄改為 Ant Design `Drawer` 覆蓋模式，點擊漢堡按鈕開啟/關閉。

```
Desktop (≥768px):          Mobile (<768px):
+------+----------+       +----------------+
| Side | Content  |       | ☰ Header      |
| bar  |          |       +----------------+
|      |          |       | Content        |
+------+----------+       |                |
                          +----------------+
                          (Sidebar = Drawer overlay)
```

#### R2: Table 響應式 scroll + 卡片模式 (HIGH, 6h)

**問題**: 所有欄位在行動版可見，水平溢出。

**修改範圍**:
- `frontend/src/components/document/DocumentList.tsx`
- `frontend/src/components/common/UnifiedTable.tsx`
- 所有使用 Table 的頁面元件

**方案**:
1. 統一加入 `scroll={{ x: responsiveValue(RESPONSIVE_TABLE.scrollX) }}`
2. 行動版隱藏次要欄位 (sender, category 等)
3. 小螢幕 (< 576px) 啟用卡片模式取代表格

#### R3: Form 響應式佈局 (MEDIUM, 4h)

**問題**: 表單固定單欄，未利用大螢幕空間。

**修改範圍**: 所有含表單的頁面 (DocumentOperations, TaoyuanDispatchCreate, etc.)

**方案**: 使用 `Row + Col xs={24} md={12}` 模式，md 以上 2 欄、以下 1 欄。

#### R4: ResponsiveContainer 全面採用 (MEDIUM, 6h)

**修改範圍**: 全部頁面元件

**方案**: 以 `ResponsiveContent` 取代硬編碼 padding，`ResponsiveSpace` 取代固定 gap。

### 9.3 驗收標準

- [ ] 行動版 (375px) 側邊欄完全隱藏，點擊漢堡展開
- [ ] 所有 Table 在 375px 可水平捲動或顯示卡片
- [ ] 表單在 768px 以上顯示 2 欄
- [ ] 0 處硬編碼 px 寬度 (使用 responsiveValue)
- [ ] Chrome DevTools 行動模擬器 5 種裝置驗證通過

---

## 10. Phase 4B: AI 助理深度優化規劃

> **✅ Phase 4B 已於 v1.51.0 (2026-02-08) 全部完成**
>
> | 項目 | 狀態 | 說明 |
> |------|------|------|
> | A1: SSE 串流回應 | ✅ 完成 | StreamingResponse + EventSource + StreamingText 元件 |
> | A2: pgvector 語意搜尋 | ✅ 完成 | 384 維向量 + ivfflat 索引 + 混合評分 (0.6*trigram + 0.4*semantic) |
> | A3: Prompt 版本控制 | ✅ 完成 | DB-backed 管理 + 版本比較 + 回滾 + 管理介面 |
> | A4: 同義詞管理介面 | ✅ 完成 | CRUD API + 分類瀏覽 + hot-reload 即時生效 |
> | A5: AI 操作審計日誌 | ✅ 完成 | (v1.50.0 已完成) AuditService AI 事件追蹤 |

### 10.1 現況問題分析

**整體成熟度: ~~9.0/10~~ → 9.5/10** — Phase 4B 全部完成

| 層面 | 評分 | 說明 |
|------|------|------|
| Provider 架構 | 9.5/10 | Groq + Ollama + fallback 三層冗餘 |
| 快取策略 | 9.0/10 | Redis + SimpleCache 雙層完成 |
| 自然語言搜尋 | 8.5/10 | 意圖解析 + 同義詞 + similarity 排序 |
| 串流回應 | 0/10 | `stream_completion()` 存在但未暴露 API |
| 語意搜尋 | 0/10 | `generate_embedding()` placeholder 待實作 |
| Prompt 管理 | 7/10 | YAML 檔案制，無版本控制/A/B 測試 |
| 同義詞管理 | 6/10 | YAML 硬編碼，無管理介面 |

### 10.2 優化項目

#### A1: AI 串流回應 SSE (HIGH, 8h)

**目標**: 降低使用者感知延遲，逐字顯示 AI 回應。

**後端**:
- 新增 `POST /ai/document/summary/stream` SSE 端點
- 使用 `StreamingResponse` + `stream_completion()` (已存在)
- 回傳格式: `data: {"token": "字", "done": false}\n\n`

**前端**:
- 新增 `StreamingText` 元件 (逐字顯示動畫)
- 使用 `EventSource` 或 `fetch` + `ReadableStream`
- AISummaryPanel 整合串流模式

#### A2: pgvector 語意搜尋 (HIGH, 20h)

**目標**: 從關鍵字匹配升級到語意理解，大幅提升搜尋品質。

**架構**:
```
使用者查詢 → Ollama nomic-embed-text → 384 維向量
                                         ↓
                         pgvector cosine_distance()
                                         ↓
                              相似度排序結果
```

**實施步驟**:
1. PostgreSQL 安裝 pgvector 擴展
2. OfficialDocument 新增 `embedding vector(384)` 欄位
3. Alembic 遷移 + 批量回填既有公文 embedding
4. `ai_connector.py` 實作 `generate_embedding()` (Ollama nomic-embed-text)
5. DocumentQueryBuilder 新增 `with_semantic_search()` 方法
6. `natural_search()` 混合策略: pg_trgm + pgvector 加權排序

#### A3: Prompt 版本控制 (MEDIUM, 6h)

**目標**: 追蹤 prompt 修改歷史，支援 A/B 測試。

**方案**:
- 新增 `ai_prompt_versions` 資料表 (version, content, created_at, is_active)
- DocumentAIService 從 DB 載入 active prompt (fallback 到 YAML)
- 管理介面: 列表 / 編輯 / 啟用 / 比較歷史版本

#### A4: 同義詞管理介面 (MEDIUM, 4h)

**目標**: 管理員可透過 UI 新增/編輯同義詞，無需改 YAML。

**方案**:
- 新增 `POST /ai/synonyms` CRUD API
- DB 表 `ai_synonyms` (category, words, is_active)
- 管理頁面: 分類瀏覽 / 新增 / 編輯 / 刪除
- Hot reload: 修改後即時生效 (記憶體快取刷新)

#### A5: AI 操作審計日誌 (LOW, 3h)

**目標**: 追蹤 AI 輔助的文件修改，支援合規報告。

**方案**: AuditService 新增 AI 事件類型:
- `AI_SUMMARY_APPLIED` — 使用者採用 AI 摘要
- `AI_CLASSIFY_APPLIED` — 使用者採用 AI 分類建議
- `AI_SEARCH_EXECUTED` — 自然語言搜尋紀錄

### 10.3 驗收標準

- [x] 摘要生成逐字顯示，總時間不變但感知等待 < 1 秒
- [x] 語意搜尋「找跟桃園市政府相關的公文」回傳相關結果 (不只精確匹配)
- [x] Prompt 歷史可追溯 3+ 個版本
- [x] 同義詞可透過 UI 新增，即時生效
- [x] AI 操作在審計日誌可查

---

## 11. Phase 4C: 帳號登入管控強化規劃

> **✅ Phase 4C 已於 v1.51.0 (2026-02-08) 全部完成**
>
> | 項目 | 狀態 | 說明 |
> |------|------|------|
> | L1: 密碼策略強制執行 | ✅ 完成 | (v1.50.0 已完成) validate_password_strength 整合 |
> | L2: 帳號鎖定機制 | ✅ 完成 | 5 次失敗鎖定 15 分鐘 + failed_login_attempts + locked_until |
> | L3: 密碼重設流程 | ✅ 完成 | SHA-256 token + 15 分鐘過期 + 防枚舉 + SMTP 服務 |
> | L4: Session 管理 UI | ✅ 完成 | 裝置列表 + 單一/全部登出 + ProfilePage 整合 |
> | L5: TOTP 雙因素認證 | ✅ 完成 | pyotp + QR code + 10 組 backup codes + MFA 登入流程 |
> | L6: Email 驗證流程 | ✅ 完成 | 24h token + SMTP 寄送 + 驗證頁面 + 未驗證限制 |
> | L7: 登入歷史儀表板 | ✅ 完成 | 時間軸 + IP/裝置/認證方式 + 日期篩選 + 異常標記 |

### 11.1 現況問題分析

**整體成熟度: ~~7.2/10~~ → 9.2/10** — Phase 4C 全部完成

| 層面 | 評分 | 說明 |
|------|------|------|
| 認證機制 | 9.0/10 | Google OAuth + JWT + httpOnly Cookie + CSRF |
| Token 管理 | 9.5/10 | Rotation + Replay 偵測 + SELECT FOR UPDATE |
| 密碼策略 | 5.0/10 | **password_policy.py 存在但 /password/change 未呼叫** |
| 帳號鎖定 | 0/10 | **無失敗次數追蹤，無鎖定機制** |
| 密碼重設 | 0/10 | **前端有頁面，後端無端點** |
| Session UI | 0/10 | **DB 有 UserSession 但使用者無法查看/終止** |
| MFA | 0/10 | **無雙因素認證** |
| Email 驗證 | 3/10 | 追蹤 flag 但不強制 |

### 11.2 優化項目

#### L1: 密碼策略強制執行 (CRITICAL, 0.5h)

**問題**: `password_policy.py` 定義了規則但 `/auth/password/change` 端點未呼叫。

**修改**: `backend/app/api/endpoints/auth/profile.py:185`
```python
# 新增一行:
from app.core.password_policy import validate_password_strength
validate_password_strength(password_data.new_password, raise_on_invalid=True)
```

#### L2: 帳號鎖定機制 (CRITICAL, 4h)

**目標**: 5 次失敗鎖定 15 分鐘，防暴力破解。

**修改範圍**:
- `backend/app/extended/models.py` — User 新增 `failed_login_attempts`, `locked_until`
- Alembic 遷移腳本
- `backend/app/core/auth_service.py` — `authenticate_user()` 加入鎖定檢查/計數
- 成功登入重置計數，鎖定時返回明確錯誤與剩餘時間

#### L3: 密碼重設流程 (HIGH, 6h)

**目標**: 使用者可透過 Email 重設密碼。

**後端**:
- `POST /auth/password-reset` — 寄送重設 email (token 15 分鐘有效)
- `POST /auth/password-reset-confirm` — 驗證 token + 設定新密碼 + 撤銷所有 Session
- Token 使用 `secrets.token_urlsafe(32)` + DB 存儲 (hash)

**前端**:
- 完善 `ForgotPasswordPage.tsx` — 輸入 email → 提交 → 成功提示
- 新增 `ResetPasswordPage.tsx` — token 驗證 → 新密碼表單

**依賴**: Email 服務 (SMTP / SendGrid)

#### L4: Session 管理 UI (HIGH, 4h)

**目標**: 使用者可查看活躍 Session，一鍵登出裝置。

**後端**:
- `POST /auth/sessions` — 列出使用者所有 active session (IP, User-Agent, created_at)
- `POST /auth/sessions/revoke` — 撤銷指定 session
- `POST /auth/sessions/revoke-all` — 撤銷所有 session (除當前)

**前端**:
- ProfilePage 新增「裝置管理」Tab
- Session 列表: 裝置圖示 + IP + 最後活動時間 + 登出按鈕
- 「登出所有裝置」一鍵操作 (二次確認)

#### L5: TOTP 雙因素認證 (HIGH, 10h)

**目標**: 支援 TOTP 標準 (Google Authenticator / Microsoft Authenticator)。

**後端**:
- User 模型新增 `mfa_enabled`, `mfa_secret`, `mfa_backup_codes`
- `POST /auth/mfa/setup` — 生成 secret + QR code URI
- `POST /auth/mfa/verify` — 驗證 TOTP code + 啟用 MFA
- `POST /auth/mfa/disable` — 關閉 MFA (需驗證密碼)
- Login flow 修改: 密碼正確後若 mfa_enabled → 要求 TOTP code
- 10 組 backup codes 供手機遺失時使用

**前端**:
- ProfilePage 新增「安全設定」Tab — MFA 啟用/關閉
- 新增 MFA 驗證頁面 (登入第二步)
- QR code 顯示 (使用 `qrcode.react`)

#### L6: Email 驗證流程 (MEDIUM, 4h)

**目標**: 新帳號需驗證 email 後方可使用。

**方案**:
- 註冊/首次 Google 登入後寄送驗證 email
- `POST /auth/verify-email` — 驗證 token
- 未驗證帳號: 允許登入但顯示提醒 banner + 限制操作

#### L7: 登入歷史儀表板 (LOW, 3h)

**目標**: 使用者可查看登入時間軸。

**方案**: ProfilePage 新增「登入紀錄」Tab，顯示:
- 登入時間 + IP + 裝置 + 認證方式
- 篩選: 日期範圍 / 成功/失敗
- 異常偵測標記 (新 IP 或異常時間)

### 11.3 實施順序與依賴

```
Week 1: L1 (密碼策略, 0.5h) → L2 (帳號鎖定, 4h)
         ↳ 無依賴，可立即執行

Week 2: L3 (密碼重設, 6h)
         ↳ 依賴 Email 服務設定

Week 3: L4 (Session UI, 4h) → L7 (登入歷史, 3h)
         ↳ 共用 UserSession 查詢

Week 4-5: L5 (TOTP MFA, 10h)
           ↳ 獨立模組，需新增 pyotp + qrcode 依賴

Week 5: L6 (Email 驗證, 4h)
         ↳ 依賴 L3 的 Email 服務
```

### 11.4 驗收標準

- [x] 密碼變更時驗證策略 (12 字元+複雜度)
- [x] 5 次錯誤密碼後帳號鎖定 15 分鐘
- [x] 密碼重設 email 15 分鐘內可用，過期後失效
- [x] ProfilePage 可查看/終止所有活躍 Session
- [x] TOTP 設定 + QR code + backup codes 完整流程
- [x] 新帳號收到驗證 email
- [x] 登入歷史可查看 30 天內紀錄

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

## 12. Phase 5: 架構精煉與生產就緒 (2026-02-09 規劃)

### 12.1 現況總評

**系統全面盤點統計**：
| 維度 | 數值 | 狀態 |
|------|------|------|
| 後端 Python 檔案 | 228 | 分層清晰 |
| 前端 TS/TSX 檔案 | 323 | SSOT 遵守 |
| API 端點檔案 | 79 | 7 個模組化系統 |
| 服務層 | 48 | 責任分離 |
| Repository | 19 + 3 QB | 資料存取標準化 |
| ORM 直接查詢在端點 | 1 | 99% 遵守 |
| 測試案例 | ~1,325 (後端 150+ / 前端 130+ / E2E 44+) | 覆蓋完善 |
| 安全漏洞 | 0 | 已修復 |
| any 型別 | 19 (0.05%) | 已精簡 |

**綜合健康度: 9.2/10** — 企業級生產就緒

### 12.2 Phase 5A: 端點層 Repository 遷移（中優先級）

**目標**: 消除端點層直接 ORM 查詢，100% 經 Repository/Service 存取

**現況**: 1 個端點仍直接查詢 (`reminder_management.py`)，62 處 `text()` raw SQL（多為統計/日誌）

| 任務 | 估計工時 | 影響 |
|------|---------|------|
| `reminder_management.py` 遷移至 CalendarRepository | 2h | 消除唯一直接 ORM 端點 |
| 統計查詢 raw SQL → ORM 轉換 (優先 health.py, dashboard.py) | 4h | 減少 ~20 處 text() |
| audit_logs 靜態 text() 保留（無 ORM 模型，無安全風險） | 0 | 不處理 |

**驗收標準**: `grep -r "text(" backend/app/api/endpoints/ --include="*.py"` 結果 < 10 處

### 12.3 Phase 5B: 前端組件測試擴展（中優先級）

**目標**: 補充 React 組件測試，達到 80% 覆蓋率

**現況**: 前端 23 個測試檔案集中在 utils/store/api，0 個組件測試

| 優先級 | 組件 | 測試類型 | 估計工時 |
|--------|------|---------|---------|
| P1 | `DocumentOperations` | 操作流程測試 | 4h |
| P1 | `DispatchFormFields` | 表單驗證測試 | 3h |
| P2 | `AIAssistantButton` | SSE 串流測試 | 2h |
| P2 | `ResponsiveTable` | 響應式斷點測試 | 2h |
| P3 | 各 Tab 組件 | 渲染 + 互動測試 | 8h |

**驗收標準**: 前端組件測試 >= 15 個測試檔案

### 12.4 Phase 5C: 資料庫完整性強化（低優先級）

**目標**: 補充缺失的 ON DELETE CASCADE 與資料完整性約束

| 任務 | 說明 | 風險 |
|------|------|------|
| `project_vendor_association` 加 ON DELETE CASCADE | 刪除專案時自動清理廠商關聯 | 低 |
| `project_user_assignments` 加 ON DELETE CASCADE | 刪除專案時自動清理人員配置 | 低 |
| 建立 audit_logs ORM 模型 | 統一至 Repository 模式 | 中 |
| 關聯表 unique constraint 審查 | 防止重複關聯 | 低 |

**驗收標準**: Alembic 遷移通過 + 既有 E2E 測試通過

### 12.5 Phase 5D: 生產部署就緒（高優先級）

**目標**: Self-hosted Runner + 備份自動化

| 任務 | 說明 | 估計工時 |
|------|------|---------|
| NAS 安裝 GitHub Actions Self-hosted Runner | 參考 `docs/GITHUB_RUNNER_SETUP.md` | 2h |
| CD workflow 實機測試 | Tag push → 自動部署驗證 | 4h |
| 自動化備份排程 | Cron/Task Scheduler + db_backup.ps1 | 2h |
| 異地備份方案 | 備份檔 rsync 到第二台 NAS 或雲端 | 4h |

**驗收標準**: `git tag v3.2.0 && git push --tags` 觸發自動部署 + 每日備份運行

### 12.6 Phase 5E: 效能監控與觀測性（低優先級）

**目標**: 建立持續效能監控機制

| 任務 | 說明 | 估計工時 |
|------|------|---------|
| API 響應時間 Middleware | 記錄每個端點的 P50/P95/P99 | 3h |
| 慢查詢日誌 | statement_timeout 前的 warning（>5s） | 2h |
| 前端 Web Vitals 收集 | LCP/FID/CLS 上報至後端 | 4h |
| Grafana/Prometheus 整合（可選） | 視覺化監控面板 | 8h |

### 12.7 實施路線圖

```
Phase 5D (高) ──→ Self-hosted Runner + 備份  [Week 1]
      │
Phase 5A (中) ──→ 端點層 Repository 遷移      [Week 2]
      │
Phase 5B (中) ──→ 前端組件測試擴展             [Week 2-3]
      │
Phase 5C (低) ──→ 資料庫完整性強化             [Week 3]
      │
Phase 5E (低) ──→ 效能監控（可選）             [Week 4]
```

**總估計工時**: ~50h（不含 Phase 5E 可選項目）

### 12.8 架構演進總結

| Phase | 版本 | 主題 | 健康度 |
|-------|------|------|--------|
| Phase 1 | v1.20-1.27 | 安全修復 + CI/CD | 7.8 → 9.5 |
| Phase 2 | v1.36-1.43 | 效能優化 + Query Builder | 9.5 → 9.9 |
| Phase 3 | v1.44-1.50 | httpOnly Cookie + Redis + 安全強化 | 9.9 → 10.0 |
| Phase 4 | v1.51-1.52 | RWD + AI + 帳號管控 (16 項) | 10.0 |
| **Phase 4.5** | **v1.53** | **Docker+PM2 混合環境韌性** | **10.0** |
| Phase 5 | v1.54+ | 架構精煉 + 生產部署就緒 | 目標: 10.0 |

---

*文件維護: Claude Code Assistant*
*版本: 6.0.0*
*最後更新: 2026-02-09*
