# /route-sync-check - 前後端路由一致性檢查

檢查前端路由定義與後端導覽資料的一致性，找出不匹配的項目。

## 新版驗證機制 (v2.0.0 - 2026-01-12)

### 後端路徑白名單驗證

後端現已內建路徑白名單驗證機制：

- **驗證器**: `backend/app/core/navigation_validator.py`
- **API 驗證**: 在 `create` 和 `update` 操作時自動驗證路徑
- **有效路徑 API**: `GET /api/secure-site-management/navigation/valid-paths`

### 前端路徑選擇器

- **SiteManagementPage**: 路徑欄位已改為下拉選單
- 下拉選單選項從後端 API 或內建列表載入
- 防止使用者輸入無效路徑

### 初始化腳本強制更新

使用 `--force-update` 參數可強制同步路徑：

```bash
cd backend && python app/scripts/init_navigation_data.py --force-update
```

## 檢查範圍

1. **前端路由來源**：`frontend/src/router/types.ts` 中的 `ROUTES` 定義
2. **後端路徑白名單**：`backend/app/core/navigation_validator.py` 中的 `VALID_NAVIGATION_PATHS`
3. **後端導覽定義**：`backend/app/scripts/init_navigation_data.py` 中的 `DEFAULT_NAVIGATION_ITEMS`
4. **資料庫導覽**：`/api/site-management/navigation` API 回應

## 執行步驟

### 步驟 1：提取前端路由定義

讀取 `frontend/src/router/types.ts`，提取所有 ROUTES 常數中的路徑值。

```bash
grep -E "^\s+[A-Z_]+:\s*['\"]" frontend/src/router/types.ts
```

### 步驟 2：提取後端導覽定義

讀取 `backend/app/scripts/init_navigation_data.py`，提取 `DEFAULT_NAVIGATION_ITEMS` 中所有 `path` 值。

```bash
grep -E '"path":\s*"[^"]*"' backend/app/scripts/init_navigation_data.py | grep -oE '"/[^"]*"'
```

### 步驟 3：查詢資料庫導覽

```bash
curl -s "http://localhost:8001/api/site-management/navigation" | jq '.items[].path, .items[].children[].path'
```

### 步驟 4：比對分析

對比三個來源的路由，找出：
- 前端有但後端沒有的路由
- 後端有但前端沒有的路由
- 路徑名稱不一致的項目

## 常見問題類型

| 問題類型 | 說明 | 解決方式 |
|---------|------|---------|
| 前端新增路由 | 新功能只在前端定義 | 同步到 `init_navigation_data.py` |
| 後端遺漏項目 | 初始化腳本編寫時遺漏 | 補充到 `DEFAULT_NAVIGATION_ITEMS` |
| 路徑重構 | 路由架構調整未同步 | 統一使用新路徑 |
| 欄位名稱錯誤 | 模型欄位與腳本不匹配 | 對照模型定義修正 |

## 修正流程

1. 修改 `backend/app/scripts/init_navigation_data.py`
2. 通過網站管理頁面更新現有導覽項目
3. 或執行資料庫遷移腳本

## 預防機制

### 自動化驗證（新增 2026-01-12）

1. **後端 API 驗證**：導覽項目的 `create` 和 `update` 操作會自動驗證路徑
2. **前端下拉選單**：SiteManagementPage 使用下拉選單，防止輸入無效路徑
3. **PowerShell 檢查腳本**：`.claude/hooks/route-sync-check.ps1`

### 開發流程

- 新增前端路由時，同步更新 `navigation_validator.py` 的白名單
- 新增後端導覽時，確保路徑在前端 ROUTES 中有定義
- 在 PR 審查時執行 `/route-sync-check`
- 使用 `init_navigation_data.py --force-update` 同步資料庫

## 相關文件

| 文件 | 說明 |
|------|------|
| `frontend/src/router/types.ts` | 前端路由定義 |
| `frontend/src/router/AppRouter.tsx` | 前端路由實作 |
| `backend/app/core/navigation_validator.py` | 後端路徑白名單驗證器 |
| `backend/app/scripts/init_navigation_data.py` | 後端導覽初始化腳本 |
| `backend/app/api/endpoints/secure_site_management.py` | 導覽 API（含驗證） |
| `.claude/hooks/route-sync-check.ps1` | PowerShell 同步檢查腳本 |
