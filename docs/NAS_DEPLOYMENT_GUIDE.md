# CK_Missive NAS Production 部署指南

> **目標伺服器**: 192.168.50.41 (QNAP NAS Container Station)
> **版本**: 1.0.0
> **建立日期**: 2026-02-02

---

## 概述

本指南說明如何將 CK_Missive 公文管理系統部署到 QNAP NAS 的 Container Station。

### 系統架構

```
┌─────────────────────────────────────────────────────────────┐
│                    QNAP NAS (192.168.50.41)                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │ Frontend│  │ Backend │  │PostgreSQL│  │  Redis  │       │
│  │  :80    │  │  :8001  │  │  :5434   │  │  :6380  │       │
│  │ (Nginx) │  │(FastAPI)│  │         │  │         │       │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘       │
│       │            │            │            │             │
│       └────────────┴────────────┴────────────┘             │
│                    Docker Network                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 服務端口

| 服務 | 內部端口 | 外部端口 | 說明 |
|------|----------|----------|------|
| Frontend | 80 | 80 | React + Nginx |
| Backend | 8000 | 8001 | FastAPI |
| PostgreSQL | 5432 | 5434 | 資料庫 |
| Redis | 6379 | 6380 | 快取 |
| Adminer | 8080 | 8080 | 資料庫管理 (可選) |

---

## 部署前準備

### 1. NAS 環境要求

- QNAP NAS 已安裝 Container Station
- Docker 和 Docker Compose 可用
- SSH 存取權限
- 至少 4GB RAM 可用
- 至少 10GB 儲存空間

### 2. 本地環境要求

- Git
- SSH 客戶端
- tar 命令 (Windows 10+ 內建)
- OpenSSL (用於生成密鑰)

### 3. 網路配置

確保以下端口在內網可存取：
- 80 (HTTP)
- 8001 (API)
- 5434 (PostgreSQL，如需外部存取)

---

## 快速部署 (推薦)

### Windows 使用者

```powershell
# 1. 開啟 PowerShell，進入專案目錄
cd C:\GeminiCli\CK_Missive

# 2. 執行部署腳本
.\scripts\deploy-nas.ps1

# 或指定參數
.\scripts\deploy-nas.ps1 -NasHost "192.168.50.41" -NasUser "admin"
```

### Linux/macOS 使用者

```bash
# 1. 進入專案目錄
cd /path/to/CK_Missive

# 2. 給予執行權限
chmod +x scripts/deploy-nas.sh

# 3. 執行部署腳本
./scripts/deploy-nas.sh
```

---

## 手動部署步驟

如果自動腳本無法執行，可按以下步驟手動部署：

### 步驟 1: 準備環境配置

```bash
# 複製生產環境配置
cp .env.production .env

# 生成安全金鑰
openssl rand -hex 32

# 編輯 .env，替換以下值：
# - POSTGRES_PASSWORD: 設定強密碼
# - SECRET_KEY: 貼上上面生成的金鑰
```

### 步驟 2: 上傳檔案到 NAS

```bash
# SSH 連接 NAS
ssh admin@192.168.50.41

# 建立部署目錄
mkdir -p /share/Container/ck-missive
exit

# 從本地上傳檔案
scp -r backend frontend configs docker-compose.production.yml .env \
    admin@192.168.50.41:/share/Container/ck-missive/
```

### 步驟 3: 建構並啟動服務

```bash
# SSH 連接 NAS
ssh admin@192.168.50.41
cd /share/Container/ck-missive

# 建構映像檔
docker-compose -f docker-compose.production.yml build

# 啟動服務
docker-compose -f docker-compose.production.yml up -d

# 檢查狀態
docker-compose -f docker-compose.production.yml ps
```

### 步驟 4: 執行資料庫遷移

```bash
# 執行 Alembic 遷移
docker-compose -f docker-compose.production.yml exec backend alembic upgrade head
```

### 步驟 5: 驗證部署

```bash
# 檢查後端健康狀態
curl http://192.168.50.41:8001/health

# 檢查前端
curl http://192.168.50.41/
```

---

## Container Station Web UI 部署

如果偏好使用圖形介面：

### 1. 登入 Container Station

開啟瀏覽器，前往 `http://192.168.50.41:8080` (Container Station 管理介面)

### 2. 建立應用

1. 點擊 "Create" → "Create Application"
2. 選擇 "Docker Compose"
3. 上傳 `docker-compose.production.yml`
4. 設定環境變數 (從 `.env.production` 複製)
5. 點擊 "Create"

### 3. 啟動應用

1. 在應用列表中找到 "ck_missive_prod"
2. 點擊 "Start"
3. 等待所有容器變為 "Running" 狀態

---

## 部署後配置

### 1. 建立管理員帳號

```bash
ssh admin@192.168.50.41
cd /share/Container/ck-missive

# 進入後端容器
docker-compose -f docker-compose.production.yml exec backend bash

# 執行建立管理員腳本
python setup_admin.py --username admin --email admin@company.com
```

### 2. 初始化導覽資料

```bash
docker-compose -f docker-compose.production.yml exec backend \
    python -m app.scripts.init_navigation_data
```

### 3. 設定 Google Calendar (選填)

如需使用 Google Calendar 整合：

1. 將 `GoogleCalendarAPIKEY.json` 上傳到 NAS
2. 設定環境變數中的 Google OAuth 相關配置
3. 重啟 backend 服務

---

## 維護指令

### 查看日誌

```bash
# 查看所有服務日誌
docker-compose -f docker-compose.production.yml logs -f

# 只看後端日誌
docker-compose -f docker-compose.production.yml logs -f backend

# 查看最近 100 行
docker-compose -f docker-compose.production.yml logs --tail=100 backend
```

### 重啟服務

```bash
# 重啟所有服務
docker-compose -f docker-compose.production.yml restart

# 只重啟後端
docker-compose -f docker-compose.production.yml restart backend
```

### 停止服務

```bash
# 停止但保留容器
docker-compose -f docker-compose.production.yml stop

# 完全停止並移除容器
docker-compose -f docker-compose.production.yml down
```

### 資料庫備份

```bash
# 備份資料庫
docker exec ck_missive_postgres pg_dump -U ck_user ck_documents > backup_$(date +%Y%m%d).sql

# 還原資料庫
docker exec -i ck_missive_postgres psql -U ck_user ck_documents < backup_20260202.sql
```

### 更新部署

```bash
# 拉取最新程式碼
git pull origin main

# 重新建構並部署
docker-compose -f docker-compose.production.yml build --no-cache
docker-compose -f docker-compose.production.yml up -d

# 執行遷移 (如有)
docker-compose -f docker-compose.production.yml exec backend alembic upgrade head
```

---

## 故障排除

### 1. 容器啟動失敗

```bash
# 查看詳細錯誤
docker-compose -f docker-compose.production.yml logs backend

# 常見原因：
# - 環境變數未設定
# - 資料庫連線失敗
# - 端口已被佔用
```

### 2. 資料庫連線錯誤

```bash
# 檢查 PostgreSQL 容器狀態
docker-compose -f docker-compose.production.yml ps postgres

# 進入 PostgreSQL 容器檢查
docker exec -it ck_missive_postgres psql -U ck_user -d ck_documents
```

### 3. 前端無法連接後端

- 確認 VITE_API_BASE_URL 設定正確
- 確認 CORS_ORIGINS 包含前端 URL
- 檢查防火牆設定

### 4. 磁碟空間不足

```bash
# 清理未使用的映像檔
docker image prune -a

# 清理未使用的卷
docker volume prune
```

---

## 安全注意事項

1. **密碼強度**: 確保 POSTGRES_PASSWORD 和 SECRET_KEY 使用強隨機值
2. **SSH 金鑰**: 建議使用 SSH 金鑰而非密碼登入
3. **防火牆**: 只開放必要的端口
4. **定期備份**: 設定自動備份排程
5. **更新維護**: 定期更新系統和依賴套件

---

## 相關資源

- [Docker Compose 官方文檔](https://docs.docker.com/compose/)
- [QNAP Container Station 手冊](https://www.qnap.com/solution/container_station/)
- [專案部署指南](./DEPLOYMENT_GUIDE.md)

---

*文件維護: Claude Code Assistant*
*最後更新: 2026-02-02*
