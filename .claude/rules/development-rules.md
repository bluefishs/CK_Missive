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

## 3. 型別定義同步 (SSOT)

每個實體型別只能有一個「真實來源」定義。

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
