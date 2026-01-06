# CSV 匯入模組 - 開發規範與維護指南

> 版本：1.0.0
> 建立日期：2026-01-06
> 模組類型：系統核心 (CRITICAL)

---

## 一、模組概述

### 1.1 功能定位

CSV 匯入模組是乾坤測繪公文管理系統的**核心功能**，負責：
- 將外部 CSV 公文資料批次匯入系統
- 自動欄位映射與資料轉換
- 智慧關聯機關與案件
- 重複資料去重處理

### 1.2 架構原則

```
┌────────────────────────────────────────────────────────────────┐
│                    分層架構 (Layered Architecture)              │
├────────────────────────────────────────────────────────────────┤
│  API Layer      → csv_import.py          (HTTP 端點)           │
│  Orchestration  → DocumentImportService  (流程編排)            │
│  Processing     → DocumentCSVProcessor   (CSV 解析)            │
│  Business Logic → DocumentService        (業務邏輯)            │
│  Data Access    → SQLAlchemy Models      (資料存取)            │
└────────────────────────────────────────────────────────────────┘
```

---

## 二、開發規範

### 2.1 欄位映射規範

#### 新增 CSV 欄位支援

當需要支援新的 CSV 欄位時：

```python
# 位置：csv_processor.py > DocumentCSVProcessor > field_mappings

# 步驟 1：在 field_mappings 新增映射
self.field_mappings = {
    # ... 現有映射 ...
    '新欄位名稱': 'internal_field_name',  # 新增
    '新欄位別名': 'internal_field_name',  # 同一欄位的不同名稱
}

# 步驟 2：在 final_columns 加入（如需輸出）
self.final_columns = [
    # ... 現有欄位 ...
    'internal_field_name',  # 新增
]
```

#### 新增資料庫欄位

當需要將新欄位存入資料庫時：

```python
# 步驟 1：更新 Model (models.py)
class OfficialDocument(Base):
    new_field = Column(String(100), comment="新欄位說明")

# 步驟 2：建立 migration
# alembic revision --autogenerate -m "add_new_field_to_documents"
# alembic upgrade head

# 步驟 3：更新 document_service.py > import_documents_from_processed_data
doc_payload = {
    # ... 現有欄位 ...
    'new_field': doc_data.get('internal_field_name', ''),  # 新增
}
```

### 2.2 流水號規範

```python
# 格式：{前綴}{4位數字}
# 收文：R0001, R0002, ...
# 發文：S0001, S0002, ...

# 產生邏輯 (document_service.py:147-164)
async def _get_next_auto_serial(self, doc_type: str) -> str:
    prefix = 'R' if doc_type == '收文' else 'S'
    # 查詢最大值並 +1
```

**⚠️ 注意事項**：
- 流水號為資料庫 NOT NULL 欄位
- 匯入時必須呼叫 `_get_next_auto_serial()` 產生
- 不可使用 CSV 中的原始流水號

### 2.3 日期處理規範

```python
# 支援格式：
# 1. 民國日期：中華民國114年9月2日 → 2025-09-02
# 2. 西元日期：2025-09-02, 2025/09/02
# 3. 含時間：2025-09-02 10:30:00

# 轉換邏輯 (csv_processor.py:91-116)
def _parse_date(self, date_str: Any) -> Optional[str]:
    # 優先匹配民國年格式
    match_roc = re.search(r'中華民國(\d{2,3})年(\d{1,2})月(\d{1,2})日', date_str)
    if match_roc:
        roc_year, month, day = map(int, match_roc.groups())
        ad_year = roc_year + 1911
        return datetime(ad_year, month, day).strftime('%Y-%m-%d')
```

### 2.4 機關智慧匹配規範

```python
# 匹配優先順序 (document_service.py:27-71)
# 1. 精確匹配 agency_name
# 2. 匹配 agency_short_name（簡稱）
# 3. 模糊匹配（包含關係）
# 4. 新增機關

async def _get_or_create_agency_id(self, agency_name: str) -> Optional[int]:
    # 1. 精確匹配
    result = await self.db.execute(
        select(GovernmentAgency).where(GovernmentAgency.agency_name == agency_name)
    )

    # 2. 簡稱匹配
    result = await self.db.execute(
        select(GovernmentAgency).where(GovernmentAgency.agency_short_name == agency_name)
    )

    # 3. 模糊匹配
    result = await self.db.execute(
        select(GovernmentAgency).where(
            or_(
                GovernmentAgency.agency_name.ilike(f"%{agency_name}%"),
                GovernmentAgency.agency_short_name.ilike(f"%{agency_name}%")
            )
        ).limit(1)
    )

    # 4. 新增
    new_agency = GovernmentAgency(agency_name=agency_name)
```

---

## 三、錯誤處理規範

### 3.1 例外類型

| 例外 | 處理方式 | 計入 |
|------|----------|------|
| `IntegrityError` | 記錄 log，繼續處理 | `skipped_count` |
| `ValueError` (日期) | 設為 None，繼續處理 | - |
| `Exception` (其他) | 記錄 log，繼續處理 | `error_count` |

### 3.2 錯誤回報格式

```python
# 位置：document_import_service.py

return {
    "success": True,
    "message": "描述性訊息",
    "total_processed": import_result.total_rows,
    "success_count": import_result.success_count,
    "skipped_count": import_result.skipped_count,
    "error_count": import_result.error_count,
    "errors": import_result.errors,  # 錯誤詳情列表
}
```

### 3.3 CORS 例外處理

```python
# 位置：exceptions.py

# ⚠️ 必須啟用 generic_exception_handler
# 否則未處理例外會導致 CORS headers 遺失
app.add_exception_handler(Exception, generic_exception_handler)
```

---

## 四、測試規範

### 4.1 單元測試項目

```python
# tests/test_csv_import.py

class TestDocumentCSVProcessor:
    def test_encoding_detection_utf8(self):
        """測試 UTF-8 編碼偵測"""
        pass

    def test_encoding_detection_big5(self):
        """測試 Big5 編碼偵測"""
        pass

    def test_header_detection(self):
        """測試標頭行偵測（前幾行為說明）"""
        pass

    def test_date_parsing_roc(self):
        """測試民國日期轉換"""
        pass

    def test_doc_number_composition(self):
        """測試公文字號組合"""
        pass

    def test_doc_type_determination(self):
        """測試文件類型判斷"""
        pass

class TestDocumentService:
    def test_duplicate_detection(self):
        """測試重複公文偵測"""
        pass

    def test_auto_serial_generation(self):
        """測試流水號產生"""
        pass

    def test_agency_matching_exact(self):
        """測試機關精確匹配"""
        pass

    def test_agency_matching_fuzzy(self):
        """測試機關模糊匹配"""
        pass
```

### 4.2 整合測試項目

```bash
# 測試單檔上傳
curl -X POST http://localhost:8001/api/csv-import/upload-and-import \
  -F "file=@test_receive.csv"

# 測試多檔上傳
curl -X POST http://localhost:8001/api/csv-import/upload-multiple \
  -F "files=@test_receive.csv" \
  -F "files=@test_send.csv"

# 驗證結果
curl -X POST http://localhost:8001/api/documents-enhanced/list \
  -H "Content-Type: application/json" \
  -d '{"page": 1, "limit": 10}'
```

---

## 五、維護檢查清單

### 5.1 新增功能前檢查

- [ ] 確認不影響現有欄位映射
- [ ] 確認資料庫 Model 已更新
- [ ] 確認已建立 migration
- [ ] 確認已更新 import_documents_from_processed_data()
- [ ] 確認已更新測試案例

### 5.2 問題排查清單

| 症狀 | 檢查項目 |
|------|----------|
| 匯入 404 | 確認端點 URL 正確 `/csv-import/upload-and-import` |
| CORS 錯誤 | 確認 `generic_exception_handler` 已啟用 |
| 全部跳過 | 檢查 `doc_number` 是否已存在 |
| auto_serial NULL | 確認呼叫 `_get_next_auto_serial()` |
| notes 欄位錯誤 | 確認 Model 有該欄位，或從 payload 移除 |
| 日期為 None | 檢查日期格式是否支援 |

### 5.3 定期維護項目

| 頻率 | 項目 |
|------|------|
| 每週 | 檢查匯入錯誤 log |
| 每月 | 清理重複機關資料 |
| 每季 | 審視欄位映射完整性 |

---

## 六、版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| 1.0.0 | 2026-01-06 | 初版建立 |

---

## 七、相關文件

| 文件 | 說明 | 強制等級 |
|------|------|----------|
| **`@DEVELOPMENT_STANDARDS.md`** | **統一開發規範總綱** | 🔴 必讀 |
| `@TYPE_CONSISTENCY_SKILL_SPEC.md` | 型別一致性規範 | 🔴 必須 |
| `@SCHEMA_VALIDATION_SKILL_SPEC.md` | Schema 驗證規範 | 🔴 必須 |
| `@CSV_IMPORT_SYSTEM_REPORT.md` | CSV 匯入系統報告 | 🟢 參考 |
| `backend/app/extended/models.py` | 資料庫 Schema | - |
| [API 文件](http://localhost:8001/api/docs) | Swagger API 文件 | - |

> ⚠️ **注意**：本規範為 `@DEVELOPMENT_STANDARDS.md` 的子規範，必須配合總綱一同遵守。

---

**文件結束**
