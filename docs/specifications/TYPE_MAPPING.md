# 前後端型別對照表

> 版本: 1.0.0
> 建立日期: 2026-01-08
> 用途: 集中管理前後端欄位型別對應關係

---

## 一、公文模組 (Documents)

### 1.1 OfficialDocument

| 欄位名稱 | Database | Python Model | Pydantic Schema | TypeScript | 說明 |
|---------|----------|--------------|-----------------|------------|------|
| id | INTEGER | int | int | number | 主鍵 |
| auto_serial | VARCHAR(50) | str | str | string | 流水序號 |
| doc_number | VARCHAR(100) | str | str | string | 公文字號 |
| doc_type | VARCHAR(10) | str | str | string | 收文/發文 |
| subject | VARCHAR(500) | str | str | string | 主旨 |
| sender | VARCHAR(200) | str | Optional[str] | string \| undefined | 發文單位 |
| receiver | VARCHAR(200) | str | Optional[str] | string \| undefined | 受文單位 |
| doc_date | DATE | date | Optional[str] | string \| undefined | 公文日期 |
| receive_date | DATE | date | Optional[str] | string \| undefined | 收文日期 |
| send_date | DATE | date | Optional[str] | string \| undefined | 發文日期 |
| status | VARCHAR(50) | str | Optional[str] | string \| undefined | 處理狀態 |
| category | VARCHAR(100) | str | Optional[str] | string \| undefined | 收發文分類 |
| delivery_method | VARCHAR(20) | str | str = "電子交換" | string | 發文形式 |
| has_attachment | BOOLEAN | bool | bool = False | boolean | 是否含附件 |
| contract_project_id | INTEGER | int | Optional[int] | number \| undefined | 承攬案件ID |
| sender_agency_id | INTEGER | int | Optional[int] | number \| undefined | 發文機關ID |
| receiver_agency_id | INTEGER | int | Optional[int] | number \| undefined | 受文機關ID |
| content | TEXT | str | Optional[str] | string \| undefined | 說明內容 |
| notes | TEXT | str | Optional[str] | string \| undefined | 備註 |
| assignee | VARCHAR(500) | str | Optional[str] | string \| undefined | 承辦人 |
| created_at | TIMESTAMP | datetime | datetime | string | 建立時間 |
| updated_at | TIMESTAMP | datetime | datetime | string | 更新時間 |

### 1.2 關聯欄位 (Virtual Fields)

| 欄位名稱 | Python | TypeScript | 來源 | 說明 |
|---------|--------|------------|------|------|
| contract_project_name | str | string \| undefined | JOIN contract_projects | 承攬案件名稱 |
| sender_agency_name | str | string \| undefined | JOIN government_agencies | 發文機關名稱 |
| receiver_agency_name | str | string \| undefined | JOIN government_agencies | 受文機關名稱 |
| attachments_count | int | number | COUNT attachments | 附件數量 |

---

## 二、承攬案件模組 (ContractProjects)

### 2.1 ContractProject

| 欄位名稱 | Database | Python Model | TypeScript | 說明 |
|---------|----------|--------------|------------|------|
| id | INTEGER | int | number | 主鍵 |
| project_name | VARCHAR(500) | str | string | 案件名稱 |
| project_code | VARCHAR(100) | str | string | 專案編號 |
| year | INTEGER | int | number | 年度 |
| client_agency | VARCHAR(200) | str | string \| undefined | 委託單位 |
| client_agency_id | INTEGER | int | number \| undefined | 委託機關ID |
| category | VARCHAR(50) | str | string \| undefined | 案件類別 |
| case_nature | VARCHAR(50) | str | string \| undefined | 案件性質 |
| status | VARCHAR(50) | str | string | 執行狀態 |
| contract_amount | FLOAT | float | number \| undefined | 契約金額 |
| start_date | DATE | date | string \| undefined | 開始日期 |
| end_date | DATE | date | string \| undefined | 結束日期 |
| progress | INTEGER | int | number | 完成進度 |
| notes | TEXT | str | string \| undefined | 備註 |

---

## 三、協力廠商模組 (PartnerVendors)

### 3.1 PartnerVendor

| 欄位名稱 | Database | Python Model | TypeScript | 說明 |
|---------|----------|--------------|------------|------|
| id | INTEGER | int | number | 主鍵 |
| vendor_name | VARCHAR(200) | str | string | 廠商名稱 |
| vendor_code | VARCHAR(50) | str | string \| undefined | 廠商代碼 |
| contact_person | VARCHAR(100) | str | string \| undefined | 聯絡人 |
| phone | VARCHAR(50) | str | string \| undefined | 電話 |
| email | VARCHAR(100) | str | string \| undefined | 電子郵件 |
| address | VARCHAR(300) | str | string \| undefined | 地址 |
| business_type | VARCHAR(100) | str | string \| undefined | 業務類型 |
| rating | INTEGER | int | number \| undefined | 評等 |

---

## 四、政府機關模組 (GovernmentAgencies)

### 4.1 GovernmentAgency

| 欄位名稱 | Database | Python Model | TypeScript | 說明 |
|---------|----------|--------------|------------|------|
| id | INTEGER | int | number | 主鍵 |
| agency_name | VARCHAR(200) | str | string | 機關名稱 |
| agency_short_name | VARCHAR(100) | str | string \| undefined | 機關簡稱 |
| agency_code | VARCHAR(50) | str | string \| undefined | 機關代碼 |
| agency_type | VARCHAR(50) | str | string \| undefined | 機關類型 |
| contact_person | VARCHAR(100) | str | string \| undefined | 聯絡人 |
| phone | VARCHAR(50) | str | string \| undefined | 電話 |
| email | VARCHAR(100) | str | string \| undefined | 電子郵件 |

---

## 五、行事曆模組 (Calendar)

### 5.1 DocumentCalendarEvent

| 欄位名稱 | Database | Python Model | TypeScript | 說明 |
|---------|----------|--------------|------------|------|
| id | INTEGER | int | number | 主鍵 |
| document_id | INTEGER | int | number \| null | 關聯公文ID |
| title | VARCHAR(500) | str | string | 事件標題 |
| description | TEXT | str | string \| undefined | 事件描述 |
| start_date | TIMESTAMP | datetime | string | 開始時間 |
| end_date | TIMESTAMP | datetime | string \| undefined | 結束時間 |
| all_day | BOOLEAN | bool | boolean | 全天事件 |
| event_type | VARCHAR(100) | str | string | 事件類型 |
| priority | VARCHAR(50) | str | string \| number | 優先級 |
| location | VARCHAR(200) | str | string \| undefined | 地點 |
| google_event_id | VARCHAR(255) | str | string \| undefined | Google 事件 ID |
| google_sync_status | VARCHAR(50) | str | string | 同步狀態 |

### 5.2 事件類型對照

| event_type 值 | 中文說明 | 顏色代碼 |
|--------------|---------|---------|
| deadline | 截止提醒 | #f5222d |
| meeting | 會議安排 | #722ed1 |
| review | 審核提醒 | #1890ff |
| reminder | 一般提醒 | #fa8c16 |
| reference | 參考事件 | #666666 |

---

## 六、使用者模組 (Users)

### 6.1 User

| 欄位名稱 | Database | Python Model | TypeScript | 說明 |
|---------|----------|--------------|------------|------|
| id | INTEGER | int | number | 主鍵 |
| username | VARCHAR(50) | str | string | 使用者名稱 |
| email | VARCHAR(100) | str | string | 電子郵件 |
| full_name | VARCHAR(100) | str | string \| undefined | 全名 |
| is_active | BOOLEAN | bool | boolean | 是否啟用 |
| is_admin | BOOLEAN | bool | boolean | 是否管理員 |
| role | VARCHAR(20) | str | string | 角色 |
| permissions | TEXT | str | string \| undefined | 權限 JSON |

---

## 七、型別轉換規則

### 7.1 日期時間

| 方向 | 格式 | 範例 |
|------|------|------|
| DB → Python | datetime | `datetime(2026, 1, 8, 10, 30)` |
| Python → API | ISO 8601 string | `"2026-01-08T10:30:00"` |
| API → Frontend | ISO 8601 string | `"2026-01-08T10:30:00"` |
| Frontend → dayjs | Dayjs object | `dayjs("2026-01-08T10:30:00")` |

### 7.2 布林值

| 層級 | 值 |
|------|-----|
| Database | TRUE / FALSE |
| Python | True / False |
| API JSON | true / false |
| TypeScript | true / false |

### 7.3 空值

| 層級 | 表示方式 |
|------|---------|
| Database | NULL |
| Python | None |
| API JSON | null |
| TypeScript | undefined / null |

---

## 八、API 回應標準格式

### 8.1 列表回應

```typescript
interface ListResponse<T> {
  success: boolean;
  items: T[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}
```

### 8.2 單筆回應

```typescript
interface SingleResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}
```

### 8.3 錯誤回應

```typescript
interface ErrorResponse {
  success: false;
  detail: string;
  error_code?: string;
}
```

---

## 九、相關文件

| 文件 | 說明 |
|------|------|
| `docs/DATABASE_SCHEMA.md` | 資料庫架構 |
| `docs/specifications/TYPE_CONSISTENCY.md` | 型別一致性規範 |
| `frontend/src/api/documentsApi.ts` | 前端 API 型別定義 |
| `backend/app/schemas/` | 後端 Pydantic Schema |

---

## 十、版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| 1.0.0 | 2026-01-08 | 初版建立 |

---

*文件維護: Claude Code Assistant*
