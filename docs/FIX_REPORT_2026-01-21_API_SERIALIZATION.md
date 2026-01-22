# 錯誤修復報告：API 序列化與型別一致性問題

> **報告日期**: 2026-01-21
> **問題類型**: 後端 API 500 錯誤
> **影響範圍**: Calendar Events Update、Dashboard Stats
> **嚴重程度**: 高（影響核心功能）

---

## 一、問題摘要

| 編號 | API 端點 | 錯誤訊息 | 根本原因 |
|------|---------|---------|---------|
| 1 | `/api/calendar/events/update` | `invalid input for query argument: expected str, got int` | Schema 與 DB 欄位類型不一致 |
| 2 | `/api/dashboard/stats` | `Unable to serialize unknown type: OfficialDocument` | 返回 SQLAlchemy 模型未序列化 |
| 3 | `/api/dashboard/stats` | `'OfficialDocument' object has no attribute 'type'` | 欄位名稱不一致 |

---

## 二、問題詳細分析

### 問題 1：Calendar Events Update - 類型不匹配

**症狀**:
```
POST /api/calendar/events/update 500 Internal Server Error
sqlalchemy.exc.DBAPIError: invalid input for query argument $2: 3 (expected str, got int)
[SQL: UPDATE document_calendar_events SET priority=$2::VARCHAR ...]
```

**根本原因**:
- 資料庫 `document_calendar_events.priority` 欄位是 `VARCHAR` 類型
- Pydantic Schema `DocumentCalendarEventUpdate.priority` 定義為 `int` 類型
- asyncpg 驅動嚴格檢查類型，拒絕將整數寫入 VARCHAR 欄位

**修復方案**:
```python
# backend/app/services/document_calendar_service.py
def update_event(...):
    for key, value in update_data.items():
        if hasattr(db_event, key):
            # 特別處理 priority：資料庫欄位是 String，schema 是 int
            if key == 'priority' and value is not None:
                value = str(value)
            setattr(db_event, key, value)
```

---

### 問題 2：Dashboard Stats - 模型未序列化

**症狀**:
```
POST /api/dashboard/stats 500 Internal Server Error
pydantic_core.PydanticSerializationError: Unable to serialize unknown type: <class 'app.extended.models.OfficialDocument'>
```

**根本原因**:
- API 直接返回 SQLAlchemy ORM 模型列表
- Pydantic 無法自動序列化非 BaseModel 的 Python 對象
- Schema 定義 `List[Any]` 允許任意類型但不處理序列化

**修復方案**:
```python
# backend/app/api/endpoints/dashboard.py
# 轉換為可序列化的字典列表
recent_documents = [
    {
        "id": doc.id,
        "doc_number": doc.doc_number,
        "subject": doc.subject,
        ...
    }
    for doc in recent_documents_raw
]
```

---

### 問題 3：Dashboard Stats - 欄位名稱錯誤

**症狀**:
```
'OfficialDocument' object has no attribute 'type'
```

**根本原因**:
- 程式碼使用 `doc.type`
- 實際資料庫模型欄位名稱是 `doc_type`

**修復方案**:
```python
# 修正欄位名稱
"doc_type": doc.doc_type,  # 不是 doc.type
```

---

## 三、根本原因分類

| 類別 | 問題數量 | 說明 |
|------|---------|------|
| **Schema-DB 類型不一致** | 1 | Schema 定義與資料庫欄位類型不同 |
| **序列化缺失** | 1 | 直接返回 ORM 模型而非字典/Schema |
| **欄位命名不一致** | 1 | 程式碼與模型欄位名稱不符 |

---

## 四、整合優化策略

### 策略 1：建立 Schema-DB 類型對照檢查

**背景**: `priority` 欄位在不同層次有不同類型定義：
- Schema: `int`
- Database Model: `String(50)`
- 實際用途: 可以是 "1"-"5" 或 "high"/"normal"/"low"

**建議措施**:
1. 在 Schema 層統一定義類型轉換規則
2. 使用 Pydantic validator 進行類型正規化
3. 建立 Schema-DB 欄位對照表

```python
# 推薦做法：在 Schema 中使用 validator
class DocumentCalendarEventUpdate(BaseModel):
    priority: Optional[str] = None  # 改為 str 與 DB 一致

    @field_validator('priority', mode='before')
    @classmethod
    def normalize_priority(cls, v):
        if v is not None:
            return str(v)
        return v
```

### 策略 2：強制 API 返回序列化處理

**規範**: 所有 API 返回必須經過以下其一：
1. 使用 Pydantic Schema 的 `model_validate()` 或 `from_attributes=True`
2. 手動轉換為字典（datetime 需 `isoformat()`）
3. 使用專用的 Response Schema

**檢查腳本**:
```bash
# 檢測直接返回 ORM 模型的程式碼
grep -r "\.scalars()\.all()" backend/app/api/endpoints/ | \
  grep -v "# serialized"
```

### 策略 3：建立欄位名稱驗證機制

**措施**:
1. 在 CI/CD 中加入欄位名稱檢查
2. 建立模型欄位與常用存取的對照文件
3. 使用 mypy 或 pyright 進行靜態型別檢查

---

## 五、預防措施

### 新增開發檢查清單項目

在 `MANDATORY_CHECKLIST.md` 新增「清單 K：API 序列化與資料返回」：

1. **返回 ORM 模型時必須序列化**
2. **Schema 欄位類型必須與 DB 一致**
3. **欄位名稱必須對照資料庫模型**
4. **datetime 欄位必須使用 `isoformat()` 或 Schema**

### 新增 Hook 檢查

```powershell
# .claude/hooks/api-serialization-check.ps1
# 檢查 API 端點是否直接返回 ORM 模型

$endpoints = Get-ChildItem "backend/app/api/endpoints/*.py"
foreach ($file in $endpoints) {
    $content = Get-Content $file -Raw
    if ($content -match '\.scalars\(\)\.all\(\)' -and
        $content -notmatch 'model_validate|isoformat|\{.*for.*in') {
        Write-Warning "可能存在未序列化的 ORM 返回: $($file.Name)"
    }
}
```

---

## 六、修正檔案清單

| 檔案 | 變更類型 | 說明 |
|------|---------|------|
| `backend/app/services/document_calendar_service.py` | 修正 | 新增 priority 類型轉換 |
| `backend/app/api/endpoints/dashboard.py` | 修正 | ORM 模型序列化為字典 |
| `backend/app/api/endpoints/dashboard.py` | 修正 | 欄位名稱 `type` → `doc_type` |

---

## 七、驗證結果

| 測試項目 | 狀態 | 說明 |
|---------|------|------|
| Calendar Events Update API | ✅ 通過 | 返回 `success: true` |
| Dashboard Stats API | ✅ 通過 | 返回正確統計數據 |
| TypeScript 編譯 | ✅ 通過 | 無型別錯誤 |
| Python 語法檢查 | ✅ 通過 | 無語法錯誤 |

---

## 八、後續行動項目

| 優先級 | 項目 | 負責人 | 預計完成 |
|-------|------|--------|---------|
| 高 | 更新 MANDATORY_CHECKLIST.md | Claude | 立即 |
| 高 | 更新 type-management.md | Claude | 立即 |
| 中 | 全面檢查其他 API 序列化問題 | 開發團隊 | 1 週內 |
| 中 | 建立 Schema-DB 對照文件 | 開發團隊 | 2 週內 |
| 低 | 加入 CI 自動檢查 | DevOps | 1 個月內 |

---

*報告撰寫: Claude Code Assistant*
*審核狀態: 待審核*
