# 型別同步檢查 (Type Synchronization Check)

檢查前後端型別定義是否同步，確保 Schema 一致性。

## 檢查項目

### 1. 公文型別 (Document)

**後端 Schema**: `backend/app/schemas/document.py`
```python
class DocumentResponse(BaseModel):
    id: int
    doc_number: str
    subject: str
    doc_type: Optional[str]
    category: Optional[str]
    # ...
    sender_agency_name: Optional[str]    # 虛擬欄位
    receiver_agency_name: Optional[str]  # 虛擬欄位
```

**前端型別**: `frontend/src/types/api.ts`
```typescript
interface OfficialDocument {
    id: number;
    doc_number: string;
    subject: string;
    doc_type?: string;
    category?: string;
    // ...
    sender_agency_name?: string;    // 虛擬欄位
    receiver_agency_name?: string;  // 虛擬欄位
}
```

### 2. 對照清單

請比對以下型別定義：

| Schema | 後端檔案 | 前端型別 |
|--------|---------|---------|
| Document | `schemas/document.py` | `OfficialDocument` |
| Agency | `schemas/agency.py` | `Agency` |
| Project | `schemas/project.py` | `Project` |
| Vendor | `schemas/vendor.py` | `Vendor` |
| CalendarEvent | `schemas/document_calendar.py` | `CalendarEvent` |

### 3. 檢查命令

```bash
# 查看後端 Schema
cat backend/app/schemas/document.py

# 查看前端型別
cat frontend/src/types/api.ts
```

## 常見不一致情況

### 1. 欄位名稱不同
```
後端: sender_agency_id
前端: senderAgencyId (駝峰式)
```
**解法**: 前端配合後端使用 snake_case

### 2. 欄位缺失
```
後端新增了 new_field
前端尚未更新
```
**解法**: 在前端 Interface 新增對應欄位

### 3. 型別不匹配
```
後端: Optional[int]
前端: number (無 undefined)
```
**解法**: 前端使用 `field?: number`

## 同步流程

1. **後端新增/修改欄位**
   ```python
   # backend/app/schemas/xxx.py
   new_field: Optional[str] = None
   ```

2. **更新前端型別**
   ```typescript
   // frontend/src/types/api.ts
   new_field?: string;
   ```

3. **執行 TypeScript 檢查**
   ```bash
   cd frontend && npx tsc --noEmit
   ```

## 相關文件
- `docs/specifications/TYPE_CONSISTENCY.md` - 型別一致性規範
- `backend/app/schemas/` - 後端 Schema 定義
- `frontend/src/types/api.ts` - 前端型別定義
