# 系統規範更新報告

> 報告日期: 2026-01-08
> 版本: v1.0
> 文件類型: 系統規範與架構改進建議

---

## 一、歷次錯誤彙整與修復紀錄

### 1.1 資料庫相關錯誤

| 錯誤類型 | 錯誤訊息 | 根本原因 | 修復方案 | 修復日期 |
|----------|----------|----------|----------|----------|
| 唯一約束違反 | `duplicate key value violates unique constraint "documents_auto_serial_key"` | 批次匯入時，資料尚未 commit 導致查詢重複流水號失敗 | 新增記憶體計數器 `_serial_counters` 追蹤已生成的流水號 | 2026-01-08 |
| 欄位對應錯誤 | doc_type 值為「收文/發文」而非「函」 | CSV 匯入時「類別」欄位錯誤對應到 `doc_type` | 修正欄位對應邏輯，新增 doc_type 白名單驗證 | 2026-01-07 |
| 日期欄位空值 | send_date 欄位為 NULL | 「發文日期」欄位對應到錯誤的 `doc_date` | 修正對應為 `send_date`，並批次更新 173 筆資料 | 2026-01-07 |
| 字串值異常 | content/notes 欄位存在 "None" 字串 | Python `str(None)` 產生 "None" 字串 | 新增 `_clean_string()` 輔助方法過濾無效值 | 2026-01-08 |
| 機關關聯遺失 | sender_agency_id/receiver_agency_id 為 NULL | 匯入時未使用智慧匹配機制 | 整合 AgencyMatcher/ProjectMatcher，並批次更新歷史資料 | 2026-01-08 |

### 1.2 前端相關錯誤

| 錯誤類型 | 錯誤訊息 | 根本原因 | 修復方案 | 修復日期 |
|----------|----------|----------|----------|----------|
| DOM 巢狀錯誤 | `validateDOMNesting(...): <div> cannot appear as a descendant of <p>` | Ant Design Upload 元件內使用 `<p>` 包含 `<div>` | 將 `<p className="ant-upload-drag-icon">` 改為 `<div>` | 2026-01-08 |
| 表單預設值 | 受文單位、收文日期無預設值 | Form.Item 未設定 initialValue | 新增 initialValue 並加入預設選項到下拉選單 | 2026-01-08 |
| 類別切換邏輯 | 收文/發文切換時欄位未連動 | 無動態欄位處理機制 | 新增 handleCategoryChange 回調函數 | 2026-01-08 |

### 1.3 編碼與匯出錯誤

| 錯誤類型 | 錯誤訊息 | 根本原因 | 修復方案 | 修復日期 |
|----------|----------|----------|----------|----------|
| 中文檔名亂碼 | Excel 下載檔名顯示亂碼 | HTTP Header 編碼不符合 RFC 5987 | 使用 `filename*=UTF-8''` 格式編碼 | 2026-01-07 |
| 匯出筆數限制 | 只匯出 10 筆資料 | 前端僅傳送當前頁面資料 | 新增 `exportAll` 參數支援全部匯出 | 2026-01-07 |

---

## 二、服務層架構改進建議

### 2.1 現有架構分析

```
backend/app/services/
├── base/
│   ├── __init__.py
│   └── unit_of_work.py      # UnitOfWork 模式
├── strategies/
│   ├── __init__.py
│   └── agency_matcher.py    # 策略模式 (AgencyMatcher, ProjectMatcher)
├── document_service.py      # 公文 CRUD
├── document_import_service.py  # CSV 匯入
├── excel_import_service.py     # Excel 匯入 (新增)
├── document_export_service.py  # 匯出服務
├── csv_processor.py            # CSV 處理器
└── ...其他服務
```

### 2.2 發現的問題

#### 問題 1: 匯入服務重複實作
**現象**: `document_import_service.py`、`excel_import_service.py`、`csv_processor.py` 存在重複邏輯

**重複項目**:
- 日期解析邏輯 (`_parse_date`)
- 字串清理邏輯 (`_clean_text`, `_clean_string`)
- doc_type 白名單驗證
- 流水號生成

**建議**: 建立 `ImportBaseService` 基礎類別

```python
# backend/app/services/base/import_base.py
class ImportBaseService:
    """匯入服務基礎類別"""

    VALID_DOC_TYPES = ['函', '開會通知單', '會勘通知單', '書函', '公告', '令', '通知']
    VALID_CATEGORIES = ['收文', '發文']

    def _clean_string(self, value: Any) -> Optional[str]:
        """統一字串清理"""
        ...

    def _parse_date(self, value: Any) -> Optional[date]:
        """統一日期解析"""
        ...

    def _validate_doc_type(self, value: str) -> str:
        """統一 doc_type 驗證"""
        ...

    async def _generate_auto_serial(self, category: str) -> str:
        """統一流水號生成"""
        ...
```

#### 問題 2: 策略模式使用不一致
**現象**: AgencyMatcher/ProjectMatcher 僅部分服務使用

**建議**: 統一在匯入服務初始化時注入策略

```python
class ExcelImportService(ImportBaseService):
    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.agency_matcher = AgencyMatcher(db)
        self.project_matcher = ProjectMatcher(db)
```

#### 問題 3: 錯誤處理不統一
**現象**: 各服務返回格式不一致

**建議**: 建立統一的服務回應結構

```python
# backend/app/services/base/response.py
@dataclass
class ServiceResponse:
    success: bool
    data: Any = None
    message: str = ""
    errors: List[str] = field(default_factory=list)
    details: List[Dict] = field(default_factory=list)
```

### 2.3 改進後的架構設計

```
backend/app/services/
├── base/
│   ├── __init__.py
│   ├── unit_of_work.py
│   ├── import_base.py       # [新增] 匯入基礎服務
│   ├── response.py          # [新增] 統一回應結構
│   └── validators.py        # [新增] 共用驗證器
├── strategies/
│   ├── __init__.py
│   ├── agency_matcher.py
│   └── serial_generator.py  # [新增] 流水號生成策略
├── import/                   # [新增] 匯入服務模組
│   ├── __init__.py
│   ├── csv_import_service.py
│   ├── excel_import_service.py
│   └── preview_service.py   # [新增] 預覽服務
├── export/                   # [新增] 匯出服務模組
│   ├── __init__.py
│   ├── excel_export_service.py
│   └── pdf_export_service.py
└── ...其他服務
```

---

## 三、模組化改進建議

### 3.1 前端模組化

#### 當前問題

| 問題 | 影響 | 建議 |
|------|------|------|
| 頁面元件過大 | `DocumentPage.tsx` 447 行，難以維護 | 拆分為容器/展示元件 |
| Hook 邏輯混雜 | 業務邏輯與 UI 狀態混合 | 建立專用 Hook |
| 表單驗證重複 | 各表單重複定義驗證規則 | 建立共用 Schema |

#### 建議的元件結構

```
frontend/src/
├── components/
│   └── document/
│       ├── DocumentList.tsx          # 展示元件
│       ├── DocumentFilter.tsx        # 展示元件
│       ├── DocumentImport/           # [重構] 匯入模組
│       │   ├── index.tsx             # 匯出入口
│       │   ├── ImportModal.tsx       # 模態框容器
│       │   ├── ExcelImportPanel.tsx  # Excel 匯入面板
│       │   ├── CsvImportPanel.tsx    # CSV 匯入面板
│       │   ├── PreviewTable.tsx      # [新增] 預覽表格
│       │   └── useImport.ts          # [新增] 匯入 Hook
│       └── DocumentForm/             # [重構] 表單模組
│           ├── index.tsx
│           ├── BasicInfoTab.tsx
│           ├── DetailsTab.tsx
│           └── useDocumentForm.ts
├── hooks/
│   ├── useDocuments.ts               # 公文查詢
│   ├── useDocumentMutation.ts        # 公文變更
│   └── useImportPreview.ts           # [新增] 匯入預覽
└── schemas/
    └── documentSchema.ts              # [新增] 表單驗證 Schema
```

### 3.2 後端模組化

#### 當前問題

| 問題 | 影響 | 建議 |
|------|------|------|
| 服務檔案過大 | `csv_processor.py` 429 行 | 拆分處理器 |
| API 端點分散 | 匯入/匯出端點在不同 router | 統一為 `/import` `/export` |
| 缺乏介面定義 | 服務間耦合度高 | 建立 Protocol/ABC |

#### 建議的 API 路由結構

```python
# backend/app/api/endpoints/document_operations.py
router = APIRouter(prefix="/documents", tags=["documents"])

# 匯入相關
@router.post("/import/csv")
@router.post("/import/excel")
@router.post("/import/preview")    # [新增] 預覽端點

# 匯出相關
@router.get("/export/excel")
@router.get("/export/csv")
@router.get("/export/pdf")         # [規劃中]

# 範本下載
@router.get("/templates/excel")
@router.get("/templates/csv")
```

---

## 四、系統規範更新

### 4.1 資料驗證規範

#### 公文類型 (doc_type) 白名單

```python
VALID_DOC_TYPES = [
    '函',           # 最常見
    '開會通知單',
    '會勘通知單',
    '書函',
    '公告',
    '令',
    '通知'
]
```

#### 公文類別 (category) 規範

```python
VALID_CATEGORIES = ['收文', '發文']

# 類別與欄位連動規則
if category == '收文':
    required: ['receiver', 'receive_date']
    default_receiver: '本公司'
elif category == '發文':
    required: ['sender', 'send_date']
    default_sender: '本公司'
```

### 4.2 字串清理規範

```python
def clean_string(value: Any) -> Optional[str]:
    """
    統一字串清理規範

    1. None 值返回 None (不轉為 "None" 字串)
    2. 去除首尾空白
    3. 過濾無效值: "none", "null", "NULL", ""
    """
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in ('none', 'null', ''):
        return None
    return text
```

### 4.3 日期處理規範

```python
def parse_date(value: Any) -> Optional[date]:
    """
    統一日期解析規範

    支援格式:
    1. datetime 物件 → 提取 date
    2. date 物件 → 直接使用
    3. 西元格式: YYYY-MM-DD, YYYY/MM/DD
    4. 民國格式: 中華民國114年1月8日
    """
```

### 4.4 流水號生成規範

```python
def generate_serial(category: str) -> str:
    """
    流水號格式: {前綴}{4位序號}

    - 收文: R0001, R0002, ...
    - 發文: S0001, S0002, ...

    批次匯入時使用記憶體計數器避免重複
    """
```

### 4.5 重複檢查規範

```python
# 唯一識別條件
DUPLICATE_CHECK_FIELDS = [
    'doc_number',  # 公文字號 (最重要)
]

# 匯入時行為
if existing_doc_number and no_doc_id:
    action = 'skip'  # 跳過並提示
    message = f"公文字號 '{doc_number}' 已存在"
```

---

## 五、錯誤處理最佳實踐

### 5.1 後端錯誤處理

```python
# backend/app/core/exceptions.py
class DocumentImportError(AppException):
    """匯入錯誤"""
    def __init__(self, message: str, row: int = None, field: str = None):
        self.row = row
        self.field = field
        super().__init__(message)

class DuplicateDocumentError(AppException):
    """重複公文錯誤"""
    def __init__(self, doc_number: str, existing_id: int):
        self.doc_number = doc_number
        self.existing_id = existing_id
        super().__init__(f"公文字號 '{doc_number}' 已存在 (ID={existing_id})")
```

### 5.2 前端錯誤處理

```typescript
// frontend/src/utils/errorHandler.ts
interface ImportError {
  row: number;
  field?: string;
  message: string;
  severity: 'error' | 'warning';
}

function handleImportErrors(errors: ImportError[]) {
  const criticalErrors = errors.filter(e => e.severity === 'error');
  const warnings = errors.filter(e => e.severity === 'warning');

  if (criticalErrors.length > 0) {
    message.error(`匯入失敗: ${criticalErrors.length} 個錯誤`);
  }
  if (warnings.length > 0) {
    message.warning(`${warnings.length} 筆資料有警告`);
  }
}
```

### 5.3 日誌記錄規範

```python
# 錯誤日誌格式
logger.error(
    f"[{service_name}] {operation} 失敗: {error}",
    exc_info=True,
    extra={
        'row': row_num,
        'doc_number': doc_number,
        'field': field_name,
    }
)

# 警告日誌格式
logger.warning(
    f"[資料品質] {field} 值無效: {value}, 已修正為: {corrected}",
    extra={'doc_number': doc_number}
)
```

---

## 六、待辦事項優先級

### 高優先級 (本週)

| 項目 | 狀態 | 說明 |
|------|------|------|
| 匯入預覽功能 | 待實作 | 使用者確認後才執行匯入 |
| 重複公文檢查 | ✅ 完成 | 已實作 doc_number 檢查 |
| 智慧機關關聯 | ✅ 完成 | AgencyMatcher 已整合 |

### 中優先級 (本月)

| 項目 | 狀態 | 說明 |
|------|------|------|
| 服務層重構 | 待實作 | 建立 ImportBaseService |
| 統一錯誤處理 | 待實作 | ServiceResponse 結構 |
| 附件備份機制 | 待實作 | /db-backup Skill |

### 低優先級 (規劃中)

| 項目 | 狀態 | 說明 |
|------|------|------|
| API 版本管理 | 規劃中 | `/api/v1/` 前綴 |
| 自動化測試 | 規劃中 | pytest 測試套件 |
| PDF 匯出 | 規劃中 | 公文 PDF 列印 |

---

## 七、相關文件更新

### 已更新文件

| 文件 | 更新內容 |
|------|----------|
| `docs/TODO.md` | 新增匯入相關待辦項目 |
| `docs/wiki/Service-Layer-Architecture.md` | 服務層架構說明 |
| `.claude/DEVELOPMENT_GUIDELINES.md` | 開發指引 |

### 建議新增文件

| 文件 | 用途 |
|------|------|
| `docs/IMPORT_SPECIFICATION.md` | 匯入功能規範 |
| `docs/ERROR_HANDLING_GUIDE.md` | 錯誤處理指南 |
| `docs/DATA_VALIDATION_RULES.md` | 資料驗證規則 |

---

*報告完成時間: 2026-01-08*
*下次審查日期: 2026-01-15*
