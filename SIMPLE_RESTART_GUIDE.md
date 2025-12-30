# 🔄 簡單重啟指南 - 避免複雜化

## 問題理解
您正確指出了複雜化的問題。為確保系統重啟後穩定運行，這裡提供**最簡單**的解決方案。

---

## 📋 **重啟後的 3 個簡單步驟**

### 1. **檔案檢查** (10秒)
```bash
# 確認關鍵檔案存在
dir .env
dir docker-compose.unified.yml
```

如果 `.env` 不存在：
```bash
copy .env.master .env
```

### 2. **啟動服務** (30秒)
```bash
docker-compose -f docker-compose.unified.yml up -d
```

### 3. **等待並測試** (1分鐘)
等待 1 分鐘，然後訪問：
- 前端：http://localhost:3000
- 後端：http://localhost:8001

---

## 🚀 **一鍵重啟腳本**

### Windows 用戶
雙擊執行：`simple-startup-check.bat`

### Linux/Mac 用戶
執行：`./simple-startup-check.sh`

---

## ⚠️ **如果遇到問題**

### 問題 1：容器無法啟動
```bash
# 重置 Docker
docker-compose -f docker-compose.unified.yml down
docker-compose -f docker-compose.unified.yml up -d
```

### 問題 2：端口被佔用
```bash
# Windows
netstat -ano | findstr ":3000"
netstat -ano | findstr ":8001"

# 結束佔用進程
taskkill /F /PID [PID號]
```

### 問題 3：配置檔案不同步
```bash
# 重新複製主配置
copy .env.master .env
```

---

## 🎯 **關鍵原則**

1. **保持簡單** - 不使用複雜的配置管理工具
2. **固定配置** - `.env.master` 作為主要配置源
3. **標準操作** - 使用標準 Docker Compose 命令
4. **快速恢復** - 問題時重新複製配置檔案

---

## 📝 **每次重啟的檢查清單**

- [ ] `.env` 檔案存在（如不存在，從 `.env.master` 複製）
- [ ] 執行 `docker-compose -f docker-compose.unified.yml up -d`
- [ ] 等待 1 分鐘
- [ ] 測試 http://localhost:3000 和 http://localhost:8001
- [ ] 如有問題，重新啟動 Docker 服務

---

## ✅ **避免的複雜化操作**

❌ **不要使用**：
- 複雜的配置檢查腳本
- 自動配置修改工具
- 檔案保護機制
- 複雜的健康檢查

✅ **只需要**：
- 簡單的檔案複製
- 標準的 Docker 命令
- 基本的連通性測試

---

## 💡 **最重要的提醒**

**如果一切正常運行，就不要改變任何配置！**

**簡單勝過複雜 - 保持現有的穩定配置不變。**