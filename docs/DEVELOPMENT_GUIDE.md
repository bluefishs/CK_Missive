# 🔧 乾坤測繪公文管理系統 - 開發環境指南

> 狀態：現行｜最後核對：2026-09-08

## 🚀 快速開始

### Windows 用戶
```powershell
# 啟動開發環境
.\dev-start.ps1

# 查看狀態
.\dev-start.ps1 -Status

# 停止環境
.\dev-start.ps1 -Stop
```

### Linux/Mac 用戶
```bash
# 啟動開發環境
./dev-start.sh

# 監控環境狀態
python dev-monitor.py watch

# 同步工具
./dev-sync.sh backend  # 重啟後端
```

## 🎯 解決 Docker 同步問題

### 問題描述
- **容器化程式碼不即時更新** - 需要重新建置才能看到變更
- **開發效率低下** - 每次修改都要等待重建
- **缺乏熱重載機制** - 無法即時反映程式碼變更

### 解決方案
我們建立了完整的開發環境解決方案：

#### 1. 開發專用配置
- **docker-compose.dev.yml** - 開發環境專用配置
- **backend/Dockerfile.dev** - 後端開發映像
- **frontend/Dockerfile.dev** - 前端開發映像

#### 2. 熱重載機制
```yaml
# 後端熱重載
volumes:
  - ./backend:/app  # 即時同步程式碼
command: uvicorn main:app --reload  # 自動重載

# 前端熱重載
volumes:
  - ./frontend:/app  # 即時同步程式碼
command: npm run dev  # Vite HMR 熱更新
```

#### 3. 環境分離
- **開發環境**: `docker-compose.dev.yml` (熱重載、即時同步)
- **生產環境**: `docker-compose.unified.yml` (最佳化、安全)

## 📊 開發環境特色

### ✅ 即時程式碼同步
- 本地程式碼直接掛載到容器
- 修改後立即反映，無需重建
- 排除不必要的目錄 (node_modules, __pycache__)

### ✅ 熱重載支援
- **後端**: uvicorn --reload 自動重啟
- **前端**: Vite HMR 熱模組替換
- **配置**: 環境變數即時生效

### ✅ 獨立開發資料
- 開發環境使用獨立的資料庫
- 不影響生產資料
- 可以隨時重置開發資料

### ✅ 完整監控工具
- 服務狀態監控
- 容器資源使用監控
- HTTP 端點健康檢查
- 檔案同步狀態檢查

## 🛠️ 開發工具使用

### 1. 環境管理
```bash
# Windows
.\dev-start.ps1              # 啟動開發環境
.\dev-start.ps1 -Clean       # 清理後啟動
.\dev-start.ps1 -Rebuild     # 重建後啟動
.\dev-start.ps1 -Stop        # 停止開發環境
.\dev-start.ps1 -Status      # 查看狀態
.\dev-start.ps1 -Logs        # 查看日誌

# Linux/Mac
./dev-start.sh               # 啟動開發環境
```

### 2. 監控工具
```bash
python dev-monitor.py        # 單次狀態檢查
python dev-monitor.py watch  # 持續監控模式
python dev-monitor.py docker # 只檢查 Docker
python dev-monitor.py http   # 只檢查 HTTP 服務
```

### 3. 同步工具
```bash
./dev-sync.sh backend        # 重啟後端服務
./dev-sync.sh frontend       # 重啟前端服務
./dev-sync.sh all           # 重啟所有服務
./dev-sync.sh logs backend  # 查看後端日誌
./dev-sync.sh shell backend # 進入後端容器
./dev-sync.sh install       # 安裝新依賴後重建
./dev-sync.sh reset         # 重置開發環境
```

## 🎛️ 服務訪問地址

### 開發環境
- **前端開發伺服器**: http://localhost:3000 (Vite HMR)
- **後端開發 API**: http://localhost:8001 (熱重載)
- **API 開發文檔**: http://localhost:8001/api/docs
- **資料庫管理**: 無獨立介面（`docker exec ck_missive_postgres psql -U ck_user -d ck_documents`；Adminer 8080 已於 2026-05 退場）
- **開發資料庫**: localhost:5434

### 生產環境
- **前端應用**: http://localhost:3000 (Nginx)
- **後端 API**: http://localhost:8001
- **API 文檔**: http://localhost:8001/api/docs
- **資料庫**: localhost:5434

## 🔄 開發工作流程

### 日常開發
1. **啟動開發環境**
   ```bash
   ./dev-start.sh  # 或 .\dev-start.ps1
   ```

2. **開始編碼**
   - 修改 `backend/` 中的 Python 程式碼 → 自動重載
   - 修改 `frontend/src/` 中的 React 程式碼 → HMR 熱更新

3. **監控狀態**
   ```bash
   python dev-monitor.py watch
   ```

4. **除錯工具**
   ```bash
   ./dev-sync.sh logs backend    # 查看後端日誌
   ./dev-sync.sh shell backend   # 進入後端容器除錯
   ```

### 新依賴安裝
1. **後端依賴**
   ```bash
   # 在本地修改 requirements.txt
   ./dev-sync.sh install  # 重建容器
   ```

2. **前端依賴**
   ```bash
   # 在本地修改 package.json
   ./dev-sync.sh install  # 重建容器
   ```

### 環境重置
```bash
./dev-sync.sh reset  # 完全重置開發環境
```

## 🚨 常見問題解決

### 問題 1: 程式碼修改後沒有反映
**解決方案:**
```bash
# 檢查容器是否正常運行
docker-compose -f docker-compose.dev.yml ps

# 重啟相關服務
./dev-sync.sh backend  # 或 frontend
```

### 問題 2: 端口佔用
**解決方案:**
```bash
# 使用端口管理工具
./scripts/port-manager.ps1 -Action kill -Service all
```

### 問題 3: 容器資源不足
**解決方案:**
```bash
# 查看資源使用
python dev-monitor.py

# 清理不用的容器和映像
docker system prune -f
```

### 問題 4: 熱重載不工作
**檢查清單:**
- ✅ 使用開發配置檔案 `docker-compose.dev.yml`
- ✅ volume 正確掛載本地程式碼目錄
- ✅ 啟動命令包含 `--reload` 或開發模式
- ✅ 沒有語法錯誤阻止重載

## 📈 效能最佳化建議

### 1. Volume 最佳化
- 排除不必要的目錄同步
- 使用 .dockerignore 檔案
- 考慮使用 bind mounts 替代 volumes

### 2. 記憶體管理
- 定期清理未使用的映像
- 監控容器記憶體使用
- 調整 Docker Desktop 記憶體限制

### 3. 網路最佳化
- 使用自定義網路
- 最小化不必要的端口暴露
- 利用 Docker 內部 DNS

## 🔒 安全注意事項

### 開發環境安全
- ⚠️ 開發環境禁用了部分安全檢查
- ⚠️ 開發資料庫使用簡單密碼
- ⚠️ 調試模式可能暴露敏感資訊

### 生產部署前檢查
- ✅ 切換到生產配置 `docker-compose.unified.yml`
- ✅ 修改所有預設密碼
- ✅ 關閉調試模式 `DEBUG=false`
- ✅ 啟用認證 `AUTH_DISABLED=false`

## 📚 相關文檔

- [專案架構](../.claude/rules/architecture.md)（2025 規劃版 `PROJECT_STRUCTURE_STANDARD.md` 已作廢）
- [API 文檔](http://localhost:8001/api/docs)
- [Docker 官方文檔](https://docs.docker.com/)
- [Vite 文檔](https://vitejs.dev/)
- [FastAPI 文檔](https://fastapi.tiangolo.com/)

---

**🎉 現在你可以享受高效的 Docker 開發體驗！**

修改程式碼 → 自動同步 → 即時重載 → 立即看到結果 ✨