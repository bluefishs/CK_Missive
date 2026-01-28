# 公文管理領域知識 (Document Management Domain)

> **版本**: 1.0.0
> **觸發關鍵字**: 公文, document, 收文, 發文, doc_number, 字號
> **適用範圍**: 公文 CRUD、流水序號、附件管理

---

## 核心概念

### 公文類別 (category)
- `收文`: 外部機關寄來的公文
- `發文`: 本公司對外發出的公文

### 公文類型 (doc_type)
```python
VALID_DOC_TYPES = ['函', '開會通知單', '會勘通知單', '書函', '公告', '令', '通知']
```

### 公文字號格式
標準格式: `機關字第1140024090號`

解構:
- 機關字: 發文機關簡稱 + 字 (如「桃工用字」)
- 文號: 民國年 + 流水序號 (如「1140024090」)

---

## 資料模型

### 主要欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | int | 主鍵 |
| `doc_number` | str | 公文字號 (唯一) |
| `category` | str | 類別: 收文/發文 |
| `doc_type` | str | 類型: 函/開會通知單 等 |
| `subject` | str | 主旨 |
| `sender` | str | 發文者 (發文時為本公司) |
| `receiver` | str | 收文者 (收文時為本公司) |
| `doc_date` | date | 公文日期 |
| `receive_date` | date | 收文日期 (收文專用) |
| `send_date` | date | 發文日期 (發文專用) |
| `auto_serial` | str | 自動流水序號 (R0001/S0001) |
| `sender_agency_id` | int | 發文機關 ID (FK) |
| `receiver_agency_id` | int | 收文機關 ID (FK) |
| `contract_project_id` | int | 關聯專案 ID (FK) |

### 流水序號規則
- 收文: `R` + 4位流水 (R0001, R0002...)
- 發文: `S` + 4位流水 (S0001, S0002...)
- 每年重置

---

## API 端點

### 後端路由
```python
# backend/app/api/routes.py
api_router.include_router(documents.router, prefix="/documents-enhanced", tags=["公文管理"])
```

### 前端端點常數
```typescript
// frontend/src/api/endpoints.ts
DOCUMENTS: {
  LIST: '/documents-enhanced/list',
  CREATE: '/documents-enhanced',
  DETAIL: (id: number) => `/documents-enhanced/${id}/detail`,
  UPDATE: (id: number) => `/documents-enhanced/${id}/update`,
  DELETE: (id: number) => `/documents-enhanced/${id}/delete`,
  STATISTICS: '/documents-enhanced/statistics',
  ATTACHMENTS: (id: number) => `/documents-enhanced/${id}/attachments`,
}
```

---

## 業務邏輯

### 服務層位置
```
backend/app/services/
├── document_service.py        # 核心公文服務
├── document_number_service.py # 流水序號服務
├── csv_processor.py           # CSV 批次匯入
└── attachment_service.py      # 附件管理
```

### 智慧匹配
匯入公文時自動匹配機關和專案：
- `AgencyMatcher`: 機關名稱智慧匹配
- `ProjectMatcher`: 專案名稱智慧匹配

---

## 常見問題

### Q: 流水序號重複錯誤
```
duplicate key value violates unique constraint "documents_auto_serial_key"
```
**解法**: 使用 `DocumentNumberService` 取得下一個序號

### Q: 機關關聯遺失
**解法**: 整合 `AgencyMatcher` 進行自動匹配

### Q: 字串欄位出現 "None"
**解法**: 使用清理函數過濾
```python
def clean_string(value) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in ('none', 'null', ''):
        return None
    return text
```
