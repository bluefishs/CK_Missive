---
name: Import/Export Round-trip Checklist
description: 確保表單導出→導入往返流程正確的檢查清單
version: 1.0.0
category: shared
triggers:
  - /roundtrip-check
  - import export
  - 往返測試
updated: 2026-02-09
---

# Import/Export Round-trip Checklist
匯入/匯出往返流程檢查清單

## 用途

確保任何新增或修改的表單類型，其導出的 Excel 檔案能夠被導入系統正確識別和解析。

---

## 核心原則

### SSOT (Single Source of Truth)

1. **欄位定義**: `unified_field_config.py` → 定義 `display_name`
2. **別名映射**: `field_mapping.py` → 定義 `field_aliases`
3. **自動同步**: `_sync_aliases_from_field_mapping()` 自動合併別名

### 往返一致性

```
系統 ORM → 導出 (display_name) → Excel → 導入 (field_aliases) → 系統 ORM
```

**要求**: 導入後的資料必須與導出前完全一致。

---

## 新增表單類型檢查清單

### Step 1: 定義欄位配置

**檔案**: `backend/app/services/import_service/unified_field_config.py`

```python
XXX_FORM_CONFIG = FormFieldConfig(
    form_type="xxx",
    display_name="XXX調查表",
    model_class="XxxForm",
    fields=[
        FieldDefinition(
            name="field_name",
            display_name="欄位顯示名稱",  # ← 這會成為 Excel 欄位名稱
            field_type=FieldType.STRING,
            export=True,  # ← 必須設為 True 才會導出
            order=1,  # ← 決定導出順序
        ),
        # ... 更多欄位
    ],
)
```

**檢查點**:
- [ ] 所有需要導出的欄位標記 `export=True`
- [ ] `display_name` 清晰易懂
- [ ] `order` 設定合理的排序

---

### Step 2: 配置別名映射

**檔案**: `backend/app/services/import_service/field_mapping.py`

```python
FORM_TYPE_MAPPINGS["xxx"] = {
    "model": "XxxForm",
    "display_name": "XXX調查表",
    "keywords": ["關鍵字1", "關鍵字2"],
    "field_aliases": {
        "field_name": [
            "欄位顯示名稱",  # ← 必須包含 unified_field_config 的 display_name
            "別名1",
            "別名2",
        ],
        # ... 更多欄位別名
    },
}
```

**檢查點**:
- [ ] **每個導出欄位的 `display_name` 都在 `field_aliases` 中**
- [ ] 別名涵蓋常見的變體（如「統一編號」vs「統編」）
- [ ] 無重複別名指向不同欄位

---

### Step 3: 實作導出邏輯

**檔案**: `backend/app/api/v1/endpoints/{module}/{resource}.py`

```python
from backend.app.services.import_service.unified_field_config import get_form_config

@router.post("/{id}/export")
async def export_xxx_form(...):
    xxx_cfg = get_form_config("xxx")
    if xxx_cfg:
        # 水平表格格式 (多筆資料)
        items_data = [_build_export_row(item, xxx_cfg.fields) for item in form.items]
        pd.DataFrame(items_data).to_excel(writer, sheet_name="XXX明細", index=False)

        # 或 垂直 KV 格式 (單筆主表)
        row = _build_export_row(form, xxx_cfg.fields)
        kv_data = {"欄位": list(row.keys()), "值": list(row.values())}
        pd.DataFrame(kv_data).to_excel(writer, sheet_name="XXX表單", index=False)
```

**檢查點**:
- [ ] 使用 `get_form_config()` 取得配置
- [ ] 使用 `_build_export_row()` 建立導出 dict
- [ ] 格式選擇正確（表格 vs KV pairs）

---

### Step 4: 建立往返測試

**檔案**: `backend/tests/services/import_service/test_xxx_roundtrip.py`

```python
class TestXxxFormRoundtrip:
    def test_xxx_export_display_names_have_import_aliases(self):
        """驗證所有導出欄位都有導入別名"""
        xxx_config = get_form_config("xxx")
        reverse_map = build_reverse_mapping("xxx")

        missing_aliases = []
        for field_def in xxx_config.fields:
            if not field_def.export:
                continue
            normalized = field_def.display_name.replace(" ", "").lower()
            if normalized not in reverse_map and field_def.display_name not in reverse_map:
                missing_aliases.append({
                    "system_field": field_def.name,
                    "display_name": field_def.display_name,
                })

        assert not missing_aliases, f"缺少導入別名: {missing_aliases}"
```

**最小測試集**:
- [ ] `test_xxx_export_display_names_have_import_aliases` (必須)
- [ ] `test_xxx_field_mapping_completeness` (建議)
- [ ] `test_xxx_no_duplicate_aliases` (建議)

---

### Step 5: 執行驗證

```bash
# 執行往返測試
pytest backend/tests/services/import_service/test_xxx_roundtrip.py -v

# 預期結果: 所有測試通過
```

**檢查點**:
- [ ] 所有測試通過
- [ ] 無缺少別名的警告
- [ ] 無重複別名的錯誤

---

## 常見問題與解決方案

### Q1: 導出欄位無法被導入識別

**症狀**:
```python
FAILED: 以下欄位在 field_mapping.py 中缺失或別名為空:
  - avg_net_income (平均淨收益)
  - total_loss (營業損失總額)
```

**解決方案**:
在 `field_mapping.py` 的 `field_aliases` 中新增對應的別名：

```python
"avg_net_income": [
    "平均淨收益",
],
"total_loss": [
    "營業損失總額",
],
```

---

### Q2: 別名衝突 (兩個欄位有相同別名)

**症狀**:
```python
FAILED: 發現重複別名:
  - '身分證字號' 映射到多個欄位: ['owner_id', 'land_owner_id']
```

**解決方案**:
使用上下文前綴區分：

```python
"owner_id": [
    "地上物所有人身分證字號",
    # 避免單獨使用 "身分證字號"
],
"land_owner_id": [
    "土地所有人身分證字號",
],
```

---

### Q3: 轉置格式 vs 表格格式

**轉置格式 (垂直 KV pairs)**:
- 用於**主表單** (單筆資料)
- 例: 營業損失表單

```
| 欄位       | 值      |
|-----------|---------|
| 商業名稱   | ABC     |
| 統一編號   | 12345678|
```

**表格格式 (水平表格)**:
- 用於**明細表** (多筆資料)
- 例: 建築改良物明細

```
| 項目編號 | 構造規格 | 數量 | 單價 |
|---------|---------|------|------|
| 1       | RC      | 100  | 5000 |
| 2       | 磚造    | 50   | 3000 |
```

**ExcelParser 兼容性**:
- ✅ 兩種格式都支援
- ✅ `_parse_form_section()` 處理 KV pairs
- ✅ `_parse_table_section()` 處理表格

---

## 自動化腳本

### 快速檢查腳本

```python
# scripts/check_roundtrip.py
from backend.app.services.import_service.unified_field_config import get_form_config
from backend.app.services.import_service.field_mapping import build_reverse_mapping

def check_form_roundtrip(form_type: str):
    config = get_form_config(form_type)
    reverse_map = build_reverse_mapping(form_type)

    missing = []
    for field_def in config.get_export_fields():
        normalized = field_def.display_name.replace(" ", "").lower()
        if normalized not in reverse_map and field_def.display_name not in reverse_map:
            missing.append(field_def.name)

    if missing:
        print(f"❌ {form_type}: 缺少別名 {missing}")
        return False
    else:
        print(f"✓ {form_type}: 往返檢查通過")
        return True

# 檢查所有表單類型
for form_type in ["building", "agri", "business", "industry"]:
    check_form_roundtrip(form_type)
```

**使用方式**:
```bash
python scripts/check_roundtrip.py
```

---

## 範例: 營業損失表單修復

### 問題發現

```bash
$ pytest test_business_roundtrip.py -v

FAILED: 缺少導入別名的欄位:
  - avg_net_income (display_name: '平均淨收益')
  - total_loss (display_name: '營業損失總額')
```

### 修復步驟

1. **檢查 unified_field_config.py**:
   - ✓ `avg_net_income` 的 `display_name` 是「平均淨收益」
   - ✓ `total_loss` 的 `display_name` 是「營業損失總額」

2. **修改 field_mapping.py**:
   ```python
   "avg_net_income": [
       "平均淨收益",
   ],
   "total_loss": [
       "營業損失總額",
       "營業損失補償費",
   ],
   ```

3. **重新執行測試**:
   ```bash
   $ pytest test_business_roundtrip.py -v
   ======================== 8 passed ========================
   ```

### 驗證結果

✅ 所有測試通過
✅ 往返流程正常
✅ 資料完整性確認

---

## 總結

### 往返流程核心要點

1. **display_name** = Excel 欄位名稱 (導出)
2. **field_aliases** = Excel 欄位名稱 → 系統欄位 (導入)
3. **必須確保**: display_name ∈ field_aliases

### 檢查清單摘要

新增或修改表單類型時，務必完成：

- [ ] 在 `unified_field_config.py` 定義 `display_name`
- [ ] 在 `field_mapping.py` 定義 `field_aliases`（包含 display_name）
- [ ] 實作導出邏輯（使用 `get_form_config()` 和 `_build_export_row()`）
- [ ] 建立往返測試（至少 `test_xxx_export_display_names_have_import_aliases`）
- [ ] 執行測試驗證（`pytest test_xxx_roundtrip.py -v`）
- [ ] 文檔更新（如需要）

### 相關技能

- `/schema-design-patterns` - Schema 設計模式
- `/api-serialization` - API 序列化規範
- `/tdd` - 測試驅動開發

---

**最後更新**: 2026-02-09
**維護者**: 系統架構組
