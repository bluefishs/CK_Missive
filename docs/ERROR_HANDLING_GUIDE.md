# 錯誤處理最佳實踐指南

> 版本: 1.0.0 | 更新日期: 2026-01-08

---

## 一、錯誤分類

### 1.1 資料驗證錯誤

| 錯誤類型 | 嚴重程度 | 處理方式 |
|----------|----------|----------|
| 必填欄位缺失 | 警告 | 跳過並記錄 |
| 無效格式 | 警告 | 自動修正或跳過 |
| 超出範圍 | 錯誤 | 拒絕並提示 |
| 資料類型錯誤 | 錯誤 | 嘗試轉換或拒絕 |

### 1.2 業務邏輯錯誤

| 錯誤類型 | 嚴重程度 | 處理方式 |
|----------|----------|----------|
| 重複資料 | 警告 | 跳過並提示 |
| 關聯不存在 | 警告 | 自動建立或標記 |
| 權限不足 | 錯誤 | 拒絕操作 |
| 狀態衝突 | 錯誤 | 拒絕並說明 |

### 1.3 系統錯誤

| 錯誤類型 | 嚴重程度 | 處理方式 |
|----------|----------|----------|
| 資料庫連線失敗 | 嚴重 | 回滾並通知 |
| 檔案讀寫失敗 | 錯誤 | 重試或回滾 |
| 記憶體不足 | 嚴重 | 終止並通知 |
| 第三方服務異常 | 錯誤 | 重試或降級 |

---

## 二、後端錯誤處理

### 2.1 例外類別定義

```python
# backend/app/core/exceptions.py

class AppException(Exception):
    """應用程式基礎例外"""
    def __init__(self, message: str, code: str = "APP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)

class ValidationError(AppException):
    """驗證錯誤"""
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message, "VALIDATION_ERROR")

class DuplicateError(AppException):
    """重複資料錯誤"""
    def __init__(self, message: str, existing_id: int = None):
        self.existing_id = existing_id
        super().__init__(message, "DUPLICATE_ERROR")

class NotFoundError(AppException):
    """資源不存在"""
    def __init__(self, resource: str, identifier: str):
        message = f"{resource} not found: {identifier}"
        super().__init__(message, "NOT_FOUND")

class ImportError(AppException):
    """匯入錯誤"""
    def __init__(self, message: str, row: int = None, details: dict = None):
        self.row = row
        self.details = details or {}
        super().__init__(message, "IMPORT_ERROR")
```

### 2.2 服務回應結構

```python
# backend/app/services/base/response.py

from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional

@dataclass
class ServiceResponse:
    """統一服務回應結構"""
    success: bool
    data: Any = None
    message: str = ""
    code: str = ""
    errors: List[Dict] = field(default_factory=list)
    warnings: List[Dict] = field(default_factory=list)

    @classmethod
    def ok(cls, data: Any = None, message: str = "操作成功") -> "ServiceResponse":
        return cls(success=True, data=data, message=message)

    @classmethod
    def fail(cls, message: str, code: str = "ERROR", errors: List = None) -> "ServiceResponse":
        return cls(success=False, message=message, code=code, errors=errors or [])

    @classmethod
    def partial(cls, data: Any, warnings: List, message: str = "部分成功") -> "ServiceResponse":
        return cls(success=True, data=data, message=message, warnings=warnings)
```

### 2.3 匯入結果結構

```python
# backend/app/services/base/import_result.py

@dataclass
class ImportRowResult:
    """單筆匯入結果"""
    row: int
    status: str  # 'inserted', 'updated', 'skipped', 'error'
    message: str
    doc_number: str = ""
    doc_id: int = None

@dataclass
class ImportResult:
    """匯入結果總計"""
    success: bool
    filename: str
    total_rows: int
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: List[ImportRowResult] = field(default_factory=list)
    warnings: List[ImportRowResult] = field(default_factory=list)
    details: List[ImportRowResult] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)
```

### 2.4 錯誤處理範例

```python
# backend/app/services/excel_import_service.py

async def _process_row(self, row_num: int, row_data: Dict) -> ImportRowResult:
    """處理單列資料"""
    result = ImportRowResult(
        row=row_num,
        status="error",
        message="",
        doc_number=self._clean_string(row_data.get('公文字號', ''))
    )

    try:
        # 1. 驗證必填欄位
        for field in self.REQUIRED_FIELDS:
            value = row_data.get(field)
            if not value or not str(value).strip():
                result.status = "skipped"
                result.message = f"缺少必填欄位: {field}"
                return result

        # 2. 驗證類別
        category = self._clean_string(row_data.get('類別', ''))
        if category not in self.VALID_CATEGORIES:
            result.status = "skipped"
            result.message = f"無效的類別: {category}"
            return result

        # 3. 檢查重複
        doc_number = result.doc_number
        if doc_number:
            existing = await self._check_duplicate(doc_number)
            if existing and not row_data.get('公文ID'):
                result.status = "skipped"
                result.message = f"公文字號已存在 (ID={existing.id})"
                return result

        # 4. 執行匯入
        doc = await self._create_or_update(row_data)
        result.status = "inserted" if doc.is_new else "updated"
        result.message = f"成功{result.status}"
        result.doc_id = doc.id

    except ValidationError as e:
        result.status = "error"
        result.message = f"驗證失敗: {e.message}"
        logger.warning(f"[匯入] 第 {row_num} 列驗證失敗: {e.message}")

    except Exception as e:
        result.status = "error"
        result.message = f"處理失敗: {str(e)}"
        logger.error(f"[匯入] 第 {row_num} 列處理異常", exc_info=True)

    return result
```

---

## 三、前端錯誤處理

### 3.1 錯誤類型定義

```typescript
// frontend/src/types/error.ts

export interface ApiError {
  code: string;
  message: string;
  field?: string;
  details?: Record<string, unknown>;
}

export interface ImportError {
  row: number;
  field?: string;
  message: string;
  severity: 'error' | 'warning' | 'info';
}

export interface ImportResult {
  success: boolean;
  filename: string;
  total_rows: number;
  inserted: number;
  updated: number;
  skipped: number;
  errors: ImportError[];
  warnings: ImportError[];
}
```

### 3.2 錯誤處理 Hook

```typescript
// frontend/src/hooks/useErrorHandler.ts

import { message, notification } from 'antd';
import { ApiError, ImportResult } from '../types/error';

export function useErrorHandler() {
  const handleApiError = (error: ApiError | Error) => {
    if ('code' in error) {
      switch (error.code) {
        case 'VALIDATION_ERROR':
          message.warning(error.message);
          break;
        case 'DUPLICATE_ERROR':
          message.warning(`資料已存在: ${error.message}`);
          break;
        case 'NOT_FOUND':
          message.error(`找不到資源: ${error.message}`);
          break;
        default:
          message.error(error.message || '操作失敗');
      }
    } else {
      message.error(error.message || '未知錯誤');
    }
  };

  const handleImportResult = (result: ImportResult) => {
    if (result.success && result.errors.length === 0) {
      message.success(
        `匯入成功: 新增 ${result.inserted} 筆, 更新 ${result.updated} 筆`
      );
    } else if (result.errors.length > 0) {
      notification.warning({
        message: '匯入完成但有錯誤',
        description: (
          <div>
            <p>成功: {result.inserted + result.updated} 筆</p>
            <p>錯誤: {result.errors.length} 筆</p>
            <p>跳過: {result.skipped} 筆</p>
          </div>
        ),
        duration: 0,
      });
    }

    // 記錄警告
    if (result.warnings.length > 0) {
      console.warn('匯入警告:', result.warnings);
    }
  };

  return { handleApiError, handleImportResult };
}
```

### 3.3 表單驗證錯誤處理

```typescript
// frontend/src/utils/formValidation.ts

import { Rule } from 'antd/es/form';

export const documentValidationRules = {
  doc_number: [
    { required: true, message: '請輸入公文字號' },
    { max: 100, message: '公文字號不得超過 100 字元' },
  ] as Rule[],

  subject: [
    { required: true, message: '請輸入主旨' },
    { min: 5, message: '主旨至少需要 5 個字元' },
  ] as Rule[],

  category: [
    { required: true, message: '請選擇類別' },
    {
      validator: (_, value) => {
        if (value && !['收文', '發文'].includes(value)) {
          return Promise.reject('無效的類別');
        }
        return Promise.resolve();
      }
    },
  ] as Rule[],

  doc_type: [
    { required: true, message: '請選擇公文類型' },
    {
      validator: (_, value) => {
        const validTypes = ['函', '開會通知單', '會勘通知單', '書函', '公告', '令', '通知'];
        if (value && !validTypes.includes(value)) {
          return Promise.reject('無效的公文類型');
        }
        return Promise.resolve();
      }
    },
  ] as Rule[],
};
```

---

## 四、日誌記錄規範

### 4.1 日誌格式

```python
# 後端日誌格式
logger.info(f"[{模組名}] {操作} 成功: {摘要}")
logger.warning(f"[{模組名}] {操作} 警告: {訊息}")
logger.error(f"[{模組名}] {操作} 失敗: {訊息}", exc_info=True)

# 範例
logger.info("[ExcelImport] 匯入完成: 新增=50, 更新=10, 跳過=5")
logger.warning("[ExcelImport] 第 15 列 doc_type 無效，已修正為「函」")
logger.error("[ExcelImport] 匯入失敗: 資料庫連線逾時", exc_info=True)
```

### 4.2 日誌層級使用規範

| 層級 | 使用場景 | 範例 |
|------|----------|------|
| DEBUG | 開發除錯資訊 | 欄位值轉換過程 |
| INFO | 正常操作記錄 | 匯入/匯出完成 |
| WARNING | 可處理的異常 | 資料自動修正 |
| ERROR | 操作失敗 | 驗證失敗、連線錯誤 |
| CRITICAL | 系統級錯誤 | 服務無法啟動 |

### 4.3 結構化日誌

```python
# 使用 extra 參數記錄結構化資料
logger.info(
    "[Import] 處理完成",
    extra={
        'row': row_num,
        'doc_number': doc_number,
        'status': 'inserted',
        'duration_ms': elapsed_ms,
    }
)
```

---

## 五、常見錯誤處理範例

### 5.1 批次匯入流水號重複

**問題**: `duplicate key value violates unique constraint "documents_auto_serial_key"`

**原因**: 批次匯入時，資料尚未 commit，查詢最大流水號會取得舊值

**解決方案**:
```python
class ExcelImportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        # 使用記憶體計數器追蹤已生成的流水號
        self._serial_counters: Dict[str, int] = {'R': 0, 'S': 0}

    async def _generate_auto_serial(self, category: str) -> str:
        prefix = 'S' if category == '發文' else 'R'

        # 首次使用時從資料庫初始化
        if self._serial_counters[prefix] == 0:
            max_serial = await self._get_max_serial(prefix)
            self._serial_counters[prefix] = max_serial

        # 遞增並返回
        self._serial_counters[prefix] += 1
        return f"{prefix}{self._serial_counters[prefix]:04d}"
```

### 5.2 字串值為 "None"

**問題**: 資料庫 content/notes 欄位存在 "None" 字串

**原因**: Python `str(None)` 產生 "None" 字串

**解決方案**:
```python
def _clean_string(self, value: Any) -> Optional[str]:
    """清理字串值，避免 None 被轉為 'None' 字串"""
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in ('none', 'null', ''):
        return None
    return text
```

### 5.3 DOM 巢狀警告

**問題**: `validateDOMNesting(...): <div> cannot appear as a descendant of <p>`

**原因**: Ant Design 元件內 HTML 結構不符合規範

**解決方案**:
```tsx
// 錯誤
<p className="ant-upload-drag-icon">
  <InboxOutlined />
</p>

// 正確
<div className="ant-upload-drag-icon">
  <InboxOutlined />
</div>
```

---

## 六、錯誤監控與通知

### 6.1 錯誤監控建議

- 設定錯誤日誌集中收集（如 Sentry、ELK）
- 設定關鍵錯誤即時通知（如 Slack、Email）
- 建立錯誤統計儀表板

### 6.2 錯誤回報格式

使用者回報錯誤時應包含：
1. 操作步驟
2. 錯誤訊息截圖
3. 瀏覽器 Console 錯誤
4. 時間戳記

---

*文件版本: 1.0.0*
*最後更新: 2026-01-08*
