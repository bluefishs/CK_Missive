# 開發強制規範

## 開發前強制檢視 (MANDATORY)

任何開發任務開始前，必須先完成對應規範檢視。

**檔案位置**: `.claude/MANDATORY_CHECKLIST.md`

| 任務類型 | 必讀檢查清單 |
|---------|-------------|
| 新增前端路由/頁面 | 清單 A - 前端路由開發 |
| 新增後端 API | 清單 B - 後端 API 開發 |
| 新增/修改導覽項目 | 清單 C - 導覽項目變更 |
| 修改認證/權限 | 清單 D - 認證權限變更 |
| 資料匯入功能 | 清單 E - 資料匯入功能 |
| 資料庫變更 | 清單 F - 資料庫變更 |
| Bug 修復 | 清單 G - Bug 修復 |
| 新增/修改型別定義 | 清單 H - 型別管理 (SSOT) |
| Docker/PM2 環境配置 | 清單 W - Docker+PM2 混合環境 |
| 可選功能開發 | 清單 X - Feature Flags |

### 導覽項目必須同步的三處位置

1. `frontend/src/router/types.ts` - ROUTES 常數
2. `frontend/src/router/AppRouter.tsx` - Route 元素
3. `backend/app/scripts/init_navigation_data.py` - DEFAULT_NAVIGATION_ITEMS

### UI 設計強制規範 (v5.2.0+)

| 規範 | 說明 |
|------|------|
| **DetailPageLayout** | 所有詳情頁必須使用 `components/common/DetailPage/DetailPageLayout`，禁止自訂 layout |
| **導航模式** | CRUD 操作採 navigate to page，禁止 Modal/Drawer 編輯 |
| **Inline 新增** | Select 下拉找不到選項時，使用 `dropdownRender` 提供即時新增 |
| **Tab 建立** | 使用 `createTabItem(key, { icon, text, count? }, children)` 統一工具函數 |

### 跨模組案號規範 (v5.2.0+)

| 欄位 | 產生時機 | 用途 |
|------|---------|------|
| `case_code` | 建案時（邀標/報價階段） | PM Cases + ERP Quotations + contract_projects 的跨模組橋樑 |
| `project_code` | 成案時（確認執行） | Contract Projects 的正式專案編號，避免未成案跳號 |

### 委託單位/協力廠商規範 (v5.2.0+)

| vendor_type | 管理頁面 | 說明 |
|------------|---------|------|
| `subcontractor` | `/vendors` | 協力廠商（乾坤委託別人） |
| `client` | `/clients` | 委託單位（別人委託乾坤） |

---

## 0. 不得引入新增費用的設計（owner 2026-08-21 立規）

> **「規範不得要新增額外費用之設計」**

任何方案在提出之前先回答：**它會不會產生新的經常性支出？**
會的話，除非 owner 明確同意，否則不採用 —— 並改提零成本的替代方案。

這不是新政策，是既有決策的明文化：

| 時間 | 決策 |
|---|---|
| 2026-03-09 | **GitHub Actions 全面停用**（收費）—— 只保留 `workflow_dispatch` |
| 2026-06-17 | 維持免費：不付費模型、不升 GPU（Groq／NVIDIA 免費 tier + 本地 ollama） |
| 2026-08-21 | 評估 `anthropics/claude-code-security-review` → **不導入**（每次分析計費、且 Actions 已停用） |

### 這條規範同時管「別人用、我們付費」

對外開放的推論端點就是這一類。2026-08-21 實測：`/api/ai/*` 的摘要、分類、
自然語言搜尋、語音轉錄、圖表與視覺分析**全部未經認證**，公網任何人
只要先從公開的 CSRF token 端點取一枚 token 就打得到 —— 那是**我們的 GPU
與 LLM 額度**。已補上 `require_auth()`。

### 零成本替代的判準

外部工具能做的事，先問「既有資產做不做得到」：

* 那次要解的是「哪些端點沒有認證」。既有的 grep 規則產生 **122 個誤判**
  （真問題的 6 倍），認不出 `Depends(require_auth())`；
* 而 **FastAPI 的 runtime dependency 樹**是權威來源，零成本、可接排程，
  一查就是 71 條 —— 成品是 `public_endpoint_auth_audit.py`（weekly 64）。

---

## 1. API 端點一致性

```typescript
// ✅ 正確 - 使用端點常數（靜態端點）
import { DOCUMENTS_ENDPOINTS } from './endpoints';
apiClient.post(DOCUMENTS_ENDPOINTS.LIST, params);

// ✅ 正確 - 使用函數型端點（動態路徑）
import { AI_ENDPOINTS } from './endpoints';
apiClient.post(AI_ENDPOINTS.ANALYSIS_GET(documentId));

// ❌ 禁止 - 硬編碼路徑
apiClient.post('/documents-enhanced/list', params);

// ❌ 禁止 - 字串拼接（應改為函數型端點）
apiClient.post(`${AI_ENDPOINTS.ANALYSIS}/${documentId}`);
```

**注意**: `authService.ts` 使用獨立 axios 實例，同樣必須使用端點常數。

## 2. 環境設定管理 (SSOT)

所有環境設定統一使用專案根目錄的 `.env` 檔案。

| 位置 | 規範 |
|------|------|
| `/.env` | 唯一來源 |
| `/backend/.env` | **禁止存在** |

## 2.5 紀年一律西元（owner 2026-08-29 裁示）

> **「系統統一採西元年建置資料與查詢服務」**

| 層 | 用什麼 |
|---|---|
| **DB 欄位** | **西元**（`pm_cases.year`／`contract_projects.year`／`erp_quotations.year` 實查全是西元，無任何 115 之類的值） |
| **API 查詢參數** | **西元**。後端不得在收到 `year` 後 `+1911` |
| **前端送出** | **西元**（`new Date().getFullYear()`，**不減 1911**） |
| **顯示層** | 民國、西元皆可，依畫面需求 —— 這一層不受本規範限制 |
| **外部資料解析** | 依來源格式（財政部 API／發票 QR／匯入 xls 都是民國）—— 解析後**立即轉西元**再進系統 |

### 為什麼立這條

2026-08-29 一天內抓到**四個「年度篩選從未生效」**：委託單位帳款／廠商帳款／
財務總覽／發票彙總。四者的形狀完全相同 —— **前端送民國 115、後端比對西元 2026**，
於是選了年度永遠是空的，而**兩邊各自用自己的紀年、沒有任何一方會報錯**。

土壤不是四個各自的疏忽，是**契約不統一**：同一支 service 裡
`get_company_overview` 收民國（`+1911`）而 `get_all_projects_summary` 收西元，
兩種寫法都「對」，只看你讀到哪一段。

### 相容處理（不靜默接受）

存量呼叫端可能還在送民國年。後端收到 `year < 1911` 時**轉換並 `logger.warning` 出聲**，
不得靜默接受 —— 靜默轉換會讓錯誤的呼叫端永遠不會被發現。

### 已改的地方（2026-08-29）

`erp/financial_summary.get_company_overview`／`ai/graph/graph_entity_graph_builder`
（後端不再 +1911）；前端 client-accounts／vendor-accounts／財務總覽／發票彙總／
知識圖譜（改送西元）。

⚠️ **不在此規範範圍**：`case_code.py` 的 `year > 1911 ? year : year + 1911` 是
**產號時的輸入容錯**（人可能手打民國年），不是查詢參數；`quotation_document.py`
的 `year - 1911` 是**輸出到正式文件**的顯示格式。兩者都保留。

---

## 3. 型別定義同步 (SSOT)

<!--enforced-by: scripts/checks/schema_ssot_audit.py-->

每個實體型別只能有一個「真實來源」定義。

> **2026-08-17**：這條規範寫了很久、大家大致遵守，**但在此之前沒有任何機制在強制**
> —— 累積出 6 檔 18 個違規而無人知曉，發現它的是 stop hook 讀規範，
> 不是 159 支檢核裡的任何一支。18 個當天全數搬回 `schemas/`，
> 現在由 `schema_ssot_audit`（weekly 59）**嚴格**把關：任何本地 BaseModel 都是 RED。
> 收斂的完整作法見 `docs/architecture/STANDARD_CONVERGENCE_PLAYBOOK.md`。

### 後端

| 位置 | 規範 |
|------|------|
| `backend/app/schemas/` | Pydantic Schema (唯一來源) |
| `backend/app/api/endpoints/` | **禁止**本地 BaseModel |

```python
# ✅ 從 schemas 匯入
from app.schemas.document import DocumentCreateRequest, DocumentUpdateRequest

# ❌ 禁止本地定義
class DocumentCreateRequest(BaseModel):  # 不允許！
    ...
```

### 前端

| 位置 | 規範 |
|------|------|
| `frontend/src/types/api.ts` | 業務實體型別 (唯一來源) |
| `frontend/src/api/*.ts` | **禁止**本地 interface |

```typescript
// ✅ 從 types/api.ts 匯入
import { User, Agency, OfficialDocument } from '../types/api';

// ❌ 禁止在 api/*.ts 中定義
export interface User { ... }  // 不允許！
```

### 新增欄位流程

只需修改：
1. **後端**: `backend/app/schemas/{entity}.py`
2. **前端**: `frontend/src/types/api.ts`

## 4. 程式碼修改後自檢

```bash
cd frontend && npx tsc --noEmit     # TypeScript
cd backend && python -m py_compile app/main.py  # Python
```

## 5. 服務層架構

> ⚠️ **2026-08-28 實測：這一節寫的是方向，不是現況。** 別把它讀成「我們已經這樣做了」。
>
> | 碰 DB 的 service（129 支） | 檔數 | 占比 |
> |---|---|---|
> | 只走 repository | **55** | 43% |
> | **只有直接 `db.execute(select(...))`** | **61** | **47%** |
> | 兩者混用 | 13 | 10% |
>
> 全庫 `services/` 底下直接 `db.execute(select(...))` 共 **435 處、74 個檔案**
> （另有 278 支純邏輯不碰 DB）。
>
> **刻意不把它做成檢核**：第一天就 435 個紅點，而「永遠是紅的訊號與沒有訊號
> 是同一個下場」—— 本 repo 2026-08-27 才在排程稽核上付過這個學費。
> 規範留著（方向是對的），但**現狀寫出來**，免得有人照著它推論「所以資料存取都在 repository」。
>
> **它已經收過一次代價**（2026-08-28）：`erp/quotation_service._get_creator_names_batch`
> 是該檔唯一不走 repository 的批次方法，於是單元測試裡 mock 掉 repository **蓋不到它**，
> `db.execute` 的 AsyncMock 讓 `.all()` 回 coroutine ⇒
> `TypeError: 'coroutine' object is not iterable`，而那支測試在基線外壞了一段時間沒人發現。
> ⇒ **繞過 repository 的直接代價是「測不到」**，不只是分層不好看。
>
> 要收斂的話請先問「哪一段的錯誤代價最高」，而不是從 435 處裡隨機挑。


| 層級 | 位置 | 職責 |
|------|------|------|
| API 層 | `backend/app/api/endpoints/` | HTTP 處理、參數驗證 |
| Service 層 | `backend/app/services/` | 業務邏輯 |
| Repository 層 | `backend/app/repositories/` | 資料存取、ORM 查詢 |
| Model 層 | `backend/app/extended/models.py` | ORM 模型定義 |

**Repository 層**：

| Repository | 特有方法 |
|------------|----------|
| `BaseRepository[T]` | CRUD + 分頁 + 搜尋 |
| `DocumentRepository` | `get_by_doc_number()`, `filter_documents()`, `get_statistics()` |
| `ProjectRepository` | `get_by_project_code()`, `check_user_access()` |
| `AgencyRepository` | `match_agency()`, `suggest_agencies()` |

```python
# ✅ 使用 Repository
from app.repositories import DocumentRepository
doc_repo = DocumentRepository(db)
docs, total = await doc_repo.filter_documents(doc_type='收文', skip=0, limit=20)
```

**BaseService 繼承原則**：簡單 CRUD 用 BaseService，複雜業務邏輯用 Repository。

### 5.1 並行 DB 操作強制規範（ADR-0021）

**asyncpg connection 單飛模式**：一個 connection 同時只能執行一個 operation。
`asyncio.gather` 多個 task 共用同一 session 會導致
`InterfaceError: another operation is in progress`。

```python
# ❌ 錯誤 — 兩個 task 共用同一 db session，會爆 asyncpg race
hints, plan = await asyncio.gather(
    planner.preprocess(db),
    planner.plan_tools(db),
)

# ✅ 正確 — 每個並行 task 使用獨立 session
from app.db.database import run_with_fresh_session

hints, plan = await asyncio.gather(
    run_with_fresh_session(lambda s: planner.preprocess(s)),
    run_with_fresh_session(lambda s: planner.plan_tools(s)),
)
```

**判斷規則**：`asyncio.gather(...)` 內只要有 2+ 個 task 會做 DB 操作（含 ORM 查詢、
`session.execute`、`repository.get_*`），**必須**用 `run_with_fresh_session` 包裝。
單一 task 或純 HTTP/LLM 呼叫不受此限。

## 6. 前端狀態管理 (雙層架構)

| 層級 | 位置 | 職責 |
|------|------|------|
| React Query | `frontend/src/hooks/use*.ts` | API 快取、伺服器同步 |
| Zustand Store | `frontend/src/store/*.ts` | UI 狀態、篩選條件 |
| 整合 Hook | `frontend/src/hooks/use*WithStore.ts` | 結合兩者 |

```typescript
// ✅ 推薦使用整合 Hook
import { useProjectsWithStore } from '../hooks';
const { projects, filters, setFilters } = useProjectsWithStore();
```

**⚠️ 資料取得強制規範**：所有 API 資料取得**必須**使用 `useQuery` / `useMutation`，**禁止** useEffect + 直接 apiClient 呼叫。詳見 `MANDATORY_CHECKLIST.md` 清單 T。

## 7. 關聯記錄處理 (link_id)

```typescript
// ❌ 禁止 - 危險的回退邏輯
const linkId = proj.link_id ?? proj.id;

// ✅ 正確 - 嚴格要求 link_id 存在
if (item.link_id === undefined) {
  message.error('關聯資料缺少 link_id，請重新整理頁面');
  return;
}
```

## 8. 依賴注入 (推薦工廠模式)

```python
# ✅ 工廠模式 (推薦)
from app.core.dependencies import get_service_with_db

@router.get("/documents")
async def list_documents(
    service: DocumentService = Depends(get_service_with_db(DocumentService))
):
    return await service.get_list()
```

常用依賴函數：`get_pagination()`, `get_query_params()`, `require_auth()`, `require_admin()`, `optional_auth()`
