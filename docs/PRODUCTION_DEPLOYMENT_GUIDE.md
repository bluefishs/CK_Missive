# 🚀 乾坤測繪公文管理系統 - 生產環境部署指南

## 📋 部署前檢查清單

### 1. 🔐 安全設定 (必須完成)

```bash
# 複製生產環境配置
cp .env.production .env

# ⚠️ 立即修改以下關鍵設定：
# 1. 資料庫密碼
POSTGRES_PASSWORD=您的強密碼

# 2. 應用程式密鑰 (32字符以上)
SECRET_KEY=您的超級安全密鑰

# 3. 域名設定
CORS_ORIGINS=https://您的域名.com
VITE_API_BASE_URL=https://api.您的域名.com

# 4. Google OAuth (生產環境憑證)
GOOGLE_CLIENT_ID=您的生產環境GoogleClientID
GOOGLE_CLIENT_SECRET=您的生產環境Secret
```

### 2. 🛡️ 安全檢查

確認以下設定正確：
- ✅ `DEBUG=false`
- ✅ `AUTH_DISABLED=false`
- ✅ `LOG_LEVEL=WARNING`
- ✅ `HTTPS_ONLY=true`
- ✅ `SECURE_COOKIES=true`

### 3. 🗄️ 資料庫準備

```bash
# 備份開發資料庫 (如需要)
docker exec ck_missive_postgres pg_dump -U ck_user ck_documents > backup.sql

# 清理並重建生產資料庫
docker-compose -f docker-compose.unified.yml down -v
```

## 🚀 部署步驟

### 步驟 1: 環境準備

```bash
# 1. 確保 Docker 和 Docker Compose 已安裝
docker --version
docker-compose --version

# 2. 複製生產配置
cp .env.production .env

# 3. 修改配置檔案中的敏感資訊
# 編輯 .env 檔案，修改所有標記為 ⚠️ 的項目
```

### 步驟 2: 建置部署

```bash
# 1. 建置並啟動生產環境
docker-compose -f docker-compose.unified.yml up --build -d

# 2. 檢查服務狀態
docker-compose -f docker-compose.unified.yml ps

# 3. 查看日誌 (如有問題)
docker-compose -f docker-compose.unified.yml logs
```

### 步驟 3: 健康檢查

```bash
# 執行系統健康檢查
python quick_health_check.py

# 檢查各項服務
curl https://您的域名.com/health
curl https://api.您的域名.com/health
```

## 🔧 維護指令

### 日常維護

```bash
# 查看系統狀態
docker-compose -f docker-compose.unified.yml ps

# 查看日誌
docker-compose -f docker-compose.unified.yml logs -f backend
docker-compose -f docker-compose.unified.yml logs -f frontend

# 重啟服務
docker-compose -f docker-compose.unified.yml restart backend
```

### 資料備份

```bash
# 備份資料庫
docker exec ck_missive_postgres pg_dump -U ck_user ck_documents > backup_$(date +%Y%m%d_%H%M%S).sql

# 備份上傳檔案
tar -czf uploads_backup_$(date +%Y%m%d_%H%M%S).tar.gz backend/uploads/
```

### 更新部署

```bash
# 1. 拉取最新代碼
git pull origin main

# 2. 重新建置並部署
docker-compose -f docker-compose.unified.yml up --build -d

# 3. 確認服務正常
python quick_health_check.py
```

## 🚨 故障排除

### 常見問題

1. **資料庫連接失敗**
   ```bash
   # 檢查資料庫狀態
   docker exec ck_missive_postgres pg_isready -U ck_user

   # 檢查密碼設定
   grep POSTGRES_PASSWORD .env
   ```

2. **前端無法載入**
   ```bash
   # 檢查前端建置
   docker exec ck_missive_frontend ls -la /usr/share/nginx/html/

   # 檢查 Nginx 配置
   docker exec ck_missive_frontend nginx -t
   ```

3. **API 無法訪問**
   ```bash
   # 檢查後端狀態
   curl http://localhost:8000/health

   # 檢查 CORS 設定
   grep CORS_ORIGINS .env
   ```

### 緊急恢復

```bash
# 快速回滾到上一版本
docker-compose -f docker-compose.unified.yml down
git checkout HEAD~1
docker-compose -f docker-compose.unified.yml up -d

# 恢復資料庫備份
docker exec -i ck_missive_postgres psql -U ck_user ck_documents < backup.sql
```

## 📊 監控建議

### 系統監控

1. **定期健康檢查**
   ```bash
   # 每5分鐘執行一次
   */5 * * * * /path/to/quick_health_check.py
   ```

2. **日誌監控**
   ```bash
   # 監控錯誤日誌
   tail -f backend/logs/errors.log
   ```

3. **效能監控**
   ```bash
   # 檢查容器資源使用
   docker stats
   ```

### 安全監控

1. **定期更新**
   - 定期更新 Docker 映像
   - 定期更新依賴套件
   - 定期檢查安全漏洞

2. **存取日誌**
   - 監控異常登入嘗試
   - 檢查 API 呼叫模式
   - 監控檔案上傳活動

## 📞 支援資訊

### 聯絡資訊
- 技術支援: [您的技術支援聯絡方式]
- 緊急聯絡: [緊急聯絡方式]

### 文件資源
- 系統架構: `UNIFIED_CONFIG_GUIDE.md`
- API 文件: `http://您的域名.com/api/docs`
- 使用手冊: [使用手冊連結]

---

🎯 **記住**: 生產環境的安全性和穩定性是最重要的。任何變更都應該在測試環境中先行驗證。