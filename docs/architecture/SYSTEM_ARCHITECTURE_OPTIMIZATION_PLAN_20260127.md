# CK_Missive 系統架構優化建議規劃

> **文件版本**: 1.0.0
> **分析日期**: 2026-01-27
> **專案版本**: v1.13.0
> **分析範圍**: 模組化、元件化、服務層、型別、SSOT、RWD
> **分析工具**: Claude Code 深度探索

---

## 目錄

1. [現況總結](#一現況總結)
2. [模組化建議](#二模組化建議)
3. [元件化建議](#三元件化建議)
4. [服務層架構建議](#四服務層架構建議)
5. [型別管理與 SSOT 建議](#五型別管理與-ssot-建議)
6. [RWD 響應式設計建議](#六rwd-響應式設計建議)
7. [綜合優先順序](#七綜合優先順序)
8. [關鍵指標追蹤](#八關鍵指標追蹤)
9. [風險與注意事項](#九風險與注意事項)
10. [附錄：詳細分析數據](#十附錄詳細分析數據)

---

## 一、現況總結

### 1.1 整體評分

| 維度 | 評分 | 狀態 | 說明 |
|------|------|------|------|
| **模組化** | 7/10 | ⚠️ | API 端點模組化良好，但服務層分層不完整 |
| **元件化** | 7.3/10 | ⚠️ | 共用元件完整，但存在 10 個超大元件需拆分 |
| **服務層** | 6/10 | ❌ | Repository 層已建立但**未整合**，DI 模式混合 |
| **型別 (SSOT)** | 8.5/10 | ✅ | 基本達成 SSOT，少數合理的 API 層本地型別 |
| **RWD** | 8.5/10 | ✅ | useResponsive Hook 統一管理，65% 元件使用 Grid |

### 1.2 程式碼規模統計

| 層級 | 檔案數 | 程式碼行數 | 說明 |
|------|--------|-----------|------|
| 前端總計 | ~200 | 79,586 行 | React + TypeScript |
| 前端元件 | 65 | 17,996 行 | 平均 277 行/元件 |
| 前端頁面 | 60 | 23,967 行 | 平均 399 行/頁面 |
| 前端 Hooks | 29 | ~15,000 行 | 業務/系統/工具分層 |
| 後端服務 | 21 | ~8,000 行 | 架構不一致 |
| 後端 Schema | 23 | ~3,000 行 | SSOT 集中管理 |

---

## 二、模組化建議

### 2.1 後端模組化現況

```
backend/app/
├── api/endpoints/          # ✅ 良好：按功能模組化
│   ├── documents/          # 公文 API (6 個子模組)
│   │   ├── list.py
│   │   ├── crud.py
│   │   ├── stats.py
│   │   ├── export.py
│   │   ├── import_.py
│   │   └── audit.py
│   ├── document_calendar/  # 行事曆 API (4 個子模組)
│   └── taoyuan_dispatch/   # 桃園派工 API (5 個子模組)
├── services/               # ⚠️ 待改進：21 個服務，架構不一致
│   ├── base/               # BaseService, ImportBaseService
│   ├── document_service.py # 1,000+ 行，未使用 Repository
│   └── ...
├── repositories/           # ❌ 問題：已建立但未使用 (0%)
│   ├── base.py             # BaseRepository[T] 泛型
│   ├── document.py         # DocumentRepository
│   ├── project.py          # ProjectRepository
│   └── agency.py           # AgencyRepository
└── schemas/                # ✅ 良好：23 個 Schema 集中管理
```

### 2.2 服務層架構問題

**現況分析**：

| 服務類型 | 數量 | 比例 | 狀態 |
|----------|------|------|------|
| 使用 BaseService | 4 | 19% | ✅ 正確 |
| 使用 Factory DI | 4 | 19% | ✅ 正確 |
| 使用 Singleton DI | 3 | 14% | ⚠️ 舊模式 |
| 無 DI / 手動實例化 | 10 | 48% | ❌ 需修正 |
| 使用 Repository | 0 | 0% | ❌ 關鍵問題 |

### 2.3 建議行動

| 優先級 | 項目 | 工作量 | 影響 |
|--------|------|--------|------|
| **P0** | 整合 Repository 層至 DocumentService | 3-4 天 | 高 |
| **P1** | 統一 DI 模式 (全面採用 Factory) | 2-3 天 | 中 |
| **P2** | 將 AdminService/BackupService 納入 DI 框架 | 1 天 | 低 |

### 2.4 Repository 整合範例

```python
# ❌ 目前：DocumentService 直接查詢 DB (1000+ 行)
class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(self, filters):
        query = select(Document)
        if filters.doc_type:
            query = query.where(Document.doc_type == filters.doc_type)
        # ... 50+ 行查詢建構邏輯
        return await self.db.execute(query)

# ✅ 目標：使用 Repository 模式
class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DocumentRepository(db)  # 委託 Repository

    async def get_list(self, filters):
        # 查詢邏輯封裝在 Repository
        return await self.repository.filter_documents(
            doc_type=filters.doc_type,
            status=filters.status,
            search=filters.search,
            skip=filters.skip,
            limit=filters.limit
        )
```

---

## 三、元件化建議

### 3.1 超大元件識別

**前端元件 (400+ 行需拆分)**：

| 元件 | 目前行數 | 複雜度 | 拆分優先級 |
|------|----------|--------|-----------|
| Layout.tsx | 786 行 | 🔴 極高 | P0 |
| DocumentList.tsx | 760 行 | 🔴 極高 | P0 |
| DashboardCalendarSection | 711 行 | 🔴 高 | P1 |
| DocumentImport.tsx | 665 行 | 🔴 高 | P1 |
| IntegratedEventModal | 661 行 | 🔴 高 | P1 |
| EnhancedDatabaseViewer | 648 行 | 🟠 中-高 | P2 |
| SimpleDatabaseViewer | 625 行 | 🟠 中-高 | P2 |
| PaymentsTab.tsx | 640 行 | 🟠 中-高 | P2 |
| EnhancedCalendarView | 605 行 | 🟠 中-高 | P2 |
| EventFormModal.tsx | 586 行 | 🟠 中-高 | P2 |

**超大頁面 (500+ 行需拆分)**：

| 頁面 | 目前行數 | 功能模組 |
|------|----------|----------|
| ReportsPage.tsx | 1,067 行 | 經費/公文統計圖表 |
| TaoyuanProjectDetailPage | 1,023 行 | 工程詳情、多 Tab |
| ReceiveDocumentCreatePage | 849 行 | 收文表單 |
| SendDocumentCreatePage | 821 行 | 發文表單 |
| DocumentDetailPage.tsx | 818 行 | 公文詳情、6 個 Tab |

### 3.2 拆分方案

#### Layout.tsx (786 行 → ~200 行)

```
目前結構：
├── Layout.tsx (786 行)
    ├── 導覽邏輯 (Menu 項目生成)
    ├── 權限判斷
    ├── 使用者下拉菜單
    └── 通知中心

拆分後：
├── Layout.tsx (主框架，150 行)
├── layout/
│   ├── Sidebar.tsx (導覽欄，250 行)
│   ├── Header.tsx (頂部欄，200 行)
│   ├── UserMenu.tsx (使用者選單，100 行)
│   └── hooks/
│       └── useMenuItems.ts (導覽邏輯，150 行)
```

#### DocumentList.tsx (760 行 → ~300 行)

```
目前結構：
├── DocumentList.tsx (760 行)
    ├── 表格顯示
    ├── 搜尋/篩選
    ├── 分頁邏輯
    ├── 批量操作
    └── 導出功能

拆分後：
├── DocumentList.tsx (主容器，300 行)
├── DocumentList/
│   ├── DocumentTable.tsx (表格，350 行)
│   ├── TableActions.tsx (操作欄，100 行)
│   └── BatchActions.tsx (批量操作，100 行)
```

### 3.3 共用元件抽取

**重複邏輯需提取**：

| 重複元件 | 出現位置 | 重複行數 | 建議 |
|----------|----------|----------|------|
| AttachmentTab | document, contractCase, taoyuan | ~400 行 | → `SharedAttachmentTab` |
| RelatedDocumentsTab | document, contractCase | ~200 行 | → `SharedRelatedDocuments` |
| ModalFormLogic | ~15 個 Modal | ~300 行 | → `useModalForm` Hook |
| FileUploadLogic | DocumentImport, Operations 等 | ~200 行 | → `useFileUpload` Hook |
| TableFilterLogic | DocumentFilter 等 | ~150 行 | → `useTableFilter` Hook |

### 3.4 建議的元件目錄重組

```
frontend/src/components/
├── common/                     # 通用元件 (已完善)
│   ├── DetailPage/
│   ├── FormPage/
│   ├── UnifiedTable/
│   ├── SharedAttachmentTab/    # 🆕 從 3 處合併
│   └── SharedRelatedDocuments/ # 🆕 從 2 處合併
├── document/                   # 公文元件
│   ├── DocumentList/           # 重構後 ~300 行
│   │   ├── index.tsx
│   │   ├── DocumentTable.tsx
│   │   ├── TableActions.tsx
│   │   └── BatchActions.tsx
│   ├── DocumentFilter/         # ✅ 已良好模組化
│   └── operations/             # ✅ 已良好拆分
├── layout/                     # 🆕 新增
│   ├── Sidebar.tsx
│   ├── Header.tsx
│   ├── UserMenu.tsx
│   └── hooks/
│       └── useMenuItems.ts
└── calendar/
    └── ... (既有結構)
```

### 3.5 Hook 拆分建議

**複雜 Hook 需拆分**：

| Hook | 目前行數 | 建議拆分 |
|------|----------|----------|
| usePermissions.ts | 10,112 行 | → usePermissionCache, usePermissionValidation, useRoleManagement |
| useDashboardCalendar.ts | 7,719 行 | → useDashboardCalendarData, useDashboardCalendarFilter |
| useDocumentRelations.ts | 8,369 行 | → useDocRelationData, useDocRelationActions |

---

## 四、服務層架構建議

### 4.1 目標架構

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (endpoints/)                    │
│  Depends(get_service_with_db(DocumentService))              │
│  職責：HTTP 處理、參數驗證、回應格式化                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Service Layer (services/)                  │
│  DocumentService → self.repository = DocumentRepository(db) │
│  職責：業務邏輯、跨實體操作、驗證規則                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                Repository Layer (repositories/)              │
│  DocumentRepository：filter_documents(), get_statistics()    │
│  職責：純資料存取、查詢建構、分頁處理                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Model Layer (models.py)                   │
│  ORM 模型定義                                                │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 依賴注入標準化

**統一採用 Factory 模式**：

```python
# backend/app/core/dependencies.py

# ✅ 推薦：Factory 模式
def get_service_with_db(service_class: Type[T]):
    def _get_service(db: AsyncSession = Depends(get_async_db)):
        return service_class(db)
    return _get_service

# 使用方式
get_document_service = get_service_with_db(DocumentService)

# API 端點
@router.post("/list")
async def list_documents(
    service: DocumentService = Depends(get_document_service)
):
    return await service.get_list()  # 無需傳遞 db
```

### 4.3 執行計畫

**Phase 1 (2 週)**: Repository 整合

| 步驟 | 說明 | 檔案 |
|------|------|------|
| 1 | 將 DocumentService 的查詢邏輯遷移至 DocumentRepository | `repositories/document.py` |
| 2 | DocumentService 改用 Repository | `services/document_service.py` |
| 3 | 為 ProjectService 新增 Repository 使用 | `services/project_service.py` |
| 4 | 更新單元測試 | `tests/unit/test_services/` |

**Phase 2 (1 週)**: DI 標準化

| 步驟 | 說明 | 檔案 |
|------|------|------|
| 1 | 為 AdminService 建立 Factory | `core/dependencies.py` |
| 2 | 為 BackupService 建立 Factory | `core/dependencies.py` |
| 3 | 更新所有 endpoints 使用 Depends() | `api/endpoints/*.py` |

---

## 五、型別管理與 SSOT 建議

### 5.1 現況評估

| 層級 | SSOT 遵循度 | 狀態 | 說明 |
|------|-------------|------|------|
| 後端 Schema | 100% | ✅ | `schemas/` 統一定義，23 個檔案 |
| 前端型別 | 95% | ✅ | `types/api.ts` (2,700+ 行) |
| API 層本地型別 | 合理 | ✅ | 查詢參數、統計型別等 API 特定邏輯 |

### 5.2 後端 Schema 結構

```
backend/app/schemas/
├── __init__.py            # 中央匯出 (SSOT 入點)
├── common.py              # 通用格式 (ErrorCode, PaginationMeta)
├── document.py            # 公文 Schema
├── project.py             # 專案 Schema
├── vendor.py              # 廠商 Schema
├── agency.py              # 機關 Schema
├── user.py                # 使用者 Schema
├── certification.py       # 證照 Schema
├── document_calendar.py   # 行事曆 Schema
├── taoyuan_dispatch.py    # 派工 Schema
└── ... (共 23 個)
```

### 5.3 前端型別結構

```
frontend/src/types/
├── api.ts                 # 業務實體型別 SSOT (2,700+ 行)
│   ├── OfficialDocument, DocumentCreate, DocumentUpdate
│   ├── Project, ProjectCreate, ProjectUpdate
│   ├── Agency, Vendor, User
│   ├── CalendarEvent, TaoyuanProject
│   └── ... (所有業務實體)
├── index.ts               # 統一匯出
└── navigation.ts          # 導覽型別
```

### 5.4 API 層允許的本地型別

| 型別類別 | 命名規範 | 說明 | 範例 |
|----------|----------|------|------|
| 查詢參數 | `${Entity}ListParams` | API 特定搜尋欄位 | `DocumentListParams` |
| 統計資料 | `${Entity}Statistics` | API 聚合計算結果 | `VendorStatistics` |
| 列表回應 | `${Entity}ListResponse` | 分頁包裝 | `ProjectStaffListResponse` |
| 原始格式 | `Raw${Entity}Response` | 後端原始格式 (需轉換) | `RawCalendarEventResponse` |

### 5.5 改進建議

**建議 1：萃取共用查詢參數基類**

```typescript
// frontend/src/types/api.ts 新增

export interface BaseQueryParams extends PaginationParams, SortParams {
  search?: string;
}

export interface DocumentQueryParams extends BaseQueryParams {
  doc_number?: string;
  doc_type?: string;
  category?: string;
  date_from?: string;
  date_to?: string;
}

export interface ProjectQueryParams extends BaseQueryParams {
  year?: number;
  category?: string;
  status?: string;
}

// 各 API 檔案直接匯入使用，減少重複定義
```

**建議 2：新增自動化 SSOT 檢查腳本**

```powershell
# scripts/check-type-ssot.ps1

# 檢查 api/*.ts 中是否有違反 SSOT 的業務實體定義
$violations = Get-ChildItem -Path "frontend/src/api/*.ts" |
    Select-String -Pattern "export interface (User|Document|Project|Agency|Vendor)\b" |
    Where-Object { $_.Filename -ne "types.ts" }

if ($violations) {
    Write-Host "❌ SSOT 違反：以下檔案定義了應在 types/api.ts 中定義的業務實體型別" -ForegroundColor Red
    $violations | ForEach-Object { Write-Host $_.Line }
    exit 1
}

Write-Host "✅ SSOT 檢查通過" -ForegroundColor Green
```

**建議 3：型別管理指南補充**

在 `.claude/skills/type-management.md` 新增：

```markdown
## API 層型別定義指南

### 允許的本地型別
1. **查詢參數型別** (`ListParams`, `QueryParams`)
2. **列表回應型別** (`ListResponse`, `*Response`)
3. **統計型別** (`Statistics`, `Stats`)

### 禁止的本地型別
1. **業務實體型別** - 必須在 `types/api.ts` 定義
2. **建立/更新型別** - 除非明確標記為擴展
```

---

## 六、RWD 響應式設計建議

### 6.1 現況優勢

| 項目 | 狀態 | 說明 |
|------|------|------|
| useResponsive Hook | ✅ 優秀 | 統一管理 breakpoint |
| Ant Design Grid 使用 | ✅ 良好 | 65% 元件使用 Row/Col |
| Viewport Meta | ✅ 正確 | `width=device-width, initial-scale=1` |
| 響應式常數 | ✅ 完整 | `RESPONSIVE_COLUMNS`, `RESPONSIVE_SPACING` |

### 6.2 Breakpoint 定義

```typescript
// frontend/src/hooks/utility/useResponsive.ts

// 標準 Breakpoint (與 Ant Design 對齊)
const BREAKPOINTS = {
  xs: 0,      // 0-575px    手機 (小)
  sm: 576,    // 576px+     手機 (大) / 平板 (小)
  md: 768,    // 768px+     平板開始點
  lg: 992,    // 992px+     桌面開始點
  xl: 1200,   // 1200px+    大桌面
  xxl: 1600,  // 1600px+    超寬螢幕
};

// 語意化裝置分類
isMobile    // < 768px
isTablet    // 768px - 991px
isDesktop   // >= 992px
```

### 6.3 待加強項目

| 項目 | 目前狀態 | 建議 | 優先級 |
|------|----------|------|--------|
| 媒體查詢集中 | 分散 3 個檔案 | 統一至 `responsive.css` | P1 |
| sm breakpoint | 未細緻使用 | 新增 576px 層級適配 | P2 |
| Tailwind CSS | 未使用 | 評估引入以簡化開發 | P3 |
| 行動表格 | 基礎卷動 | 固定表頭、列固定 | P2 |

### 6.4 執行計畫

**短期 (1 週)**：

1. 建立 `frontend/src/styles/responsive.css` 統一媒體查詢
2. 為主要表格新增 `sticky` 表頭

```css
/* frontend/src/styles/responsive.css */

/* 統一的媒體查詢 */
@media (max-width: 575px) {
  /* xs: 手機小螢幕 */
}

@media (min-width: 576px) and (max-width: 767px) {
  /* sm: 手機大螢幕 */
}

@media (min-width: 768px) and (max-width: 991px) {
  /* md: 平板 */
}

@media (min-width: 992px) {
  /* lg+: 桌面 */
}
```

**中期 (1 個月)**：

1. 評估 Tailwind CSS 整合可行性
2. 新增 576px (sm) 層級的細緻樣式
3. 實施行動設備視覺迴歸測試

---

## 七、綜合優先順序

### Phase 1：高影響快速見效 (1-2 週)

| 任務 | 類別 | 預期效益 | 工作量 |
|------|------|----------|--------|
| 拆分 Layout.tsx | 元件化 | 主框架可讀性提升 | 2-3 天 |
| 拆分 DocumentList.tsx | 元件化 | 列表頁維護性提升 | 2-3 天 |
| 提取 SharedAttachmentTab | 元件化 | 減少 ~400 行重複 | 1-2 天 |
| 統一媒體查詢到 responsive.css | RWD | 樣式管理集中化 | 1 天 |

### Phase 2：架構標準化 (3-4 週)

| 任務 | 類別 | 預期效益 | 工作量 |
|------|------|----------|--------|
| DocumentService 整合 Repository | 服務層 | 查詢邏輯解耦 | 3-4 天 |
| 全面採用 Factory DI | 服務層 | 依賴注入一致性 | 2-3 天 |
| 萃取 useModalForm Hook | 元件化 | 減少 ~300 行重複 | 1-2 天 |
| 新增 SSOT 檢查腳本 | 型別 | 自動化驗證 | 1 天 |

### Phase 3：長期優化 (1-2 個月)

| 任務 | 類別 | 預期效益 | 工作量 |
|------|------|----------|--------|
| 拆分 10 個超大頁面 | 元件化 | 整體可維護性 | 2-3 週 |
| 拆分複雜 Hook (usePermissions) | 元件化 | Hook 單一職責 | 1 週 |
| 評估 Tailwind CSS | RWD | 開發效率提升 | 1 週 |
| 建立 Storybook 文件 | 元件化 | 新人上手效率 | 2 週 |

---

## 八、關鍵指標追蹤

### 8.1 量化指標

| 指標 | 目前值 | 目標值 | 檢測方式 |
|------|--------|--------|----------|
| 超大元件數量 (400+ 行) | 10 個 | ≤3 個 | `cloc` + 行數統計 |
| 超大頁面數量 (500+ 行) | 10 個 | ≤5 個 | `cloc` + 行數統計 |
| Repository 使用率 | 0% | ≥80% | 程式碼審查 |
| DI 覆蓋率 | 45% | ≥90% | `grep "Depends"` |
| SSOT 違反數 | 0 | 0 | `/type-sync` 指令 |
| RWD 元件覆蓋率 | 65% | ≥85% | `grep "useResponsive"` |
| 程式碼重複率 | ~15% | ≤5% | 共用元件提取後計算 |

### 8.2 驗證命令

```bash
# 前端元件行數統計
find frontend/src/components -name "*.tsx" -exec wc -l {} \; | sort -rn | head -20

# 檢查 Repository 使用
grep -r "Repository" backend/app/services/ --include="*.py"

# 檢查 DI 覆蓋
grep -r "Depends(" backend/app/api/endpoints/ --include="*.py" | wc -l

# 型別同步檢查
cd frontend && npx tsc --noEmit

# SSOT 檢查
/type-sync
```

---

## 九、風險與注意事項

### 9.1 Repository 整合風險

| 風險 | 說明 | 緩解措施 |
|------|------|----------|
| DocumentService 複雜度高 | 1,000+ 行，涉及多種查詢 | 漸進式遷移，每次只移動一類查詢 |
| 業務邏輯混雜 | 查詢邏輯與業務邏輯交織 | 先分離純查詢方法，再逐步遷移 |
| 測試覆蓋不足 | 修改後可能引入 regression | 先補充單元測試，再進行重構 |

### 9.2 元件拆分風險

| 風險 | 說明 | 緩解措施 |
|------|------|----------|
| Layout.tsx 事件機制 | 涉及 `navigation-updated` 事件監聽 | 保留事件機制，只拆分 UI 渲染 |
| 狀態共享 | 拆分後子元件可能需要狀態共享 | 使用 Context 或提升狀態 |
| Props 傳遞 | 拆分過細可能導致 props drilling | 適度拆分，避免過度細粒度 |

### 9.3 型別變更風險

| 風險 | 說明 | 緩解措施 |
|------|------|----------|
| types/api.ts 影響全站 | 修改會影響所有匯入的檔案 | 任何變更需執行 `npx tsc --noEmit` |
| 前後端不同步 | 後端 Schema 變更後前端未更新 | 建立 CI 自動化型別檢查 |

---

## 十、附錄：詳細分析數據

### 10.1 前端元件詳細統計

**components/ 目錄 (17,996 行)**：

| 子目錄 | 檔案數 | 行數 | 說明 |
|--------|--------|------|------|
| common/ | 13 | ~1,700 | 通用元件 |
| document/ | 17 | ~3,500 | 公文元件 (最複雜) |
| calendar/ | 10 | ~3,800 | 行事曆元件 |
| admin/ | 5 | ~2,300 | 管理元件 |
| taoyuan/ | 5 | ~2,500 | 桃園專區 |
| extended/ | - | ~2,000 | 擴展元件 |
| project/ | - | ~1,500 | 專案元件 |
| hoc/ | 2 | ~700 | 高階元件 |

### 10.2 後端服務詳細統計

**services/ 目錄 (21 個服務)**：

| 服務 | 行數 | 架構模式 | 狀態 |
|------|------|----------|------|
| DocumentService | ~1,000 | 無 Repository | ❌ 需重構 |
| DocumentImportService | ~500 | ImportBaseService | ✅ |
| AgencyService | ~300 | BaseService | ✅ |
| ProjectService | ~300 | BaseService | ✅ |
| VendorService | ~250 | BaseService | ✅ |
| DocumentCalendarService | ~400 | 無 DI | ⚠️ |
| AdminService | ~300 | 手動實例化 | ❌ |
| BackupService | ~200 | 手動實例化 | ❌ |

### 10.3 Hooks 詳細統計

**hooks/ 目錄 (29 個檔案)**：

| 類別 | 檔案數 | 最大檔案 | 行數 |
|------|--------|----------|------|
| business/ | 12 | useDocuments.ts | 6,021 |
| system/ | 8 | useDocumentRelations.ts | 8,369 |
| utility/ | 7 | usePermissions.ts | 10,112 |

---

## 十一、執行進度記錄

### 11.1 已完成項目 ✅

| 項目 | 完成日期 | 成果 |
|------|----------|------|
| **Phase 1-1: Layout.tsx 拆分** | 2026-01-27 | 786 行 → 93 行 (減少 88%) |
| **Phase 1-4: responsive.css** | 2026-01-27 | 建立統一響應式樣式表 (~300 行) |

### 11.2 Layout.tsx 重構詳情

**拆分結構**：
```
frontend/src/components/
├── Layout.tsx                    # 93 行 (主框架)
└── layout/
    ├── Sidebar.tsx               # 106 行 (側邊欄)
    ├── Header.tsx                # 141 行 (頂部欄)
    ├── index.ts                  # 統一匯出
    └── hooks/
        ├── useNavigationData.tsx # 202 行 (導覽資料)
        ├── useMenuItems.tsx      # 314 行 (選單轉換)
        └── index.ts
```

**重構效益**：
- 主框架精簡為 93 行，職責單一
- 導覽邏輯完全封裝在 Hooks
- 側邊欄、頂部欄可獨立測試和複用
- TypeScript 編譯 100% 通過

### 11.3 responsive.css 建立詳情

**檔案位置**：`frontend/src/styles/responsive.css`

**內容**：
- 標準 Breakpoint 定義 (xs/sm/md/lg/xl/xxl)
- CSS 變數統一間距
- 響應式工具類別 (show-xs, hide-lg 等)
- 表格、表單、導覽列響應式覆寫
- Dashboard 網格響應式

### 11.4 待辦項目

| 優先級 | 項目 | 狀態 | 說明 |
|--------|------|------|------|
| P1 | Phase 1-2: DocumentList.tsx 拆分 | 待辦 | 建議: columns 移至 documentColumns.tsx |
| P1 | Phase 1-3: SharedAttachmentTab | 待辦 | 從 3 個模組合併 |
| P2 | Phase 2-1: Repository 整合 | 待辦 | DocumentService 改用 DocumentRepository |
| P2 | Phase 2-2: 統一 DI 模式 | 待辦 | 全面採用 Factory 模式 |

### 11.5 複查建議

基於執行過程中的發現，提出以下補充建議：

#### A. 短期建議 (1 週內)

1. **完成 DocumentList 列定義提取**
   - 將 400 行 columns 定義移至 `document/columns/documentColumns.tsx`
   - 提取 `useAttachments` Hook 處理附件邏輯

2. **整合 SharedAttachmentTab**
   - 從 `document/tabs`, `contractCase/tabs`, `taoyuan/tabs` 合併
   - 建立 `common/SharedAttachmentTab.tsx`

#### B. 中期建議 (1 個月內)

1. **Repository 層漸進式整合**
   - 先從簡單查詢開始：`get_by_id`, `get_list`
   - 再遷移複雜查詢：`filter_documents`, `get_statistics`

2. **DI 標準化**
   - 為所有手動實例化的服務建立 Factory
   - 更新 endpoints 使用 `Depends()`

#### C. 監控指標

| 指標 | 初始值 | 目前值 | 目標值 |
|------|--------|--------|--------|
| Layout.tsx 行數 | 786 | **93** | ≤150 ✅ |
| 超大元件數 (400+) | 10 | 9 | ≤3 |
| 響應式樣式統一 | 分散 3 處 | **統一** | 統一 ✅ |

---

## 版本記錄

| 版本 | 日期 | 變更說明 |
|------|------|----------|
| 1.1.0 | 2026-01-27 | 新增執行進度記錄、複查建議 |
| 1.0.0 | 2026-01-27 | 初版建立，完整架構分析與建議 |

---

*文件維護：Claude Code Assistant*
*最後更新：2026-01-27*
