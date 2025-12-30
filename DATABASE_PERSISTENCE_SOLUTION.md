# 🗄️ 資料庫持久化問題解決方案

## ❌ **問題根本原因**

每次檢視資料庫都是空的，是因為：

1. **使用了 `docker-compose down --volumes`**
   - 這個命令會**刪除所有 Volume 資料**
   - 包括資料庫的所有資料

2. **沒有自動初始化機制**
   - 即使 Volume 保留，新容器可能沒有初始資料

## ✅ **解決方案**

### 🎯 **立即解決**

**使用新的啟動腳本（自動檢查資料庫）：**

```bash
# Windows
start-with-db-check.bat

# Linux/Mac
./start-with-db-check.sh
```

### 🔧 **長期解決**

1. **永遠不要使用 `--volumes` 參數**
   ```bash
   # ❌ 錯誤：會刪除資料庫
   docker-compose down --volumes

   # ✅ 正確：保留資料庫
   docker-compose down
   ```

2. **使用資料庫自動初始化**
   ```bash
   python database-auto-init.py
   ```

## 📋 **啟動流程**

### 方法一：使用自動檢查腳本（推薦）
```bash
# Windows
start-with-db-check.bat

# Linux/Mac
./start-with-db-check.sh
```

### 方法二：手動啟動
```bash
# 1. 啟動服務（不要用 --volumes）
docker-compose -f configs/docker-compose.yml --env-file .env up -d

# 2. 等待 20 秒

# 3. 檢查並初始化資料庫
python database-auto-init.py
```

## 🛡️ **預防措施**

### ⚠️ **絕對避免的命令**
```bash
# 這些命令會刪除資料庫資料
docker-compose down --volumes
docker volume rm ck_missive_postgres_data
docker system prune -a --volumes
```

### ✅ **安全的重啟方式**
```bash
# 重啟服務（保留資料）
docker-compose restart

# 或停止後重新啟動
docker-compose down
docker-compose up -d
```

## 🔍 **故障排除**

### 檢查資料庫狀態
```bash
# 檢查表數量
docker exec ck_missive_postgres psql -U ck_user -d ck_documents -c "\dt"

# 檢查導航資料
docker exec ck_missive_postgres psql -U ck_user -d ck_documents -c "SELECT COUNT(*) FROM site_navigation_items;"
```

### 手動重新初始化
```bash
# 如果資料真的遺失了
python database-auto-init.py
```

## 💡 **核心原則**

1. **資料持久化**：永遠保留 Docker Volume
2. **自動檢查**：每次啟動都檢查資料庫狀態
3. **自動修復**：發現問題自動初始化

## 🎯 **最佳實踐**

### 日常使用
- 使用 `start-with-db-check.bat` 啟動系統
- 重啟用 `docker-compose restart`
- 停止用 `docker-compose down`（不加 --volumes）

### 開發測試
- 需要重置資料庫時才使用 `--volumes`
- 重置後必須執行 `database-auto-init.py`

**🔑 記住：資料庫為空是因為我們意外刪除了 Volume，不是系統問題！**