# CK_Missive 強制性開發規範檢查清單

> **版本**: 1.11.0
> **建立日期**: 2026-01-11
> **最後更新**: 2026-02-03
> **狀態**: 強制執行 - 所有開發任務啟動前必須檢視

---

## 重要聲明

**本檢查清單為強制性文件。任何開發任務開始前，必須先完成相關規範檢視。**

違反規範可能導致：
- 程式碼審查不通過
- 前後端資料不同步
- 系統運行異常
- 維護成本增加

---

## 一、開發任務類型判斷

根據任務類型，選擇對應的檢查清單：

| 任務類型 | 必讀規範 | 對應檢查清單 |
|---------|---------|-------------|
| **新增前端路由/頁面** | 路由同步規範 | [清單 A](#清單-a前端路由頁面開發) |
| **新增後端 API** | API 開發規範 | [清單 B](#清單-b後端-api-開發) |
| **新增導覽項目** | 路由同步規範 | [清單 C](#清單-c導覽項目變更) |
| **修改認證/權限** | 前端架構規範 | [清單 D](#清單-d認證權限變更) |
| **資料匯入功能** | 服務層規範 | [清單 E](#清單-e資料匯入功能) |
| **資料庫變更** | 資料庫規範 | [清單 F](#清單-f資料庫變更) |
| **Bug 修復** | 通用規範 | [清單 G](#清單-g-bug-修復) |
| **新增/修改型別定義** | 型別管理規範 | [清單 H](#清單-h型別管理) |
| **前端元件/Hook 開發** | 前端架構規範 | [清單 I](#清單-i前端元件hook-開發) |
| **多對多關聯功能** | **Link ID 規範** | [清單 J](#清單-j關聯記錄處理) |
| **後端 API 開發/返回** | **序列化規範** | [清單 K](#清單-k-api-序列化與資料返回) |
| **前端 API 呼叫** | **端點常數規範** | [清單 L](#清單-l-api-端點常數使用) |
| **效能敏感操作** | **效能檢查規範** | [清單 M](#清單-m效能檢查) |
| **前端 API 請求** | **請求參數處理規範** | [清單 N](#清單-n前端-api-請求參數處理) |
| **Ant Design 元件** | **元件使用規範** | [清單 O](#清單-oant-design-元件使用規範) |
| **Pydantic Schema 開發** | **Python 常見陷阱** | [清單 P](#清單-ppydantic-schema-開發) |
| **非同步資料庫查詢** | **Python 常見陷阱** | [清單 Q](#清單-q非同步資料庫查詢) |
| **新功能部署上線** | **部署驗證規範** | [清單 R](#清單-r部署驗證-v1300-新增) |
| **敏感功能開發** | **安全審查規範** | [清單 S](#清單-s安全審查-v1300-新增) |
| **useEffect 中呼叫 API** | **無限迴圈防護** | [清單 T](#清單-tuseeffect-無限迴圈防護-v1120-新增) |
| **重構/刪除模組** | **跨檔案引用安全** | [清單 U](#清單-u重構刪除模組安全-v1120-新增) |

---

## 清單 A：前端路由/頁面開發

### 必讀文件
- [ ] `docs/DEVELOPMENT_STANDARDS.md` 第九節（前端開發規範）
- [ ] `.claude/skills/frontend-architecture.md`
- [ ] `frontend/src/router/types.ts`（現有路由定義）

### 開發前檢查
- [ ] 確認路由路徑在 `ROUTES` 常數中定義
- [ ] 確認使用 `VITE_API_BASE_URL` 從 `config/env.ts` 取得
- [ ] 確認認證檢測使用 `isAuthDisabled()` 函數

### 開發後檢查
- [ ] TypeScript 編譯通過：`cd frontend && npx tsc --noEmit`
- [ ] 同步更新 `backend/app/scripts/init_navigation_data.py`
- [ ] 執行路由一致性檢查（見清單 C）

---

## 清單 B：後端 API 開發

### 必讀文件
- [ ] `docs/DEVELOPMENT_STANDARDS.md` 第二至四節
- [ ] `docs/specifications/API_ENDPOINT_CONSISTENCY.md`
- [ ] `.claude/skills/api-development.md`

### 開發前檢查
- [ ] 確認使用 `ServiceResponse` 回應結構
- [ ] 確認使用 POST 方法進行資料修改操作
- [ ] 確認輸入使用 Pydantic Schema 驗證

### 開發後檢查
- [ ] Python 語法檢查通過
- [ ] 同步更新前端 `API_ENDPOINTS` 定義
- [ ] API 端點文件更新（若需要）

---

## 清單 C：導覽項目變更

### 必讀文件
- [ ] `.claude/commands/route-sync-check.md`
- [ ] `.claude/skills/frontend-architecture.md`（六、導覽系統架構）
- [ ] `backend/app/scripts/init_navigation_data.py`
- [ ] `frontend/src/router/types.ts`

### ⚠️ 重要架構須知

**主佈局元件是 `Layout.tsx`，非 `DynamicLayout.tsx`**

```
AppRouter.tsx → Layout.tsx → 側邊導覽列
                    ↓
             secureApiService.getNavigationItems()
                    ↓
             convertToMenuItems() → Ant Design Menu
```

**導覽更新事件機制：**
- `SiteManagementPage` 觸發：`window.dispatchEvent(new CustomEvent('navigation-updated'))`
- `Layout.tsx` 監聽：`window.addEventListener('navigation-updated', handler)`

### 同步檢查項目

**新增導覽項目時，必須同步更新四處：**

| 序號 | 位置 | 檔案 | 說明 |
|------|------|------|------|
| 1 | 前端路由定義 | `frontend/src/router/types.ts` | ROUTES 常數 |
| 2 | 前端路由實作 | `frontend/src/router/AppRouter.tsx` | Route 元素 |
| 3 | 後端路徑白名單 | `backend/app/core/navigation_validator.py` | VALID_NAVIGATION_PATHS |
| 4 | 後端導覽定義 | `backend/app/scripts/init_navigation_data.py` | DEFAULT_NAVIGATION_ITEMS |

### 路徑一致性規則
- 前端 ROUTES 定義的路徑 **必須** 與後端導覽的 `path` 完全一致
- 後端路徑白名單會在 API 層面驗證路徑合法性
- 圖標名稱使用 Ant Design 格式：`XxxOutlined`

### 自動化驗證機制 (2026-01-12 新增)

| 機制 | 說明 |
|------|------|
| 後端 API 驗證 | `navigation/action` 的 create/update 會驗證路徑 |
| 前端下拉選單 | SiteManagementPage 路徑欄位使用下拉選單 |
| 初始化腳本 | `--force-update` 參數可強制同步路徑 |
| PowerShell 腳本 | `.claude/hooks/route-sync-check.ps1` |

### 開發後驗證
```bash
# 執行路徑同步檢查
/route-sync-check

# 或使用 PowerShell 腳本
.\.claude\hooks\route-sync-check.ps1

# 強制同步資料庫導覽路徑
cd backend && python app/scripts/init_navigation_data.py --force-update
```

---

## 清單 D：認證/權限變更

### 必讀文件
- [ ] `.claude/skills/frontend-architecture.md`
- [ ] `frontend/src/config/env.ts`
- [ ] `frontend/src/hooks/useAuthGuard.ts`
- [ ] `frontend/src/hooks/usePermissions.ts`

### 強制規範

**認證相關函數唯一來源：**
```typescript
// 正確 - 從 config/env.ts 匯入
import { isAuthDisabled, isInternalIP, detectEnvironment } from '../config/env';

// 禁止 - 重複定義或直接讀取環境變數
const isInternal = window.location.hostname.startsWith('192.168.');  // ❌
```

**環境類型判斷：**
| 類型 | 條件 | 認證行為 |
|------|------|---------|
| localhost (DEV) | localhost + DEV=true | 免認證，自動 admin |
| internal | 內網 IP | 免認證，自動 admin |
| localhost (PROD) | localhost + DEV=false | Google OAuth |
| public | 其他 | Google OAuth |

### 開發後檢查
- [ ] 不得新增 `isInternalIP` 或類似函數的重複實作
- [ ] `ProtectedRoute` 正確處理 `authDisabled` 狀態
- [ ] 側邊欄正確顯示對應權限的選項

---

## 清單 E：資料匯入功能

### 必讀文件
- [ ] `docs/DEVELOPMENT_STANDARDS.md` 第七節
- [ ] `.claude/DEVELOPMENT_GUIDELINES.md`（交易安全檢查）
- [ ] `backend/app/services/base/import_base.py`

### 強制規範

**必須繼承 ImportBaseService：**
```python
from app.services.base.import_base import ImportBaseService

class NewImportService(ImportBaseService):
    async def import_from_file(self, ...): ...
    async def process_row(self, ...): ...
```

**必須使用共用驗證器：**
- `DocumentValidators.validate_doc_type()` - 公文類型驗證
- `StringCleaners.clean_string()` - 字串清理
- `DateParsers.parse_date()` - 日期解析

### 開發後檢查
- [ ] 使用 `ServiceResponse` 回應結構
- [ ] 匯入前呼叫 `reset_serial_counters()`
- [ ] 使用智慧匹配：`match_agency()`, `match_project()`

---

## 清單 F：資料庫變更

### 必讀文件
- [ ] `docs/DATABASE_SCHEMA.md`
- [ ] `.claude/skills/database-schema.md`
- [ ] `backend/app/extended/models.py`

### 強制規範

**欄位命名一致性：**
- 模型欄位名稱 = 資料庫欄位名稱
- 初始化腳本欄位名稱 **必須** 與模型一致

**範例錯誤：**
```python
# 模型定義
class SiteConfiguration(Base):
    key = Column(String(100))  # 欄位名稱是 'key'

# 錯誤的初始化腳本
DEFAULT_CONFIGS = [
    {"config_key": "site_title", ...}  # ❌ 應該用 'key'
]
```

### 開發後檢查
- [ ] 確認模型欄位與初始化腳本一致
- [ ] 必要時建立資料庫遷移
- [ ] 更新 Schema 定義

---

## 清單 G：Bug 修復

### 必讀文件
- [ ] `docs/ERROR_HANDLING_GUIDE.md`
- [ ] `.claude/DEVELOPMENT_GUIDELINES.md`

### 開發前檢查
- [ ] 確認問題根因，不只是修復表面症狀
- [ ] 檢查是否為架構性問題（需要通盤考量）
- [ ] 檢查是否有其他地方存在相同問題

### 開發後檢查
- [ ] TypeScript 編譯通過（前端變更）
- [ ] Python 語法檢查通過（後端變更）
- [ ] 相關測試通過
- [ ] 不引入新的技術債

---

## 清單 H：型別管理

### 必讀文件
- [ ] `.claude/skills/type-management.md`
- [ ] `.claude/commands/type-sync.md`
- [ ] `backend/app/schemas/` (現有 Schema 結構)

### ⚠️ 核心規範：單一真實來源 (SSOT)

**所有 Pydantic BaseModel 定義必須集中在 `schemas/` 目錄**

```
backend/app/schemas/     ← 唯一的型別定義來源
backend/app/api/endpoints/  ← 只匯入，禁止本地定義
```

### 禁止事項

```python
# ❌ 禁止：在 endpoints 中定義 BaseModel
# backend/app/api/endpoints/xxx.py
class MyRequest(BaseModel):  # 違規！
    field: str

# ✅ 正確：從 schemas 匯入
from app.schemas.xxx import MyRequest
```

### 新增型別定義流程

1. **在 `schemas/` 建立或擴展 Schema 檔案**
   ```python
   # backend/app/schemas/xxx.py
   class NewEntity(BaseModel):
       field: str = Field(..., description="欄位說明")
   ```

2. **在 endpoint 匯入使用**
   ```python
   from app.schemas.xxx import NewEntity
   ```

3. **重新生成前端型別**
   ```bash
   cd frontend && npm run api:generate
   ```

4. **(可選) 更新前端型別包裝層**
   ```typescript
   // frontend/src/types/generated/index.ts
   export type ApiNewEntity = components['schemas']['NewEntity'];
   ```

### 開發後檢查
- [ ] `endpoints/` 目錄無本地 BaseModel 定義
- [ ] Python 語法檢查通過：`python -m py_compile app/schemas/*.py`
- [ ] 執行 `npm run api:generate` 更新前端型別
- [ ] TypeScript 編譯通過：`npx tsc --noEmit`

### 快速驗證命令

```bash
# 檢查 endpoints 本地定義數量 (應為 0)
grep -r "class.*\(BaseModel\)" backend/app/api/endpoints/ --include="*.py" | wc -l

# 完整型別同步檢查
/type-sync
```

---

## 清單 I：前端元件/Hook 開發

### 必讀文件
- [ ] `frontend/src/components/README.md`（組件架構規範）
- [ ] `frontend/src/hooks/index.ts`（Hook 組織結構）
- [ ] `frontend/src/utils/validators.ts`（共用驗證器）
- [ ] `frontend/src/repositories/`（Repository 模式）

### ⚠️ 架構須知 (v1.4.0 更新)

**Hooks 目錄結構：**
```
hooks/
├── business/     # 業務邏輯 Hooks (useDocuments, useProjects)
├── system/       # 系統功能 Hooks (useAuth, usePermissions)
├── utility/      # 工具類 Hooks (useResponsive, useForm)
└── index.ts      # 統一匯出
```

**Repository 抽象層：**
```
repositories/
├── BaseRepository.ts    # 抽象基類
├── VendorRepository.ts  # 廠商資料存取
├── AgencyRepository.ts  # 機關資料存取
└── index.ts             # 統一匯出
```

### 組件命名規範

| 類型 | 規則 | 範例 |
|------|------|------|
| 頁面組件 | `*Page.tsx` | `DocumentPage.tsx` |
| 彈窗組件 | `*Modal.tsx` | `UserEditModal.tsx` |
| 表單組件 | `*Form.tsx` | `NavigationItemForm.tsx` |
| 列表組件 | `*List.tsx` | `VendorList.tsx` |
| 管理面板 | `*Management.tsx` | `AgencyManagement.tsx` |

### ⚠️ React Hooks 使用規範 (v1.7.0 新增)

**核心規則：Hooks 必須在元件頂層呼叫，不可在 render 函數內呼叫**

**常見違規案例 - Form.useWatch：**
```tsx
// ❌ 違規：在 render 函數內呼叫 Hook
function MyComponent() {
  const renderPaymentSection = () => {
    const watchedValue = Form.useWatch('field', form);  // 錯誤！
    return <div>{watchedValue}</div>;
  };
  return <div>{renderPaymentSection()}</div>;
}

// ✅ 正確：所有 Hook 在元件頂層
function MyComponent() {
  const watchedValue = Form.useWatch('field', form);  // 頂層

  const renderPaymentSection = () => {
    return <div>{watchedValue}</div>;  // 使用頂層變數
  };
  return <div>{renderPaymentSection()}</div>;
}
```

**多欄位監聽模式：**
```tsx
// ✅ 正確：多個 watch 都在頂層
const watchedWork01 = Form.useWatch('work_01_amount', form) || 0;
const watchedWork02 = Form.useWatch('work_02_amount', form) || 0;
const watchedWork03 = Form.useWatch('work_03_amount', form) || 0;

const totalAmount = useMemo(() => {
  return watchedWork01 + watchedWork02 + watchedWork03;
}, [watchedWork01, watchedWork02, watchedWork03]);
```

### 開發前檢查
- [ ] 確認組件位置符合架構規範
- [ ] Hook 放置於正確的子目錄 (business/system/utility)
- [ ] 使用 `frontend/src/utils/validators.ts` 的共用驗證器
- [ ] **確認所有 Hooks 呼叫在元件頂層（不在 render 函數、條件判斷內）**

### 開發後檢查
- [ ] TypeScript 編譯通過：`cd frontend && npx tsc --noEmit`
- [ ] 組件/Hook 已加入對應的 `index.ts` 匯出
- [ ] 驗證規則與後端 `validators.py` 保持一致
- [ ] **無 "Rendered more hooks than during the previous render" 錯誤**

---

## 清單 J：關聯記錄處理

### 必讀文件
- [ ] `docs/specifications/LINK_ID_HANDLING_SPECIFICATION.md`
- [ ] `frontend/src/types/api.ts`（BaseLink 介面定義）
- [ ] 相關的關聯表模型（如 `taoyuan_dispatch_project_link`）

### ⚠️ 核心概念：實體 ID vs 關聯 ID

**ID 類型區分（必須理解）：**

| ID 類型 | 說明 | 用途 |
|---------|------|------|
| 實體 ID (`id`) | 業務實體主鍵 | 查看、編輯實體 |
| 關聯 ID (`link_id`) | 多對多關聯表主鍵 | **解除關聯操作** |

**錯誤示例（導致 404）：**
```typescript
// ❌ 危險：當 link_id 為 undefined 時會使用實體 ID
const linkId = proj.link_id ?? proj.id;
unlinkApi(projectId, linkId);  // 可能傳入錯誤的 ID
```

### 強制規範

#### 前端：禁止回退邏輯

```typescript
// ❌ 禁止
const linkId = item.link_id ?? item.id;

// ✅ 正確：嚴格要求 link_id 存在
if (item.link_id === undefined || item.link_id === null) {
  message.error('關聯資料缺少 link_id，請重新整理頁面');
  console.error('[unlink] link_id 缺失:', item);
  refetch();
  return;
}
const linkId = item.link_id;
```

#### 前端：UI 條件渲染

```typescript
// ✅ 只有當 link_id 存在時才顯示移除按鈕
{canEdit && item.link_id !== undefined && (
  <Popconfirm onConfirm={() => handleUnlink(item.link_id)}>
    <Button danger>移除關聯</Button>
  </Popconfirm>
)}
```

#### 後端：詳細錯誤訊息

```python
# ✅ 區分「ID 不匹配」和「ID 不存在」兩種錯誤
if not link:
    existing = await db.execute(select(LinkTable).where(LinkTable.id == link_id))
    if existing.scalar_one_or_none():
        raise HTTPException(404, f"link_id={link_id} 對應的實體 ID 不匹配")
    else:
        raise HTTPException(404, f"關聯記錄 ID {link_id} 不存在")
```

### 關聯表設計規範

**命名規範：**
| 項目 | 規則 | 範例 |
|------|------|------|
| 關聯表名稱 | `{entity1}_{entity2}_link` | `taoyuan_dispatch_project_link` |
| API 響應欄位 | 統一使用 `link_id` | `"link_id": 123` |
| 外鍵命名 | `{entity}_id` | `dispatch_order_id`, `project_id` |

**API 響應必須包含：**
```json
{
  "link_id": 123,        // 關聯記錄 ID（必填）
  "entity_id": 456,      // 被關聯實體 ID
  "link_type": "...",    // 關聯類型（若適用）
  "created_at": "..."    // 建立時間
}
```

### 開發前檢查
- [ ] 確認後端 API 響應包含 `link_id` 欄位
- [ ] 確認前端類型定義 `link_id: number`（非 optional）
- [ ] 確認 unlink API 的參數說明文檔

### 開發後檢查
- [ ] 搜尋危險模式：`grep -r "link_id ??" frontend/src/`
- [ ] 搜尋 any 類型：`grep -r ": any" frontend/src/pages/`
- [ ] 後端錯誤訊息能區分「ID 不匹配」和「ID 不存在」
- [ ] TypeScript 編譯通過
- [ ] Python 語法檢查通過

### 受影響的 API 端點

| 端點 | link_id 來源表 |
|------|----------------|
| `/project/{id}/unlink-dispatch/{link_id}` | `taoyuan_dispatch_project_link` |
| `/dispatch/{id}/unlink-document/{link_id}` | `taoyuan_dispatch_document_link` |
| `/document/{id}/unlink-dispatch/{link_id}` | `taoyuan_dispatch_document_link` |
| `/document/{id}/unlink-project/{link_id}` | `taoyuan_document_project_link` |

---

## 清單 K：API 序列化與資料返回

### 必讀文件
- [ ] `docs/FIX_REPORT_2026-01-21_API_SERIALIZATION.md`（案例分析）
- [ ] `.claude/skills/type-management.md`
- [ ] `backend/app/schemas/`（現有 Schema 結構）

### ⚠️ 核心問題：ORM 模型無法直接序列化

**典型錯誤**:
```
pydantic_core.PydanticSerializationError: Unable to serialize unknown type: <class 'app.extended.models.XXX'>
```

**原因**: 直接返回 SQLAlchemy ORM 模型，Pydantic 無法自動序列化。

### 強制規範

#### 規範 1：禁止直接返回 ORM 模型

```python
# ❌ 禁止：直接返回 ORM 模型列表
result = await db.execute(select(Document))
documents = result.scalars().all()
return {"items": documents}  # 錯誤！

# ✅ 正確方式 A：使用 Pydantic Schema
from app.schemas.document import DocumentResponse
return {"items": [DocumentResponse.model_validate(doc) for doc in documents]}

# ✅ 正確方式 B：手動轉換為字典
return {"items": [
    {
        "id": doc.id,
        "name": doc.name,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }
    for doc in documents
]}
```

#### 規範 2：Schema 欄位類型必須與資料庫一致

**典型錯誤**:
```
asyncpg.exceptions.DataError: invalid input for query argument: expected str, got int
```

**對照表範例**:

| 欄位 | DB 類型 | Schema 類型 | 說明 |
|------|---------|------------|------|
| `priority` | `VARCHAR(50)` | `str` | 需一致 |
| `status` | `VARCHAR(50)` | `str` | 需一致 |
| `count` | `INTEGER` | `int` | 需一致 |

**若無法修改 Schema，需在 Service 層轉換**:
```python
# Service 層類型轉換
if key == 'priority' and value is not None:
    value = str(value)  # 確保類型正確
```

#### 規範 3：欄位名稱必須與資料庫模型一致

```python
# ❌ 錯誤：使用不存在的欄位名稱
{"type": doc.type}  # OfficialDocument 沒有 'type' 欄位

# ✅ 正確：使用實際欄位名稱
{"doc_type": doc.doc_type}  # 正確的欄位名稱
```

#### 規範 4：datetime 欄位必須轉換為 ISO 格式

```python
# ❌ 錯誤：直接返回 datetime 對象
{"created_at": doc.created_at}  # 可能無法序列化

# ✅ 正確：轉換為 ISO 格式字串
{"created_at": doc.created_at.isoformat() if doc.created_at else None}
```

### 常見 Schema-DB 類型不一致

| 情境 | Schema 定義 | DB 定義 | 問題 | 解法 |
|------|------------|---------|------|------|
| 優先級 | `priority: int` | `VARCHAR(50)` | asyncpg 類型錯誤 | 改 Schema 為 `str` 或 Service 層轉換 |
| 狀態 | `status: StatusEnum` | `VARCHAR` | Enum 序列化 | 使用 `.value` |
| ID | `id: str` | `INTEGER` | 類型不符 | 統一使用 `int` |

#### 規範 5：批次處理效能優化 (v1.7.0 新增)

```python
# ❌ 錯誤：每筆都 commit，造成 N 次資料庫寫入
for item in items:
    if needs_update(item):
        item.calculated_field = await calculate(item)
        await db.commit()  # N 次 commit！

# ✅ 正確：收集後批次 commit
items_to_update = []
for item in items:
    if needs_update(item):
        item.calculated_field = await calculate(item)
        items_to_update.append(item)
if items_to_update:
    await db.commit()  # 一次 commit
```

#### 規範 6：避免硬編碼設定值 (v1.7.0 新增)

```python
# ❌ 錯誤：硬編碼預算金額
total_budget = 6035000  # 如果金額變更需改程式碼

# ✅ 正確：從資料庫動態取得
budget_result = await db.execute(
    select(ContractProject.winning_amount)
    .where(ContractProject.id == contract_project_id)
)
total_budget = budget_result.scalar_one_or_none() or 0
```

### 開發前檢查
- [ ] 確認 API 返回格式（Schema 或字典）
- [ ] 確認 Schema 欄位類型與 DB 一致
- [ ] 確認欄位名稱與 ORM 模型一致
- [ ] **確認業務設定值從資料庫或設定檔取得（非硬編碼）**

### 開發後檢查
- [ ] 測試 API 端點，確認無 500 錯誤
- [ ] 檢查 response 中 datetime 已轉換為 ISO 格式
- [ ] 搜尋直接返回 ORM 的程式碼：
```bash
grep -r "\.scalars()\.all()" backend/app/api/endpoints/ --include="*.py"
```
- [ ] **確認迴圈內無逐筆 commit（應批次處理）**

### 快速驗證命令

```bash
# 測試 API 端點
curl -X POST http://localhost:8001/api/{endpoint} \
  -H "Content-Type: application/json" \
  -d '{}' | jq .

# 檢查後端日誌中的序列化錯誤
pm2 logs ck-backend --lines 50 | grep -i "serialize\|serialization"
```

---

## 清單 L：API 端點常數使用

### 必讀文件
- [ ] `frontend/src/api/endpoints.ts`（API 端點定義）
- [ ] `docs/specifications/API_ENDPOINT_CONSISTENCY.md`
- [ ] `.claude/skills/api-development.md`

### ⚠️ 核心規範：禁止硬編碼 API 路徑

**所有 API 呼叫必須使用 `API_ENDPOINTS` 常數**

```typescript
// ❌ 禁止：硬編碼路徑
apiClient.post('/documents-enhanced/list', params);
apiClient.get('/taoyuan-dispatch/projects/123');

// ✅ 正確：使用集中管理的端點常數
import { API_ENDPOINTS } from '../api/endpoints';
apiClient.post(API_ENDPOINTS.DOCUMENTS.LIST, params);
apiClient.get(`${API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECTS.BASE}/${id}`);
```

### 端點命名規範

| 類型 | 命名格式 | 範例 |
|------|---------|------|
| 列表查詢 | `{ENTITY}.LIST` | `API_ENDPOINTS.DOCUMENTS.LIST` |
| 單筆查詢 | `{ENTITY}.GET` | `API_ENDPOINTS.DOCUMENTS.GET` |
| 新增 | `{ENTITY}.CREATE` | `API_ENDPOINTS.PROJECTS.CREATE` |
| 更新 | `{ENTITY}.UPDATE` | `API_ENDPOINTS.VENDORS.UPDATE` |
| 刪除 | `{ENTITY}.DELETE` | `API_ENDPOINTS.AGENCIES.DELETE` |
| 基礎路徑 | `{ENTITY}.BASE` | `API_ENDPOINTS.TAOYUAN_DISPATCH.BASE` |

### 新增端點流程

1. **後端建立 API 端點**
2. **更新前端 `endpoints.ts`**
   ```typescript
   export const API_ENDPOINTS = {
     NEW_MODULE: {
       BASE: '/new-module',
       LIST: '/new-module/list',
       CREATE: '/new-module/create',
     }
   };
   ```
3. **在呼叫處使用常數**

### 開發前檢查
- [ ] 確認需要呼叫的 API 是否已在 `endpoints.ts` 定義
- [ ] 若無，先更新 `endpoints.ts`

### 開發後檢查
- [ ] 搜尋硬編碼路徑：
```bash
grep -rn "apiClient\.\(get\|post\|put\|delete\).*'/\|\"/" frontend/src/ --include="*.ts" --include="*.tsx" | grep -v "endpoints"
```
- [ ] 確認新端點已加入 `API_ENDPOINTS`
- [ ] TypeScript 編譯通過

---

## 清單 M：效能檢查

### 必讀文件
- [ ] `.claude/skills/database-performance.md`
- [ ] `.claude/hooks/performance-check.ps1`
- [ ] `docs/Architecture_Optimization_Recommendations.md`

### ⚠️ 核心問題：N+1 查詢

**N+1 查詢是最常見的效能問題**

```python
# ❌ 問題：N+1 查詢
projects = await db.execute(select(Project))
for project in projects.scalars():
    # 每次迭代都發出額外查詢！
    print(project.vendors)  # N 次額外查詢

# ✅ 正確：使用 selectinload 預載入
from sqlalchemy.orm import selectinload

stmt = select(Project).options(
    selectinload(Project.vendors),
    selectinload(Project.documents)
)
projects = await db.execute(stmt)
for project in projects.scalars():
    print(project.vendors)  # 無額外查詢
```

### 強制規範

#### 規範 1：迴圈中禁止 db 查詢

```python
# ❌ 禁止
for doc_id in document_ids:
    doc = await db.execute(select(Document).where(Document.id == doc_id))

# ✅ 正確：批次查詢
docs = await db.execute(
    select(Document).where(Document.id.in_(document_ids))
)
```

#### 規範 2：列表查詢必須有分頁

```python
# ❌ 禁止：無限制查詢
result = await db.execute(select(Document))

# ✅ 正確：使用分頁
result = await db.execute(
    select(Document).offset(skip).limit(limit)
)
```

#### 規範 3：多層關聯必須明確載入

```python
# ✅ 多層關聯載入
stmt = select(TaoyuanDispatchOrder).options(
    selectinload(TaoyuanDispatchOrder.project_links)
        .selectinload(TaoyuanDispatchProjectLink.project),
    selectinload(TaoyuanDispatchOrder.document_links)
        .selectinload(TaoyuanDispatchDocumentLink.document)
)
```

### 效能檢測指令

```bash
# 執行效能檢查 Hook
powershell -File .claude/hooks/performance-check.ps1

# 搜尋潛在 N+1 模式
grep -rn "for .* in.*:" backend/app/api/endpoints/ --include="*.py" -A 5 | grep "await db\."

# 啟用 SQLAlchemy 查詢日誌
export SQLALCHEMY_ECHO=True
```

### 效能反模式清單

| 反模式 | 問題 | 解法 |
|--------|------|------|
| 迴圈中 db 查詢 | N+1 查詢 | 批次查詢 + IN 子句 |
| 無分頁 | 載入過多資料 | 加入 limit/offset |
| SELECT * | 傳輸無用欄位 | 只選取需要的欄位 |
| 未使用索引 | 全表掃描 | 建立適當索引 |
| 重複查詢 | 相同資料多次取得 | 快取或變數暫存 |

### 開發前檢查
- [ ] 確認是否涉及大量資料操作
- [ ] 確認關聯資料載入策略

### 開發後檢查
- [ ] 執行 `/performance-check` 指令
- [ ] 無 N+1 查詢警告
- [ ] 列表 API 已實作分頁
- [ ] 多層關聯已使用 selectinload

---

## 清單 N：前端 API 請求參數處理

### 必讀文件
- [ ] `.claude/skills/_shared/backend/api-development.md`（前端 API 請求參數處理規範）
- [ ] `frontend/src/api/vendorsApi.ts`（參考範本）

### ⚠️ 核心問題：undefined 值導致 422 錯誤

**問題描述**：
前端傳送 API 請求時，`undefined` 值會被 `JSON.stringify()` 轉換為 `null`，
後端 Pydantic 收到 `null` 後驗證失敗，回傳 422 Unprocessable Entity。

**典型錯誤日誌**：
```
POST /api/vendors/list 422 (Unprocessable Content)
```

### 強制規範

#### 規範 1：禁止直接傳入可能為 undefined 的值

```typescript
// ❌ 禁止：undefined 會被序列化為 null
const queryParams = {
  page: params?.page ?? 1,
  search: params?.search,         // undefined → JSON null → 422
  status: params?.status,         // undefined → JSON null → 422
};

// ✅ 正確：使用條件式添加
const queryParams: Record<string, unknown> = {
  page: params?.page ?? 1,
};
if (params?.search) queryParams.search = params.search;
if (params?.status) queryParams.status = params.status;
```

#### 規範 2：特殊類型的判斷條件

| 參數類型 | 判斷條件 | 說明 |
|---------|---------|------|
| 字串 | `if (params?.field)` | 空字串視為無效 |
| 數值 | `if (params?.field !== undefined)` | 0 是有效值 |
| 布林 | `if (params?.field !== undefined)` | false 是有效值 |
| 陣列 | `if (params?.field?.length)` | 空陣列視為無效 |

```typescript
// 布林值範例
if (params?.is_active !== undefined) queryParams.is_active = params.is_active;

// 數值範例（0 是有效年度）
if (params?.year !== undefined) queryParams.year = params.year;
```

### 開發前檢查
- [ ] 確認 API 的可選參數有哪些
- [ ] 確認各參數的資料類型（字串/數值/布林）

### 開發後檢查
- [ ] 搜尋可能的違規模式：
```bash
grep -rn "params\?\." frontend/src/api/ --include="*.ts" | grep -v "if ("
```
- [ ] 測試 API 無 422 錯誤
- [ ] TypeScript 編譯通過

### 已修復的參考範本

| 檔案 | 修復的參數 |
|------|-----------|
| `vendorsApi.ts` | `search`, `business_type` |
| `projectsApi.ts` | `search`, `year`, `category`, `status` |
| `agenciesApi.ts` | `search`, `agency_type` |
| `usersApi.ts` | `search`, `role`, `is_active` |

---

## 清單 O：Ant Design 元件使用規範

### 必讀文件
- [ ] [Ant Design 官方文件](https://ant.design/components/overview)
- [ ] `frontend/src/components/common/`（通用元件）

### ⚠️ 常見元件警告與錯誤

#### 問題 1：Spin 元件 tip 屬性警告

**警告訊息**：
```
[antd: Spin] `tip` only work in nest or fullscreen pattern
```

**原因**：`tip` 屬性只在 Spin 包裹子元件（nest 模式）時有效

```tsx
// ❌ 錯誤：獨立 Spin 使用 tip
<Spin size="large" tip="載入中..." />

// ✅ 正確：Spin 包裹內容（nest 模式）
<Spin spinning={loading} tip="載入中...">
  <div style={{ minHeight: 200 }}>
    {!loading && children}
  </div>
</Spin>
```

#### 問題 2：Tag 元件沒有 size 屬性

**錯誤訊息**：
```
Property 'size' does not exist on type 'IntrinsicAttributes & TagProps'
```

**解決方案**：使用 style 控制大小

```tsx
// ❌ 錯誤：Tag 沒有 size 屬性
<Tag size="small">標籤</Tag>

// ✅ 正確：使用 style
<Tag style={{ fontSize: 12 }}>標籤</Tag>
```

#### 問題 3：Row 元件 align 屬性

**有效值**：`'top' | 'middle' | 'bottom' | 'stretch'`

```tsx
// ❌ 錯誤：使用無效值
<Row align="start">...</Row>

// ✅ 正確
<Row align="top">...</Row>
<Row align="middle">...</Row>
```

### 強制規範

| 元件 | 常見錯誤 | 正確用法 |
|------|---------|---------|
| `Spin` | 獨立使用 `tip` | 必須包裹子元件 |
| `Tag` | 使用 `size` 屬性 | 使用 `style={{ fontSize }}` |
| `Row` | `align="start"` | `align="top"` |
| `Modal` | 未設定 `destroyOnClose` | 表單 Modal 需設定 |

### 開發前檢查
- [ ] 查閱 Ant Design 官方文件確認 API

### 開發後檢查
- [ ] 瀏覽器 Console 無 antd 警告
- [ ] TypeScript 編譯通過

---

## 清單 P：Pydantic Schema 開發

### 必讀文件
- [ ] `.claude/skills/python-common-pitfalls.md`（Python 常見陷阱規範）
- [ ] `backend/app/schemas/`（現有 Schema 結構）

### ⚠️ 核心問題 1：前向引用 (Forward Reference)

**錯誤訊息**：
```
PydanticUserError: TaoyuanProjectListResponse is not fully defined;
you may need to call TaoyuanProjectListResponse.model_rebuild()
```

**原因**：使用字串型別提示時，該型別在使用時尚未被解析。

### 強制規範

#### 規範 1：在 `__init__.py` 呼叫 model_rebuild()

```python
# ❌ 錯誤：直接匯出未解析的 Schema
# schemas/__init__.py
from .project import TaoyuanProjectListResponse
from .links import TaoyuanProjectWithLinks
# 直接使用會報錯！

# ✅ 正確：匯入後呼叫 model_rebuild()
from .project import TaoyuanProjectListResponse
from .links import TaoyuanProjectWithLinks

# 重建前向引用 (解決循環依賴)
TaoyuanProjectListResponse.model_rebuild()
```

#### 規範 2：使用 TYPE_CHECKING 避免循環匯入

```python
# schemas/project.py
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .links import TaoyuanProjectWithLinks

class TaoyuanProjectListResponse(BaseModel):
    items: List["TaoyuanProjectWithLinks"]  # 使用字串前向引用
```

### ⚠️ 核心問題 2：預設參數被 None 覆蓋

**問題**：函數參數有預設值，但傳入 `None` 時預設值不會生效。

```python
# ❌ 錯誤：None 會覆蓋預設值
def get_next_number(prefix: str = '乾坤測字第'):
    return f"{prefix}001號"

get_next_number(None)  # 返回 "None001號" 而非 "乾坤測字第001號"

# ✅ 正確：在函數內部處理 None
def get_next_number(prefix: Optional[str] = None):
    if prefix is None:
        prefix = '乾坤測字第'
    return f"{prefix}001號"
```

### 開發前檢查
- [ ] 確認是否使用前向引用（字串型別提示）
- [ ] 確認函數參數是否可能接收 None

### 開發後檢查
- [ ] `__init__.py` 中有呼叫 `model_rebuild()`（若使用前向引用）
- [ ] 函數內部有處理 `None` 參數的邏輯
- [ ] 測試 API 端點無序列化錯誤

---

## 清單 Q：非同步資料庫查詢

### 必讀文件
- [ ] `.claude/skills/python-common-pitfalls.md`（Python 常見陷阱規範）
- [ ] `backend/app/repositories/`（Repository 模式範例）

### ⚠️ 核心問題：MissingGreenlet 錯誤

**錯誤訊息**：
```
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called;
can't call await_only() here. Was IO attempted in an unexpected place?
```

**原因**：在 async context 中存取未預載入的 relationship 屬性。

### 強制規範

#### 規範 1：必須使用 selectinload() 預載入關聯

```python
# ❌ 錯誤：未預載入關聯
async def get_document(db: AsyncSession, doc_id: int):
    result = await db.execute(
        select(OfficialDocument).where(OfficialDocument.id == doc_id)
    )
    doc = result.scalar_one()
    project_name = doc.contract_project.project_name  # MissingGreenlet 錯誤！

# ✅ 正確：預載入關聯
from sqlalchemy.orm import selectinload

async def get_document(db: AsyncSession, doc_id: int):
    result = await db.execute(
        select(OfficialDocument)
        .options(selectinload(OfficialDocument.contract_project))
        .where(OfficialDocument.id == doc_id)
    )
    doc = result.scalar_one()
    project_name = doc.contract_project.project_name  # 安全
```

#### 規範 2：多層關聯必須鏈式載入

```python
# ✅ 多層關聯預載入
result = await db.execute(
    select(TaoyuanDispatchOrder)
    .options(
        selectinload(TaoyuanDispatchOrder.project_links)
            .selectinload(TaoyuanDispatchProjectLink.project),
        selectinload(TaoyuanDispatchOrder.document_links)
            .selectinload(TaoyuanDispatchDocumentLink.document),
    )
    .where(TaoyuanDispatchOrder.id == dispatch_id)
)
```

#### 規範 3：載入策略選擇

| 策略 | 用途 | SQL 行為 |
|------|------|----------|
| `selectinload()` | 一對多、多對多 | 額外 SELECT IN 查詢 |
| `joinedload()` | 多對一 | LEFT JOIN 同一查詢 |
| `raiseload('*')` | 禁止 lazy load | 存取時拋出異常（開發時除錯用） |

### 開發前檢查
- [ ] 列出查詢後會存取的所有 relationship 屬性
- [ ] 確認關聯的層級（一層或多層）

### 開發後檢查
- [ ] 測試 API 端點無 MissingGreenlet 錯誤
- [ ] 確認無 N+1 查詢問題
- [ ] 複雜查詢使用 `raiseload('*')` 驗證無遺漏

### 快速驗證命令

```bash
# 搜尋可能缺少預載入的查詢
grep -rn "\.scalars()" backend/app/api/endpoints/ --include="*.py" -B 5 | grep -v "selectinload\|joinedload"

# 啟用 SQLAlchemy 查詢日誌檢查 N+1
export SQLALCHEMY_ECHO=True
```

---

## 二、通用開發後檢查清單

**所有開發任務完成後，必須執行：**

### 程式碼檢查
```bash
# 前端 TypeScript 編譯
cd frontend && npx tsc --noEmit

# 後端語法檢查
cd backend && python -m py_compile app/main.py
```

### 一致性檢查
- [ ] 前後端型別定義一致
- [ ] API 端點路徑一致
- [ ] 導覽路由一致

### 文件更新
- [ ] 必要時更新規範文件
- [ ] 必要時更新 CHANGELOG

---

## 三、違規處理流程

### 發現違規時
1. 停止當前開發工作
2. 閱讀相關規範文件
3. 修正違規項目
4. 重新執行檢查清單
5. 確認通過後繼續

### 常見違規類型

| 違規類型 | 說明 | 修正方式 |
|---------|------|---------|
| 路由不同步 | 前端路由與後端導覽不一致 | 執行清單 C |
| 認證重複實作 | 在多處定義 isInternalIP | 統一使用 config/env.ts |
| 欄位名稱錯誤 | 初始化腳本欄位名與模型不符 | 對照模型修正腳本 |
| 缺少驗證 | 未使用共用驗證器 | 改用 DocumentValidators |

---

## 四、快速參考

### 關鍵檔案位置

| 用途 | 檔案路徑 |
|------|---------|
| 前端路由定義 | `frontend/src/router/types.ts` |
| 前端路由實作 | `frontend/src/router/AppRouter.tsx` |
| 後端導覽定義 | `backend/app/scripts/init_navigation_data.py` |
| 後端路徑白名單 | `backend/app/core/navigation_validator.py` |
| 認證配置 | `frontend/src/config/env.ts` |
| 服務基類 | `backend/app/services/base/` |
| 後端驗證器 | `backend/app/services/base/validators.py` |
| 前端驗證器 | `frontend/src/utils/validators.ts` |
| 前端 Repository | `frontend/src/repositories/` |
| 前端 Hooks | `frontend/src/hooks/` |
| 組件架構規範 | `frontend/src/components/README.md` |
| 開發規範 | `docs/DEVELOPMENT_STANDARDS.md` |

### 常用指令

```bash
# 路由一致性檢查
/route-sync-check

# API 端點檢查
/api-check

# 型別同步檢查
/type-sync

# 開發環境檢查
/dev-check
```

---

## 清單 R：部署驗證 (v1.30.0 新增)

### 必讀文件
- [ ] `docs/DEPLOYMENT_CHECKLIST.md` - 完整性檢查清單
- [ ] `docs/DEPLOYMENT_GAP_ANALYSIS.md` - 缺漏分析
- [ ] `.claude/commands/verify.md` - 驗證指令

### ⚠️ 核心概念：代碼提交 ≠ 功能上線

**部署流程三階段：**
```
本地開發 → Git 提交 → 生產部署
                        ↑
                  必須手動或自動觸發
```

### 開發完成後檢查

#### 本地驗證
- [ ] 執行 `/verify` 確認 Build/Type/Lint/Test 通過
- [ ] 確認所有相關檔案已暫存：`git status`
- [ ] 確認 TypeScript 編譯通過
- [ ] 確認 Python 語法檢查通過

#### Git 提交
- [ ] 代碼已推送至遠端：`git push origin main`
- [ ] CI 檢查通過（GitHub Actions）

#### 生產部署
- [ ] 通知運維或自行執行部署
- [ ] 在生產服務器拉取最新代碼
- [ ] 重啟相關服務
- [ ] 執行端點可用性驗證

### 部署驗證指令

```bash
# 在生產服務器執行
cd /share/Container/CK_Missive
git pull origin main
docker-compose restart backend

# 驗證 API 端點
curl -X POST http://localhost:8001/api/[endpoint] \
  -H "Content-Type: application/json" -d "{}"
```

### 功能驗證清單
- [ ] 新增 API 端點可正常呼叫
- [ ] 前端頁面可正常載入
- [ ] 相關功能操作正常
- [ ] 無 Console 錯誤
- [ ] 無 Network 錯誤

### 回滾準備
- [ ] 記錄當前版本 commit hash
- [ ] 確認回滾指令可用：`git checkout [hash]`
- [ ] 備份資料庫（若有資料變更）

---

## 清單 S：安全審查 (v1.30.0 新增)

### 必讀文件
- [ ] `.claude/rules/security.md` - 安全規則
- [ ] `.claude/agents/security-reviewer.md` (若有)
- [ ] `backend/app/core/security_utils.py` - 安全工具

### 敏感功能檢查

#### 認證相關
- [ ] 無硬編碼密碼
- [ ] 密碼使用 bcrypt/argon2 雜湊
- [ ] JWT 正確驗證
- [ ] Session 管理安全

#### 資料輸入
- [ ] 所有輸入使用 Pydantic 驗證
- [ ] SQL 查詢使用 ORM（無字串拼接）
- [ ] 檔案上傳有驗證（類型、大小）

#### API 安全
- [ ] 敏感操作使用 POST 方法
- [ ] 有適當的認證和授權檢查
- [ ] 有 Rate Limiting
- [ ] 錯誤訊息不洩漏敏感資訊

### 安全掃描指令

```bash
# 依賴漏洞掃描
npm audit
pip-audit

# 密碼掃描
grep -r "password\|api_key\|secret" --include="*.py" --include="*.ts" .
```

---

## 清單 T：useEffect 無限迴圈防護 (v1.12.0 新增)

### 事前檢查
- [ ] useEffect 依賴陣列中**不包含**任何 API 回應值 (total, count, data.length, unreadCount)
- [ ] useEffect 中的 API 呼叫**不會**透過 setState 間接改變自身依賴
- [ ] 若需要 API 回應的派生狀態，使用 `useMemo` 而非 useEffect

### Code Review 必查項目
- [ ] 確認無「state → useEffect → API → setState → re-render → useEffect」循環
- [ ] catch 區塊中**不要**用 API 回應值覆蓋 state（避免二次觸發）
- [ ] 優先使用 React Query 的 `useQuery` 而非 useEffect + 手動 fetch

### 判斷規則

| 可以放入依賴陣列 | 禁止放入依賴陣列 |
|------------------|------------------|
| 使用者輸入的篩選條件 | API 回應的 total / count |
| URL 參數 (id, page) | 從 API 回應衍生的 state |
| 使用者選擇的 tab | data.length / isLoading |
| 元件外部 props (非 API 回應) | refetch 回傳值 |

**相關事故**: 2026-02-06 DocumentTabs.tsx 無限迴圈 → 後端 OOM → 全系統崩潰

---

## 清單 U：重構/刪除模組安全 (v1.12.0 新增)

### 刪除函數或模組前
- [ ] **已全域 grep 確認所有引用點** (`grep -r "函數名" backend/` 或 `Ctrl+Shift+F`)
- [ ] 每個引用點都已更新或移除
- [ ] 刪除後執行 `python -c "from app.api.routes import api_router"` 驗證 import

### 重命名或移動後
- [ ] 所有 `from old_module import xxx` 都改為 `from new_module import xxx`
- [ ] 前端若有對應的 API 呼叫路徑也已同步更新
- [ ] CI 的 Python import 驗證能捕捉到此類錯誤

### 安全原則
- 刪除前先 grep，永遠不要「先刪再看」
- 重構大型模組時，保留向後相容的 re-export（至少一個版本週期）

**相關事故**: 2026-02-06 vendors.py ImportError 導致後端啟動失敗

---

## 版本記錄

| 版本 | 日期 | 說明 |
|------|------|------|
| 1.12.0 | 2026-02-06 | **新增清單 T、U**（useEffect 無限迴圈防護、重構/刪除模組安全）- 連鎖崩潰事故後建立 |
| 1.11.0 | 2026-02-03 | **新增清單 R、S**（部署驗證、安全審查）- Everything Claude Code 整合 |
| 1.10.0 | 2026-01-28 | **新增清單 P、Q**（Pydantic Schema 開發、非同步資料庫查詢）- Python 常見陷阱規範 |
| 1.9.0 | 2026-01-22 | **新增清單 N、O**（前端 API 請求參數處理、Ant Design 元件使用規範） |
| 1.8.0 | 2026-01-22 | **新增清單 L、M**（API 端點常數使用規範、效能檢查規範） |
| 1.7.0 | 2026-01-22 | 新增 React Hooks 使用規範、批次處理效能優化、避免硬編碼設定值 |
| 1.6.0 | 2026-01-21 | **新增清單 K - API 序列化與資料返回**（ORM 模型序列化、Schema-DB 類型一致性、欄位名稱檢查） |
| 1.5.0 | 2026-01-21 | 新增清單 J - 關聯記錄處理規範（link_id vs id 概念區分、禁止回退邏輯、詳細錯誤訊息） |
| 1.4.0 | 2026-01-21 | 新增清單 I - 前端元件/Hook 開發（Hooks 目錄重組、Repository 層、共用驗證器） |
| 1.3.0 | 2026-01-18 | 新增清單 H - 型別管理規範 (SSOT 架構) |
| 1.2.0 | 2026-01-12 | 新增導覽路徑自動化驗證機制（白名單、下拉選單、強制同步） |
| 1.1.0 | 2026-01-12 | 新增導覽系統架構說明（Layout.tsx vs DynamicLayout.tsx） |
| 1.0.0 | 2026-01-11 | 初版建立 |

---

*本文件為強制性規範，所有開發人員必須遵守*
