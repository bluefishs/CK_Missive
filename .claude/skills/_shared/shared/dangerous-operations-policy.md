---
name: dangerous-operations-policy
description: 定義系統禁止執行的危險操作，確保資料安全
version: 1.0.0
category: shared
triggers:
  - 危險操作
  - 禁止
  - DROP
  - DELETE
  - TRUNCATE
  - 資料安全
updated: 2026-01-22
---

# Dangerous Operations Policy

> **用途**: 定義系統禁止執行的危險操作
> **觸發**: 危險操作, 禁止, DROP, DELETE, TRUNCATE
> **版本**: 1.0.0
> **分類**: shared

**適用場景**：所有涉及資料庫、系統配置的操作

---

## 一、絕對禁止的操作

### 1.1 資料庫層級

**禁止操作清單**：

```sql
-- ❌ 禁止：清空資料庫
DROP DATABASE landvaluation;
TRUNCATE TABLE *;

-- ❌ 禁止：刪除核心表
DROP TABLE public.users;
DROP TABLE public.land_parcels;
DROP TABLE public.navigation_items;
DROP TABLE public.spatial_layers;
DROP TABLE public.assessment_projects;
DROP TABLE public.assessment_cases;

-- ❌ 禁止：無條件刪除所有資料
DELETE FROM users;
DELETE FROM land_parcels WHERE 1=1;

-- ❌ 禁止：修改關鍵約束
ALTER TABLE DISABLE TRIGGER ALL;
SET session_replication_role = 'replica';
```

### 1.2 系統層級

**禁止操作清單**：

```bash
# ❌ 禁止：刪除 Docker volumes
docker volume rm postgres_data
docker volume rm redis_data
docker system prune -a --volumes

# ❌ 禁止：強制重建容器 (會丟失資料)
docker-compose down -v

# ❌ 禁止：刪除備份目錄
rm -rf ./backups/
rm -rf ./data/postgres/
```

### 1.3 程式碼層級

**禁止操作清單**：

```python
# ❌ 禁止：批量刪除使用者
db.query(User).delete()

# ❌ 禁止：清空導航選單
db.query(NavigationItem).delete()

# ❌ 禁止：刪除所有空間圖層
db.query(SpatialLayer).delete()
```

---

## 1.4 環境區分 (Environment Separation)

**重要：開發環境與展示環境必須嚴格區分**

| 環境 | 用途 | 前端端口 | 後端端口 | 可執行操作 |
|------|------|----------|----------|-----------|
| **開發環境** | 開發、測試、維護 | `localhost:3003` | `localhost:8002` | 全部操作 |
| **展示環境 (NAS)** | 僅供展示/Demo | `192.168.50.41:3003` | `192.168.50.41:8002` | 僅讀取操作 |

**強制規則**：
- ⚠️ **所有 API 測試、驗證操作必須使用 localhost 端口**
- ❌ **禁止對展示環境 (192.168.50.41) 執行任何寫入操作**
- ❌ **禁止對展示環境執行資料庫修改、容器重啟等操作**

```bash
# ✅ 正確：使用開發環境測試
curl -s "http://localhost:8002/api/health"
curl -s "http://localhost:8002/api/v1/unified-cadastral/cities"

# ❌ 錯誤：對展示環境執行操作
curl -s "http://192.168.50.41:8002/api/v1/..." -X POST
docker-compose -f ... restart  # 影響展示環境
```

### 1.5 前端地圖功能變更 (2026-01-06 新增)

**需謹慎操作的項目**：

```typescript
// ⚠️ 變更以下項目需確認完整性
handleClearAllFeatures()  // 清除圖徵函數

// 新增圖層功能時必須同步更新：
// 1. 圖層可見性清除
// 2. 高亮標記清除
// 3. 相關面板關閉
```

**強制規則**：
- ✅ 新增地圖功能時，同步更新 `handleClearAllFeatures`
- ✅ 遵循 Map Feature Hook 模式 (useXxxMapFeature)
- ❌ 禁止僅清除部分圖層

---

## 二、需要特別審核的操作

### 2.1 高風險資料修改

執行以下操作前**必須**先備份：

| 操作類型 | 風險等級 | 備份要求 |
|---------|---------|---------|
| 批量更新欄位值 | 高 | 完整表備份 |
| Schema 變更 | 高 | 資料庫備份 |
| 刪除歷史資料 | 中 | 表快照 |
| 修改 ENUM 類型 | 中 | 資料庫備份 |

### 2.2 安全操作流程

```bash
# ✅ 正確：執行危險操作前先備份
docker compose run --rm db-backup

# ✅ 正確：使用交易保護
BEGIN;
-- 執行變更
-- 確認結果
COMMIT; -- 或 ROLLBACK;

# ✅ 正確：刪除前先查詢確認
SELECT COUNT(*) FROM table WHERE condition;
-- 確認數量正確後
DELETE FROM table WHERE condition;
```

---

## 三、替代安全方案

### 3.1 資料清理 (非刪除)

```sql
-- ✅ 軟刪除：標記為停用
UPDATE users SET is_active = false WHERE condition;
UPDATE navigation_items SET is_visible = false WHERE condition;

-- ✅ 封存：移至歷史表
INSERT INTO assessment_cases_archive SELECT * FROM assessment_cases WHERE created_at < '2024-01-01';
```

### 3.2 表結構變更

```sql
-- ✅ 安全：添加可空欄位
ALTER TABLE table ADD COLUMN IF NOT EXISTS new_col VARCHAR(100);

-- ✅ 安全：建立索引 (CONCURRENTLY)
CREATE INDEX CONCURRENTLY idx_name ON table(column);

-- ✅ 安全：重命名欄位 (需程式碼配合)
ALTER TABLE table RENAME COLUMN old_name TO new_name;
```

---

## 四、錯誤恢復程序

### 4.1 如果誤刪資料

1. **立即停止應用程式**
   ```bash
   docker compose stop backend celery-worker
   ```

2. **從最近備份恢復**
   ```bash
   # 找到最近備份
   ls -lt ./backups/database/*.dump.gz | head -5

   # 解壓並恢復
   gunzip backup_landvaluation_YYYYMMDD.dump.gz
   docker exec -i ck_lvrland_webmap-db-1 pg_restore -U postgres -d landvaluation < backup.dump
   ```

3. **驗證恢復結果**
   ```bash
   docker exec ck_lvrland_webmap-db-1 psql -U postgres -d landvaluation -c "SELECT COUNT(*) FROM users;"
   ```

### 4.2 如果資料庫損壞

1. 停止所有服務
2. 使用 Docker volume 中的資料
3. 聯繫資料庫管理員

---

## 五、審計日誌

所有資料庫操作應記錄：

- 執行者 (who)
- 執行時間 (when)
- 執行內容 (what)
- 影響範圍 (scope)

```sql
-- 審計觸發器範例
CREATE OR REPLACE FUNCTION audit_trigger()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (
        table_name,
        action,
        old_data,
        new_data,
        changed_at
    ) VALUES (
        TG_TABLE_NAME,
        TG_OP,
        row_to_json(OLD),
        row_to_json(NEW),
        NOW()
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

**建立日期**：2025-12-30
**最後更新**：2026-01-06
**維護者**：系統管理員
