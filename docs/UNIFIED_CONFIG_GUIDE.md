# 🎯 乾坤測繪公文管理系統 - 統一配置管理指南

## 🚨 問題解決方案

之前的**17個環境變數檔案**已經被統一為**單一配置源**！

## 📁 新的配置架構

```
CK_Missive/
├── .env.master                    # ✅ 主配置檔案 (Single Source of Truth)
├── .env                          # ✅ 當前環境配置 (自動同步)
├── docker-compose.unified.yml    # ✅ 統一 Docker 編排
├── setup-config.ps1             # ✅ 配置管理腳本
├── setup.sh                     # ✅ 一鍵部署腳本
├── backend/
│   └── Dockerfile.unified       # ✅ 統一後端容器
└── frontend/
    ├── Dockerfile.unified       # ✅ 統一前端容器
    └── nginx.conf               # ✅ Nginx 配置
```

## 🔧 快速開始

### 1. 配置設定
```bash
# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File setup-config.ps1

# Linux/Mac
chmod +x setup.sh && ./setup.sh
```

### 2. 啟動系統
```bash
# 使用統一配置啟動
docker-compose -f docker-compose.unified.yml up --build -d
```

### 3. 驗證部署
```bash
# 檢查服務狀態
docker-compose -f docker-compose.unified.yml ps

# 檢查健康狀態
curl http://localhost:8001/health  # 後端
curl http://localhost:3000         # 前端
```

## 🎯 核心改進

### ✅ 解決的問題
- ❌ **17個環境變數檔案** → ✅ **1個主配置檔案**
- ❌ **4個Dockerfile** → ✅ **2個統一Dockerfile**
- ❌ **配置不同步** → ✅ **自動同步機制**
- ❌ **重複依賴問題** → ✅ **統一依賴管理**
- ❌ **部署複雜** → ✅ **一鍵部署**

### 🔧 統一配置管理
```bash
# 主配置檔案位置
.env.master    # 所有配置的單一來源

# 自動同步命令
setup-config.ps1    # Windows
setup.sh             # Linux/Mac
```

## 📋 配置檔案說明

### `.env.master` - 主配置檔案
```bash
# 專案基本資訊
COMPOSE_PROJECT_NAME=ck_missive
PROJECT_VERSION=3.1
ENVIRONMENT=development

# 服務端口配置
FRONTEND_HOST_PORT=3000
BACKEND_HOST_PORT=8001
POSTGRES_HOST_PORT=5434
ADMINER_HOST_PORT=8080

# 資料庫配置
POSTGRES_USER=ck_user
POSTGRES_PASSWORD=ck_password_2024
POSTGRES_DB=ck_documents
DATABASE_URL=postgresql://ck_user:ck_password_2024@localhost:5434/ck_documents

# 安全設定
SECRET_KEY=your_super_secret_key_here_change_in_production
DEBUG=true
AUTH_DISABLED=false

# API 設定
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
VITE_API_BASE_URL=http://localhost:8001
```

## 🐳 Docker 服務編排

### `docker-compose.unified.yml`
- **postgres**: PostgreSQL 15 資料庫
- **redis**: Redis 快取服務
- **backend**: FastAPI 應用程式
- **frontend**: React + Nginx 應用程式
- **adminer**: 資料庫管理介面

### 健康檢查
所有服務都配置了健康檢查：
- 資料庫連接檢查
- API 端點檢查
- 前端服務檢查

## 🚀 常用命令

### 開發命令
```bash
# 啟動開發環境
docker-compose -f docker-compose.unified.yml up --build

# 查看日誌
docker-compose -f docker-compose.unified.yml logs -f

# 停止服務
docker-compose -f docker-compose.unified.yml down

# 完全重建
docker-compose -f docker-compose.unified.yml down --volumes --remove-orphans
docker-compose -f docker-compose.unified.yml up --build --force-recreate
```

### 維護命令
```bash
# 更新配置
powershell -ExecutionPolicy Bypass -File setup-config.ps1

# 清理系統
docker system prune -af
docker volume prune -f
```

## 🌐 訪問端點

| 服務 | 網址 | 說明 |
|------|------|------|
| 前端應用 | http://localhost:3000 | React 應用程式 |
| 後端 API | http://localhost:8001 | FastAPI 服務 |
| API 文件 | http://localhost:8001/api/docs | Swagger UI |
| 資料庫管理 | http://localhost:8080 | Adminer |

## ⚠️ 生產環境注意事項

### 必須修改的設定
```bash
# 安全設定
SECRET_KEY=generate_strong_random_key_here
POSTGRES_PASSWORD=strong_database_password
DEBUG=false
AUTH_DISABLED=false

# 網域設定
CORS_ORIGINS=https://yourdomain.com
VITE_API_BASE_URL=https://api.yourdomain.com
```

### 部署檢查清單
- [ ] 修改預設密碼
- [ ] 設定強密鑰
- [ ] 關閉除錯模式
- [ ] 啟用認證機制
- [ ] 配置 HTTPS
- [ ] 設定防火牆規則
- [ ] 備份策略

## 🔍 故障排除

### 常見問題
1. **端口衝突**: 檢查 `.env` 中的端口設定
2. **權限問題**: 確保 Docker 有足夠權限
3. **資料庫連接失敗**: 檢查 PostgreSQL 容器狀態
4. **前端無法訪問**: 檢查 Nginx 配置和容器狀態

### 日誌檢查
```bash
# 查看特定服務日誌
docker-compose -f docker-compose.unified.yml logs backend
docker-compose -f docker-compose.unified.yml logs frontend
docker-compose -f docker-compose.unified.yml logs postgres

# 查看容器狀態
docker-compose -f docker-compose.unified.yml ps -a
```

## 🎉 總結

這個統一配置管理系統解決了以下核心問題：

1. **配置一致性**: 單一配置源確保所有服務使用相同設定
2. **部署簡化**: 一鍵部署腳本自動化整個過程
3. **依賴管理**: 統一的 Dockerfile 和依賴定義
4. **錯誤減少**: 消除了配置不同步導致的錯誤
5. **維護效率**: 大幅簡化了系統維護工作

**不再有17個環境變數檔案的混亂！** 🎯