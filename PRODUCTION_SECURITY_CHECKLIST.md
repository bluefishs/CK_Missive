# 🔒 乾坤測繪公文管理系統 - 生產環境安全檢核清單

## 📋 基於安全檢查工具的完整檢核

---

## 🚨 **關鍵安全問題修正** (必須完成)

### ✅ **密鑰和密碼安全**
- [ ] **SECRET_KEY** - 更換預設值 `your_super_secret_key_here_change_in_production`
  ```bash
  # 使用安全工具產生
  python security-config-check.py --create-production
  ```
- [ ] **POSTGRES_PASSWORD** - 更換預設值 `ck_password_2024`
- [ ] **GOOGLE_CLIENT_SECRET** - 更換預設值 `your_google_client_secret`
- [ ] 所有密鑰長度至少 16 字符
- [ ] 使用隨機產生的強密碼，包含大小寫字母、數字和特殊字符

### ✅ **除錯和開發設定**
- [ ] `DEBUG=false` (當前: true)
- [ ] `AUTH_DISABLED=false` (當前: true)
- [ ] `DATABASE_ECHO=false` ✅ (已正確)
- [ ] `LOG_LEVEL=WARNING` 或 `ERROR` (當前: INFO)

### ✅ **環境標識**
- [ ] `ENVIRONMENT=production` (當前: development)
- [ ] `NODE_ENV=production` (當前: development)

---

## 🌐 **網路和 CORS 安全**

### ✅ **CORS 配置**
- [ ] 移除開發環境地址: `localhost`, `127.0.0.1`
- [ ] 只包含實際生產域名
- [ ] 範例：`CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com`

### ✅ **API 端點配置**
- [ ] `VITE_API_BASE_URL` 使用 HTTPS 和實際域名
- [ ] 移除所有 localhost 參考
- [ ] 確保 API 端點使用 SSL/TLS

---

## 🗄️ **資料庫安全**

### ✅ **連接安全**
- [ ] `DATABASE_URL` 使用實際資料庫主機 (非 localhost)
- [ ] 使用加密連接 (SSL)
- [ ] 資料庫使用者權限最小化
- [ ] 定期備份策略已建立

### ✅ **PostgreSQL 安全設定**
- [ ] 資料庫密碼複雜度足夠 (至少 12 字符)
- [ ] 啟用連接加密
- [ ] 限制資料庫訪問 IP
- [ ] 定期更新資料庫軟體

---

## 🐳 **Docker 容器安全**

### ✅ **容器權限**
- [ ] 後端容器使用非 root 使用者 ✅
- [ ] 前端容器使用非 root 使用者 ⚠️ (需檢查)
- [ ] 移除不必要的特權
- [ ] 使用最小權限原則

### ✅ **映像安全**
- [ ] 使用官方基礎映像
- [ ] 定期更新基礎映像
- [ ] 掃描安全漏洞
- [ ] 移除不必要的套件

### ✅ **網路隔離**
- [ ] 使用自定義網路
- [ ] 限制不必要的端口暴露
- [ ] 容器間通訊加密

---

## 🔐 **SSL/TLS 和 HTTPS**

### ✅ **憑證配置**
- [ ] 獲得有效的 SSL 憑證
- [ ] 配置 HTTPS 重定向
- [ ] 使用 TLS 1.2 或更高版本
- [ ] 配置安全的密碼套件

### ✅ **Nginx 安全配置**
- [ ] 啟用 HSTS (HTTP Strict Transport Security)
- [ ] 設定安全標頭
  ```nginx
  add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
  add_header X-Content-Type-Options "nosniff" always;
  add_header X-Frame-Options "SAMEORIGIN" always;
  add_header X-XSS-Protection "1; mode=block" always;
  ```

---

## 🔒 **OAuth 和認證安全**

### ✅ **Google OAuth 設定**
- [ ] 使用實際的 Google Client ID 和 Secret
- [ ] 配置正確的重定向 URI
- [ ] 限制 OAuth 範圍
- [ ] 啟用 2FA (如適用)

### ✅ **JWT 安全**
- [ ] 使用強密鑰簽名
- [ ] 設定適當的過期時間
- [ ] 實施 token 刷新機制
- [ ] 保護敏感端點

---

## 📊 **監控和日誌**

### ✅ **安全監控**
- [ ] 啟用訪問日誌
- [ ] 監控異常登入
- [ ] 設定安全告警
- [ ] 定期安全掃描

### ✅ **日誌管理**
- [ ] 不記錄敏感資訊 (密碼、token)
- [ ] 設定日誌輪轉
- [ ] 集中化日誌管理
- [ ] 定期檢查安全事件

---

## 🚀 **部署安全**

### ✅ **環境隔離**
- [ ] 生產環境獨立部署
- [ ] 限制生產環境訪問
- [ ] 使用跳板機 (Bastion Host)
- [ ] 實施變更管控

### ✅ **備份和恢復**
- [ ] 定期自動備份
- [ ] 測試恢復程序
- [ ] 異地備份存儲
- [ ] 災難恢復計劃

---

## 📋 **自動化安全檢查**

### ✅ **使用安全檢查工具**
```bash
# 執行完整安全檢查
python security-config-check.py

# 創建安全的生產環境配置
python security-config-check.py --create-production

# 檢查系統配置
python system-config-test.py security

# 監控系統狀態
python dev-monitor.py
```

### ✅ **持續安全監控**
- [ ] 設定自動化安全掃描
- [ ] 定期執行安全檢查
- [ ] 監控依賴漏洞
- [ ] 更新安全補丁

---

## 🔧 **生產環境部署步驟**

### 1. **配置準備**
```bash
# 1. 使用安全配置
cp .env.production.secure .env

# 2. 修改域名和實際配置
# 編輯 .env 檔案，設定實際的：
# - 域名
# - 資料庫主機
# - SSL 憑證路徑
```

### 2. **安全驗證**
```bash
# 3. 執行安全檢查
python security-config-check.py

# 4. 確認所有 CRITICAL 和 HIGH 問題已解決
```

### 3. **部署執行**
```bash
# 5. 使用生產配置部署
docker-compose -f docker-compose.unified.yml up --build -d

# 6. 驗證部署
python quick_health_check.py
```

---

## ⚠️ **生產環境注意事項**

### 🚫 **禁止事項**
- ❌ 在生產環境中使用預設密碼
- ❌ 啟用除錯模式
- ❌ 停用認證系統
- ❌ 暴露不必要的端口
- ❌ 使用 HTTP 而非 HTTPS
- ❌ 在日誌中記錄敏感資訊

### ✅ **必須事項**
- ✅ 使用強密碼和密鑰
- ✅ 啟用 HTTPS 和安全標頭
- ✅ 實施適當的訪問控制
- ✅ 定期備份和安全更新
- ✅ 監控和日誌記錄
- ✅ 災難恢復計劃

---

## 📊 **安全檢核報告範本**

### **檢核完成確認**
完成日期: ___________
檢核人員: ___________

**關鍵安全問題修正狀態：**
- [ ] 所有 CRITICAL 問題已解決
- [ ] 所有 HIGH 風險問題已解決
- [ ] MEDIUM 風險問題評估完成
- [ ] 生產環境配置已建立
- [ ] 安全測試已通過

**部署前最終確認：**
- [ ] 密鑰已更換為生產環境值
- [ ] 除錯模式已關閉
- [ ] HTTPS 配置已完成
- [ ] 監控和告警已設定
- [ ] 備份策略已實施

**簽名確認：**
技術負責人: ___________  日期: ___________
安全負責人: ___________  日期: ___________

---

## 🎯 **快速修正指令**

對於發現的主要問題，以下是快速修正指令：

```bash
# 1. 創建安全的生產配置
python security-config-check.py --create-production

# 2. 使用安全配置
cp .env.production.secure .env

# 3. 修改為實際生產環境值
# 編輯 .env 檔案中的域名和實際配置

# 4. 重新部署
docker-compose -f docker-compose.unified.yml down
docker-compose -f docker-compose.unified.yml up --build -d

# 5. 驗證安全性
python security-config-check.py
```

**🛡️ 記住：安全性是一個持續的過程，而不是一次性的任務！**