# 資料庫結構說明文件

> 版本: v2.0.0
> 最後更新: 2026-01-08
> 維護者: 系統開發團隊

## 資料庫概況

**資料庫系統**: PostgreSQL 15+ (Docker 容器)

| 項目 | 值 |
|------|-----|
| Host | localhost |
| Port | 5434 |
| Database | ck_documents |
| Username | ck_user |
| Password | ck_password_2024 |

---

## 核心資料表總覽

| 資料表 | 說明 | 對應模型 |
|--------|------|----------|
| documents | 公文檔案 | OfficialDocument |
| contract_projects | 承攬案件 | ContractProject |
| partner_vendors | 協力廠商 | PartnerVendor |
| government_agencies | 政府機關 | GovernmentAgency |
| users | 使用者 | User |
| document_calendar_events | 行事曆事件 | DocumentCalendarEvent |
| event_reminders | 事件提醒 | EventReminder |
| document_attachments | 公文附件 | DocumentAttachment |
| project_vendor_association | 案件廠商關聯 | (Table) |
| project_user_assignments | 專案人員指派 | (Table) |
| system_notifications | 系統通知 | SystemNotification |
| user_sessions | 使用者會話 | UserSession |
| site_navigation_items | 網站導航 | SiteNavigationItem |
| site_configurations | 網站配置 | SiteConfiguration |
| project_agency_contacts | 專案機關承辦 | ProjectAgencyContact |

---

## 詳細資料表定義

### 1. documents (公文檔案表)

**對應模型**: `app.extended.models.OfficialDocument`

| 欄位名稱 | 資料類型 | 限制條件 | 說明 |
|----------|----------|----------|------|
| id | INTEGER | PRIMARY KEY | 自增主鍵 |
| auto_serial | VARCHAR(50) | INDEX | 流水序號 (R0001=收文, S0001=發文) |
| doc_number | VARCHAR(100) | INDEX | 公文文號 |
| doc_type | VARCHAR(10) | INDEX | 公文類型 (收文/發文) |
| subject | VARCHAR(500) | | 主旨 |
| sender | VARCHAR(200) | INDEX | 發文單位 |
| receiver | VARCHAR(200) | INDEX | 受文單位 |
| doc_date | DATE | INDEX | 發文日期 (西元) |
| receive_date | DATE | | 收文日期 (西元) |
| send_date | DATE | | 發文日期 |
| status | VARCHAR(50) | INDEX | 處理狀態 |
| category | VARCHAR(100) | INDEX | 收發文分類 |
| delivery_method | VARCHAR(20) | INDEX, DEFAULT '電子交換' | 發文形式 |
| has_attachment | BOOLEAN | DEFAULT false | 是否含附件 |
| contract_project_id | INTEGER | FK → contract_projects.id | 關聯承攬案件ID |
| sender_agency_id | INTEGER | FK → government_agencies.id | 發文機關ID |
| receiver_agency_id | INTEGER | FK → government_agencies.id | 受文機關ID |
| title | TEXT | | 標題 |
| content | TEXT | | 說明 |
| cloud_file_link | VARCHAR(500) | | 雲端檔案連結 |
| dispatch_format | VARCHAR(20) | DEFAULT '電子' | 發文形式 |
| assignee | VARCHAR(500) | | 承辦人（多人逗號分隔） |
| notes | TEXT | | 備註 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新時間 |

**索引**:
- PRIMARY KEY: `documents_pkey` (id)
- INDEX: `idx_documents_auto_serial` (auto_serial)
- INDEX: `idx_documents_doc_number` (doc_number)
- INDEX: `idx_documents_doc_type` (doc_type)
- INDEX: `idx_documents_sender` (sender)
- INDEX: `idx_documents_receiver` (receiver)
- INDEX: `idx_documents_doc_date` (doc_date)
- INDEX: `idx_documents_status` (status)
- INDEX: `idx_documents_category` (category)

**關聯**:
- `contract_project` → ContractProject (多對一)
- `sender_agency` → GovernmentAgency (多對一)
- `receiver_agency` → GovernmentAgency (多對一)
- `calendar_events` → DocumentCalendarEvent (一對多, CASCADE)
- `attachments` → DocumentAttachment (一對多, CASCADE)

---

### 2. contract_projects (承攬案件表)

**對應模型**: `app.extended.models.ContractProject`

| 欄位名稱 | 資料類型 | 限制條件 | 說明 |
|----------|----------|----------|------|
| id | INTEGER | PRIMARY KEY | 自增主鍵 |
| project_name | VARCHAR(500) | NOT NULL | 案件名稱 |
| project_code | VARCHAR(100) | UNIQUE | 專案編號 (CK{年度}_{類別}_{性質}_{流水號}) |
| year | INTEGER | | 年度 |
| client_agency | VARCHAR(200) | | 委託單位 |
| client_agency_id | INTEGER | FK → government_agencies.id | 委託機關ID |
| contract_doc_number | VARCHAR(100) | | 契約文號 |
| category | VARCHAR(50) | | 案件類別 (01委辦/02協力/03小額/04其他) |
| case_nature | VARCHAR(50) | | 案件性質 (01測量/02資訊/03複合) |
| status | VARCHAR(50) | DEFAULT '執行中' | 執行狀態 |
| contract_amount | FLOAT | | 契約金額 |
| winning_amount | FLOAT | | 得標金額 |
| start_date | DATE | | 開始日期 |
| end_date | DATE | | 結束日期 |
| completion_date | DATE | | 完工日期 |
| acceptance_date | DATE | | 驗收日期 |
| warranty_end_date | DATE | | 保固結束日期 |
| progress | INTEGER | DEFAULT 0 | 完成進度 (0-100) |
| completion_percentage | INTEGER | | 完成百分比 |
| contract_number | VARCHAR(100) | | 合約編號 |
| contract_type | VARCHAR(50) | | 合約類型 |
| location | VARCHAR(200) | | 專案地點 |
| procurement_method | VARCHAR(100) | | 採購方式 |
| project_path | VARCHAR(500) | | 專案路徑 |
| contact_person | VARCHAR(100) | | 聯絡人 |
| contact_phone | VARCHAR(50) | | 聯絡電話 |
| agency_contact_person | VARCHAR(100) | | 機關承辦人 |
| agency_contact_phone | VARCHAR(50) | | 機關承辦電話 |
| agency_contact_email | VARCHAR(100) | | 機關承辦Email |
| notes | TEXT | | 備註 |
| description | TEXT | | 專案描述 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新時間 |

---

### 3. partner_vendors (協力廠商表)

**對應模型**: `app.extended.models.PartnerVendor`

| 欄位名稱 | 資料類型 | 限制條件 | 說明 |
|----------|----------|----------|------|
| id | INTEGER | PRIMARY KEY | 自增主鍵 |
| vendor_name | VARCHAR(200) | NOT NULL | 廠商名稱 |
| vendor_code | VARCHAR(50) | UNIQUE | 廠商代碼 |
| contact_person | VARCHAR(100) | | 聯絡人 |
| phone | VARCHAR(50) | | 電話 |
| email | VARCHAR(100) | | 電子郵件 |
| address | VARCHAR(300) | | 地址 |
| business_type | VARCHAR(100) | | 業務類型 |
| rating | INTEGER | | 評等 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新時間 |

---

### 4. government_agencies (政府機關表)

**對應模型**: `app.extended.models.GovernmentAgency`

| 欄位名稱 | 資料類型 | 限制條件 | 說明 |
|----------|----------|----------|------|
| id | INTEGER | PRIMARY KEY | 自增主鍵 |
| agency_name | VARCHAR(200) | NOT NULL | 機關名稱 |
| agency_short_name | VARCHAR(100) | | 機關簡稱 |
| agency_code | VARCHAR(50) | | 機關代碼 |
| agency_type | VARCHAR(50) | | 機關類型 |
| contact_person | VARCHAR(100) | | 聯絡人 |
| phone | VARCHAR(50) | | 電話 |
| address | VARCHAR(500) | | 地址 |
| email | VARCHAR(100) | | 電子郵件 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新時間 |

---

### 5. users (使用者表)

**對應模型**: `app.extended.models.User`

| 欄位名稱 | 資料類型 | 限制條件 | 說明 |
|----------|----------|----------|------|
| id | INTEGER | PRIMARY KEY | 自增主鍵 |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 使用者名稱 |
| email | VARCHAR(100) | UNIQUE, NOT NULL | 電子郵件 |
| password_hash | VARCHAR(100) | | 密碼雜湊 |
| full_name | VARCHAR(100) | | 全名 |
| is_active | BOOLEAN | DEFAULT true | 是否啟用 |
| is_admin | BOOLEAN | DEFAULT false | 是否為管理員 |
| is_superuser | BOOLEAN | DEFAULT false | 是否為超級使用者 |
| role | VARCHAR(20) | DEFAULT 'user' | 角色 |
| permissions | TEXT | | 權限 (JSON) |
| google_id | VARCHAR(100) | | Google ID |
| avatar_url | VARCHAR(255) | | 頭像 URL |
| auth_provider | VARCHAR(20) | DEFAULT 'email' | 認證提供者 |
| email_verified | BOOLEAN | DEFAULT false | Email 已驗證 |
| login_count | INTEGER | DEFAULT 0 | 登入次數 |
| last_login | TIMESTAMP | | 最後登入時間 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新時間 |

---

### 6. document_calendar_events (行事曆事件表)

**對應模型**: `app.extended.models.DocumentCalendarEvent`

| 欄位名稱 | 資料類型 | 限制條件 | 說明 |
|----------|----------|----------|------|
| id | INTEGER | PRIMARY KEY | 自增主鍵 |
| document_id | INTEGER | FK → documents.id (SET NULL) | 關聯公文ID |
| title | VARCHAR(500) | NOT NULL | 事件標題 |
| description | TEXT | | 事件描述 |
| start_date | TIMESTAMP | NOT NULL | 開始時間 |
| end_date | TIMESTAMP | | 結束時間 |
| all_day | BOOLEAN | DEFAULT false | 全天事件 |
| event_type | VARCHAR(100) | DEFAULT 'reminder' | 事件類型 |
| priority | VARCHAR(50) | DEFAULT 'normal' | 優先級 |
| location | VARCHAR(200) | | 地點 |
| assigned_user_id | INTEGER | FK → users.id | 指派使用者ID |
| created_by | INTEGER | FK → users.id | 建立者ID |
| google_event_id | VARCHAR(255) | INDEX | Google Calendar 事件 ID |
| google_sync_status | VARCHAR(50) | DEFAULT 'pending' | 同步狀態 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新時間 |

---

### 7. event_reminders (事件提醒表)

**對應模型**: `app.extended.models.EventReminder`

| 欄位名稱 | 資料類型 | 限制條件 | 說明 |
|----------|----------|----------|------|
| id | INTEGER | PRIMARY KEY | 自增主鍵 |
| event_id | INTEGER | FK → document_calendar_events.id (CASCADE) | 關聯事件ID |
| recipient_user_id | INTEGER | FK → users.id (CASCADE) | 接收用戶ID |
| recipient_email | VARCHAR(100) | | 接收者Email |
| reminder_type | VARCHAR(50) | NOT NULL, DEFAULT 'email' | 提醒類型 |
| notification_type | VARCHAR(50) | NOT NULL, DEFAULT 'email' | 通知類型 |
| reminder_time | TIMESTAMP | NOT NULL | 提醒時間 |
| reminder_minutes | INTEGER | | 提前提醒分鐘數 |
| title | VARCHAR(200) | | 提醒標題 |
| message | TEXT | | 提醒訊息 |
| is_sent | BOOLEAN | DEFAULT false | 是否已發送 |
| sent_at | TIMESTAMP | | 發送時間 |
| status | VARCHAR(50) | DEFAULT 'pending' | 提醒狀態 |
| priority | INTEGER | DEFAULT 3 | 優先級 (1-5) |
| retry_count | INTEGER | DEFAULT 0 | 重試次數 |
| max_retries | INTEGER | NOT NULL, DEFAULT 3 | 最大重試次數 |
| next_retry_at | TIMESTAMP | | 下次重試時間 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新時間 |

---

### 8. document_attachments (公文附件表)

**對應模型**: `app.extended.models.DocumentAttachment`

| 欄位名稱 | 資料類型 | 限制條件 | 說明 |
|----------|----------|----------|------|
| id | INTEGER | PRIMARY KEY | 自增主鍵 |
| document_id | INTEGER | FK → documents.id (CASCADE) | 關聯公文ID |
| file_name | VARCHAR(255) | | 檔案名稱 |
| original_name | VARCHAR(255) | | 原始檔案名稱 |
| file_path | VARCHAR(500) | | 檔案路徑 |
| file_size | INTEGER | | 檔案大小 (bytes) |
| mime_type | VARCHAR(100) | | MIME 類型 |
| storage_type | VARCHAR(20) | DEFAULT 'local' | 儲存類型 |
| checksum | VARCHAR(64) | INDEX | SHA256 校驗碼 |
| uploaded_by | INTEGER | FK → users.id (SET NULL) | 上傳者 ID |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新時間 |

---

### 9. project_vendor_association (案件廠商關聯表)

| 欄位名稱 | 資料類型 | 限制條件 | 說明 |
|----------|----------|----------|------|
| project_id | INTEGER | PK, FK → contract_projects.id | 專案ID |
| vendor_id | INTEGER | PK, FK → partner_vendors.id | 廠商ID |
| role | VARCHAR(50) | | 廠商角色 |
| contract_amount | FLOAT | | 合約金額 |
| start_date | DATE | | 合作開始日期 |
| end_date | DATE | | 合作結束日期 |
| status | VARCHAR(20) | | 合作狀態 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新時間 |

---

### 10. project_user_assignments (專案人員指派表)

| 欄位名稱 | 資料類型 | 限制條件 | 說明 |
|----------|----------|----------|------|
| id | INTEGER | PRIMARY KEY | 自增主鍵 |
| project_id | INTEGER | NOT NULL, FK → contract_projects.id | 專案ID |
| user_id | INTEGER | NOT NULL, FK → users.id | 使用者ID |
| role | VARCHAR(50) | DEFAULT 'member' | 角色 |
| is_primary | BOOLEAN | DEFAULT false | 是否為主要負責人 |
| assignment_date | DATE | | 指派日期 |
| start_date | DATE | | 開始日期 |
| end_date | DATE | | 結束日期 |
| status | VARCHAR(50) | DEFAULT 'active' | 狀態 |
| notes | TEXT | | 備註 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新時間 |

---

### 11. system_notifications (系統通知表)

**對應模型**: `app.extended.models.SystemNotification`

| 欄位名稱 | 資料類型 | 限制條件 | 說明 |
|----------|----------|----------|------|
| id | INTEGER | PRIMARY KEY | 自增主鍵 |
| user_id | INTEGER | FK → users.id (CASCADE) | 接收者ID |
| recipient_id | INTEGER | FK → users.id (CASCADE) | 接收者ID (別名) |
| title | VARCHAR(200) | NOT NULL | 通知標題 |
| message | TEXT | NOT NULL | 通知內容 |
| notification_type | VARCHAR(50) | DEFAULT 'info' | 通知類型 |
| is_read | BOOLEAN | DEFAULT false | 是否已讀 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 建立時間 |
| read_at | TIMESTAMP | | 已讀時間 |

---

### 12. user_sessions (使用者會話表)

**對應模型**: `app.extended.models.UserSession`

| 欄位名稱 | 資料類型 | 限制條件 | 說明 |
|----------|----------|----------|------|
| id | INTEGER | PRIMARY KEY | 自增主鍵 |
| user_id | INTEGER | NOT NULL, FK → users.id (CASCADE) | 使用者ID |
| token_jti | VARCHAR(255) | UNIQUE, NOT NULL | JWT ID |
| refresh_token | VARCHAR(255) | | 刷新令牌 |
| ip_address | VARCHAR(255) | | IP 位址 |
| user_agent | TEXT | | 使用者代理 |
| device_info | TEXT | | 裝置資訊 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 建立時間 |
| expires_at | TIMESTAMP | NOT NULL | 過期時間 |
| last_activity | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 最後活動時間 |
| is_active | BOOLEAN | DEFAULT true | 是否活躍 |
| revoked_at | TIMESTAMP | | 撤銷時間 |

---

### 13. site_navigation_items (網站導航表)

**對應模型**: `app.extended.models.SiteNavigationItem`

| 欄位名稱 | 資料類型 | 限制條件 | 說明 |
|----------|----------|----------|------|
| id | INTEGER | PRIMARY KEY | 自增主鍵 |
| title | VARCHAR(100) | NOT NULL | 導航標題 |
| key | VARCHAR(100) | UNIQUE, NOT NULL | 導航鍵值 |
| path | VARCHAR(200) | | 路徑 |
| icon | VARCHAR(50) | | 圖標 |
| sort_order | INTEGER | DEFAULT 0 | 排序 |
| parent_id | INTEGER | FK → site_navigation_items.id | 父級ID |
| is_enabled | BOOLEAN | DEFAULT true | 是否啟用 |
| is_visible | BOOLEAN | DEFAULT true | 是否顯示 |
| level | INTEGER | DEFAULT 1 | 層級 |
| description | VARCHAR(500) | | 描述 |
| target | VARCHAR(50) | DEFAULT '_self' | 打開方式 |
| permission_required | TEXT | | 所需權限 (JSON) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新時間 |

---

### 14. site_configurations (網站配置表)

**對應模型**: `app.extended.models.SiteConfiguration`

| 欄位名稱 | 資料類型 | 限制條件 | 說明 |
|----------|----------|----------|------|
| id | INTEGER | PRIMARY KEY | 自增主鍵 |
| key | VARCHAR(100) | UNIQUE, NOT NULL | 配置鍵 |
| value | TEXT | | 配置值 |
| description | VARCHAR(200) | | 描述 |
| category | VARCHAR(50) | DEFAULT 'general' | 分類 |
| is_active | BOOLEAN | DEFAULT true | 是否啟用 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新時間 |

---

### 15. project_agency_contacts (專案機關承辦表)

**對應模型**: `app.extended.models.ProjectAgencyContact`

| 欄位名稱 | 資料類型 | 限制條件 | 說明 |
|----------|----------|----------|------|
| id | INTEGER | PRIMARY KEY | 自增主鍵 |
| project_id | INTEGER | NOT NULL, FK → contract_projects.id (CASCADE) | 關聯專案ID |
| contact_name | VARCHAR(100) | NOT NULL | 承辦人姓名 |
| position | VARCHAR(100) | | 職稱 |
| department | VARCHAR(200) | | 單位/科室 |
| phone | VARCHAR(50) | | 電話 |
| mobile | VARCHAR(50) | | 手機 |
| email | VARCHAR(100) | | 電子郵件 |
| is_primary | BOOLEAN | DEFAULT false | 是否為主要承辦人 |
| notes | TEXT | | 備註 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新時間 |

---

## 重要對應關係

### 模型與表名對應
```python
# 正確對應
class OfficialDocument(Base):
    __tablename__ = "documents"  # ✅ 正確

class ContractProject(Base):
    __tablename__ = "contract_projects"  # ✅ 正確

class PartnerVendor(Base):
    __tablename__ = "partner_vendors"  # ✅ 正確
```

### 欄位命名規範
```python
# 使用 snake_case 命名
sender_agency_id = Column(Integer, ...)       # ✅ 正確
contract_project_id = Column(Integer, ...)    # ✅ 正確

# 避免駝峰式命名
senderAgencyId = Column(Integer, ...)         # ❌ 錯誤
```

---

## 常用查詢範例

### 檢查所有表格
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

### 查看表格結構
```sql
\d documents
\d contract_projects
```

### 檢查欄位資訊
```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'documents'
ORDER BY ordinal_position;
```

### 常用業務查詢
```sql
-- 按年度統計公文數量
SELECT
    EXTRACT(YEAR FROM doc_date) as year,
    COUNT(*) as doc_count
FROM documents
WHERE doc_date IS NOT NULL
GROUP BY EXTRACT(YEAR FROM doc_date)
ORDER BY year DESC;

-- 按狀態統計
SELECT status, COUNT(*) as count
FROM documents
GROUP BY status
ORDER BY count DESC;

-- 查詢關聯資料
SELECT
    d.doc_number,
    d.subject,
    cp.project_name,
    ga.agency_name as sender_agency
FROM documents d
LEFT JOIN contract_projects cp ON d.contract_project_id = cp.id
LEFT JOIN government_agencies ga ON d.sender_agency_id = ga.id
LIMIT 10;
```

---

## 維護指令

### 資料庫連接測試
```bash
# 使用 docker 連接
docker exec CK_Missive_postgres psql -U ck_user -d ck_documents -c "SELECT 1"

# 檢查表格數量
docker exec CK_Missive_postgres psql -U ck_user -d ck_documents -c "SELECT COUNT(*) FROM documents"
```

### 備份與恢復
```bash
# 備份
docker exec CK_Missive_postgres pg_dump -U ck_user ck_documents > backup_$(date +%Y%m%d).sql

# 恢復
docker exec -i CK_Missive_postgres psql -U ck_user ck_documents < backup.sql
```

---

## 效能優化建議

1. **索引使用**:
   - 查詢經常使用的欄位已建立索引
   - 定期分析查詢效能：`EXPLAIN ANALYZE`

2. **資料清理**:
   - 定期清理軟刪除資料
   - 歸檔舊資料：建議按年度歸檔

3. **連接池設置**:
   - 使用 asyncpg 連接池
   - 適當設置最大連接數

---

## 變更記錄

| 日期 | 版本 | 變更內容 |
|------|------|----------|
| 2026-01-08 | v2.0.0 | 全面更新至最新 schema，新增 15 個資料表定義 |
| 2024-09-11 | v1.0.0 | 初始版本 |
