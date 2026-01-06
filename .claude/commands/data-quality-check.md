# 資料品質檢查 (Data Quality Check)

執行 CK_Missive 公文管理系統的資料品質檢查。

## 檢查項目

### 1. 公文字號格式檢查
檢查公文字號是否符合標準格式（包含「字第」且前有機關字首）。

### 2. 主旨內容檢查
檢查是否有空白或測試資料的主旨。

### 3. 資料關聯檢查
檢查專案關聯的有效性。

## 執行步驟

請按以下順序執行檢查：

1. **連接資料庫**
```bash
docker exec -it ck_missive_postgres_dev psql -U ck_user -d ck_documents
```

2. **執行檢查 SQL**

### 空白主旨檢查
```sql
SELECT id, doc_number, category, created_at
FROM documents
WHERE subject IS NULL OR subject = '' OR subject = 'test'
ORDER BY id;
```

### 公文字號格式檢查
```sql
SELECT id, doc_number, subject
FROM documents
WHERE doc_number NOT LIKE '%字第%'
ORDER BY id;
```

### 孤立專案關聯檢查
```sql
SELECT d.id, d.doc_number, d.contract_project_id
FROM documents d
WHERE d.contract_project_id IS NOT NULL
AND d.contract_project_id NOT IN (SELECT id FROM contract_projects)
ORDER BY d.id;
```

### 統計摘要
```sql
SELECT
    COUNT(*) as total_documents,
    SUM(CASE WHEN subject IS NULL OR subject = '' THEN 1 ELSE 0 END) as empty_subject,
    SUM(CASE WHEN subject = 'test' OR subject = 'testing' THEN 1 ELSE 0 END) as test_data,
    SUM(CASE WHEN doc_number NOT LIKE '%字第%' THEN 1 ELSE 0 END) as invalid_doc_number,
    SUM(CASE WHEN contract_project_id IS NOT NULL THEN 1 ELSE 0 END) as linked_to_project
FROM documents;
```

## 修復指南

如果發現問題，請參考以下修復方式：

### 修復空白主旨
1. 查找原始 CSV 檔案中的正確資料
2. 執行更新：
```sql
UPDATE documents SET subject = '正確主旨' WHERE id = <問題ID>;
```

### 修復測試資料
直接刪除測試資料：
```sql
DELETE FROM documents WHERE subject IN ('test', 'testing', '測試') AND id > 0;
```

## 預防措施

確保 `backend/app/services/csv_processor.py` 中的驗證規則已啟用：
- 公文字號格式驗證
- 測試資料過濾
- 空白主旨檢查

## 相關文件
- 系統規範: `@fix_plan.md` (資料品質管理章節)
- 備份腳本: `scripts/backup/README.md`
- CSV 處理器: `backend/app/services/csv_processor.py`
