# 手動部署指引

> **建立日期**: 2026-02-03
> **目標環境**: QNAP NAS (192.168.50.210)
> **當前狀態**: SSH 連線不可用，需手動操作

---

## 情況說明

目前無法透過 SSH 遠端部署，原因可能是：
- QNAP NAS 的 SSH 服務未啟用
- 防火牆阻擋 SSH 連線

但服務是運行中的：
- ✅ 後端 API: `http://192.168.50.210:8001/health` 回應正常
- ✅ 前端: `http://192.168.50.210:3000` 可訪問

---

## 方法一：透過 QNAP 控制台啟用 SSH

### 步驟 1: 登入 QNAP 控制台

1. 開啟瀏覽器，訪問 `https://192.168.50.210:8080` 或 `http://192.168.50.210:5000`
2. 使用管理員帳號登入

### 步驟 2: 啟用 SSH 服務

1. 進入「控制台」→「網路與檔案服務」→「Telnet / SSH」
2. 勾選「允許 SSH 連線」
3. 設定連接埠 (預設 22)
4. 點擊「套用」

### 步驟 3: 執行部署

SSH 啟用後，在本機執行：

```powershell
# Windows PowerShell
ssh admin@192.168.50.210

# 在 NAS 上執行
cd /share/Container/CK_Missive
git pull origin main
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d --build
```

---

## 方法二：使用 Container Station Web UI

### 步驟 1: 登入 Container Station

1. 開啟瀏覽器，訪問 QNAP 管理介面
2. 進入「Container Station」應用程式

### 步驟 2: 重新部署容器

1. 找到 `ck-missive-backend` 容器
2. 點擊「停止」
3. 點擊「移除」（保留資料）
4. 重新建立容器或使用 compose 功能重新部署

---

## 方法三：直接在 NAS 終端操作

如果可以透過 QNAP 控制台開啟終端：

1. 控制台 → 應用程式 → Terminal/SSH
2. 或使用 Container Station 的「終端」功能

執行以下命令：

```bash
# 進入專案目錄
cd /share/Container/CK_Missive

# 拉取最新程式碼
git pull origin main

# 重啟服務
docker-compose -f docker-compose.production.yml restart backend

# 或完整重建
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d --build

# 驗證服務
curl http://localhost:8001/health
```

---

## 驗證部署成功

部署完成後，執行以下驗證：

| 項目 | 驗證方式 | 預期結果 |
|------|----------|----------|
| 健康檢查 | `curl http://192.168.50.210:8001/health` | `"status":"healthy"` |
| 部署 API | `curl -X POST http://192.168.50.210:8001/api/deploy/config -d "{}"` | 回傳配置 JSON |
| 前端頁面 | 訪問 `http://192.168.50.210:3000/admin/deployment` | 頁面正常顯示 |
| 版本確認 | 健康檢查回傳的 `version` 欄位 | 應為最新版本 |

---

## 待部署的新功能

本次部署包含以下新功能：

1. **部署管理頁面** (`/admin/deployment`)
   - 系統狀態監控
   - 部署歷史查詢
   - 手動觸發部署/回滾

2. **新增 API 端點**
   - `POST /api/deploy/status`
   - `POST /api/deploy/history`
   - `POST /api/deploy/trigger`
   - `POST /api/deploy/rollback`
   - `POST /api/deploy/logs/{run_id}`
   - `POST /api/deploy/config`

3. **導航選單項目**
   - 系統管理 → 部署管理

---

## 後續建議

### 1. 啟用 SSH 服務
建議在 QNAP 上啟用 SSH 服務，以便未來可以遠端部署。

### 2. 安裝 Self-hosted Runner
參考 `docs/GITOPS_EVALUATION.md` 在 NAS 上安裝 GitHub Actions Runner，
實現程式碼提交後自動部署。

### 3. 設定自動更新
考慮設定 cron job 定期執行 `git pull` 和重啟。

---

*文件維護: Claude Code Assistant*
*最後更新: 2026-02-03*
