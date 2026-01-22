# 開發環境檢查指南 (Development Environment Guide)

> **觸發關鍵字**: 環境, 開發環境, Docker, 依賴, 配置, env, 環境變數
> **適用範圍**: 本地開發環境設定與驗證
> **版本**: 1.0.0
> **最後更新**: 2026-01-22

---

## 架構概述

CK_Missive 專案開發環境包含以下組件：

| 組件 | 技術 | 預設埠號 |
|------|------|---------|
| 後端 API | FastAPI + Uvicorn | 8001 |
| 前端 | React + Vite | 3000 |
| 資料庫 | PostgreSQL 16 | 5432 |
| 快取 | Redis (可選) | 6379 |

---

## 1. 環境變數驗證

### 必要環境變數

**位置**: 專案根目錄 `/.env` (唯一來源)

```bash
# 資料庫
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ck_documents

# 認證
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx
JWT_SECRET_KEY=your-secret-key

# 應用
ENVIRONMENT=development
DEBUG=true
```

### ❌ 禁止事項

```bash
# 禁止在 backend/.env 建立重複設定
backend/.env  # ❌ 不應存在！
```

### 驗證腳本

```powershell
# 檢查 .env 是否存在
if (!(Test-Path ".env")) {
    Write-Error "缺少 .env 檔案！請從 .env.example 複製"
}

# 檢查 backend/.env 不應存在
if (Test-Path "backend/.env") {
    Write-Warning "發現 backend/.env，可能導致設定衝突！"
}
```

---

## 2. 依賴版本檢查

### Python 依賴

```bash
# 檢查 Python 版本 (需要 3.11+)
python --version

# 檢查關鍵套件版本
pip show fastapi sqlalchemy pydantic | grep -E "^(Name|Version)"
```

### Node.js 依賴

```bash
# 檢查 Node 版本 (需要 18+)
node --version

# 檢查 npm 版本
npm --version

# 檢查 package.json 與 lock 檔案一致性
cd frontend && npm ci
```

### 版本要求

| 套件 | 最低版本 | 建議版本 |
|------|---------|---------|
| Python | 3.11 | 3.12 |
| Node.js | 18 | 20 |
| PostgreSQL | 15 | 16 |
| FastAPI | 0.109 | 0.110+ |
| React | 18 | 18.2+ |

---

## 3. Docker 服務狀態

### 檢查 Docker 服務

```bash
# 檢查 Docker 是否運行
docker info > /dev/null 2>&1 && echo "Docker OK" || echo "Docker 未運行"

# 檢查相關容器狀態
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(postgres|redis)"
```

### 資料庫容器

```bash
# 啟動 PostgreSQL 容器
docker-compose up -d postgres

# 驗證連線
docker exec -it ck_missive_postgres_dev psql -U ck_user -d ck_documents -c "SELECT 1"
```

---

## 4. 本地配置驗證

### 驗證清單

```markdown
## 開發環境檢查清單

- [ ] `.env` 檔案存在且包含所有必要變數
- [ ] `backend/.env` 不存在（避免衝突）
- [ ] Python 虛擬環境已啟用
- [ ] Node modules 已安裝 (`frontend/node_modules` 存在)
- [ ] PostgreSQL 容器運行中
- [ ] 資料庫遷移已執行 (`alembic upgrade head`)
- [ ] 前端 TypeScript 編譯無錯誤
- [ ] 後端 Python 語法檢查通過
```

### 一鍵檢查腳本

```powershell
# scripts/check-dev-env.ps1
Write-Host "=== 開發環境檢查 ===" -ForegroundColor Cyan

# 1. 檢查 .env
if (Test-Path ".env") {
    Write-Host "[OK] .env 存在" -ForegroundColor Green
} else {
    Write-Host "[ERROR] 缺少 .env" -ForegroundColor Red
}

# 2. 檢查 Python
$pyVersion = python --version 2>&1
Write-Host "[INFO] $pyVersion"

# 3. 檢查 Node
$nodeVersion = node --version 2>&1
Write-Host "[INFO] Node $nodeVersion"

# 4. 檢查 Docker
$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Docker 運行中" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Docker 未運行" -ForegroundColor Yellow
}

# 5. 檢查前端編譯
cd frontend
$tscResult = npx tsc --noEmit 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] TypeScript 編譯通過" -ForegroundColor Green
} else {
    Write-Host "[ERROR] TypeScript 編譯錯誤" -ForegroundColor Red
}
cd ..
```

---

## 5. 常見環境問題排解

### 問題 1: 資料庫連線失敗

```bash
# 症狀
sqlalchemy.exc.OperationalError: connection refused

# 解決方案
1. 檢查 Docker 容器是否運行
   docker ps | grep postgres

2. 檢查 DATABASE_URL 是否正確
   echo $DATABASE_URL

3. 檢查埠號是否被占用
   netstat -an | findstr 5432
```

### 問題 2: 前端編譯錯誤

```bash
# 症狀
Type 'xxx' is not assignable to type 'yyy'

# 解決方案
1. 確認 types/api.ts 是最新版本
2. 執行 npm run generate:types 重新生成型別
3. 清除快取重新安裝
   rm -rf node_modules && npm ci
```

### 問題 3: 環境變數未載入

```bash
# 症狀
KeyError: 'DATABASE_URL'

# 解決方案
1. 確認 .env 在專案根目錄
2. 確認變數名稱正確（區分大小寫）
3. 重新啟動服務
```

---

## 參考文件

- `CLAUDE.md` - 專案配置總覽
- `.claude/commands/dev-check.md` - 開發環境檢查指令
- `ecosystem.config.js` - PM2 配置
