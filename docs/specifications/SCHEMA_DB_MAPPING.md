# Schema-DB 欄位對照表

> **版本**: 1.0.0
> **建立日期**: 2026-01-21
> **用途**: 記錄 Pydantic Schema 與資料庫欄位的對應關係，避免類型不一致導致的 500 錯誤

---

## 重要提示

在定義或修改 Pydantic Schema 時，**必須先確認資料庫欄位類型**。

常見問題場景：
- Schema 定義 `int`，資料庫是 `VARCHAR` → asyncpg 報錯
- Schema 定義 `Enum`，資料庫是 `VARCHAR` → 序列化問題
- Schema 欄位名稱與資料庫不符 → AttributeError

---

## 主要實體對照表

### DocumentCalendarEvent（行事曆事件）

| Schema 欄位 | Schema 類型 | DB 欄位 | DB 類型 | 注意事項 |
|------------|------------|---------|---------|---------|
| `id` | `int` | `id` | `INTEGER` | 主鍵 |
| `title` | `str` | `title` | `VARCHAR(500)` | - |
| `description` | `Optional[str]` | `description` | `TEXT` | - |
| `start_date` | `datetime` | `start_date` | `TIMESTAMP` | - |
| `end_date` | `Optional[datetime]` | `end_date` | `TIMESTAMP` | - |
| `all_day` | `bool` | `all_day` | `BOOLEAN` | - |
| `event_type` | `str` | `event_type` | `VARCHAR(100)` | - |
| **`priority`** | **`str`** | **`priority`** | **`VARCHAR(50)`** | **⚠️ 易錯：前端傳 int 需轉換** |
| `location` | `Optional[str]` | `location` | `VARCHAR(500)` | - |
| `document_id` | `Optional[int]` | `document_id` | `INTEGER` | 外鍵 |
| `assigned_user_id` | `Optional[int]` | `assigned_user_id` | `INTEGER` | 外鍵 |
| `google_event_id` | `Optional[str]` | `google_event_id` | `VARCHAR(500)` | - |
| `google_sync_status` | `Optional[str]` | `google_sync_status` | `VARCHAR(50)` | - |
| `reminder_enabled` | `bool` | `reminder_enabled` | `BOOLEAN` | - |
| `created_at` | `datetime` | `created_at` | `TIMESTAMP` | - |
| `updated_at` | `datetime` | `updated_at` | `TIMESTAMP` | - |

---

### OfficialDocument（公文）

| Schema 欄位 | Schema 類型 | DB 欄位 | DB 類型 | 注意事項 |
|------------|------------|---------|---------|---------|
| `id` | `int` | `id` | `INTEGER` | 主鍵 |
| `doc_number` | `Optional[str]` | `doc_number` | `VARCHAR(100)` | - |
| `subject` | `Optional[str]` | `subject` | `VARCHAR(500)` | - |
| **`doc_type`** | `str` | **`doc_type`** | `VARCHAR(50)` | **⚠️ 易錯：不是 `type`** |
| `status` | `Optional[str]` | `status` | `VARCHAR(50)` | - |
| `sender_agency` | `Optional[str]` | `sender_agency` | `VARCHAR(200)` | - |
| `sender_agency_id` | `Optional[int]` | `sender_agency_id` | `INTEGER` | 外鍵 |
| `receiver_agency` | `Optional[str]` | `receiver_agency` | `VARCHAR(200)` | - |
| `receiver_agency_id` | `Optional[int]` | `receiver_agency_id` | `INTEGER` | 外鍵 |
| `project_id` | `Optional[int]` | `project_id` | `INTEGER` | 外鍵 |
| `deadline` | `Optional[datetime]` | `deadline` | `TIMESTAMP` | - |
| `created_at` | `datetime` | `created_at` | `TIMESTAMP` | - |
| `updated_at` | `datetime` | `updated_at` | `TIMESTAMP` | - |

---

### User（使用者）

| Schema 欄位 | Schema 類型 | DB 欄位 | DB 類型 | 注意事項 |
|------------|------------|---------|---------|---------|
| `id` | `int` | `id` | `INTEGER` | 主鍵 |
| `email` | `str` | `email` | `VARCHAR(255)` | 唯一 |
| `username` | `Optional[str]` | `username` | `VARCHAR(100)` | - |
| `full_name` | `Optional[str]` | `full_name` | `VARCHAR(200)` | - |
| `is_active` | `bool` | `is_active` | `BOOLEAN` | - |
| `is_admin` | `bool` | `is_admin` | `BOOLEAN` | - |
| `role` | `Optional[str]` | `role` | `VARCHAR(50)` | - |
| `last_login` | `Optional[datetime]` | `last_login` | `TIMESTAMP` | - |
| `created_at` | `datetime` | `created_at` | `TIMESTAMP` | - |

---

### Agency（機關）

| Schema 欄位 | Schema 類型 | DB 欄位 | DB 類型 | 注意事項 |
|------------|------------|---------|---------|---------|
| `id` | `int` | `id` | `INTEGER` | 主鍵 |
| `agency_name` | `str` | `agency_name` | `VARCHAR(200)` | - |
| `agency_code` | `Optional[str]` | `agency_code` | `VARCHAR(50)` | - |
| `contact_person` | `Optional[str]` | `contact_person` | `VARCHAR(100)` | - |
| `contact_phone` | `Optional[str]` | `contact_phone` | `VARCHAR(50)` | - |
| `contact_email` | `Optional[str]` | `contact_email` | `VARCHAR(255)` | - |
| `address` | `Optional[str]` | `address` | `VARCHAR(500)` | - |
| `is_active` | `bool` | `is_active` | `BOOLEAN` | 預設 True |

---

### ContractProject（承攬案件）

| Schema 欄位 | Schema 類型 | DB 欄位 | DB 類型 | 注意事項 |
|------------|------------|---------|---------|---------|
| `id` | `int` | `id` | `INTEGER` | 主鍵 |
| `project_name` | `str` | `project_name` | `VARCHAR(500)` | - |
| `project_code` | `Optional[str]` | `project_code` | `VARCHAR(100)` | - |
| `agency_id` | `Optional[int]` | `agency_id` | `INTEGER` | 外鍵 |
| `start_date` | `Optional[date]` | `start_date` | `DATE` | - |
| `end_date` | `Optional[date]` | `end_date` | `DATE` | - |
| `status` | `Optional[str]` | `status` | `VARCHAR(50)` | - |
| `budget` | `Optional[Decimal]` | `budget` | `DECIMAL(15,2)` | - |

---

### TaoyuanProject（桃園轄管工程）

| Schema 欄位 | Schema 類型 | DB 欄位 | DB 類型 | 注意事項 |
|------------|------------|---------|---------|---------|
| `id` | `int` | `id` | `INTEGER` | 主鍵 |
| `project_name` | `str` | `project_name` | `VARCHAR(500)` | - |
| `district` | `Optional[str]` | `district` | `VARCHAR(50)` | - |
| `section` | `Optional[str]` | `section` | `VARCHAR(100)` | - |
| `contractor` | `Optional[str]` | `contractor` | `VARCHAR(200)` | - |
| `land_agreement_status` | `Optional[bool]` | `land_agreement_status` | `BOOLEAN` | - |
| `building_survey_status` | `Optional[bool]` | `building_survey_status` | `BOOLEAN` | - |

---

### TaoyuanDispatch（桃園派工單）

| Schema 欄位 | Schema 類型 | DB 欄位 | DB 類型 | 注意事項 |
|------------|------------|---------|---------|---------|
| `id` | `int` | `id` | `INTEGER` | 主鍵 |
| `project_id` | `int` | `project_id` | `INTEGER` | 外鍵 |
| `dispatch_number` | `Optional[str]` | `dispatch_number` | `VARCHAR(100)` | - |
| `dispatch_date` | `Optional[date]` | `dispatch_date` | `DATE` | - |
| `agency_doc_id` | `Optional[int]` | `agency_doc_id` | `INTEGER` | 外鍵 |
| `company_doc_id` | `Optional[int]` | `company_doc_id` | `INTEGER` | 外鍵 |
| `contact_note` | `Optional[str]` | `contact_note` | `TEXT` | - |

---

## 類型對照速查表

| Python / Pydantic 類型 | PostgreSQL 類型 | 注意事項 |
|----------------------|-----------------|---------|
| `int` | `INTEGER`, `BIGINT` | - |
| `str` | `VARCHAR`, `TEXT`, `CHAR` | - |
| `bool` | `BOOLEAN` | - |
| `float` | `REAL`, `DOUBLE PRECISION` | 避免用於金額 |
| `Decimal` | `DECIMAL`, `NUMERIC` | 金額推薦 |
| `datetime` | `TIMESTAMP`, `TIMESTAMPTZ` | API 返回用 `.isoformat()` |
| `date` | `DATE` | - |
| `time` | `TIME` | - |
| `Dict[str, Any]` | `JSONB`, `JSON` | - |
| `List[...]` | `ARRAY` | - |
| `Optional[T]` | 任意 (可 NULL) | - |

---

## 易錯欄位速查

| 實體 | 易錯欄位 | 正確類型 | 常見錯誤 |
|------|---------|---------|---------|
| DocumentCalendarEvent | `priority` | `str` (DB: VARCHAR) | 定義為 `int` |
| OfficialDocument | `doc_type` | `str` | 存取 `type` (不存在) |
| User | `role` | `str` | 使用 Enum 直接存儲 |
| ContractProject | `budget` | `Decimal` | 使用 `float` |

---

## 新增欄位檢查流程

1. **查詢資料庫欄位定義**
   ```sql
   SELECT column_name, data_type, is_nullable
   FROM information_schema.columns
   WHERE table_name = 'your_table';
   ```

2. **對照上表確認正確的 Pydantic 類型**

3. **如需類型轉換，使用 `field_validator`**
   ```python
   @field_validator('priority', mode='before')
   @classmethod
   def normalize_priority(cls, v):
       return str(v) if v is not None else v
   ```

4. **測試 API 確認無類型錯誤**

---

## 相關文件

| 文件 | 說明 |
|------|------|
| `.claude/skills/api-serialization.md` | API 序列化規範 |
| `.claude/skills/type-management.md` | 型別管理規範 |
| `.claude/MANDATORY_CHECKLIST.md` | 開發檢查清單 |
| `docs/FIX_REPORT_2026-01-21_API_SERIALIZATION.md` | 修復案例報告 |

---

## 版本記錄

| 版本 | 日期 | 說明 |
|------|------|------|
| 1.0.0 | 2026-01-21 | 初版建立，包含主要實體對照表 |

---

*維護者: Claude Code Assistant*
