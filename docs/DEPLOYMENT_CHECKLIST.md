# 部署管理功能完整性檢查清單

> **建立日期**: 2026-02-03
> **版本**: 1.0.0
> **狀態**: 已完成本地開發，待部署至生產環境

---

## 一、組件檢查清單

### 1. 後端 API (Backend)

| 組件 | 檔案 | 狀態 | 說明 |
|------|------|------|------|
| API 端點模組 | `backend/app/api/endpoints/deployment.py` | ✅ 已完成 | 580+ 行，6 個 POST 端點 |
| 路由註冊 | `backend/app/api/routes.py` | ✅ 已完成 | 第 15, 58 行 |
| Git 提交 | commit `61d7df1` | ✅ 已提交 | security: 部署管理 API 改為 POST-only |

**API 端點列表：**

| 端點 | 方法 | 功能 | 權限 |
|------|------|------|------|
| `/api/deploy/status` | POST | 取得系統狀態 | admin |
| `/api/deploy/history` | POST | 取得部署歷史 | admin |
| `/api/deploy/trigger` | POST | 觸發部署 | admin |
| `/api/deploy/rollback` | POST | 回滾部署 | admin |
| `/api/deploy/logs/{run_id}` | POST | 取得部署日誌 | admin |
| `/api/deploy/config` | POST | 取得部署配置 | admin |

### 2. 前端 API 服務 (Frontend API)

| 組件 | 檔案 | 狀態 | 說明 |
|------|------|------|------|
| API 端點定義 | `frontend/src/api/endpoints.ts` | ✅ 已完成 | DEPLOYMENT_ENDPOINTS (516-529 行) |
| API 服務函數 | `frontend/src/api/deploymentApi.ts` | ✅ 已完成 | 200 行，6 個函數 |
| Git 提交 | commit `d48326a` | ✅ 已提交 | feat: 新增部署管理頁面 |

### 3. 前端路由 (Frontend Router)

| 組件 | 檔案 | 狀態 | 說明 |
|------|------|------|------|
| 路由常數 | `frontend/src/router/types.ts` | ✅ 已完成 | DEPLOYMENT_MANAGEMENT (第 70 行) |
| 路由元數據 | `frontend/src/router/types.ts` | ✅ 已完成 | ROUTE_META (238-244 行) |
| 路由元素 | `frontend/src/router/AppRouter.tsx` | ✅ 已完成 | 第 71, 184 行 |

### 4. 前端頁面 (Frontend Page)

| 組件 | 檔案 | 狀態 | 說明 |
|------|------|------|------|
| 頁面組件 | `frontend/src/pages/DeploymentManagementPage.tsx` | ✅ 已完成 | 726 行 |
| 懶載入 | `AppRouter.tsx` 第 71 行 | ✅ 已完成 | lazy import |

### 5. 導航選單 (Navigation)

| 組件 | 檔案 | 狀態 | 說明 |
|------|------|------|------|
| 靜態選單備用 | `frontend/src/components/layout/hooks/useMenuItems.tsx` | ✅ 已完成 | 第 291-295 行 |
| 圖標映射 | `useMenuItems.tsx` | ✅ 已完成 | RocketOutlined (第 36, 94 行) |
| 資料庫導航項目 | `site_navigation_items` 表 | ✅ 已新增 | ID: 43, parent_id: 20 |
| 初始化腳本 | `backend/app/scripts/init_navigation_data.py` | ✅ 已更新 | 包含部署管理項目 |
| 快速新增腳本 | `backend/app/scripts/add_deployment_nav.py` | ✅ 已建立 | 獨立新增腳本 |

### 6. CD 工作流 (CI/CD)

| 組件 | 檔案 | 狀態 | 說明 |
|------|------|------|------|
| GitHub Actions | `.github/workflows/deploy-production.yml` | ✅ 已完成 | 完整 CD 工作流 |
| Runner 設置指南 | `docs/GITHUB_RUNNER_SETUP.md` | ✅ 已完成 | Self-hosted Runner 設置 |

---

## 二、環境變數要求

生產服務器需配置以下環境變數：

```bash
# GitHub API (部署管理必須)
GITHUB_REPO=bluefishs/CK_Missive
GITHUB_TOKEN=ghp_xxxxxxxxxxxx  # 需要 repo 和 workflow 權限

# 部署路徑
DEPLOY_PATH=/share/CACHEDEV1_DATA/Container/ck-missive
ENVIRONMENT=production
```

---

## 三、生產環境部署指令

### 方法 A：手動部署 (立即生效)

```bash
# 1. SSH 連線到 NAS
ssh admin@192.168.50.210

# 2. 進入專案目錄
cd /share/Container/CK_Missive  # 或實際部署路徑

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

### 方法 B：使用 CD 工作流 (自動化)

需先完成 GitHub Runner 設置：

1. 在 NAS 上安裝 Self-hosted Runner
2. 配置 Repository Secrets
3. 觸發 `deploy-production.yml` 工作流

詳見 `docs/GITHUB_RUNNER_SETUP.md`

---

## 四、驗證清單

部署完成後執行以下驗證：

| 項目 | 驗證方式 | 預期結果 |
|------|----------|----------|
| API 可達性 | `curl -X POST http://192.168.50.210:8001/api/deploy/config -d "{}"` | 200 OK |
| 頁面載入 | 訪問 `http://192.168.50.210:3000/admin/deployment` | 頁面正常顯示 |
| 導航顯示 | 檢查系統管理選單 | 出現「部署管理」項目 |
| 系統狀態 | 點擊「刷新狀態」 | 顯示服務狀態 |
| 部署歷史 | 切換到「部署歷史」Tab | 顯示歷史記錄 (需配置 GITHUB_TOKEN) |

---

## 五、已知限制

1. **GitHub Token 必須配置**：部署歷史、觸發部署、查看日誌功能需要有效的 GitHub Token
2. **管理員權限必須**：所有端點都需要 `admin` 角色
3. **回滾功能限制**：需要 Docker 權限，且必須預先保存 `:rollback` 標籤的映像

---

## 六、相關提交記錄

| Commit | 說明 |
|--------|------|
| `7acb4fc` | feat: 新增部署管理導航項目腳本 |
| `1e2b067` | feat: 前端選單新增備份管理與部署管理項目 |
| `f9fca52` | fix: 調整部署管理導航順序至系統監控之後 |
| `61d7df1` | security: 部署管理 API 改為 POST-only 安全模式 |
| `d48326a` | feat: 新增部署管理頁面 |
| `c48245d` | ci: 建立 GitHub Actions CD 自動部署工作流 |

---

*文件維護: Claude Code Assistant*
*最後更新: 2026-02-03*
