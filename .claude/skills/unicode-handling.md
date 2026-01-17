# Unicode 字元處理指南

> **觸發關鍵字**: Unicode, 編碼, 字元, 康熙部首, 正規化, normalize
> **版本**: 1.0.0
> **更新日期**: 2026-01-16

## 概述

本指南說明 CK_Missive 系統中 Unicode 字元處理的最佳實踐，特別是針對中文字元的正規化問題。

## 常見問題

### 康熙部首問題

政府系統、PDF 文件或某些字型可能使用 **康熙部首** (Unicode U+2F00-U+2FDF) 而非標準中文字元，導致字串比對失敗。

| 正常字元 | 康熙部首 | Unicode |
|----------|----------|---------|
| 用 | ⽤ | U+7528 vs U+2F64 |
| 土 | ⼟ | U+571F vs U+2F1F |
| 口 | ⼝ | U+53E3 vs U+2F14 |
| 日 | ⽇ | U+65E5 vs U+2F47 |

**症狀**：視覺上相同的文字，但字串比對/搜尋失敗。

## 解決方案

### 1. 匯入時自動正規化

`backend/app/services/document_service.py` 已實現匯入時自動清理：

```python
from app.services.document_service import normalize_text

# 匯入前正規化
doc_data['subject'] = normalize_text(doc_data['subject'])
doc_data['contract_case'] = normalize_text(doc_data['contract_case'])
```

### 2. 資料庫清理工具

使用 `normalize_unicode.py` 腳本修復現有資料：

```bash
# 檢查異常字元（不修改）
python -m app.scripts.normalize_unicode --check

# 執行修復
python -m app.scripts.normalize_unicode --fix

# 指定特定表
python -m app.scripts.normalize_unicode --check --table contract_projects
```

### 3. SQL 直接修復

```sql
-- 修復特定記錄
UPDATE contract_projects
SET project_name = REPLACE(REPLACE(REPLACE(
    project_name, '⽤', '用'), '⼟', '土'), '⼝', '口')
WHERE project_name LIKE '%⽤%'
   OR project_name LIKE '%⼟%'
   OR project_name LIKE '%⼝%';
```

### 4. 前端篩選優化

使用唯一識別碼（如案件編號）取代全名進行篩選：

```typescript
// 避免特殊字元問題
const FIXED_CONTRACT_CODE = 'CK2025_01_03_001';  // 精確匹配
const FIXED_CONTRACT_NAME = '115年度桃園市...';   // 僅用於顯示
```

## 相關檔案

| 檔案 | 用途 |
|------|------|
| `backend/app/scripts/normalize_unicode.py` | Unicode 正規化工具 |
| `backend/app/services/document_service.py` | 匯入時正規化邏輯 |

## 預防措施

1. **資料來源驗證**：匯入前檢查 CSV/Excel 檔案的字元編碼
2. **唯一識別碼**：優先使用編號而非名稱進行關聯
3. **定期檢查**：使用 `--check` 定期掃描資料庫

## 技術細節

### Python 正規化函數

```python
import unicodedata

KANGXI_RADICALS = {
    '⽤': '用', '⼟': '土', '⼝': '口', '⽇': '日', '⽉': '月',
    '⽔': '水', '⽕': '火', '⽊': '木', '⾦': '金', '⼈': '人',
    # ... 更多對照
}

def normalize_text(text: str) -> str:
    if not text:
        return text

    result = text
    for kangxi, normal in KANGXI_RADICALS.items():
        result = result.replace(kangxi, normal)

    # NFKC 正規化處理其他相容字元
    return unicodedata.normalize('NFKC', result)
```

### PostgreSQL 檢測查詢

```sql
-- 找出含有康熙部首的記錄
SELECT id, project_name
FROM contract_projects
WHERE project_name ~ '[⼀-⿕]';
```

## 參考資源

- [Unicode 康熙部首區塊](https://en.wikipedia.org/wiki/Kangxi_Radicals_(Unicode_block))
- [Python unicodedata 模組](https://docs.python.org/3/library/unicodedata.html)
- [Unicode 正規化形式](https://unicode.org/reports/tr15/)
