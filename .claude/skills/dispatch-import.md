---
name: dispatch-import
description: 派工單匯入與公文關聯 (Dispatch Import & Document Linking)
version: 1.0.0
category: project
triggers:
  - 匯入
  - import
  - Excel
  - 派工單匯入
  - batch-relink
  - 文號
  - doc_number
  - agency_doc_number
  - company_doc_number
updated: '2026-03-05'
---

# 派工單匯入與公文關聯

## 概述

派工單 Excel 匯入服務，負責：
1. Excel 工作表智慧偵測與欄位映射
2. 派工單批次建立（含自動序號生成）
3. **文號解析 + 公文自動關聯**（匯入時即時匹配）
4. **批次重新關聯**（公文後建檔時補建關聯）

---

## Excel 欄位映射

| Excel 欄位 | DB 欄位 | 類型 | 說明 |
|-----------|---------|------|------|
| 派工單號 | `dispatch_no` | String(50) | 無則自動生成 |
| 機關函文號 | `agency_doc_number_raw` | String(500) | 原始值保留，支援多文號 |
| 工程名稱/派工事項 | `project_name` | String(500) | **必填** |
| 作業類別 | `work_type` | String(200) | **必填** |
| 分案名稱/派工備註 | `sub_case_name` | String(200) | 選填 |
| 履約期限 | `deadline` | String(200) | Excel 日期→民國年格式 |
| 案件承辦 | `case_handler` | String(50) | 選填 |
| 查估單位 | `survey_unit` | String(100) | 選填 |
| 乾坤函文號 | `company_doc_number_raw` | String(500) | 原始值保留，支援多文號 |
| 雲端資料夾 | `cloud_folder` | String(500) | 選填 |
| 專案資料夾 | `project_folder` | String(500) | 選填 |
| 聯絡備註 | `contact_note` | String(500) | 選填 |

---

## 匯入流程

```
1. 工作表偵測
   ├─ 精確匹配：{派工單號, 工程名稱/派工事項, 作業類別} 三欄皆在同一 Sheet
   ├─ 部分匹配：≥3 個映射欄位 → 自動選擇
   └─ 未找到 → 錯誤回報（列出所有 Sheet 名稱）

2. 年度解析
   └─ 從承攬案件名稱解析民國年（支援「112至113年度」→ 取首年 112）

3. 公文預載 (效能優化)
   └─ SELECT doc_number, id FROM documents WHERE project_id = ? → Map

4. 逐行處理
   ├─ 欄位提取 + 轉換
   ├─ 派工單號自動生成（若空白）
   ├─ 原始文號保留 → agency_doc_number_raw / company_doc_number_raw
   ├─ 建立派工單（auto_commit=False）
   ├─ 文號解析 → 公文匹配 → 建立關聯（不阻斷匯入）
   └─ 異常捕捉 → 記錄至 errors 列表

5. 統一 Commit + 回傳結果
```

---

## 文號解析規則

**工具函數**: `backend/app/utils/doc_number_parser.py`

```python
parse_doc_numbers(raw_input: str) -> List[str]
```

| 規則 | 範例 |
|------|------|
| 換行分隔 | `"桃工用字第1號\n桃工用字第2號"` → `['桃工用字第1號', '桃工用字第2號']` |
| 分號分隔 | `"桃工用字第1號；桃工用字第2號"` → 同上 |
| 移除書名號 | `"「桃工用字第1號」"` → `'桃工用字第1號'` |
| 全形→半形 | 全形數字/括號轉半形 |
| 去重保序 | 多次出現同文號只取第一次 |

---

## 公文關聯機制

### 匯入時自動關聯 (`_link_documents_by_number`)

```
1. 解析文號列表
2. 每個文號 → 查詢預載 Map 精確匹配
3. 找到 → DispatchDocLinkRepository.link_dispatch_to_document()
   - 機關函文號 → link_type='agency_incoming'
   - 乾坤函文號 → 智慧判斷（「乾坤」開頭='company_outgoing'，否則='agency_incoming'）
4. 第一筆匹配 → 更新 FK（agency_doc_id / company_doc_id，僅當 FK 為空時）
5. 找不到 → 記入 not_found（不阻斷匯入）
```

### 批次重新關聯 (`batch_relink_by_project`)

**適用場景**：派工單先匯入，公文後建檔

```
POST /dispatch/batch-relink-documents
Body: { "contract_project_id": int }

流程：
1. 查詢有原始文號的所有派工單
2. 預載該案件公文 Map
3. 逐筆解析文號 + 匹配 + 建立關聯
4. 回傳：{ total_scanned, newly_linked, already_linked, not_found }
```

---

## API 端點

| 端點 | 說明 |
|------|------|
| `POST /dispatch/import` | Excel 匯入（含自動關聯） |
| `POST /dispatch/import-template` | 下載匯入範本 |
| `POST /dispatch/batch-relink-documents` | 批次重新關聯 |

**路由順序**：靜態路由（import, batch-relink-documents）**必須**在 `{dispatch_id}` 動態路由之前。

---

## 回傳 Schema

```python
{
    'success': bool,
    'total': int,               # 總列數
    'success_count': int,       # 成功建立數
    'error_count': int,         # 錯誤列數
    'errors': List[str],        # 錯誤訊息
    'doc_link_stats': {         # 公文關聯統計
        'linked': int,
        'not_found': List[str],
    },
    'warnings': List[str],      # 非致命警告
}
```

---

## 關鍵檔案

| 檔案 | 職責 |
|------|------|
| `backend/app/services/taoyuan/dispatch_import_service.py` | 核心匯入邏輯 |
| `backend/app/utils/doc_number_parser.py` | 文號解析工具 |
| `backend/app/api/endpoints/taoyuan_dispatch/dispatch.py` | API 端點 |
| `backend/app/schemas/taoyuan/dispatch.py` | 請求/回應 Schema |
| `backend/app/repositories/taoyuan/dispatch_doc_link_repository.py` | 派工-公文關聯 |

## 常見陷阱

1. **Excel 日期格式**：Excel 內建日期為浮點數（如 45371），需轉為民國年字串
2. **多文號欄位**：一個儲存格可能含多筆文號（換行分隔），必須逐一解析
3. **文號未匹配不阻斷**：匯入必須繼續，未匹配文號記入 warnings
4. **向下相容 FK**：`agency_doc_id` / `company_doc_id` 僅當 FK 為空時設定第一筆匹配
5. **冪等性**：`link_dispatch_to_document()` 有唯一約束，重複執行安全
6. **原始文號保留**：`agency_doc_number_raw` / `company_doc_number_raw` ≤500 字元，供批次重新關聯使用
