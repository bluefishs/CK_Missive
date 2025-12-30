# 文管中心概念與設計

## 1. 概念目標

「文管中心」將作為系統中所有公文相關操作的統一入口和核心樞紐。它不僅提供基本的公文管理功能，更旨在提供一個全面、高效、智能化的文件生命週期管理平台，讓使用者能輕鬆地進行公文的存儲、檢索、處理和分析。

## 2. 核心功能模組

### 2.1. 公文總覽與儀表板 (Document Overview & Dashboard)
*   **目的**：提供公文數據的宏觀視圖和關鍵指標。
*   **內容**：公文總數、收發文統計、各類別公文分佈、近期活動、待處理公文概覽等。

### 2.2. 公文查詢與檢索 (Document Search & Retrieval)
*   **目的**：支援多維度、精確和模糊的公文查詢。
*   **內容**：
    *   **基本查詢**：文號、主旨、發文/收文機關、日期範圍、狀態等。
    *   **高級查詢**：組合多個條件、關鍵字全文檢索（若有全文索引）。
    *   **篩選與排序**：按年度、類別、承辦人等進行篩選，並支援多種排序方式。

### 2.3. 公文生命週期管理 (Document Lifecycle Management)
*   **目的**：管理公文從創建到歸檔的整個過程。
*   **內容**：
    *   **公文創建**：手動錄入新公文。
    *   **公文詳情**：查看單一公文的所有詳細資訊。
    *   **公文編輯**：修改公文元數據。
    *   **公文刪除**：支援軟刪除（`is_deleted` 標記）。
    *   **公文狀態流轉**：例如從「待處理」到「已辦畢」（若有工作流）。

### 2.4. 公文批次處理與匯入/匯出 (Document Batch Processing & Import/Export)
*   **目的**：支援大量公文的自動化處理。
*   **內容**：
    *   **CSV 匯入**：利用現有 `csv_processor` 實現批量公文數據匯入。
    *   **數據匯出**：支援將查詢結果匯出為 Excel、PDF 等格式。
    *   **批次更新/刪除**：對符合條件的公文進行批量操作。

### 2.5. 公文統計與分析 (Document Statistics & Analysis)
*   **目的**：提供公文數據的深度分析和報告。
*   **內容**：按年度、類型、機關、承辦人等維度進行統計圖表展示。

## 3. 架構整合

### 3.1. 前端 (React)
*   建立一個專門的「文管中心」主頁面，作為所有公文相關功能的導航入口。
*   設計儀表板組件，展示公文概覽數據。
*   開發公文列表、詳情、編輯、匯入/匯出等頁面，並與後端 API 進行互動。
*   利用現有的 UI 組件庫 (Material-UI) 保持介面一致性。

### 3.2. 後端 (FastAPI)
*   **API 端點**：主要利用現有的 `app/api/endpoints/documents.py`，並根據需要進行擴展或新增。
*   **服務層**：主要利用現有的 `app/services/document_service.py`，並根據需要新增方法或創建新的服務（例如 `document_stats_service.py`）。
*   **數據模型**：繼續使用 `OfficialDocument` 模型。
*   **數據處理**：繼續利用 `csv_processor.py` 進行 CSV 數據預處理。
*   **快取**：繼續利用 `app/core/cache.py` 進行 API 響應快取，提升性能。

## 4. API 服務規劃 (基於現有 API 擴展與新增)

### 4.1. 公文總覽與儀表板
*   **`GET /api/documents/stats`**
    *   **目的**：獲取公文總數、收發文統計、年度分佈等儀表板數據。
    *   **服務層**：擴展 `DocumentService` 或新增 `DocumentStatsService`。
    *   **說明**：提供快速概覽，支援按年度、類型等篩選。

### 4.2. 公文查詢與檢索
*   **`GET /api/documents`** (現有 API，增強篩選和排序能力)
    *   **目的**：獲取公文列表。
    *   **服務層**：`DocumentService.get_documents`。
    *   **說明**：支援更複雜的組合查詢條件（例如多個關鍵字、多個狀態）。
*   **`GET /api/documents/{doc_id}`** (現有 API)
    *   **目的**：獲取單一公文詳情。
    *   **服務層**：`DocumentService.get_document_by_id`。

### 4.3. 公文生命週期管理
*   **`POST /api/documents`** (現有 API)
    *   **目的**：創建新公文。
    *   **服務層**：`DocumentService.create_document`。
*   **`PUT /api/documents/{doc_id}`** (現有 API)
    *   **目的**：更新公文。
    *   **服務層**：`DocumentService.update_document`。
*   **`DELETE /api/documents/{doc_id}`** (現有 API)
    *   **目的**：刪除公文（軟刪除）。
    *   **服務層**：`DocumentService.delete_document`。

### 4.4. 公文批次處理與匯入/匯出
*   **`POST /api/documents/import`** (現有 API)
    *   **目的**：匯入 CSV 格式公文。
    *   **服務層**：`DocumentService.import_documents_from_processed_data`。
*   **`GET /api/documents/export`**
    *   **目的**：匯出公文數據（例如 Excel）。
    *   **服務層**：擴展 `DocumentService.export_to_excel`。
    *   **說明**：支援按篩選條件匯出。
*   **`POST /api/documents/batch-update`**
    *   **目的**：批量更新公文狀態、承辦人等。
    *   **服務層**：新增 `DocumentService.batch_update_documents`。
    *   **請求體**：包含公文 ID 列表和要更新的欄位。
*   **`POST /api/documents/batch-delete`**
    *   **目的**：批量軟刪除公文。
    *   **服務層**：新增 `DocumentService.batch_delete_documents`。
    *   **請求體**：包含公文 ID 列表。

### 4.5. 公文統計與分析
*   **`GET /api/documents/analysis/by-year`**
    *   **目的**：按年度統計公文數量。
    *   **服務層**：擴展 `DocumentService` 或新增 `DocumentStatsService`。
*   **`GET /api/documents/analysis/by-type`**
    *   **目的**：按公文類型（收文/發文）統計。
    *   **服務層**：同上。
*   **`GET /api/documents/analysis/by-agency`**
    *   **目的**：按發文/收文機關統計。
    *   **服務層**：同上。
