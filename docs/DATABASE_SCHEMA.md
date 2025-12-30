# 資料庫結構說明文件

## 📊 資料庫概況

**資料庫系統**: PostgreSQL 15+ (Docker容器)
**連接資訊**:
- Host: localhost
- Port: 5434
- Database: ck_documents
- Username: ck_user
- Password: ck_password

## 📋 核心資料表

### 1. documents (公文檔案表)

**對應模型**: `app.extended.models.OfficialDocument`

| 欄位名稱 | 資料類型 | 限制條件 | 說明 |
|----------|----------|----------|------|
| id | integer | PRIMARY KEY | 自增主鍵 |
| doc_number | varchar(100) | UNIQUE | 公文文號 |
| doc_type | varchar(50) | | 公文類型 (收文/發文) |
| subject | text | | 公文主旨 |
| content | text | | 公文內容摘要 |
| sender | varchar(200) | | 發文單位 |
| receiver | varchar(200) | | 收文單位 |
| doc_date | date | | 公文日期 |
| receive_date | date | | 收文日期 |
| send_date | date | | 發文日期 |
| serial_number | integer | | 流水號 |
| status | varchar(50) | DEFAULT '收文完成' | 處理狀態 |
| category | varchar(100) | | 公文分類 |
| doc_class | varchar(50) | | 公文類別 (函、令等) |
| doc_word | varchar(50) | | 公文字 (府、院、部等) |
| contract_case | varchar(200) | | 承攬案件名稱 |
| assignee | varchar(100) | | 承辦人 |
| priority | integer | DEFAULT 3 | 優先級 (數字) |
| user_confirm | boolean | DEFAULT false | 使用者確認狀態 |
| auto_serial | integer | | 自動生成流水號 |
| notes | text | | 備註 |
| is_deleted | boolean | DEFAULT false | 軟刪除標記 |
| creator | varchar(100) | | 建立者 |
| created_at | timestamp | DEFAULT CURRENT_TIMESTAMP | 建立時間 |
| updated_at | timestamp | DEFAULT CURRENT_TIMESTAMP | 更新時間 |

**索引**:
- PRIMARY KEY: `documents_pkey` (id)
- UNIQUE: `documents_doc_number_key` (doc_number)
- INDEX: `idx_documents_created_at_desc` (created_at DESC)
- INDEX: `idx_documents_doc_date_status` (doc_date DESC, status)
- INDEX: `idx_documents_sender_receiver` (sender, receiver)
- INDEX: `idx_documents_status_category` (status, category)
- INDEX: `idx_documents_subject_search` (subject)

### 2. users (用戶管理表)

**對應模型**: `User`

| 欄位名稱 | 資料類型 | 限制條件 | 說明 |
|----------|----------|----------|------|
| id | integer | PRIMARY KEY | 自增主鍵 |
| username | varchar(100) | UNIQUE, NOT NULL | 用戶名 |
| email | varchar(100) | UNIQUE | 電子郵件 |
| created_at | timestamp | DEFAULT CURRENT_TIMESTAMP | 建立時間 |
| updated_at | timestamp | DEFAULT CURRENT_TIMESTAMP | 更新時間 |

### 3. cases (承攬案件表)

**對應模型**: `Case`

| 欄位名稱 | 資料類型 | 限制條件 | 說明 |
|----------|----------|----------|------|
| id | integer | PRIMARY KEY | 自增主鍵 |
| case_name | varchar(200) | NOT NULL | 案件名稱 |
| status | varchar(50) | | 案件狀態 |
| created_at | timestamp | DEFAULT CURRENT_TIMESTAMP | 建立時間 |
| updated_at | timestamp | DEFAULT CURRENT_TIMESTAMP | 更新時間 |

## ⚠️ 重要對應關係

### 模型與表名對應
```python
# 正確對應
class OfficialDocument(Base):
    __tablename__ = "documents"  # ✅ 正確

# 錯誤範例
class OfficialDocument(Base):
    __tablename__ = "official_documents"  # ❌ 錯誤
```

### 欄位名稱對應
```python
# 正確欄位名稱
sender = Column(String(200), comment="發文單位")          # ✅
receiver = Column(String(200), comment="收文單位")        # ✅
priority = Column(Integer, comment="優先級")              # ✅

# 錯誤範例
sender_agency = Column(String(200))                      # ❌
receiver_agency = Column(String(200))                    # ❌
priority_level = Column(String(20))                      # ❌
```

## 🔍 常用查詢範例

### 1. 檢查所有表格
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
```

### 2. 查看 documents 表結構
```sql
\d documents
```

### 3. 檢查欄位資訊
```sql
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'documents' 
ORDER BY ordinal_position;
```

### 4. 常用業務查詢
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

-- 按發文單位統計
SELECT sender, COUNT(*) as count
FROM documents 
WHERE sender IS NOT NULL
GROUP BY sender
ORDER BY count DESC
LIMIT 10;
```

## 🛠️ 維護指令

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
docker exec CK_Missive_postgres pg_dump -U ck_user ck_documents > backup.sql

# 恢復
docker exec -i CK_Missive_postgres psql -U ck_user ck_documents < backup.sql
```

## 📈 效能優化建議

1. **索引使用**:
   - 查詢經常使用的欄位已建立索引
   - 定期分析查詢效能：`EXPLAIN ANALYZE`

2. **資料清理**:
   - 定期清理軟刪除資料：`WHERE is_deleted = false`
   - 歸檔舊資料：建議按年度歸檔

3. **連接池設置**:
   - 使用 asyncpg 連接池
   - 適當設置最大連接數

---

**最後更新**: 2024年9月11日
**維護者**: 系統開發團隊