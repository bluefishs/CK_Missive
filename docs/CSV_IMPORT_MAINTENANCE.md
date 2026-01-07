# CSV 匯入功能維護指南

本文件說明 CK_Missive 系統 CSV 匯入功能的完整流程、關鍵程式碼位置，以及維護注意事項。

## 目錄

- [整體架構](#整體架構)
- [匯入流程圖](#匯入流程圖)
- [關鍵檔案位置](#關鍵檔案位置)
- [機關名稱解析邏輯](#機關名稱解析邏輯)
- [常見問題與修復](#常見問題與修復)
- [維護 API](#維護-api)
- [擴展指南](#擴展指南)

---

## 整體架構

CSV 匯入功能採用分層架構設計：

```
┌─────────────────────────────────────────────────────────────┐
│                      前端 (Frontend)                         │
│  DocumentImport.jsx → documentsApi.importCSV()              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    API 端點 (Endpoint)                       │
│  csv_import.py: upload_and_import_csv()                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   匯入服務 (Service)                         │
│  document_import_service.py: import_documents_from_file()   │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────────┐
│   CSV 處理器             │     │   文件服務                   │
│   csv_processor.py       │     │   document_service.py       │
│   - 編碼偵測             │     │   - 資料庫操作               │
│   - 標頭解析             │     │   - 機關/案件匹配            │
│   - 資料轉換             │     │   - 流水號產生               │
└─────────────────────────┘     └─────────────────────────────┘
                                              │
                              ┌───────────────┴───────────────┐
                              ▼                               ▼
                ┌─────────────────────────┐     ┌─────────────────────────┐
                │   AgencyMatcher         │     │   ProjectMatcher        │
                │   機關名稱智慧匹配       │     │   案件名稱智慧匹配       │
                └─────────────────────────┘     └─────────────────────────┘
```

---

## 匯入流程圖

```
使用者上傳 CSV 檔案
        │
        ▼
┌───────────────────────────────────────┐
│ 1. DocumentCSVProcessor.load_csv_data │
│    - 自動偵測編碼 (UTF-8/BIG5/CP950)  │
│    - 搜尋標頭行                        │
│    - 載入資料                          │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│ 2. DocumentCSVProcessor.prepare_data  │
│    - 欄位名稱映射                      │
│    - 公文字號組合                      │
│    - 民國日期轉換                      │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│ 3. DocumentService.import_documents   │
│    - 去重檢查 (doc_number)            │
│    - 機關匹配 (AgencyMatcher)         │  ← 重要！
│    - 案件匹配 (ProjectMatcher)        │
│    - 流水號產生                        │
│    - 寫入資料庫                        │
└───────────────────────────────────────┘
        │
        ▼
    回傳結果
```

---

## 關鍵檔案位置

| 功能 | 檔案路徑 | 關鍵函數/類別 |
|------|---------|--------------|
| API 端點 | `backend/app/api/endpoints/csv_import.py` | `upload_and_import_csv()` |
| 匯入服務 | `backend/app/services/document_import_service.py` | `DocumentImportService` |
| CSV 處理 | `backend/app/services/csv_processor.py` | `DocumentCSVProcessor` |
| 文件服務 | `backend/app/services/document_service.py` | `import_documents_from_processed_data()` |
| **機關匹配** | `backend/app/services/strategies/agency_matcher.py` | `AgencyMatcher`, `parse_agency_string()` |
| 案件匹配 | `backend/app/services/strategies/agency_matcher.py` | `ProjectMatcher` |
| 機關 API | `backend/app/api/endpoints/agencies.py` | `fix_agency_parsed_names()` |
| 前端元件 | `frontend/src/components/Documents/DocumentImport.jsx` | - |
| 前端 API | `frontend/src/api/documentsApi.ts` | `importCSV()` |

---

## 機關名稱解析邏輯

### 支援的輸入格式

`parse_agency_string()` 函數支援以下格式：

| 格式 | 輸入範例 | 輸出 (代碼, 名稱) |
|------|---------|-------------------|
| A: 括號 | `A01020100G (內政部國土管理署)` | `("A01020100G", "內政部國土管理署")` |
| B: 空格 | `EB50819619 乾坤測繪科技公司` | `("EB50819619", "乾坤測繪科技公司")` |
| C: 全形括號 | `376470600A（彰化縣和美地政事務所）` | `("376470600A", "彰化縣和美地政事務所")` |
| D: 純名稱 | `內政部國土測繪中心` | `(None, "內政部國土測繪中心")` |

### 機關代碼規則

- **長度**：6-12 位
- **組成**：英文字母 (A-Z, a-z) + 數字 (0-9)
- **常見格式**：
  - 政府機關：`A01020100G` (10位，英數混合)
  - 地政事務所：`376470600A` (10位，數字開頭)
  - 公司行號：`EB50819619` (10位，英文開頭)

### 匹配優先順序

`AgencyMatcher.match_or_create()` 依序嘗試：

1. **精確匹配** - 原始字串與 `agency_name` 完全相符
2. **解析後匹配** - 解析出的名稱與 `agency_name` 完全相符
3. **代碼匹配** - 解析出的代碼與 `agency_code` 相符
4. **簡稱匹配** - 與 `agency_short_name` 相符
5. **模糊匹配** - 包含關係 (LIKE '%name%')
6. **自動建立** - 若以上都未匹配，建立新機關記錄

---

## 常見問題與修復

### 問題 1: 機關名稱顯示代碼

**症狀**：機關列表顯示 `A01020100G (內政部國土管理署)` 而非 `內政部國土管理署`

**原因**：舊版匯入邏輯未分離代碼和名稱

**修復方式**：
```bash
# 乾跑模式 - 預覽將修復的資料
curl -X POST "http://localhost:8001/api/agencies/fix-parsed-names" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'

# 實際修復
curl -X POST "http://localhost:8001/api/agencies/fix-parsed-names" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}'
```

### 問題 2: 重複的機關記錄

**症狀**：同一機關有多筆記錄 (格式不同)

**原因**：解析後的名稱已存在，但原始格式不同

**處理方式**：修復 API 會自動合併重複記錄，更新關聯的公文後刪除錯誤記錄

### 問題 3: 新格式無法解析

**症狀**：CSV 中的機關欄位有新的格式，系統無法正確分離

**修復方式**：修改 `parse_agency_string()` 函數，新增對應的正規表達式

---

## 維護 API

### POST /api/agencies/fix-parsed-names

修復機關名稱/代碼解析錯誤的資料。

**請求參數**：
```json
{
  "dry_run": true  // true=預覽模式, false=實際修復
}
```

**回應範例**：
```json
{
  "success": true,
  "message": "找到 4 筆需要修復的機關資料，已修復（0 筆更新，4 筆合併）",
  "fixed_count": 4,
  "details": [
    {
      "id": 18,
      "action": "merge",
      "original_name": "EB50819619 乾坤測繪科技有限公司",
      "new_name": "乾坤測繪科技有限公司",
      "new_code": "EB50819619",
      "merge_to_id": 1
    }
  ]
}
```

**動作類型**：
- `update`: 直接更新名稱和代碼欄位
- `merge`: 合併至已存在的記錄（更新公文關聯後刪除重複記錄）

---

## 擴展指南

### 新增機關代碼格式

1. 編輯 `backend/app/services/strategies/agency_matcher.py`
2. 在 `parse_agency_string()` 函數中新增正規表達式
3. 確保向後相容（不影響現有格式）
4. 新增單元測試

**範例**：新增支援 `[代碼] 名稱` 格式
```python
# 在 parse_agency_string() 中新增
match = re.match(r'^\[([A-Za-z0-9]{6,12})\]\s*(.+)$', raw_string)
if match:
    return match.group(1).strip(), match.group(2).strip()
```

### 新增匹配策略

1. 在 `AgencyMatcher` 類別中新增私有方法 `_try_xxx_match()`
2. 在 `match_or_create()` 中適當位置呼叫
3. 注意快取更新

---

## 更新記錄

| 日期 | 版本 | 變更內容 |
|------|------|---------|
| 2025-01 | 1.0 | 初始版本，新增 `parse_agency_string()` 函數 |
| 2025-01 | 1.1 | 新增 `/fix-parsed-names` 修復 API，支援重複記錄合併 |

---

## 相關文件

- [資料庫結構](./DATABASE_SCHEMA.md)
- [後端 API 概覽](./wiki/Backend-API-Overview.md)
- [服務層架構](./wiki/Service-Layer-Architecture.md)
