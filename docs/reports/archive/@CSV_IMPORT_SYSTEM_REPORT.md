# CSV 匯入機制系統報告

> 最後更新：2026-01-06
> 狀態：✅ 運作正常

---

## 一、系統架構總覽

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CSV 匯入完整流程                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Frontend (DocumentPage.tsx)                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  handleCSVUpload()                                                   │   │
│  │  - 支援單檔/多檔上傳                                                  │   │
│  │  - 單檔 → /api/csv-import/upload-and-import                         │   │
│  │  - 多檔 → /api/csv-import/upload-multiple                           │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                           │
│                                 ▼                                           │
│  Backend API (csv_import.py)                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  POST /upload-and-import     POST /upload-multiple                   │   │
│  │  - 接收 UploadFile           - 接收 List[UploadFile]                │   │
│  │  - 驗證 .csv 副檔名          - 循環處理每個檔案                       │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                           │
│                                 ▼                                           │
│  Service Layer (DocumentImportService)                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  import_documents_from_file()                                        │   │
│  │  1. 呼叫 CSVProcessor 處理原始 bytes                                 │   │
│  │  2. 呼叫 DocumentService 匯入處理後資料                              │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                           │
│             ┌───────────────────┴───────────────────┐                       │
│             ▼                                       ▼                       │
│  ┌─────────────────────────┐         ┌─────────────────────────────────┐   │
│  │ DocumentCSVProcessor    │         │ DocumentService                 │   │
│  │ (csv_processor.py)      │         │ (document_service.py)           │   │
│  │                         │         │                                 │   │
│  │ ✓ 編碼自動偵測          │         │ ✓ 去重檢查 (doc_number)         │   │
│  │   (UTF-8/Big5/CP950)    │         │ ✓ 自動產生流水號                │   │
│  │ ✓ 標頭行自動偵測        │         │   (R0001=收文, S0001=發文)      │   │
│  │ ✓ 欄位名稱映射          │         │ ✓ 智慧機關匹配                  │   │
│  │ ✓ 民國日期→西元日期     │         │   (精確→簡稱→模糊→新增)         │   │
│  │ ✓ 公文字號組合          │         │ ✓ 案件自動關聯                  │   │
│  │   ({字}字第{文號}號)    │         │ ✓ IntegrityError 處理           │   │
│  │ ✓ 文件類型判斷          │         │                                 │   │
│  │   (依檔名/發文單位)     │         │                                 │   │
│  └─────────────────────────┘         └─────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、核心元件說明

### 2.1 DocumentCSVProcessor (`csv_processor.py`)

**職責**：將原始 CSV bytes 轉換為標準化的字典列表

**關鍵功能**：

| 功能 | 說明 | 程式碼位置 |
|------|------|-----------|
| 編碼偵測 | 自動嘗試 UTF-8, UTF-8-sig, Big5, CP950 | `_detect_encoding()` :74-83 |
| 標頭偵測 | 搜尋包含「序號」且包含「主旨」或「文號」的行 | `load_csv_data()` :144-149 |
| 欄位映射 | 17 個核心欄位 + 相容性欄位對應 | `field_mappings` :20-48 |
| 日期轉換 | 民國年 → 西元年 (中華民國114年9月2日 → 2025-09-02) | `_parse_date()` :91-116 |
| 字號組合 | `{字}字第{文號}號` 格式 | `prepare_data()` :199-210 |
| 類型判斷 | 依檔名 (send/receive) 或發文單位判斷 | `_determine_doc_type()` :118-130 |

**欄位映射表**：

```python
CSV 欄位          →  內部欄位            →  資料庫欄位
─────────────────────────────────────────────────────
序號/流水號/編號  →  auto_serial         →  (由 Service 重新產生)
文件類型/類型     →  doc_type            →  doc_type
公文日期          →  roc_date → doc_date →  doc_date
字                →  doc_word            →  (組合用)
文號              →  legacy_doc_number   →  (組合用)
                  →  doc_number          →  doc_number
主旨              →  subject             →  subject
發文單位          →  sender              →  sender
受文單位          →  receiver            →  receiver
收發狀態/狀態     →  status              →  status
收文日期          →  receive_date        →  receive_date
承攬案件          →  contract_case       →  contract_project_id (關聯)
備註              →  notes               →  ⚠️ 模型無此欄位，已略過
```

### 2.2 DocumentService (`document_service.py`)

**職責**：將處理後的資料匯入資料庫

**關鍵方法**：`import_documents_from_processed_data()` :166-276

**處理流程**：

```
1. 去重檢查
   └─ 根據 doc_number 查詢是否已存在 → 存在則 skip

2. 關聯處理
   ├─ _get_or_create_agency_id(sender)    → sender_agency_id
   ├─ _get_or_create_agency_id(receiver)  → receiver_agency_id
   └─ _get_or_create_project_id(contract_case) → contract_project_id

3. 流水號產生
   └─ _get_next_auto_serial(doc_type)
      └─ 收文='R' + 4位數, 發文='S' + 4位數

4. 資料映射
   └─ doc_payload = {
        auto_serial, doc_number, doc_type, category,
        subject, sender, receiver, status,
        sender_agency_id, receiver_agency_id, contract_project_id,
        doc_date, receive_date
      }

5. 寫入資料庫
   └─ Document(**doc_payload) → db.add() → db.flush()

6. 提交事務
   └─ db.commit()
```

### 2.3 API 端點 (`csv_import.py`)

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/csv-import/upload-and-import` | POST | 單檔上傳 |
| `/api/csv-import/upload-multiple` | POST | 多檔批次上傳 |

**回應格式**：

```json
{
  "success": true,
  "message": "CSV 匯入完成：新增 5 筆，跳過重複 2 筆",
  "total_processed": 7,
  "success_count": 5,
  "skipped_count": 2,
  "error_count": 0,
  "errors": [],
  "debug_doc_numbers": ["乾坤測字第1150000001號", ...],
  "processor_used": "DocumentImportService"
}
```

---

## 三、已修復問題清單

### 3.1 嚴重問題 (已修復)

| # | 問題 | 原因 | 修復方式 | 檔案 |
|---|------|------|----------|------|
| 1 | 404 錯誤 | 前端呼叫 `/documents/import`，實際端點為 `/csv-import/upload-and-import` | 修正 endpoint URL | `DocumentPage.tsx` |
| 2 | `processing_time` 驗證失敗 | Schema 要求但未提供 | 加入 `time.time()` 計時 | `document_service.py` |
| 3 | `notes` 欄位錯誤 | OfficialDocument 模型無 `notes` 欄位 | 從 payload 移除 | `document_service.py` |
| 4 | `auto_serial` NOT NULL 違規 | 匯入時未產生流水號 | 新增 `_get_next_auto_serial()` 方法 | `document_service.py` |
| 5 | CORS 錯誤 | 未處理的例外導致 CORS headers 遺失 | 啟用 `generic_exception_handler` | `exceptions.py` |

### 3.2 功能增強

| # | 功能 | 說明 |
|---|------|------|
| 1 | 多檔上傳 | 新增 `/upload-multiple` 端點，前端支援 `multiple={true}` |
| 2 | 詳細錯誤回報 | 加入 `debug_doc_numbers` 和 `errors` 陣列 |
| 3 | IntegrityError 處理 | 捕獲資料庫約束違規，計入 `skipped_count` |

---

## 四、資料庫模型對照

### OfficialDocument 模型 (`models.py`:87-136)

```python
class OfficialDocument(Base):
    __tablename__ = "documents"

    # 必填欄位
    id              = Column(Integer, primary_key=True)
    auto_serial     = Column(String(20), index=True)           # ⚠️ 資料庫 NOT NULL
    doc_number      = Column(String(100), nullable=False)      # NOT NULL
    doc_type        = Column(String(10), nullable=False)       # NOT NULL
    subject         = Column(String(500), nullable=False)      # NOT NULL

    # 選填欄位
    sender          = Column(String(200))
    receiver        = Column(String(200))
    doc_date        = Column(Date)
    receive_date    = Column(Date)
    status          = Column(String(50))
    category        = Column(String(100))
    delivery_method = Column(String(20), default="電子")
    has_attachment  = Column(Boolean, default=False)

    # 外鍵關聯
    contract_project_id = Column(Integer, ForeignKey('contract_projects.id'))
    sender_agency_id    = Column(Integer, ForeignKey('government_agencies.id'))
    receiver_agency_id  = Column(Integer, ForeignKey('government_agencies.id'))
```

**⚠️ 重要：模型沒有的欄位**
- `notes` - CSV 有但模型無，匯入時略過
- `roc_date` - 僅用於日期轉換，不存入資料庫
- `doc_word` / `legacy_doc_number` - 僅用於組合 doc_number

---

## 五、測試結果

### 最近一次匯入測試 (2026-01-06)

| 檔案 | 新增 | 跳過 | 錯誤 | 狀態 |
|------|------|------|------|------|
| 2026-01-06_receiveList.csv | 3 | 0 | 0 | ✅ |
| 2026-01-06_sendList.csv | 4 | 1 | 0 | ✅ |
| **總計** | **510** 筆 | | | |

---

## 六、優化建議

### 6.1 立即可做

| 優先級 | 項目 | 說明 |
|--------|------|------|
| 高 | 移除 `debug_doc_numbers` | 生產環境不需要，減少回應大小 |
| 高 | 加入匯入進度 WebSocket | 大量匯入時提供即時進度 |
| 中 | 批次提交 | 目前逐筆 flush，可改為每 100 筆批次提交 |

### 6.2 長期改進

| 項目 | 說明 |
|------|------|
| 匯入預覽 | 上傳後先預覽資料，確認後再匯入 |
| 欄位映射 UI | 讓使用者自訂 CSV 欄位對應 |
| 匯入歷史記錄 | 記錄每次匯入的結果供查詢 |
| 回滾機制 | 支援撤銷最近一次匯入 |

---

## 七、檔案清單

| 類型 | 檔案路徑 | 說明 |
|------|----------|------|
| API | `backend/app/api/endpoints/csv_import.py` | CSV 匯入端點 |
| Service | `backend/app/services/document_import_service.py` | 匯入流程編排 |
| Service | `backend/app/services/document_service.py` | 資料庫操作 |
| Service | `backend/app/services/csv_processor.py` | CSV 解析處理 |
| Schema | `backend/app/schemas/document.py` | DocumentImportResult |
| Model | `backend/app/extended/models.py` | OfficialDocument |
| Frontend | `frontend/src/pages/DocumentPage.tsx` | UI 與上傳邏輯 |

---

## 八、常見問題排查

### Q1: 匯入顯示成功但無資料

**檢查項目**：
1. 查看 `skipped_count` 是否等於 `total_processed` (全部重複)
2. 檢查 backend log 中的 `doc_number` 是否正確組合
3. 確認資料庫中是否已有相同 `doc_number`

### Q2: CORS 錯誤

**解決方案**：
1. 確認 `exceptions.py` 中 `generic_exception_handler` 已啟用
2. 檢查 backend 是否正常運行 (`curl http://localhost:8001/health`)

### Q3: 日期解析失敗

**支援格式**：
- 民國：`中華民國114年9月2日`
- 西元：`2025-09-02`, `2025/09/02`, `2025-09-02 10:30:00`

---

**報告結束**
