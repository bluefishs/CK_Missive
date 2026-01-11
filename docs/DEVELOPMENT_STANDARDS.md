# CK_Missive 統一開發規範總綱

> 版本: 1.1.0
> 建立日期: 2026-01-08
> 最後更新: 2026-01-11
> 狀態: 強制遵守

---

## 一、規範總覽

本文件為 CK_Missive 專案的統一開發規範，所有開發人員必須遵守。規範涵蓋：

1. **服務層架構規範**
2. **資料驗證規範**
3. **錯誤處理規範**
4. **程式碼品質規範**
5. **安全性規範**

---

## 二、服務層架構規範

### 2.1 服務繼承架構

```
ImportBaseService (抽象基類)
    │
    ├── ExcelImportService      # Excel 匯入服務
    │
    └── DocumentImportService   # CSV 匯入服務
```

**強制要求**：
- 所有匯入服務必須繼承 `ImportBaseService`
- 必須實作 `import_from_file()` 和 `process_row()` 抽象方法
- 必須使用共用驗證器和回應結構

### 2.2 共用元件使用

| 元件 | 位置 | 用途 |
|------|------|------|
| `ImportBaseService` | `services/base/import_base.py` | 匯入服務基類 |
| `ServiceResponse` | `services/base/response.py` | 統一服務回應 |
| `ImportResult` | `services/base/response.py` | 匯入結果結構 |
| `DocumentValidators` | `services/base/validators.py` | 驗證規則 |
| `StringCleaners` | `services/base/validators.py` | 字串清理 |
| `DateParsers` | `services/base/validators.py` | 日期解析 |

### 2.3 服務回應規範

所有服務方法應使用 `ServiceResponse` 結構：

```python
# 成功回應
return ServiceResponse.ok(data=result, message="操作成功")

# 失敗回應
return ServiceResponse.fail(message="驗證失敗", code="VALIDATION_ERROR")

# 部分成功
return ServiceResponse.partial(data=result, warnings=warnings_list)
```

---

## 三、資料驗證規範

### 3.1 公文類型白名單

**唯一來源**: `DocumentValidators.VALID_DOC_TYPES`

```python
VALID_DOC_TYPES = ['函', '開會通知單', '會勘通知單', '書函', '公告', '令', '通知']
```

**強制要求**：
- 不得在其他位置定義 doc_type 白名單
- 所有驗證必須使用 `DocumentValidators.validate_doc_type()`

### 3.2 公文類別規範

```python
VALID_CATEGORIES = ['收文', '發文']

# 類別與欄位連動規則
if category == '收文':
    required_fields = ['receiver', 'receive_date']
    default_receiver = '本公司'
elif category == '發文':
    required_fields = ['sender', 'send_date']
    default_sender = '本公司'
```

### 3.3 字串清理規範

**強制要求**：所有字串欄位必須使用 `StringCleaners.clean_string()` 清理

```python
# 正確做法
from app.services.base.validators import StringCleaners

value = StringCleaners.clean_string(input_value)

# 錯誤做法 - 禁止直接使用 str()
value = str(input_value)  # 會產生 "None" 字串
```

### 3.4 日期解析規範

使用 `DateParsers.parse_date()` 統一處理日期：

```python
from app.services.base.validators import DateParsers

# 支援格式：
# - datetime 物件
# - date 物件
# - 西元格式: 2026-01-08, 2026/01/08
# - 民國格式: 中華民國115年1月8日, 115年1月8日, 115/01/08

parsed_date = DateParsers.parse_date(input_value)
```

---

## 四、錯誤處理規範

### 4.1 錯誤代碼定義

| 代碼 | 說明 | HTTP 狀態 |
|------|------|-----------|
| `VALIDATION_ERROR` | 資料驗證失敗 | 400 |
| `NOT_FOUND` | 資源不存在 | 404 |
| `DUPLICATE_ERROR` | 重複資料 | 409 |
| `IMPORT_ERROR` | 匯入失敗 | 400 |
| `EXPORT_ERROR` | 匯出失敗 | 500 |
| `DATABASE_ERROR` | 資料庫錯誤 | 500 |
| `UNKNOWN_ERROR` | 未知錯誤 | 500 |

### 4.2 錯誤回應結構

```python
{
    "success": False,
    "message": "驗證失敗：無效的公文類型",
    "code": "VALIDATION_ERROR",
    "errors": [
        {"field": "doc_type", "message": "不在允許的類型清單中"}
    ]
}
```

### 4.3 例外處理原則

1. **服務層**：返回 `ServiceResponse.fail()`，不拋出 HTTPException
2. **API 層**：根據 ServiceResponse 決定回傳的 HTTP 狀態碼
3. **日誌**：使用 `logger.error()` 記錄錯誤詳情

---

## 五、程式碼品質規範

### 5.1 修改後必要流程

**強制要求**：任何程式碼修改後，必須執行以下檢查：

```bash
# 前端 TypeScript 檢查
cd frontend && npx tsc --noEmit

# 後端語法檢查
docker exec ck_missive_backend_dev python -c "
from app.services import (
    ImportBaseService, ServiceResponse, ImportResult,
    DocumentValidators, StringCleaners, DateParsers
)
print('模組匯入成功')
"
```

### 5.2 程式碼風格

- **Python**: 遵循 PEP 8
- **TypeScript**: 使用 strict mode
- **命名規範**:
  - 類別：PascalCase (`DocumentService`)
  - 函數/變數：snake_case (`get_document`)
  - 常數：UPPER_SNAKE_CASE (`VALID_DOC_TYPES`)

### 5.3 文件結構

```
backend/app/services/
├── __init__.py           # 模組匯出
├── base/
│   ├── __init__.py
│   ├── import_base.py    # 匯入基類
│   ├── response.py       # 回應結構
│   ├── validators.py     # 驗證器
│   └── unit_of_work.py   # UoW 模式
├── strategies/
│   ├── __init__.py
│   └── agency_matcher.py # 匹配策略
└── *_service.py          # 業務服務
```

---

## 六、安全性規範

### 6.1 POST-only 機制

**強制要求**：所有涉及資料修改的 API 必須使用 POST 方法

```python
# 正確
@router.post("/documents/create")
async def create_document(...): ...

# 錯誤 - 禁止使用 GET 進行修改操作
@router.get("/documents/delete/{id}")  # 禁止
```

### 6.2 輸入驗證

- 所有使用者輸入必須經過驗證
- 使用 Pydantic Schema 定義輸入結構
- 敏感欄位需加密或遮罩處理

---

## 七、匯入服務開發指南

### 7.1 建立新的匯入服務

```python
from app.services.base.import_base import ImportBaseService
from app.services.base.response import ImportResult, ImportRowResult

class NewImportService(ImportBaseService):
    """新的匯入服務"""

    async def import_from_file(
        self,
        file_content: bytes,
        filename: str
    ) -> ImportResult:
        """實作匯入邏輯"""
        # 使用繼承的方法
        self.reset_serial_counters()

        # 處理每一列
        results = []
        for i, row in enumerate(data):
            result = await self.process_row(i, row)
            results.append(result)

        # 返回統一結構
        return ImportResult(
            success=True,
            filename=filename,
            total_rows=len(data),
            inserted=inserted_count,
            updated=updated_count,
            skipped=skipped_count,
            errors=errors,
            warnings=warnings
        )

    async def process_row(
        self,
        row_num: int,
        row_data: Dict[str, Any]
    ) -> ImportRowResult:
        """實作單列處理邏輯"""
        # 使用繼承的驗證方法
        doc_type = self.validate_doc_type(row_data.get('doc_type'))
        clean_value = self.clean_string(row_data.get('value'))
        parsed_date = self.parse_date(row_data.get('date'))

        # 使用智慧匹配
        agency_id = await self.match_agency(row_data.get('agency'))
        project_id = await self.match_project(row_data.get('project'))

        return ImportRowResult(
            row=row_num,
            status='inserted',
            message='匯入成功',
            doc_number=row_data.get('doc_number', '')
        )
```

### 7.2 繼承方法清單

| 方法 | 用途 |
|------|------|
| `clean_string(value)` | 清理字串，過濾 None/null |
| `clean_agency_name(name)` | 清理機關名稱 |
| `parse_date(value)` | 解析日期 |
| `validate_doc_type(value)` | 驗證公文類型 |
| `validate_category(value)` | 驗證類別 |
| `generate_auto_serial(category)` | 生成流水號 |
| `reset_serial_counters()` | 重置流水號計數器 |
| `match_agency(name)` | 智慧匹配機關 |
| `match_project(name)` | 智慧匹配案件 |
| `check_duplicate_by_doc_number(doc_number)` | 檢查重複公文字號 |
| `check_duplicate_by_id(doc_id)` | 根據 ID 查詢公文 |
| `validate_required_fields(row_data, fields)` | 驗證必填欄位 |

---

## 八、常見問題與解決方案

### 8.1 批次匯入流水號重複

**錯誤訊息**：
```
duplicate key value violates unique constraint "documents_auto_serial_key"
```

**解決方案**：
- 使用 `ImportBaseService` 的記憶體計數器
- 在匯入開始前呼叫 `reset_serial_counters()`

### 8.2 字串欄位出現 "None"

**原因**：直接使用 `str(None)` 產生 "None" 字串

**解決方案**：
```python
# 使用 StringCleaners
value = StringCleaners.clean_string(input_value)
```

### 8.3 機關/案件關聯遺失

**原因**：匯入時未使用智慧匹配

**解決方案**：
```python
# 使用繼承的匹配方法
agency_id = await self.match_agency(agency_name)
project_id = await self.match_project(project_name)
```

---

## 九、前端開發規範

### 9.1 認證與環境檢測

**唯一來源**: `frontend/src/config/env.ts`

```typescript
// 必須使用共用函數
import { isAuthDisabled, isInternalIP, detectEnvironment } from '../config/env';

// ✅ 正確
const authDisabled = isAuthDisabled();

// ❌ 禁止 - 重複定義邏輯
const authDisabled = import.meta.env.VITE_AUTH_DISABLED === 'true';
```

### 9.2 環境類型

| 類型 | 判斷條件 | 認證要求 |
|------|----------|----------|
| `localhost` | localhost / 127.0.0.1 | Google OAuth |
| `internal` | 內網 IP (10.x / 172.16-31.x / 192.168.x) | 免認證 |
| `ngrok` | *.ngrok.io / *.ngrok-free.app | Google OAuth |
| `public` | 其他 | Google OAuth |

### 9.3 API 呼叫規範

```typescript
// 必須使用 apiClient 和 API_ENDPOINTS
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';

const result = await apiClient.post(API_ENDPOINTS.DOCUMENTS.LIST, params);
```

### 9.4 路由保護

```tsx
// 需要認證的頁面
<ProtectedRoute>
  <MyPage />
</ProtectedRoute>

// 需要管理員權限
<ProtectedRoute roles={['admin']}>
  <AdminPage />
</ProtectedRoute>
```

---

## 十、相關文件

| 文件 | 說明 |
|------|------|
| `docs/TODO.md` | 待辦事項清單 |
| `docs/ERROR_HANDLING_GUIDE.md` | 錯誤處理指南 |
| `docs/reports/ARCHITECTURE_REVIEW_20260108.md` | 架構檢視報告 |
| `docs/wiki/Service-Layer-Architecture.md` | 服務層架構說明 |
| `.claude/DEVELOPMENT_GUIDELINES.md` | 開發指引 |
| `.claude/skills/frontend-architecture.md` | **前端架構規範 (v1.0.0)** |

---

## 十一、規範遵守聲明

**本規範為強制遵守文件，違反規範將導致：**

1. Pull Request 無法合併
2. 程式碼審查不通過
3. CI/CD 流程失敗

**修訂記錄**：

| 版本 | 日期 | 說明 |
|------|------|------|
| 1.0.0 | 2026-01-08 | 初版建立 |
| 1.1.0 | 2026-01-11 | 新增前端開發規範、認證環境檢測規範 |

---

*本文件由系統架構檢視後建立，整合所有開發規範為統一來源*
