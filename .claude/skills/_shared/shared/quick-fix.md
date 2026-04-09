---
name: quick-fix
description: 快速修復常見問題與錯誤
version: 1.0.0
category: shared
triggers:
  - 快速修復
  - quick fix
  - hotfix
  - 緊急修復
  - 常見問題
updated: 2026-01-22
---

# Quick Fix Skill

> **用途**: 快速修復常見問題與錯誤
> **觸發**: 快速修復, quick fix, hotfix, 緊急修復
> **版本**: 1.0.0
> **分類**: shared

**適用場景**：緊急修復、已知問題快速處理

---

## 常見問題修復手冊

### 1. 安全性問題

#### 問題：敏感信息暴露在 git 版本庫中

**症狀**：
```bash
git ls-files | grep "\.env\.production"
# 輸出：.env.production
```

**修復步驟**：
```bash
# 1. 從 git 移除敏感檔案（保留本地檔案）
git rm --cached .env.production
git rm --cached .env.dev

# 2. 確認 .gitignore 包含這些檔案
cat .gitignore | grep "\.env\.production" || echo ".env.production" >> .gitignore

# 3. 提交變更
git add .gitignore
git commit -m "security: remove sensitive env files from version control"

# 4. 推送到遠端
git push

# 5. 通知團隊重新生成密鑰
echo "⚠️ 請重新生成 SECRET_KEY 和 API Keys"
```

#### 問題：使用弱密碼

**修復步驟**：
```bash
# 1. 生成強密碼
python3 -c "import secrets; print('New SECRET_KEY:', secrets.token_hex(32))"
python3 -c "import secrets; print('New DB Password:', secrets.token_urlsafe(24))"

# 2. 更新 .env.production（僅在本地，不提交）
# SECRET_KEY=<新生成的密鑰>
# POSTGRES_PASSWORD=<新生成的密碼>

# 3. 重啟服務
docker-compose -f docker-compose.prod.yml restart backend db

# 4. 驗證
docker-compose -f docker-compose.prod.yml logs backend | grep "系統啟動完成"
```

#### 問題：API Key 硬編碼

**位置**：`docker-compose.prod.yml:70, 212`

**修復**：
```yaml
# ❌ 修復前
environment:
  - ORS_API_KEY=eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImZjOGZkMWM0N2RhZTQ3NjRiZjEzMDNhMTM3YTc0Y2Y1IiwiaCI6Im11cm11cjY0In0=

# ✅ 修復後
environment:
  - ORS_API_KEY=${ORS_API_KEY}
```

### 2. 後端問題

#### 問題：APScheduler 未啟動

**症狀**：
```python
# backend/app/main.py:45-46
# scheduler.start()  # ❌ 被註釋
```

**修復步驟**：
```bash
# 1. 檢查問題原因
cd backend
python -c "from backend.app.tasks import init_scheduled_tasks; init_scheduled_tasks()"

# 2. 如果沒有錯誤，編輯 main.py
```

**修改檔案**：
```python
# backend/app/main.py

# ❌ 修復前（line 37-47）
# print("Loading scheduled tasks...")
# from backend.app.tasks import init_scheduled_tasks
# init_scheduled_tasks()
# scheduler.start()

# ✅ 修復後
print("Loading scheduled tasks...")
from backend.app.tasks import init_scheduled_tasks
init_scheduled_tasks()
print("[OK] Tasks initialized")

print("Starting scheduler...")
from backend.app.core.scheduler import scheduler
scheduler.start()
print("[OK] Scheduler started")
```

**驗證**：
```bash
# 重啟後端
docker-compose -f docker-compose.prod.yml restart backend

# 檢查日誌
docker-compose -f docker-compose.prod.yml logs backend | grep "Scheduler started"
```

#### 問題：資料庫連線失敗

**症狀**：
```
psycopg2.OperationalError: could not connect to server
```

**常見原因**：
1. **端口錯誤** - 本機開發應使用 **5433**（非 5432）
2. **容器未啟動**
3. **密碼不正確**

**修復步驟**：
```bash
# 1. 確認端口配置正確
# ⚠️ 重要：主機端口是 5433，不是 5432！
grep "5433" .env docker-compose.yml

# 2. 檢查資料庫容器狀態
docker ps | grep db

# 3. 檢查資料庫健康狀態
docker compose exec db pg_isready -U postgres

# 4. 如果未就緒，重啟資料庫
docker compose restart db

# 5. 等待資料庫啟動
sleep 10

# 6. 重啟後端
docker compose restart backend

# 7. 驗證連線
curl http://localhost:8002/api/health
```

**配置修正**：
```bash
# ❌ 錯誤 (使用容器內部端口)
DATABASE_URL=postgresql://postgres:pass@localhost:5432/landvaluation

# ✅ 正確 (使用主機映射端口 5433)
DATABASE_URL=postgresql://postgres:pass@localhost:5433/landvaluation

# ✅ 正確 (Docker 容器內)
DATABASE_URL=postgresql://postgres:pass@db:5432/landvaluation
```

#### 問題：Redis 連線失敗

**症狀**：
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**修復步驟**：
```bash
# 1. 檢查 Redis 容器
docker ps | grep landvaluation_redis_prod

# 2. 如果未運行，啟動 Redis（需使用 profile）
docker-compose -f docker-compose.prod.yml --profile with-redis up -d redis

# 3. 測試 Redis 連線
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping
# 預期輸出：PONG

# 4. 重啟後端
docker-compose -f docker-compose.prod.yml restart backend
```

### 3. 前端問題

#### 問題：前端無法連線到後端 API

**症狀**：
```
Failed to fetch
CORS error
```

**常見原因**：
1. **API 端口錯誤** - 應使用 **8002**（非 8000）
2. **CORS 來源未配置**
3. **後端未運行**

**修復步驟**：
```bash
# 1. 確認 API 端口正確
# ⚠️ 重要：主機端口是 8002，不是 8000！
grep "VITE_API_TARGET" frontend/.env
# 應為：VITE_API_TARGET=http://localhost:8002

# 2. 檢查後端是否運行
curl http://localhost:8002/health

# 3. 檢查 CORS 設定
# ⚠️ 重要：CORS 由 YAML 配置控制，非 .env！
cat backend/app/config/dev.yaml | grep -A 10 "cors:"

# 4. 新增 CORS 來源（如需要）
# 編輯 backend/app/config/dev.yaml
# cors:
#   origins:
#     - "http://新來源:端口"

# 5. 重啟後端
docker compose restart backend

# 6. 清除瀏覽器快取
# Chrome: Ctrl+Shift+Delete
```

**前端配置修正**：
```bash
# frontend/.env
# ❌ 錯誤 (使用容器內部端口)
VITE_API_TARGET=http://localhost:8000

# ✅ 正確 (使用主機映射端口 8002)
VITE_API_TARGET=http://localhost:8002
```

#### 問題：地圖無法載入

**症狀**：
```
Leaflet map container not found
```

**修復步驟**：
```javascript
// 檢查 Map 組件的容器
useEffect(() => {
  const container = document.getElementById('map-container');
  if (!container) {
    console.error('Map container not found!');
  }
}, []);

// 確保容器有正確的高度
// App.css
#map-container {
  width: 100%;
  height: 600px; /* 必須有明確的高度 */
}
```

#### 問題：前端建置失敗

**症狀**：
```
npm run build
Error: Cannot find module 'xxx'
```

**修復步驟**：
```bash
# 1. 清除 node_modules
cd frontend
rm -rf node_modules package-lock.json

# 2. 重新安裝依賴
npm install

# 3. 清除 Vite 快取
rm -rf .vite

# 4. 重新建置
npm run build

# 5. 如果仍失敗，檢查 Node.js 版本
node --version  # 應該是 v18 或更高
```

### 4. Docker 問題

#### 問題：容器啟動失敗

**修復步驟**：
```bash
# 1. 查看容器日誌
docker-compose -f docker-compose.prod.yml logs backend --tail=50

# 2. 檢查容器狀態
docker-compose -f docker-compose.prod.yml ps

# 3. 重新建置映像檔
docker-compose -f docker-compose.prod.yml build --no-cache backend

# 4. 停止並移除所有容器
docker-compose -f docker-compose.prod.yml down

# 5. 重新啟動
docker-compose -f docker-compose.prod.yml up -d

# 6. 監控啟動過程
docker-compose -f docker-compose.prod.yml logs -f
```

#### 問題：磁碟空間不足

**症狀**：
```
no space left on device
```

**修復步驟**：
```bash
# 1. 檢查磁碟使用量
df -h

# 2. 清理未使用的 Docker 資源
docker system prune -a --volumes

# 3. 清理舊的日誌
find ./logs -name "*.log" -mtime +30 -delete

# 4. 清理舊的備份
find ./data/backups -name "*.sql" -mtime +30 -delete

# 5. 檢查大型檔案
du -sh * | sort -h | tail -10
```

#### 問題：Port 衝突

**症狀**：
```
Bind for 0.0.0.0:8002 failed: port is already allocated
```

**修復步驟**：
```bash
# 1. 查找佔用 port 的程序（Windows）
netstat -ano | findstr :8002

# 2. 查找佔用 port 的程序（Linux）
lsof -i :8002

# 3. 停止佔用的程序
# Windows: taskkill /PID <PID> /F
# Linux: kill -9 <PID>

# 4. 或修改 docker-compose.prod.yml 中的 port 映射
ports:
  - "8003:8000"  # 改用其他 port
```

---

## 緊急修復檢查清單

### 生產環境故障

```
[ ] 1. 檢查所有容器是否運行
    docker-compose -f docker-compose.prod.yml ps

[ ] 2. 檢查資料庫連線
    curl http://localhost:8002/api/health

[ ] 3. 檢查日誌錯誤
    docker-compose -f docker-compose.prod.yml logs --tail=100

[ ] 4. 檢查磁碟空間
    df -h

[ ] 5. 檢查記憶體使用
    docker stats --no-stream

[ ] 6. 嘗試重啟服務
    docker-compose -f docker-compose.prod.yml restart

[ ] 7. 如果仍失敗，重新建置
    docker-compose -f docker-compose.prod.yml up -d --build
```

---

## 專案結構問題 (2025-12-25 新增)

### 問題：找不到 CRUD 模組

**症狀**：
```python
ModuleNotFoundError: No module named 'backend.app.crud'
```

**修復**：
```python
# ❌ 舊路徑 (已廢棄)
from backend.app.crud import CRUDBase

# ✅ 新路徑
from backend.app.api.v1.crud import CRUDBase
```

### 問題：找不到 migrations

**修復**：
```bash
# ❌ 舊位置
backend/db/migrations/
backend/database/migrations/

# ✅ 新位置 (統一)
backend/migrations/sql/
```

### 問題：環境變數檔案載入失敗

**症狀**：
```
Attempting to load settings from: .env.dev
FileNotFoundError: .env.dev
```

**原因**：配置系統使用 `APP_ENV` 環境變數決定載入 `.env.{APP_ENV}`

**修復**：
```bash
# 確保 .env.dev 存在
cp .env.development .env.dev

# 或設定 APP_ENV
export APP_ENV=development
```

### 問題：前端 API 導入錯誤

**修復優先順序**：
```typescript
// 1. 優先使用統一 API
import { gisApi } from '@/api/unified';

// 2. 舊 API 仍可用 (2026-03 前)
import { queryByBBox } from '@/api/gisApi';
```

### 問題：前端 Hooks 導入錯誤

**修復**：
```typescript
// ❌ 舊方式 (即將棄用)
import { useSpatialLayers } from '@/hooks/useSpatialData';
import { useGisLayers } from '@/hooks/useLayerManager';

// ✅ 新方式 (推薦)
import { useGisSpatialLayers, useGisLayers } from '@/hooks/unified';
```

### 問題：前端建置記憶體不足

**症狀**：
```
FATAL ERROR: Ineffective mark-compacts near heap limit
Allocation failed - JavaScript heap out of memory
```

**修復**：
```bash
# 增加 Node.js 記憶體限制至 8GB
NODE_OPTIONS="--max-old-space-size=8192" npm run build
```

### 問題：環境變數檔案不同步

**症狀**：`.env.dev` 和 `.env.development` 內容不一致

**修復**：
```bash
# 使用同步工具
python scripts/sync_env.py

# 或手動複製
cp .env.dev .env.development
```

---

## 回滾策略

### Git 回滾
```bash
# 查看最近的提交
git log --oneline -10

# 回滾到上一個版本
git reset --hard HEAD~1

# 回滾到特定版本
git reset --hard <commit-hash>

# 強制推送（謹慎使用）
git push --force
```

### Docker 映像回滾
```bash
# 查看映像歷史
docker images landvaluation_backend

# 使用舊版本映像
docker-compose -f docker-compose.prod.yml up -d backend:1.0.0
```

### 資料庫回滾
```bash
# 列出備份
ls -lh data/backups/

# 恢復備份
docker-compose -f docker-compose.prod.yml exec db \
  psql -U postgres -d landvaluation -f /backups/backup_20251027.sql
```

---

**建立日期**：2025-10-27
**最後更新**：2025-12-25
