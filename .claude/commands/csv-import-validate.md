# CSV 匯入驗證 (CSV Import Validation)

驗證並匯入公文 CSV 檔案，確保資料品質。

## CSV 檔案規範

### 收文 CSV (receiveList.csv)
必要欄位：
- `收文日期` - 格式: YYYY/MM/DD
- `發文字號` - 公文字號 (需包含「字第」)
- `發文單位` - 機關名稱
- `主旨` - 公文主旨

### 發文 CSV (sendList.csv)
必要欄位：
- `發文日期` - 格式: YYYY/MM/DD
- `發文字號` - 公文字號 (需包含「字第」)
- `受文單位` - 機關名稱
- `主旨` - 公文主旨

## 驗證規則

| 規則 | 說明 | 失敗處理 |
|------|------|----------|
| 公文字號格式 | 必須包含「字第」且前有機關字首 (≥2字元) | 跳過該筆 |
| 主旨內容檢查 | 不可為空、test、testing、測試 | 跳過該筆 |
| 主旨長度警告 | 少於 5 字元 | 記錄警告，繼續匯入 |
| 日期格式 | 必須為有效日期 | 跳過該筆 |

## 匯入前檢查

在匯入前，先檢查 CSV 檔案內容：

```python
import pandas as pd

# 讀取 CSV
df = pd.read_csv('path/to/file.csv', encoding='utf-8-sig')

# 檢查空主旨
empty_subject = df[df['主旨'].isna() | (df['主旨'] == '')]
print(f"空主旨: {len(empty_subject)} 筆")

# 檢查測試資料
test_data = df[df['主旨'].str.lower().isin(['test', 'testing', '測試'])]
print(f"測試資料: {len(test_data)} 筆")

# 檢查公文字號格式
invalid_doc = df[~df['發文字號'].str.contains('字第', na=False)]
print(f"格式異常: {len(invalid_doc)} 筆")
```

## 匯入步驟

### 1. 上傳 CSV 檔案
將 CSV 檔案放置於 `data/imports/` 目錄

### 2. 執行匯入
```bash
# 透過 API 匯入
curl -X POST http://localhost:8001/api/documents/import \
  -F "file=@data/imports/receiveList.csv" \
  -F "category=receive"
```

### 3. 驗證匯入結果
```sql
-- 檢查最新匯入的資料
SELECT id, doc_number, subject, created_at
FROM documents
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY id DESC;
```

## 驗證器位置

主要驗證邏輯位於：
`backend/app/services/csv_processor.py`

關鍵函數：
- `process_csv_row()` - 單筆資料驗證
- `validate_doc_number()` - 公文字號格式驗證
- `validate_subject()` - 主旨內容驗證

## 錯誤處理

### 常見錯誤及解決方案

| 錯誤 | 原因 | 解決方案 |
|------|------|----------|
| UnicodeDecodeError | 編碼問題 | 使用 `utf-8-sig` 編碼 |
| KeyError | 欄位名稱不符 | 檢查 CSV 標題列 |
| 空主旨被匯入 | 驗證未啟用 | 確認 csv_processor.py 驗證邏輯 |

## 相關文件

- 系統規範: `@fix_plan.md` (資料品質管理章節)
- CSV 處理器: `backend/app/services/csv_processor.py`
- 匯入 API: `backend/app/api/endpoints/documents_enhanced.py`
