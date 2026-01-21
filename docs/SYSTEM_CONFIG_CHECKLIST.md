# 🎯 乾坤測繪公文管理系統 - 系統設定檢核清單

## 📋 基於 UNIFIED_CONFIG_GUIDE.md 的全面檢核

---

## 🔍 **第一部分：配置檔案完整性檢查**

### ✅ 必要檔案檢查
- [ ] `.env` - 主環境配置檔案存在
- [ ] `.env.master` - 主配置範本檔案存在
- [ ] `.env.production` - 生產環境配置存在
- [ ] `docker-compose.unified.yml` - 統一Docker配置存在
- [ ] `docker-compose.dev.yml` - 開發環境配置存在
- [ ] `port-config.json` - 端口配置檔案存在
- [ ] `backend/Dockerfile.unified` - 後端統一映像存在
- [ ] `frontend/Dockerfile.unified` - 前端統一映像存在
- [ ] `setup.sh` - 部署腳本存在
- [ ] `setup-config.ps1` - Windows配置腳本存在

### ✅ 開發工具檔案檢查
- [ ] `dev-start.sh` - Linux/Mac開發啟動腳本
- [ ] `dev-start.ps1` - Windows開發啟動腳本
- [ ] `dev-monitor.py` - 開發環境監控工具
- [ ] `dev-sync.sh` - 開發同步工具
- [ ] `system-config-test.py` - 系統配置測試工具
- [ ] `config-check.py` - 簡化配置檢查工具
- [ ] `env-switch-test.py` - 環境切換測試工具

---

## 🔧 **第二部分：環境變數配置檢查**

### ✅ 核心專案設定
- [ ] `COMPOSE_PROJECT_NAME=ck_missive`
- [ ] `PROJECT_VERSION=3.1`
- [ ] `ENVIRONMENT=development/production`
- [ ] `NODE_ENV=development/production`

### ✅ 服務端口配置
- [ ] `FRONTEND_HOST_PORT=3000`
- [ ] `BACKEND_HOST_PORT=8001`
- [ ] `POSTGRES_HOST_PORT=5434`
- [ ] `ADMINER_HOST_PORT=8080`
- [ ] `REDIS_HOST_PORT=6380`

### ✅ 資料庫配置
- [ ] `POSTGRES_USER=ck_user`
- [ ] `POSTGRES_PASSWORD` 已設定（生產環境須修改預設值）
- [ ] `POSTGRES_DB=ck_documents`
- [ ] `DATABASE_URL` 格式正確
- [ ] `REDIS_URL` 格式正確

### ✅ API 與 CORS 設定
- [ ] `VITE_API_BASE_URL=http://localhost:8001`
- [ ] `CORS_ORIGINS` 包含所需域名
- [ ] `SECRET_KEY` 已設定（生產環境須修改預設值）

### ✅ 安全設定
- [ ] `DEBUG=false`（生產環境）/ `DEBUG=true`（開發環境）
- [ ] `AUTH_DISABLED=false`（生產環境）
- [ ] Google OAuth 設定正確

---

## 🐳 **第三部分：Docker 配置檢查**

### ✅ Docker Compose 語法檢查
```bash
# 執行命令檢查語法
docker-compose -f docker-compose.unified.yml config
docker-compose -f docker-compose.dev.yml config
```

- [ ] `docker-compose.unified.yml` 語法正確
- [ ] `docker-compose.dev.yml` 語法正確
- [ ] 服務依賴關係正確配置
- [ ] 健康檢查配置正確
- [ ] 網路配置正確

### ✅ Dockerfile 檢查
- [ ] `backend/Dockerfile.unified` 多階段建置正確
- [ ] `frontend/Dockerfile.unified` 包含 Nginx 配置
- [ ] `backend/Dockerfile.dev` 開發環境配置正確
- [ ] `frontend/Dockerfile.dev` 支援熱重載
- [ ] 所有 Dockerfile 包含健康檢查

### ✅ Volume 和網路配置
- [ ] 持久化儲存配置正確
- [ ] 開發環境程式碼掛載配置
- [ ] 自定義網路配置
- [ ] 容器間通訊配置

---

## 🌐 **第四部分：服務連通性檢查**

### ✅ 端口可用性檢查
```bash
# 執行檢查命令
python config-check.py
```

- [ ] 前端服務：http://localhost:3000
- [ ] 後端API：http://localhost:8001
- [ ] API文檔：http://localhost:8001/api/docs
- [ ] 資料庫管理：http://localhost:8080
- [ ] 資料庫連接：localhost:5434

### ✅ 健康檢查端點
- [ ] `/health` - 後端健康檢查
- [ ] `/api/docs` - API 文檔可訪問
- [ ] Nginx 健康檢查正常

---

## 🔄 **第五部分：環境切換測試**

### ✅ 開發環境測試
```bash
# 測試開發環境
python env-switch-test.py dev
./dev-start.sh  # 或 .\dev-start.ps1
```

- [ ] 開發環境配置載入正確
- [ ] 熱重載功能正常
- [ ] 程式碼同步正常
- [ ] 開發工具可用

### ✅ 生產環境測試
```bash
# 測試生產環境
python env-switch-test.py prod
docker-compose -f docker-compose.unified.yml up --build
```

- [ ] 生產環境配置載入正確
- [ ] 安全設定已調整
- [ ] 效能最佳化啟用
- [ ] 除錯模式已關閉

---

## 🛠️ **第六部分：開發工具功能測試**

### ✅ 監控工具測試
```bash
python dev-monitor.py
python dev-monitor.py watch
```

- [ ] 容器狀態監控正常
- [ ] HTTP 服務檢查正常
- [ ] 資源使用監控正常
- [ ] 檔案同步狀態正常

### ✅ 同步工具測試
```bash
./dev-sync.sh backend
./dev-sync.sh frontend
./dev-sync.sh logs
```

- [ ] 服務重啟功能正常
- [ ] 日誌查看功能正常
- [ ] 容器 shell 進入正常

---

## 🔒 **第七部分：安全配置檢查**

### ✅ 開發環境安全檢查
- [ ] 預設密碼可接受（開發環境）
- [ ] 除錯模式啟用（開發環境）
- [ ] 認證可選擇性停用

### ✅ 生產環境安全檢查
- [ ] `SECRET_KEY` 非預設值
- [ ] `POSTGRES_PASSWORD` 非預設值
- [ ] `DEBUG=false`
- [ ] `AUTH_DISABLED=false`
- [ ] HTTPS 配置（如適用）
- [ ] 防火牆規則配置

---

## 📊 **第八部分：效能與最佳化檢查**

### ✅ 容器最佳化
- [ ] 多階段建置減少映像大小
- [ ] 非 root 使用者執行
- [ ] 健康檢查配置適當
- [ ] 資源限制設定

### ✅ 網路最佳化
- [ ] Nginx gzip 壓縮啟用
- [ ] 靜態資源快取設定
- [ ] API 代理配置正確

---

## 🚀 **第九部分：部署流程驗證**

### ✅ 一鍵部署測試
```bash
# Linux/Mac
./setup.sh

# Windows
powershell -ExecutionPolicy Bypass -File setup-config.ps1
```

- [ ] 配置自動同步
- [ ] 依賴檢查通過
- [ ] 服務啟動成功
- [ ] 健康檢查通過

### ✅ 部署後驗證
```bash
python quick_health_check.py
curl http://localhost:8001/health
curl http://localhost:3000
```

- [ ] 所有服務正常運行
- [ ] API 回應正常
- [ ] 前端載入正常
- [ ] 資料庫連接正常

---

## 📋 **第十部分：文檔與維護**

### ✅ 文檔完整性
- [ ] `UNIFIED_CONFIG_GUIDE.md` 更新
- [ ] `DEVELOPMENT_GUIDE.md` 完整
- [ ] `README.md` 包含快速開始
- [ ] API 文檔自動生成

### ✅ 維護腳本
- [ ] 定期清理腳本
- [ ] 備份恢復腳本
- [ ] 日誌輪轉配置
- [ ] 監控告警設定

---

## 🎯 **執行檢核的建議順序**

1. **基礎檢查** → 執行 `python config-check.py`
2. **完整測試** → 執行 `python system-config-test.py`
3. **環境切換** → 執行 `python env-switch-test.py`
4. **服務測試** → 執行 `python quick_health_check.py`
5. **開發測試** → 執行 `./dev-start.sh` 或 `.\dev-start.ps1`
6. **監控測試** → 執行 `python dev-monitor.py watch`

## 🚨 **常見問題解決**

### 配置不同步
```bash
# 重新同步配置
copy .env.master .env  # Windows
cp .env.master .env    # Linux/Mac
```

### 端口衝突
```bash
# 使用端口管理工具
.\scripts\port-manager.ps1 -Action kill -Service all
```

### 容器問題
```bash
# 完全重置
docker-compose -f docker-compose.unified.yml down --volumes
docker system prune -f
```

---

## ✅ **檢核完成確認**

完成所有檢查項目後，確認：

- [ ] 所有必要檔案存在且正確
- [ ] 環境變數配置完整
- [ ] Docker 配置語法正確
- [ ] 服務可正常啟動和連通
- [ ] 開發和生產環境可正常切換
- [ ] 安全設定符合環境要求
- [ ] 效能最佳化已實施
- [ ] 部署流程可順利執行
- [ ] 監控和維護工具正常運作

**🎉 當所有項目都勾選完成時，系統配置即達到生產就緒狀態！**