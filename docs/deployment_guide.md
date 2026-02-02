# CK_Missive 自動部署指南

> **版本**: 1.0.0
> **建立日期**: 2026-02-02
> **適用範圍**: GitHub Actions CD 工作流配置

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
│   GitHub    │────▶│   GitHub     │────▶│   Target        │
│   Push      │     │   Actions    │     │   Server        │
└─────────────┘     └──────────────┘     └─────────────────┘
                           │
                           ▼
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

## 相關文件

- [CI 工作流](.github/workflows/ci.yml)
- [CD 工作流](.github/workflows/cd.yml)
- [Docker Compose 配置](docker-compose.unified.yml)
- [環境變數範本](.env.example)

---

*文件維護: Claude Code Assistant*
*最後更新: 2026-02-02*
