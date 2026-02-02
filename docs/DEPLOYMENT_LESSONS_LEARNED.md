# CK_Missive NAS 部署經驗總結與優化建議

> **文件版本**: v1.0.0
> **部署日期**: 2026-02-02
> **目標環境**: QNAP NAS (192.168.50.41) Container Station
> **部署結果**: ✅ 成功

---

## 📋 部署問題彙總

### 1. 後端依賴問題

| 問題 | 根因 | 解決方案 | 耗時影響 |
|------|------|----------|----------|
| `ModuleNotFoundError: asyncpg` | `pyproject.toml` 中 asyncpg 被註解 | 改用 `requirements.txt` + pip 安裝 | 高 (~30 分鐘) |
| Poetry 安裝不一致 | poetry.lock 與 requirements.txt 不同步 | Dockerfile 改用 pip 直接安裝 | 中 |

**建議**:
- [ ] 統一依賴管理：選擇 Poetry 或 pip，不要混用
- [ ] 建立 CI 檢查確保 `pyproject.toml` 和 `requirements.txt` 同步
- [ ] 本地測試 Docker 建置後再部署到 NAS

### 2. 檔案與目錄權限問題

| 問題 | 根因 | 解決方案 |
|------|------|----------|
| `PermissionError: /app/logs/system.log` | Docker volume 掛載覆蓋容器內目錄權限 | 在 NAS 上預先建立目錄並設定 777 權限 |
| `PermissionError: /backups` | 備份服務使用根目錄路徑 | 新增 volume 掛載 `./backend/backups:/backups` |
| `PermissionError: /logs` | 備份日誌使用根目錄路徑 | 新增 volume 掛載 `./backend/backup-logs:/logs` |

**建議**:
- [ ] 建立部署前置腳本，自動建立所需目錄
- [ ] 考慮修改應用程式使用相對路徑或可配置路徑
- [ ] 在 docker-compose 中使用 named volumes 取代 bind mounts

### 3. 資料庫遷移問題

| 問題 | 根因 | 解決方案 |
|------|------|----------|
| `alembic.ini` 未包含在映像中 | `.dockerignore` 排除了該檔案 | 從 `.dockerignore` 移除 `alembic.ini` |
| 遷移順序錯誤 | 多個 base migrations 互相衝突 | 使用 `Base.metadata.create_all()` 建立表格，再 `alembic stamp heads` |
| 表格不存在導致啟動失敗 | Schema 驗證在啟動時執行 | 先執行 init_db.py 建立表格 |

**建議**:
- [ ] 整理 Alembic 遷移歷史，合併多個 heads
- [ ] 建立初始化腳本處理全新部署情境
- [ ] 考慮在應用啟動時自動執行遷移（需謹慎）

### 4. 網路與端口問題

| 問題 | 根因 | 解決方案 |
|------|------|----------|
| Port 80 已被佔用 | NAS 系統服務使用 port 80 | 前端改用 port 3000 |
| CORS 錯誤 | `CORS_ORIGINS` 未包含新端口 | 加入 `http://192.168.50.41:3000` |
| Health check 失敗 | 路徑錯誤 `/api/health` vs `/health` | 修正為 `/health` |

**建議**:
- [ ] 部署前檢查目標端口可用性
- [ ] CORS 設定使用環境變數並支援多端口
- [ ] 統一 health check 端點路徑 (建議: `/health` 或 `/api/health`，擇一)

### 5. 環境變數傳遞問題

| 問題 | 根因 | 解決方案 |
|------|------|----------|
| 後端缺少 DB 連線資訊 | docker-compose 未傳遞 POSTGRES_* 變數 | 新增環境變數傳遞 |
| 容器重啟後變數未更新 | `docker restart` 不重新讀取 .env | 使用 `docker compose up -d --force-recreate` |

**建議**:
- [ ] 在 docker-compose 中明確列出所有必要環境變數
- [ ] 建立 `.env.example` 作為部署範本
- [ ] 使用 `env_file` 指令簡化環境變數管理

---

## 🔧 優化建議事項

### A. 短期改進 (立即可執行)

#### A1. 建立部署前置腳本
```bash
#!/bin/bash
# scripts/pre-deploy.sh

# 建立必要目錄
mkdir -p backend/logs backend/uploads backend/backups backend/backup-logs
chmod 777 backend/logs backend/uploads backend/backups backend/backup-logs

# 檢查端口可用性
for port in 3000 8001 5434 6380; do
  if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null; then
    echo "⚠️ Port $port is in use"
  fi
done

# 驗證 .env 檔案
required_vars="POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB SECRET_KEY CORS_ORIGINS"
for var in $required_vars; do
  if ! grep -q "^$var=" .env; then
    echo "❌ Missing required variable: $var"
  fi
done
```

#### A2. 建立資料庫初始化腳本
```python
# scripts/init_production_db.py
"""Production database initialization script."""
import asyncio
from app.extended.models import Base
from app.db.database import engine

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created")

if __name__ == "__main__":
    asyncio.run(init_db())
```

#### A3. 更新 docker-compose.production.yml
```yaml
# 建議的改進配置
services:
  backend:
    environment:
      # 明確列出所有變數，避免遺漏
      - DATABASE_URL=${DATABASE_URL}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - CORS_ORIGINS=${CORS_ORIGINS}
      - ENVIRONMENT=production
    healthcheck:
      # 統一使用 /health
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      start_period: 90s  # 增加啟動等待時間
    volumes:
      # 使用 named volumes 提高可攜性
      - backend_logs:/app/logs
      - backend_uploads:/app/uploads
      - backend_backups:/backups

volumes:
  backend_logs:
  backend_uploads:
  backend_backups:
```

### B. 中期改進 (1-2 週)

#### B1. 統一依賴管理
- **選項 A**: 完全使用 Poetry
  - 確保 `pyproject.toml` 包含所有依賴
  - Dockerfile 使用 `poetry install`

- **選項 B**: 完全使用 pip (建議)
  - 移除 `pyproject.toml` 和 `poetry.lock`
  - 只維護 `requirements.txt`
  - Dockerfile 使用 `pip install -r requirements.txt`

#### B2. 整理 Alembic 遷移
```bash
# 合併多個 heads
alembic merge heads -m "merge_all_heads"

# 或重新生成初始遷移
alembic revision --autogenerate -m "initial_schema"
```

#### B3. 建立部署 Checklist
```markdown
## Production Deployment Checklist

### 部署前
- [ ] 本地 Docker 建置測試通過
- [ ] 環境變數檔案已準備 (.env.production)
- [ ] 資料庫備份已完成
- [ ] 目標端口已確認可用

### 部署中
- [ ] 上傳部署檔案
- [ ] 建立必要目錄
- [ ] 建置 Docker 映像
- [ ] 執行資料庫遷移
- [ ] 啟動服務

### 部署後
- [ ] 驗證 health endpoint
- [ ] 測試前端存取
- [ ] 確認 CORS 正常
- [ ] 檢查日誌無錯誤
```

### C. 長期改進 (1 個月以上)

#### C1. CI/CD 自動化部署
```yaml
# .github/workflows/deploy-nas.yml
name: Deploy to NAS
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build and test locally
        run: |
          docker compose -f docker-compose.production.yml build
          docker compose -f docker-compose.production.yml up -d
          sleep 30
          curl -f http://localhost:8001/health
          docker compose down

      - name: Deploy to NAS
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.NAS_HOST }}
          username: ${{ secrets.NAS_USER }}
          password: ${{ secrets.NAS_PASSWORD }}
          script: |
            cd /share/CACHEDEV1_DATA/Container/ck-missive
            docker compose pull
            docker compose up -d --force-recreate
```

#### C2. 監控與告警
- 整合 Prometheus + Grafana 監控
- 設定容器健康告警
- 日誌集中管理 (ELK Stack 或 Loki)

#### C3. 藍綠部署或滾動更新
- 實現零停機部署
- 自動回滾機制

---

## 📊 部署時間分析

| 階段 | 預期時間 | 實際時間 | 主要延遲原因 |
|------|----------|----------|--------------|
| 環境準備 | 10 分鐘 | 15 分鐘 | SSH 連線設定 |
| 映像建置 | 5 分鐘 | 20 分鐘 | asyncpg 問題排查 |
| 服務啟動 | 2 分鐘 | 30 分鐘 | 權限問題、遷移問題 |
| 驗證測試 | 5 分鐘 | 15 分鐘 | CORS、端口問題 |
| **總計** | **22 分鐘** | **80 分鐘** | +260% |

### 優化後預期時間
實施上述建議後，預期部署時間可縮短至 **15-20 分鐘**。

---

## ✅ 行動項目優先級

| 優先級 | 項目 | 負責 | 預估工時 |
|--------|------|------|----------|
| 🔴 高 | 統一依賴管理 (改用 pip) | 開發團隊 | 2 小時 |
| 🔴 高 | 建立部署前置腳本 | DevOps | 1 小時 |
| 🟡 中 | 整理 Alembic 遷移 | 開發團隊 | 4 小時 |
| 🟡 中 | 更新 docker-compose 配置 | DevOps | 1 小時 |
| 🟢 低 | CI/CD 自動化部署 | DevOps | 8 小時 |
| 🟢 低 | 監控系統整合 | DevOps | 16 小時 |

---

## 📝 附錄：最終部署配置

### 服務端口對照
| 服務 | 容器內部端口 | 對外端口 |
|------|--------------|----------|
| Frontend (Nginx) | 80 | 3000 |
| Backend (FastAPI) | 8001 | 8001 |
| PostgreSQL | 5432 | 5434 |
| Redis | 6379 | 6380 |

### 目錄結構
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

### 存取 URL
- 前端: http://192.168.50.41:3000/
- 後端 API: http://192.168.50.41:8001/
- API 文件: http://192.168.50.41:8001/docs
- 健康檢查: http://192.168.50.41:8001/health

---

*文件維護: Claude Code Assistant*
*最後更新: 2026-02-02*
