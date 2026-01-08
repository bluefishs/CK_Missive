# 型別一致性與整合開發規範 (Type Consistency & Integration)

> 版本：1.2.0
> 建立日期：2026-01-06
> 最後更新：2026-01-08
> 用途：確保前後端欄位對應、UI 風格一致、降低整合錯誤
> 原始檔案：`@TYPE_CONSISTENCY_SKILL_SPEC.md` (已遷移)

---

## 一、核心原則

### 1.1 Single Source of Truth (單一真實來源)

```
┌─────────────────────────────────────────────────────────────────┐
│                   型別定義層級 (Type Definition Hierarchy)        │
├─────────────────────────────────────────────────────────────────┤
│  Level 1: Database Schema    → PostgreSQL 表格定義 (權威來源)     │
│  Level 2: Backend Models     → SQLAlchemy ORM (models.py)        │
│  Level 3: Backend Schemas    → Pydantic Schemas (schemas/*.py)   │
│  Level 4: Frontend Types     → TypeScript Interfaces             │
│  Level 5: UI Components      → Props & State Types               │
└─────────────────────────────────────────────────────────────────┘

同步方向：Database → Backend → Frontend → UI
```

### 1.2 命名一致性原則

| 層級 | 命名風格 | 範例 |
|------|----------|------|
| Database | snake_case | `delivery_method` |
| Backend (Python) | snake_case | `delivery_method` |
| Frontend (TypeScript) | snake_case (API) | `delivery_method` |
| UI Display | 中文標籤 | "發文形式" |

---

## 二、前後端欄位對應規範

### 2.1 新增欄位流程

當需要新增業務欄位時，必須依序更新以下位置：

```
步驟 1: Database Migration
────────────────────────────────────────────────────
# backend/alembic/versions/xxx_add_new_field.py
def upgrade():
    op.add_column('documents', sa.Column('delivery_method', sa.String(20)))

步驟 2: Backend Model
────────────────────────────────────────────────────
# backend/app/extended/models.py
class OfficialDocument(Base):
    delivery_method = Column(String(20), default="電子交換", comment="發文形式")

步驟 3: Backend Schema (Response)
────────────────────────────────────────────────────
# backend/app/schemas/document.py
class DocumentBase(BaseModel):
    delivery_method: Optional[str] = Field("電子交換", description="發文形式")

class DocumentResponse(DocumentBase):
    # 自動繼承 delivery_method

步驟 4: Frontend API Types
────────────────────────────────────────────────────
# frontend/src/api/documentsApi.ts
export interface Document {
    delivery_method?: string;  // 發文形式
}

步驟 5: Frontend Business Types (如需要)
────────────────────────────────────────────────────
# frontend/src/types/index.ts
export interface Document {
    readonly delivery_method?: string;
}
```

### 2.2 欄位對應檢查清單

每次新增/修改欄位後，必須確認：

- [ ] Database Schema 已更新 (migration)
- [ ] `models.py` ORM Model 已更新
- [ ] `schemas/*.py` Pydantic Schema 已更新
- [ ] `api/*Api.ts` TypeScript Interface 已更新
- [ ] `types/index.ts` 全域型別已同步 (如有)
- [ ] API 端點正確回傳新欄位
- [ ] 前端正確接收並顯示

### 2.3 常見欄位對應表

| 欄位 | Database | Backend Schema | Frontend API | 用途 |
|------|----------|----------------|--------------|------|
| `delivery_method` | VARCHAR(20) | `str` | `string` | 發文形式 |
| `has_attachment` | BOOLEAN | `bool` | `boolean` | 是否含附件 |
| `contract_project_id` | INTEGER | `int` | `number` | 承攬案件 ID |
| `contract_project_name` | - (關聯) | `str` | `string` | 承攬案件名稱 |
| `assigned_staff` | - (關聯) | `List[StaffInfo]` | `Array<{...}>` | 負責同仁 |
| `category` | VARCHAR(100) | `str` | `string` | 收文/發文 |
| `auto_serial` | VARCHAR(50) | `str` | `string` | 流水序號 |

---

## 三、UI 風格一致性規範

### 3.1 表格欄位設計標準

參考 `/documents` 頁面的 `DocumentList.tsx` 設計：

```typescript
// 標準欄位寬度
const COLUMN_WIDTHS = {
    doc_number: 180,       // 公文字號
    delivery_method: 95,   // 發文形式
    correspondent: 160,    // 收發單位
    doc_date: 100,         // 公文日期
    subject: 'auto',       // 主旨 (自動填滿)
    actions: 80,           // 操作
};

// 發文形式 Tag 顏色
const DELIVERY_METHOD_COLORS: Record<string, string> = {
    '電子交換': 'green',
    '紙本郵寄': 'orange',
    '電子+紙本': 'blue',
};

// 收發單位前綴與顏色
const CORRESPONDENT_STYLES = {
    '收文': { prefix: '來文：', color: '#52c41a' },
    '發文': { prefix: '發至：', color: '#1890ff' },
};
```

### 3.2 共用 UI 組件規範

| 組件 | 用途 | 引用位置 |
|------|------|----------|
| `DocumentOperations` | 公文檢視/編輯/複製 Modal | `components/document/` |
| `UnifiedTable` | 統一表格組件 | `components/common/` |
| `extractAgencyName()` | 機關名稱提取 | 各頁面共用函數 |

---

## 四、TypeScript 嚴格模式最佳實踐

### 4.1 介面繼承與擴展

```typescript
// ✅ 正確：擴展基礎介面
import { NavigationItem as BaseNavItem } from '../hooks/usePermissions';
interface NavigationItem extends BaseNavItem {
    additionalField?: string;
}

// ❌ 避免：重複定義相同名稱介面
interface NavigationItem { /* 重複欄位... */ }
```

### 4.2 泛型元件類型

```typescript
// ✅ InputNumber 指定數值型別
<InputNumber<number>
    formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
    parser={(value) => Number(value!.replace(/\$\s?|(,*)/g, ''))}
/>
```

### 4.3 RangePicker 日期範圍處理

```typescript
// ✅ 正確處理可能為 null 的日期值
<RangePicker
    onChange={(dates) => setFilters({
        dateRange: dates && dates[0] && dates[1]
            ? [dates[0], dates[1]]
            : null
    })}
/>
```

### 4.4 陣列索引安全存取

```typescript
// ✅ 使用 nullish coalescing
const value = array.split(':')[0] ?? '';

// ✅ 確認非空後使用非空斷言
if (exportData.length > 0) {
    const firstItem = exportData[0]!;
}
```

### 4.5 ID 型別一致性

```typescript
// ✅ 正確：ID 使用 number 型別
const mockUser = { id: 0, username: 'dev-user', ... };

// ❌ 錯誤：字串與數字型別混用
const mockUser = { id: 'dev-user', ... };
```

---

## 五、驗證檢查清單

### 5.1 每次提交前檢查

- [ ] TypeScript 編譯無錯誤 (`npx tsc --noEmit`)
- [ ] 前端開發伺服器無警告
- [ ] API 端點回傳結構符合 Schema
- [ ] 新欄位在所有相關頁面正確顯示

### 5.2 整合測試

```bash
# 前端型別檢查
cd frontend && npx tsc --noEmit

# 後端 Schema 一致性
cd backend && pytest tests/test_schema_consistency.py -v
```

---

## 六、相關文件

| 文件 | 說明 | 強制等級 |
|------|------|----------|
| `docs/DEVELOPMENT_STANDARDS.md` | 統一開發規範總綱 | 🔴 必讀 |
| `docs/specifications/SCHEMA_VALIDATION.md` | Schema 驗證規範 | 🔴 必須 |
| `docs/DATABASE_SCHEMA.md` | 資料庫架構 | 🔴 必須 |

---

## 七、版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| 1.2.0 | 2026-01-08 | 遷移至 docs/specifications/ 目錄，更新引用路徑 |
| 1.1.0 | 2026-01-06 | 新增 TypeScript 嚴格模式最佳實踐 |
| 1.0.0 | 2026-01-06 | 初版 |

---

*文件維護: Claude Code Assistant*
