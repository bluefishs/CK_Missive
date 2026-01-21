# 開發環境檢查 (Development Environment Check)

執行完整的開發環境和程式碼檢查。

## 檢查項目

### 1. 前端 TypeScript 檢查
```bash
cd frontend && npx tsc --noEmit
```

### 2. 後端 Python 語法檢查
```bash
cd backend && python -m py_compile app/main.py
```

### 3. 資料庫連線檢查
```bash
docker exec -it ck_missive_postgres_dev psql -U ck_user -d ck_documents -c "SELECT 1"
```

### 4. 專案結構檢查
```bash
python claude_plant/development_tools/validation/validate_structure.py
```

## 快速檢查腳本

執行以下步驟進行完整檢查：

```powershell
# 1. 前端檢查
Write-Host "=== 前端 TypeScript 檢查 ===" -ForegroundColor Cyan
Push-Location frontend
npx tsc --noEmit
$frontendResult = $LASTEXITCODE
Pop-Location

# 2. 後端檢查
Write-Host "=== 後端 Python 檢查 ===" -ForegroundColor Cyan
Push-Location backend
python -m py_compile app/main.py
$backendResult = $LASTEXITCODE
Pop-Location

# 3. 結果摘要
Write-Host "=== 檢查結果 ===" -ForegroundColor Yellow
if ($frontendResult -eq 0) {
    Write-Host "前端: PASS" -ForegroundColor Green
} else {
    Write-Host "前端: FAIL" -ForegroundColor Red
}

if ($backendResult -eq 0) {
    Write-Host "後端: PASS" -ForegroundColor Green
} else {
    Write-Host "後端: FAIL" -ForegroundColor Red
}
```

## 常見問題排解

### TypeScript 錯誤
1. 檢查 `tsconfig.json` 設定
2. 確認型別定義完整
3. 安裝缺少的 @types 套件

### Python 語法錯誤
1. 檢查縮排是否正確
2. 確認 import 路徑正確
3. 檢查 async/await 使用

### 資料庫連線失敗
1. 確認 Docker 容器運行中
2. 檢查連線參數
3. 確認資料庫存在

## 開發服務啟動

### 後端 API
```bash
# main.py 在 backend/ 根目錄
cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### 前端開發
```bash
cd frontend && npm run dev
```

### API 文檔
http://localhost:8001/docs

## 相關文件
- `.claude/DEVELOPMENT_GUIDELINES.md` - 開發指引
- `docs/DEVELOPMENT_STANDARDS.md` - 開發規範
- `STRUCTURE.md` - 專案結構
