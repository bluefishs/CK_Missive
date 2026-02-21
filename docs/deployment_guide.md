# CK_Missive 自動部署指南

> Version: 2.0.0 | Last Updated: 2026-02-21

> **版本**: 2.0.0
> **建立日期**: 2026-02-02
> **最後整合**: 2026-02-21
> **適用範圍**: GitHub Actions CD 工作流配置、NAS 部署、部署管理功能

---

## 概述

本專案使用 GitHub Actions 實現自動部署 (CD - Continuous Deployment)，支援：

- **自動部署**: main/develop 分支推送後自動觸發
- **手動部署**: 透過 GitHub Actions 手動觸發
- **環境隔離**: staging 和 production 環境分離
- **Docker 映像檔**: 使用 GitHub Container Registry (ghcr.io)

---

## 部署架構

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   GitHub    │────>│   GitHub     │────>│   Target        │
│   Push      │     │   Actions    │     │   Server        │
└─────────────┘     └──────────────┘     └─────────────────┘
                           │
                           v
                    ┌──────────────┐
                    │   ghcr.io    │
                    │   Registry   │
                    └──────────────┘
```

### 工作流程

1. **develop 分支** → 自動部署到 **Staging**
2. **main 分支** → 自動部署到 **Production**

---

## 設置指南

### 1. GitHub Secrets 配置

在 GitHub Repository → Settings → Secrets and variables → Actions 中設置：

#### 通用 Secrets

| Secret | 說明 | 範例 |
|--------|------|------|
| `VITE_API_BASE_URL` | API 基礎 URL | `https://api.example.com` |
| `VITE_GOOGLE_CLIENT_ID` | Google OAuth Client ID | `xxx.apps.googleusercontent.com` |

#### Staging 環境

| Secret | 說明 | 範例 |
|--------|------|------|
| `STAGING_HOST` | Staging 伺服器 IP/域名 | `192.168.50.100` |
| `STAGING_USER` | SSH 使用者名稱 | `deploy` |
| `STAGING_SSH_KEY` | SSH 私鑰 (PEM 格式) | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `STAGING_SSH_PORT` | SSH 埠號 (可選) | `22` |
| `STAGING_DEPLOY_PATH` | 部署目錄路徑 | `/opt/ck-missive` |
| `STAGING_URL` | Staging 環境 URL | `https://staging.example.com` |

#### Production 環境

| Secret | 說明 | 範例 |
|--------|------|------|
| `PRODUCTION_HOST` | Production 伺服器 IP/域名 | `10.0.0.50` |
| `PRODUCTION_USER` | SSH 使用者名稱 | `deploy` |
| `PRODUCTION_SSH_KEY` | SSH 私鑰 (PEM 格式) | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `PRODUCTION_SSH_PORT` | SSH 埠號 (可選) | `22` |
| `PRODUCTION_DEPLOY_PATH` | 部署目錄路徑 | `/opt/ck-missive` |
| `PRODUCTION_URL` | Production 環境 URL | `https://app.example.com` |

### 2. GitHub Environments 配置

在 GitHub Repository → Settings → Environments 中建立：

#### staging 環境
- 無需額外保護規則
- 用於開發測試

#### production 環境
- **啟用 Required reviewers**: 至少 1 人審核
- **啟用 Wait timer**: 建議 5-10 分鐘
- 確保生產環境部署經過審核

### 3. 伺服器端準備

在目標伺服器上執行：

```bash
# 1. 建立部署目錄
sudo mkdir -p /opt/ck-missive
sudo chown deploy:deploy /opt/ck-missive

# 2. 安裝 Docker 和 Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker deploy

# 3. 登入 GitHub Container Registry
docker login ghcr.io -u <github-username>
# 輸入 Personal Access Token (需有 read:packages 權限)

# 4. 複製專案配置
git clone https://github.com/<org>/CK_Missive.git /opt/ck-missive
cd /opt/ck-missive
cp .env.example .env
# 編輯 .env 設置正確的環境變數

# 5. 首次啟動
docker-compose -f docker-compose.unified.yml up -d
```

---

## 使用方式

### 自動部署

推送到對應分支即可觸發：

```bash
# 部署到 Staging
git push origin develop

# 部署到 Production
git push origin main
```

### 手動部署

1. 前往 GitHub → Actions → CD - Deploy
2. 點擊 "Run workflow"
3. 選擇環境 (staging/production)
4. 選擇是否跳過測試 (緊急情況使用)
5. 點擊 "Run workflow"

### 查看部署狀態

- GitHub Actions 頁面查看工作流程狀態
- 點擊具體的 job 查看詳細日誌

---

## 回滾機制

### 自動回滾 (建議)

若部署失敗，可手動執行：

```bash
# SSH 到伺服器
ssh deploy@<server>
cd /opt/ck-missive

# 回滾到前一版本
docker tag ck-missive-backend:previous ck-missive-backend:latest
docker tag ck-missive-frontend:previous ck-missive-frontend:latest
docker-compose -f docker-compose.unified.yml up -d --force-recreate backend frontend
```

### 回滾到特定版本

```bash
# 查看可用版本
docker images | grep ck-missive

# 回滾到特定版本 (例如 20260202-abc1234)
docker pull ghcr.io/<org>/ck_missive/backend:20260202-abc1234
docker pull ghcr.io/<org>/ck_missive/frontend:20260202-abc1234
docker tag ghcr.io/<org>/ck_missive/backend:20260202-abc1234 ck-missive-backend:latest
docker tag ghcr.io/<org>/ck_missive/frontend:20260202-abc1234 ck-missive-frontend:latest
docker-compose -f docker-compose.unified.yml up -d --force-recreate backend frontend
```

---

## 本地部署

若需要在本地或不使用 GitHub Actions 的情況下部署：

```bash
# 使用部署腳本
./scripts/deploy.sh staging   # 部署到 Staging
./scripts/deploy.sh production # 部署到 Production
```

---

## 故障排除

### 1. SSH 連線失敗

```
Error: ssh: connect to host xxx port 22: Connection timed out
```

**解決方案**:
- 確認伺服器防火牆允許 SSH 連線
- 確認 SSH 金鑰格式正確 (PEM 格式)
- 確認 SSH 使用者有權限

### 2. Docker 登入失敗

```
Error: unauthorized: authentication required
```

**解決方案**:
- 在伺服器上重新登入 ghcr.io
- 確認 Personal Access Token 有 `read:packages` 權限

### 3. 健康檢查失敗

```
Error: curl: (7) Failed to connect to localhost port 8001
```

**解決方案**:
- 檢查容器日誌: `docker logs ck_missive_backend`
- 確認資料庫連線正常
- 確認環境變數設置正確

### 4. 資料庫遷移失敗

```
Error: alembic.util.exc.CommandError: Can't locate revision
```

**解決方案**:
- 手動執行遷移: `docker exec -it ck_missive_backend alembic upgrade head`
- 檢查遷移狀態: `docker exec -it ck_missive_backend alembic current`

---

## 安全注意事項

1. **SSH 金鑰**: 使用專用的部署金鑰，不要使用個人金鑰
2. **最小權限**: 部署使用者只需 docker 和部署目錄的權限
3. **Secrets 輪換**: 定期更換 SSH 金鑰和 Token
4. **審計日誌**: GitHub Actions 會保留所有部署記錄

---

## 部署經驗教訓

> 整合自 `DEPLOYMENT_LESSONS_LEARNED.md` (v1.0.0, 2026-02-02)
> 目標環境: QNAP NAS (192.168.50.41) Container Station

### 問題彙總

#### 1. 後端依賴問題

| 問題 | 根因 | 解決方案 | 耗時影響 |
|------|------|----------|----------|
| `ModuleNotFoundError: asyncpg` | `pyproject.toml` 中 asyncpg 被註解 | 改用 `requirements.txt` + pip 安裝 | 高 (~30 分鐘) |
| Poetry 安裝不一致 | poetry.lock 與 requirements.txt 不同步 | Dockerfile 改用 pip 直接安裝 | 中 |

**建議**:
- 統一依賴管理：選擇 Poetry 或 pip，不要混用
- 建立 CI 檢查確保 `pyproject.toml` 和 `requirements.txt` 同步
- 本地測試 Docker 建置後再部署到 NAS

#### 2. 檔案與目錄權限問題

| 問題 | 根因 | 解決方案 |
|------|------|----------|
| `PermissionError: /app/logs/system.log` | Docker volume 掛載覆蓋容器內目錄權限 | 在 NAS 上預先建立目錄並設定 777 權限 |
| `PermissionError: /backups` | 備份服務使用根目錄路徑 | 新增 volume 掛載 `./backend/backups:/backups` |
| `PermissionError: /logs` | 備份日誌使用根目錄路徑 | 新增 volume 掛載 `./backend/backup-logs:/logs` |

**建議**:
- 建立部署前置腳本，自動建立所需目錄
- 考慮修改應用程式使用相對路徑或可配置路徑
- 在 docker-compose 中使用 named volumes 取代 bind mounts

#### 3. 資料庫遷移問題

| 問題 | 根因 | 解決方案 |
|------|------|----------|
| `alembic.ini` 未包含在映像中 | `.dockerignore` 排除了該檔案 | 從 `.dockerignore` 移除 `alembic.ini` |
| 遷移順序錯誤 | 多個 base migrations 互相衝突 | 使用 `Base.metadata.create_all()` 建立表格，再 `alembic stamp heads` |
| 表格不存在導致啟動失敗 | Schema 驗證在啟動時執行 | 先執行 init_db.py 建立表格 |

**建議**:
- 整理 Alembic 遷移歷史，合併多個 heads
- 建立初始化腳本處理全新部署情境
- 考慮在應用啟動時自動執行遷移（需謹慎）

#### 4. 網路與端口問題

| 問題 | 根因 | 解決方案 |
|------|------|----------|
| Port 80 已被佔用 | NAS 系統服務使用 port 80 | 前端改用 port 3000 |
| CORS 錯誤 | `CORS_ORIGINS` 未包含新端口 | 加入 `http://192.168.50.41:3000` |
| Health check 失敗 | 路徑錯誤 `/api/health` vs `/health` | 修正為 `/health` |

**建議**:
- 部署前檢查目標端口可用性
- CORS 設定使用環境變數並支援多端口
- 統一 health check 端點路徑 (建議: `/health` 或 `/api/health`，擇一)

#### 5. 環境變數傳遞問題

| 問題 | 根因 | 解決方案 |
|------|------|----------|
| 後端缺少 DB 連線資訊 | docker-compose 未傳遞 POSTGRES_* 變數 | 新增環境變數傳遞 |
| 容器重啟後變數未更新 | `docker restart` 不重新讀取 .env | 使用 `docker compose up -d --force-recreate` |

**建議**:
- 在 docker-compose 中明確列出所有必要環境變數
- 建立 `.env.example` 作為部署範本
- 使用 `env_file` 指令簡化環境變數管理

### 優化建議

#### A. 短期改進 (立即可執行)

**A1. 部署前置腳本**

```bash
#!/bin/bash
# scripts/pre-deploy.sh

# 建立必要目錄
mkdir -p backend/logs backend/uploads backend/backups backend/backup-logs
chmod 777 backend/logs backend/uploads backend/backups backend/backup-logs

# 檢查端口可用性
for port in 3000 8001 5434 6380; do
  if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null; then
    echo "WARNING: Port $port is in use"
  fi
done

# 驗證 .env 檔案
required_vars="POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB SECRET_KEY CORS_ORIGINS"
for var in $required_vars; do
  if ! grep -q "^$var=" .env; then
    echo "ERROR: Missing required variable: $var"
  fi
done
```

**A2. 資料庫初始化腳本**

```python
# scripts/init_production_db.py
"""Production database initialization script."""
import asyncio
from app.extended.models import Base
from app.db.database import engine

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully")

if __name__ == "__main__":
    asyncio.run(init_db())
```

**A3. docker-compose.production.yml 改進配置**

```yaml
services:
  backend:
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - CORS_ORIGINS=${CORS_ORIGINS}
      - ENVIRONMENT=production
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      start_period: 90s
    volumes:
      - backend_logs:/app/logs
      - backend_uploads:/app/uploads
      - backend_backups:/backups

volumes:
  backend_logs:
  backend_uploads:
  backend_backups:
```

#### B. 中期改進 (1-2 週)

**B1. 統一依賴管理**

- **選項 A**: 完全使用 Poetry — 確保 `pyproject.toml` 包含所有依賴，Dockerfile 使用 `poetry install`
- **選項 B (建議)**: 完全使用 pip — 移除 `pyproject.toml` 和 `poetry.lock`，只維護 `requirements.txt`

**B2. 整理 Alembic 遷移**

```bash
# 合併多個 heads
alembic merge heads -m "merge_all_heads"

# 或重新生成初始遷移
alembic revision --autogenerate -m "initial_schema"
```

#### C. 長期改進 (1 個月以上)

- **監控與告警**: 整合 Prometheus + Grafana 監控、容器健康告警、日誌集中管理
- **藍綠部署或滾動更新**: 實現零停機部署、自動回滾機制

### 部署時間分析

| 階段 | 預期時間 | 實際時間 | 主要延遲原因 |
|------|----------|----------|--------------|
| 環境準備 | 10 分鐘 | 15 分鐘 | SSH 連線設定 |
| 映像建置 | 5 分鐘 | 20 分鐘 | asyncpg 問題排查 |
| 服務啟動 | 2 分鐘 | 30 分鐘 | 權限問題、遷移問題 |
| 驗證測試 | 5 分鐘 | 15 分鐘 | CORS、端口問題 |
| **總計** | **22 分鐘** | **80 分鐘** | +260% |

實施上述建議後，預期部署時間可縮短至 **15-20 分鐘**。

### NAS 部署參考配置

#### 服務端口對照

| 服務 | 容器內部端口 | 對外端口 |
|------|--------------|----------|
| Frontend (Nginx) | 80 | 3000 |
| Backend (FastAPI) | 8001 | 8001 |
| PostgreSQL | 5432 | 5434 |
| Redis | 6379 | 6380 |

#### NAS 目錄結構

```
/share/CACHEDEV1_DATA/Container/ck-missive/
├── .env                          # 環境變數
├── docker-compose.production.yml # 部署配置
├── backend/
│   ├── Dockerfile
│   ├── logs/                     # 應用日誌
│   ├── uploads/                  # 上傳檔案
│   ├── backups/                  # 資料庫備份
│   └── backup-logs/              # 備份日誌
└── frontend/
    └── Dockerfile
```

#### 存取 URL

- 前端: `http://192.168.50.41:3000/`
- 後端 API: `http://192.168.50.41:8001/`
- API 文件: `http://192.168.50.41:8001/docs`
- 健康檢查: `http://192.168.50.41:8001/health`

---

## 部署檢查清單

> 整合自 `DEPLOYMENT_CHECKLIST.md` (v1.0.0, 2026-02-03)

### 一、組件檢查清單

#### 1. 後端 API (Backend)

| 組件 | 檔案 | 說明 |
|------|------|------|
| API 端點模組 | `backend/app/api/endpoints/deployment.py` | 580+ 行，6 個 POST 端點 |
| 路由註冊 | `backend/app/api/routes.py` | 第 15, 58 行 |

**API 端點列表：**

| 端點 | 方法 | 功能 | 權限 |
|------|------|------|------|
| `/api/deploy/status` | POST | 取得系統狀態 | admin |
| `/api/deploy/history` | POST | 取得部署歷史 | admin |
| `/api/deploy/trigger` | POST | 觸發部署 | admin |
| `/api/deploy/rollback` | POST | 回滾部署 | admin |
| `/api/deploy/logs/{run_id}` | POST | 取得部署日誌 | admin |
| `/api/deploy/config` | POST | 取得部署配置 | admin |

#### 2. 前端 API 服務

| 組件 | 檔案 | 說明 |
|------|------|------|
| API 端點定義 | `frontend/src/api/endpoints.ts` | DEPLOYMENT_ENDPOINTS |
| API 服務函數 | `frontend/src/api/deploymentApi.ts` | 200 行，6 個函數 |

#### 3. 前端路由

| 組件 | 檔案 | 說明 |
|------|------|------|
| 路由常數 | `frontend/src/router/types.ts` | DEPLOYMENT_MANAGEMENT |
| 路由元素 | `frontend/src/router/AppRouter.tsx` | lazy import |

#### 4. 前端頁面

| 組件 | 檔案 | 說明 |
|------|------|------|
| 頁面組件 | `frontend/src/pages/DeploymentManagementPage.tsx` | 726 行 |

#### 5. 導航選單

| 組件 | 檔案 | 說明 |
|------|------|------|
| 靜態選單備用 | `frontend/src/components/layout/hooks/useMenuItems.tsx` | RocketOutlined 圖標 |
| 資料庫導航項目 | `site_navigation_items` 表 | ID: 43, parent_id: 20 |
| 初始化腳本 | `backend/app/scripts/init_navigation_data.py` | 包含部署管理項目 |

#### 6. CD 工作流

| 組件 | 檔案 | 說明 |
|------|------|------|
| GitHub Actions | `.github/workflows/deploy-production.yml` | 完整 CD 工作流 |
| Runner 設置指南 | `docs/GITHUB_RUNNER_SETUP.md` | Self-hosted Runner 設置 |

### 二、環境變數要求

生產服務器需配置以下環境變數：

```bash
# GitHub API (部署管理必須)
GITHUB_REPO=bluefishs/CK_Missive
GITHUB_TOKEN=ghp_xxxxxxxxxxxx  # 需要 repo 和 workflow 權限

# 部署路徑
DEPLOY_PATH=/share/CACHEDEV1_DATA/Container/ck-missive
ENVIRONMENT=production
```

### 三、生產環境部署指令

#### 方法 A：手動部署 (立即生效)

```bash
# 1. SSH 連線到 NAS
ssh admin@192.168.50.210

# 2. 進入專案目錄
cd /share/Container/CK_Missive

# 3. 拉取最新代碼
git pull origin main

# 4. 重啟後端服務
# Docker Compose 方式:
docker-compose -f docker-compose.production.yml restart backend

# 或 PM2 方式:
pm2 restart ck-backend

# 5. 驗證 API
curl -X POST http://localhost:8001/api/deploy/config \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d "{}"
```

#### 方法 B：使用 CD 工作流 (自動化)

需先完成 GitHub Runner 設置：

1. 在 NAS 上安裝 Self-hosted Runner
2. 配置 Repository Secrets
3. 觸發 `deploy-production.yml` 工作流

詳見 `docs/GITHUB_RUNNER_SETUP.md`

### 四、部署後驗證清單

| 項目 | 驗證方式 | 預期結果 |
|------|----------|----------|
| API 可達性 | `curl -X POST http://<host>:8001/api/deploy/config -d "{}"` | 200 OK |
| 頁面載入 | 訪問 `http://<host>:3000/admin/deployment` | 頁面正常顯示 |
| 導航顯示 | 檢查系統管理選單 | 出現「部署管理」項目 |
| 系統狀態 | 點擊「刷新狀態」 | 顯示服務狀態 |
| 部署歷史 | 切換到「部署歷史」Tab | 顯示歷史記錄 (需配置 GITHUB_TOKEN) |

### 五、已知限制

1. **GitHub Token 必須配置**：部署歷史、觸發部署、查看日誌功能需要有效的 GitHub Token
2. **管理員權限必須**：所有端點都需要 `admin` 角色
3. **回滾功能限制**：需要 Docker 權限，且必須預先保存 `:rollback` 標籤的映像

---

## 相關文件

- [CI 工作流](../.github/workflows/ci.yml)
- [CD 工作流](../.github/workflows/cd.yml)
- [Docker Compose 配置](../docker-compose.unified.yml)
- [環境變數範本](../.env.example)
- [GitHub Runner 設置指南](GITHUB_RUNNER_SETUP.md)
- [Alembic 遷移管理指南](ALEMBIC_MIGRATION_GUIDE.md)

---

*文件維護: Claude Code Assistant*
*版本: 2.0.0 - 整合 DEPLOYMENT_LESSONS_LEARNED.md + DEPLOYMENT_CHECKLIST.md*
*最後更新: 2026-02-21*
