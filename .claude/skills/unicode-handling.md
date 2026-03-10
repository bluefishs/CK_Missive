---
name: unicode-handling
description: Unicode 字元處理指南（康熙部首 + CJK 相容漢字）
version: 2.0.0
category: backend
triggers:
  - Unicode
  - 編碼
  - 字元
  - 康熙部首
  - CJK
  - 正規化
  - normalize
  - 亂碼
  - 搜尋失敗
  - ILIKE
updated: '2026-03-04'
---

# Unicode 字元處理指南

## 概述

本指南說明 CK_Missive 系統中 Unicode 字元處理的最佳實踐。涵蓋兩大類異常字元的偵測與正規化。

## 異常字元範圍

### 1. 康熙部首 (U+2F00 - U+2FDF)

政府系統、PDF 複製可能引入康熙部首字元。

| 正常字元 | 康熙部首 | Unicode |
|----------|----------|---------|
| 用 | ⽤ | U+7528 vs U+2F64 |
| 土 | ⼟ | U+571F vs U+2F1F |
| 口 | ⼝ | U+53E3 vs U+2F14 |

### 2. CJK 相容漢字 (U+F900 - U+FAFF) — v2.0 新增

**最危險的類別**：字元外觀與標準漢字完全相同，肉眼無法辨別。

| 正常字元 | CJK 相容 | Unicode | 來源 |
|----------|----------|---------|------|
| 龍 | 龍 | U+9F8D vs U+F9C4 | 政府公文系統 |
| 路 | 路 | U+8DEF vs U+F937 | PDF 複製 |
| 金 | 金 | U+91D1 vs U+F90A | 某些字型 |

**症狀**：`ILIKE '%龍岡%'` 查無結果，但肉眼看文字完全正常。

### 3. 全形英數 (U+FF01 - U+FF5E) — 僅選擇性處理

中文語境中全形標點（，、。「」）是**正常**的，預設不視為異常。僅 `--fullwidth` 模式才處理。

## 解決方案

### 1. 寫入時自動正規化（防禦層）

`document_service.py` 在 `create_document()` 時自動正規化 7 個文字欄位：

```python
from app.scripts.normalize_unicode import normalize_text

# create_document() 中
for key in ('doc_number', 'subject', 'sender', 'receiver', 'notes', 'content', 'ck_note'):
    if key in doc_data and doc_data[key] and isinstance(doc_data[key], str):
        doc_data[key] = normalize_text(doc_data[key])
```

### 2. 資料庫清理工具 (v3.0)

```bash
cd backend

# 檢查異常字元（不修改）
python -m app.scripts.normalize_unicode --check

# 顯示異常字元細節
python -m app.scripts.normalize_unicode --check --verbose

# 同時檢查全形英數
python -m app.scripts.normalize_unicode --check --fullwidth

# 執行修復
python -m app.scripts.normalize_unicode --fix

# 指定特定表
python -m app.scripts.normalize_unicode --check --table documents
```

### 3. 前端篩選優化

使用唯一識別碼（如案件編號）取代全名進行篩選：

```typescript
const FIXED_CONTRACT_CODE = 'CK2025_01_03_001';  // 精確匹配
const FIXED_CONTRACT_NAME = '115年度桃園市...';   // 僅用於顯示
```

## 正規化策略

### 核心函數（SSOT）

位於 `backend/app/scripts/normalize_unicode.py`，由 `document_service.py` 匯入使用。

```python
def normalize_text(value: str) -> str:
    """逐字元判斷，僅轉換異常範圍，保留全形標點"""
    if not value:
        return value
    result = []
    for char in value:
        cp = ord(char)
        if 0x2F00 <= cp <= 0x2FDF or 0xF900 <= cp <= 0xFAFF:
            result.append(unicodedata.normalize('NFKC', char))
        else:
            result.append(char)
    return ''.join(result)
```

**為什麼不用全域 NFKC？** 全域 `unicodedata.normalize('NFKC', text)` 會把全形逗號（，）轉成半形（,），但中文語境中全形標點是正常的。

### 掃描白名單

| 表 | 欄位 |
|----|------|
| `documents` | subject, content, notes, ck_note, doc_number |
| `contract_projects` | project_name, project_code, description |
| `government_agencies` | agency_name, agency_short_name, address |
| `partner_vendors` | vendor_name, contact_person, address |
| `taoyuan_dispatch_orders` | project_name, dispatch_no, sub_case_name, contact_note |

## 相關檔案

| 檔案 | 用途 |
|------|------|
| `backend/app/scripts/normalize_unicode.py` | Unicode 正規化工具 (v3.0, SSOT) |
| `backend/app/services/document_service.py` | 寫入時自動正規化 |

## 常見陷阱

1. **UNIQUE 約束衝突**：正規化後兩筆記錄可能變成相同值（如 government_agencies），需先 `--check` 再 `--fix`
2. **全形標點誤殺**：禁止使用全域 NFKC，必須逐字元判斷
3. **Per-table session**：修復時每個表用獨立 session，避免一表錯誤中斷全部

## 參考資源

- [Unicode 康熙部首](https://en.wikipedia.org/wiki/Kangxi_Radicals_(Unicode_block))
- [CJK Compatibility Ideographs](https://en.wikipedia.org/wiki/CJK_Compatibility_Ideographs)
- [Python unicodedata](https://docs.python.org/3/library/unicodedata.html)
- [Unicode 正規化形式](https://unicode.org/reports/tr15/)
