# 型別同步檢查 (Type Synchronization Check)

> **版本**: 2.0.0
> **更新日期**: 2026-01-18

檢查前後端型別定義是否同步，確保 Schema 一致性。

---

## 快速檢查命令

```bash
# 1. 檢查 endpoints 是否有本地 BaseModel 定義 (應為 0)
cd backend && grep -r "class.*\(BaseModel\)" app/api/endpoints/ --include="*.py" | wc -l

# 2. 重新生成前端型別
cd frontend && npm run api:generate

# 3. 驗證 TypeScript 編譯
cd frontend && npx tsc --noEmit

# 4. 驗證 Python 語法
cd backend && python -m py_compile app/schemas/*.py
```

---

## SSOT 架構驗證

### 後端 Schema 檢查

**所有型別定義必須集中在 `schemas/` 目錄**

```bash
# 確認 endpoints 無本地 BaseModel
grep -r "class.*\(BaseModel\)" backend/app/api/endpoints/ --include="*.py"
# 預期結果：無輸出 (0 matches)
```

### 前端型別檢查

```bash
# 確認自動生成檔案存在
ls frontend/src/types/generated/api.d.ts

# 確認型別包裝層存在
ls frontend/src/types/generated/index.ts
```

---

## Schema 對照清單

### 核心實體

| 後端 Schema | 前端型別 | 檔案位置 |
|-------------|---------|---------|
| `DocumentResponse` | `ApiDocumentResponse` | `schemas/document.py` |
| `Agency` | `ApiAgency` | `schemas/agency.py` |
| `ProjectResponse` | `ApiProjectResponse` | `schemas/project.py` |
| `UserResponse` | `ApiUserResponse` | `schemas/user.py` |
| `Vendor` | `ApiVendor` | `schemas/vendor.py` |

### 查詢參數

| 後端 Schema | 前端型別 | 檔案位置 |
|-------------|---------|---------|
| `DocumentListQuery` | `ApiDocumentListQuery` | `schemas/document.py` |
| `AgencyListQuery` | `ApiAgencyListQuery` | `schemas/agency.py` |
| `ProjectListQuery` | `ApiProjectListQuery` | `schemas/project.py` |
| `UserListQuery` | `ApiUserListQuery` | `schemas/user.py` |

### 輔助 Schema

| 後端 Schema | 說明 | 檔案位置 |
|-------------|------|---------|
| `NotificationItem` | 通知項目 | `schemas/notification.py` |
| `ConflictCheckRequest` | 衝突檢查 | `schemas/document_calendar.py` |
| `SecureRequest` | 安全請求 | `schemas/secure.py` |
| `CreateBackupRequest` | 備份請求 | `schemas/backup.py` |

---

## 自動生成流程

### 1. 生成 TypeScript 型別

```bash
cd frontend
npm run api:generate
```

**輸出檔案**: `src/types/generated/api.d.ts`

### 2. 生成變更日誌

```bash
npm run api:generate:changelog
```

**輸出檔案**: `src/types/generated/CHANGELOG.md`

### 3. 更新型別包裝層 (如需要)

```typescript
// src/types/generated/index.ts
import type { components } from './api';

// 新增對應的型別匯出
export type ApiNewEntity = components['schemas']['NewEntity'];
```

---

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

**解法**:
1. 執行 `npm run api:generate`
2. 更新型別包裝層 (如需要)

### 3. 型別不匹配

```python
# 後端
field: Optional[int] = None
```

```typescript
// 前端應該
field?: number;
```

### 4. endpoints 存在本地定義

```python
# backend/app/api/endpoints/xxx.py
class LocalQuery(BaseModel):  # 違規！
    ...
```

**解法**: 將類別移動到 `schemas/xxx.py`，endpoint 改為匯入

---

## 同步流程

### 新增欄位時

1. **後端 Schema 新增**
   ```python
   # backend/app/schemas/xxx.py
   new_field: Optional[str] = Field(None, description="新欄位")
   ```

2. **重新生成前端型別**
   ```bash
   cd frontend && npm run api:generate
   ```

3. **驗證 TypeScript**
   ```bash
   npx tsc --noEmit
   ```

### 新增 Schema 時

1. **建立後端 Schema 檔案**
   ```python
   # backend/app/schemas/new_module.py
   class NewModuleResponse(BaseModel):
       ...
   ```

2. **在 endpoint 匯入使用**
   ```python
   from app.schemas.new_module import NewModuleResponse
   ```

3. **重新生成前端型別**
   ```bash
   cd frontend && npm run api:generate
   ```

4. **更新型別包裝層**
   ```typescript
   export type ApiNewModuleResponse = components['schemas']['NewModuleResponse'];
   ```

---

## 驗證腳本

### PowerShell 完整檢查

```powershell
# check-type-sync.ps1
Write-Host "=== 型別同步檢查 ===" -ForegroundColor Cyan

# 1. 檢查 endpoints 本地定義
Write-Host "`n[1/4] 檢查 endpoints 本地 BaseModel..." -ForegroundColor Yellow
$localDefs = Get-ChildItem -Path "backend/app/api/endpoints" -Filter "*.py" -Recurse |
    Select-String -Pattern "class.*\(BaseModel\)"
if ($localDefs) {
    Write-Host "  ❌ 發現本地定義:" -ForegroundColor Red
    $localDefs | ForEach-Object { Write-Host "     $_" }
} else {
    Write-Host "  ✅ 無本地定義" -ForegroundColor Green
}

# 2. Python 語法檢查
Write-Host "`n[2/4] Python Schema 語法檢查..." -ForegroundColor Yellow
python -m py_compile backend/app/schemas/*.py 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ Python 語法正確" -ForegroundColor Green
} else {
    Write-Host "  ❌ Python 語法錯誤" -ForegroundColor Red
}

# 3. 重新生成型別
Write-Host "`n[3/4] 重新生成前端型別..." -ForegroundColor Yellow
Set-Location frontend
npm run api:generate 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ 型別生成成功" -ForegroundColor Green
} else {
    Write-Host "  ❌ 型別生成失敗" -ForegroundColor Red
}

# 4. TypeScript 編譯檢查
Write-Host "`n[4/4] TypeScript 編譯檢查..." -ForegroundColor Yellow
npx tsc --noEmit 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ TypeScript 編譯通過" -ForegroundColor Green
} else {
    Write-Host "  ❌ TypeScript 編譯失敗" -ForegroundColor Red
}

Set-Location ..
Write-Host "`n=== 檢查完成 ===" -ForegroundColor Cyan
```

---

## 相關文件

| 文件 | 說明 |
|------|------|
| `.claude/skills/type-management.md` | 型別管理規範 (Skill) |
| `docs/specifications/TYPE_CONSISTENCY.md` | 型別一致性規範 |
| `backend/app/schemas/` | 後端 Schema 定義 |
| `frontend/src/types/generated/` | 前端自動生成型別 |
| `frontend/scripts/type-changelog.js` | 型別變更日誌生成器 |

---

## 版本記錄

| 版本 | 日期 | 說明 |
|------|------|------|
| 2.0.0 | 2026-01-18 | 全面更新，新增 SSOT 架構、自動生成流程、驗證腳本 |
| 1.0.0 | 2026-01-05 | 初版建立 |

---

*維護者: Claude Code Assistant*
