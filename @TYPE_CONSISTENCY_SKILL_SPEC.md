# 型別一致性與整合開發規範 (Type Consistency & Integration SKILL)

> 版本：1.1.0
> 建立日期：2026-01-06
> 最後更新：2026-01-06
> 用途：確保前後端欄位對應、UI 風格一致、降低整合錯誤

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

### 3.2 標準 Table Column 範例

```typescript
// 公文字號 - 可點擊連結
{
    title: '公文字號',
    dataIndex: 'doc_number',
    key: 'doc_number',
    width: 180,
    ellipsis: true,
    render: (text, record) => (
        <Button
            type="link"
            style={{ padding: 0, fontWeight: 500 }}
            onClick={() => navigate(`/documents/${record.id}`)}
        >
            {text}
        </Button>
    ),
}

// 發文形式 - 顏色標籤
{
    title: '發文形式',
    dataIndex: 'delivery_method',
    key: 'delivery_method',
    width: 95,
    align: 'center',
    render: (method: string) => {
        const colorMap: Record<string, string> = {
            '電子交換': 'green',
            '紙本郵寄': 'orange',
            '電子+紙本': 'blue',
        };
        return <Tag color={colorMap[method] || 'default'}>{method || '電子交換'}</Tag>;
    },
}

// 收發單位 - 帶前綴顯示
{
    title: '收發單位',
    key: 'correspondent',
    width: 160,
    ellipsis: true,
    render: (_, record) => {
        const rawValue = record.category === '收文' ? record.sender : record.receiver;
        const labelPrefix = record.category === '收文' ? '來文：' : '發至：';
        const labelColor = record.category === '收文' ? '#52c41a' : '#1890ff';

        return (
            <Tooltip title={rawValue}>
                <Text ellipsis>
                    <span style={{ color: labelColor, fontWeight: 500, fontSize: '11px' }}>
                        {labelPrefix}
                    </span>
                    {rawValue}
                </Text>
            </Tooltip>
        );
    },
}
```

### 3.3 共用 UI 組件規範

| 組件 | 用途 | 引用位置 |
|------|------|----------|
| `DocumentOperations` | 公文檢視/編輯/複製 Modal | `components/document/` |
| `UnifiedTable` | 統一表格組件 | `components/common/` |
| `extractAgencyName()` | 機關名稱提取 | 各頁面共用函數 |

---

## 四、降低錯誤策略

### 4.1 型別安全檢查

```typescript
// ❌ 錯誤：直接存取可能不存在的欄位
const method = doc.delivery_method;  // 可能是 undefined

// ✅ 正確：提供預設值
const method = doc.delivery_method || '電子交換';

// ✅ 正確：使用可選鏈與預設值
const projectName = doc.contract_project?.name ?? '未關聯';
```

### 4.2 API 回應驗證

```typescript
// 前端接收 API 資料時的防禦性處理
const loadedDocs = docsResponse.items.map(doc => ({
    id: doc.id,
    doc_number: doc.doc_number,
    doc_type: doc.doc_type || '函',
    subject: doc.subject,
    doc_date: doc.doc_date || '',
    sender: doc.sender || '',
    receiver: doc.receiver || '',
    category: doc.category || '收文',
    delivery_method: doc.delivery_method || '電子交換',  // 預設值
    has_attachment: doc.has_attachment || false,         // 預設值
}));
```

### 4.3 後端回應完整性

```python
# 確保關聯資料被正確填充
response_items = []
for doc in documents:
    doc_dict = {
        **{k: v for k, v in doc.__dict__.items() if not k.startswith('_')},
        'contract_project_name': project_map.get(doc.contract_project_id),
        'assigned_staff': staff_map.get(doc.contract_project_id, [])
    }
    response_items.append(DocumentResponse.model_validate(doc_dict))
```

### 4.4 常見錯誤與解決方案

| 錯誤類型 | 原因 | 解決方案 |
|----------|------|----------|
| `undefined is not iterable` | API 回傳結構不符預期 | 加入 `?.` 和預設值 `\|\| []` |
| `Property does not exist` | TypeScript 型別缺少欄位 | 更新 Interface 定義 |
| `405 Method Not Allowed` | HTTP Method 不匹配 | 前後端同步使用 POST |
| `ReferenceError: xxx is not defined` | 變數作用域問題 | 在 try 外部宣告變數 |
| `null/undefined in render` | 資料未載入完成 | 加入 loading 狀態檢查 |

### 4.5 TypeScript 嚴格模式最佳實踐 (2026-01-06)

#### 4.5.1 介面繼承與擴展

跨檔案共用介面時，使用 `extends` 擴展基礎介面，避免重複定義：

```typescript
// ✅ 正確：擴展基礎介面
import { NavigationItem as BaseNavItem } from '../hooks/usePermissions';
interface NavigationItem extends BaseNavItem {
    additionalField?: string;
}

// ❌ 避免：重複定義相同名稱介面
interface NavigationItem { /* 重複欄位... */ }
```

#### 4.5.2 泛型元件類型

Ant Design 泛型元件使用時需明確指定型別：

```typescript
// ✅ InputNumber 指定數值型別
<InputNumber<number>
    formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
    parser={(value) => Number(value!.replace(/\$\s?|(,*)/g, ''))}
/>

// ⚠️ 注意：parser 需返回 number，使用 Number() 轉換
```

#### 4.5.3 RangePicker 日期範圍處理

RangePicker 的 onChange 回傳值可能包含 null，需妥善處理：

```typescript
// ✅ 正確處理可能為 null 的日期值
<RangePicker
    onChange={(dates) => setFilters({
        dateRange: dates && dates[0] && dates[1]
            ? [dates[0], dates[1]]
            : null
    })}
/>

// ❌ 錯誤：直接賦值可能導致型別不符
onChange={(dates) => setFilters({ dateRange: dates })}
```

#### 4.5.4 陣列索引安全存取

TypeScript strict 模式下，陣列索引可能回傳 undefined：

```typescript
// ✅ 使用 nullish coalescing
const value = array.split(':')[0] ?? '';

// ✅ 確認非空後使用非空斷言
if (exportData.length > 0) {
    const firstItem = exportData[0]!;  // 已確認非空
}

// ❌ 避免：直接存取可能導致 undefined
const item = array[0];  // 型別為 T | undefined
```

#### 4.5.5 狀態初始化輔助函數

複雜狀態初始化使用輔助函數確保型別安全：

```typescript
// ✅ 正確：使用輔助函數處理可能的 undefined
const getInitialConfig = (): SequenceConfig => {
    if (config) return config;
    if (category && DEFAULT_CONFIGS[category]) return DEFAULT_CONFIGS[category]!;
    return DEFAULT_CONFIGS.document!;
};
const [currentConfig, setCurrentConfig] = useState<SequenceConfig>(getInitialConfig);

// ❌ 錯誤：直接使用可能為 undefined 的值
const [config] = useState(DEFAULT_CONFIGS[category]);  // 可能是 undefined
```

#### 4.5.6 API 回應型別斷言

處理未知 API 回應時使用型別斷言：

```typescript
// ✅ 正確：明確斷言回傳型別
const data = await secureApiService.getNavigationItems() as { items?: NavigationItem[] };
const items = data.items ?? [];

// ⚠️ 注意：型別斷言應在確認 API 契約正確時使用
```

#### 4.5.7 ID 型別一致性

開發模式的 mock user 應使用正確型別：

```typescript
// ✅ 正確：ID 使用 number 型別
const mockUser = { id: 0, username: 'dev-user', ... };

// ❌ 錯誤：字串與數字型別混用
const mockUser = { id: 'dev-user', ... };  // 與後端不一致
```

#### 4.5.8 可選屬性與必填屬性轉換

當介面間屬性必填性不同時，需提供預設值：

```typescript
// 介面 A: all_day 為可選
interface CalendarEvent { all_day?: boolean; }

// 介面 B: all_day 為必填
interface EventFormProps { event: { all_day: boolean } }

// ✅ 正確：傳遞時提供預設值
<EventFormModal
    event={selectedEvent
        ? { ...selectedEvent, all_day: selectedEvent.all_day ?? true }
        : null
    }
/>
```

---

## 五、整合開發最佳實踐

### 5.1 API 設計原則

```
POST-only 資安機制：
- 所有資料查詢使用 POST (避免敏感資料暴露於 URL)
- GET 僅用於靜態資源或公開端點
- 每個 POST 端點都應有對應的 Response Schema
```

### 5.2 前後端同步開發流程

```
1. 確認需求 → 定義 API 契約 (Swagger/OpenAPI)
2. 後端實作 → 建立 Schema + 端點
3. 前端實作 → 更新 TypeScript Interface + API 方法
4. 整合測試 → 驗證資料流完整性
5. UI 調整 → 確保顯示一致性
```

### 5.3 跨頁面資料一致性

當多個頁面顯示相同資料時：

```typescript
// 建立共用的欄位渲染函數
// utils/documentColumnRenderers.ts

export const renderDeliveryMethod = (method: string) => {
    const colorMap: Record<string, string> = {
        '電子交換': 'green',
        '紙本郵寄': 'orange',
        '電子+紙本': 'blue',
    };
    return <Tag color={colorMap[method] || 'default'}>{method || '電子交換'}</Tag>;
};

export const renderCorrespondent = (category: string, sender: string, receiver: string) => {
    const rawValue = category === '收文' ? sender : receiver;
    const labelPrefix = category === '收文' ? '來文：' : '發至：';
    const labelColor = category === '收文' ? '#52c41a' : '#1890ff';
    // ...
};
```

---

## 六、驗證檢查清單

### 6.1 每次提交前檢查

- [ ] TypeScript 編譯無錯誤 (`npx tsc --noEmit`)
- [ ] 前端開發伺服器無警告
- [ ] API 端點回傳結構符合 Schema
- [ ] 新欄位在所有相關頁面正確顯示

### 6.2 整合測試項目

```bash
# 前端型別檢查
cd frontend && npx tsc --noEmit

# 後端 Schema 一致性
cd backend && pytest tests/test_schema_consistency.py -v

# API 端點測試
curl -X POST http://localhost:8001/api/documents-enhanced/list \
  -H "Content-Type: application/json" \
  -d '{"page": 1, "limit": 5}'
```

---

## 七、相關文件

| 文件 | 說明 |
|------|------|
| `@SCHEMA_VALIDATION_SKILL_SPEC.md` | Model-Database 一致性驗證 |
| `@CSV_IMPORT_SKILL_SPEC.md` | CSV 匯入模組規範 |
| `backend/app/schemas/document.py` | 後端公文 Schema |
| `frontend/src/api/documentsApi.ts` | 前端公文 API |
| `frontend/src/types/index.ts` | 前端型別定義 |

---

## 八、版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| 1.1.0 | 2026-01-06 | 新增 TypeScript 嚴格模式最佳實踐 (4.5 節) - 涵蓋介面繼承、泛型元件、日期處理、陣列索引、狀態初始化等 8 個子章節 |
| 1.0.0 | 2026-01-06 | 初版 - 整合型別一致性與 UI 風格規範 |

---

*文件維護: Claude Code Assistant*
