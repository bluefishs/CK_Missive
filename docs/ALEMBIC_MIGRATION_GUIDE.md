# Alembic 遷移管理指南

> **最後更新**: 2026-02-02
> **目前狀態**: 健康 (單一 HEAD)

---

## 📋 遷移歷史概覽

### 遷移統計
- **總遷移數**: 26 個
- **初始遷移**: `e42b691ba7b2` (2025-09-07)
- **最新遷移**: `increase_work_type_len` (2026-01-30)
- **Merge 遷移**: 3 個

### 遷移鏈結構

```
e42b691ba7b2 (initial)
    ↓
7970ab493fdc (vendor & project models)
    ↓
41ae83315df9 (sync database models)
    ↓
[多個功能遷移...]
    ↓
5c2da4a2d8aa (merge heads for taoyuan)
    ↓
78a02098c4cd (taoyuan dispatch tables)
    ↓
[桃園派工相關遷移...]
    ↓
133fbad5cf1e (merge heads and coordinates)
    ↓
[後續功能遷移...]
    ↓
increase_work_type_len (current HEAD)
```

---

## 🔧 常用命令

### 檢查遷移狀態

```bash
# 在 Docker 容器中執行
docker compose exec backend alembic current
docker compose exec backend alembic heads

# 本地開發環境
cd backend && alembic current
cd backend && alembic heads
```

### 執行遷移

```bash
# 升級到最新
docker compose exec backend alembic upgrade head

# 升級到特定版本
docker compose exec backend alembic upgrade <revision>

# 降級
docker compose exec backend alembic downgrade -1
```

### 建立新遷移

```bash
# 自動生成 (比對 ORM 與資料庫差異)
cd backend && alembic revision --autogenerate -m "description"

# 手動建立空白遷移
cd backend && alembic revision -m "description"
```

---

## 🚀 部署相關

### 全新部署流程

1. **建立資料表** (使用 ORM):
   ```bash
   docker compose exec backend python scripts/deploy/init-database.py
   ```

2. **標記遷移版本**:
   ```bash
   docker compose exec backend alembic stamp heads
   ```

3. **驗證狀態**:
   ```bash
   docker compose exec backend alembic current
   ```

### 已有資料庫升級

```bash
# 執行待處理遷移
docker compose exec backend alembic upgrade head

# 檢查是否有未執行的遷移
docker compose exec backend alembic current
docker compose exec backend alembic heads
```

---

## ⚠️ 注意事項

### 不要做的事

1. **不要 squash 已部署的遷移**
   - 已在生產環境執行的遷移不應被合併
   - 這會破壞 `alembic_version` 表的追蹤

2. **不要手動修改 revision ID**
   - 會破壞遷移鏈
   - 導致 `alembic upgrade` 失敗

3. **不要刪除已執行的遷移檔案**
   - 即使資料庫已有這些變更
   - 需要保留以供其他環境使用

### 最佳實踐

1. **遷移命名規範**:
   ```
   # 建議格式
   YYYYMMDD_description.py

   # 或使用 Alembic 自動生成的格式
   <revision_id>_description.py
   ```

2. **遷移前備份**:
   ```bash
   # 在執行遷移前先備份資料庫
   pg_dump -h localhost -U ck_user -d ck_documents > backup_before_migration.sql
   ```

3. **測試遷移**:
   ```bash
   # 先在測試環境驗證
   alembic upgrade head
   alembic downgrade -1
   alembic upgrade head
   ```

---

## 📁 目錄結構

```
backend/
├── alembic.ini              # Alembic 配置
└── alembic/
    ├── env.py               # 遷移環境設定
    ├── script.py.mako       # 遷移模板
    └── versions/            # 遷移檔案
        ├── e42b691ba7b2_initial_database_schema.py
        ├── 7970ab493fdc_add_vendor_and_project_models.py
        ├── ...
        └── 20260130_increase_dispatch_work_type_length.py
```

---

## 🔍 故障排除

### Multiple Heads 錯誤

```bash
# 檢查所有 heads
alembic heads

# 建立 merge 遷移
alembic merge -m "merge heads" <head1> <head2>
```

### 遷移與資料庫不同步

```bash
# 查看當前資料庫版本
alembic current

# 查看待執行遷移
alembic history --indicate-current

# 強制標記版本 (謹慎使用)
alembic stamp <revision>
```

### Schema 驗證失敗

如果 health check 回報 schema 不一致：

1. 檢查缺失的表格
2. 執行 `alembic upgrade head`
3. 如果是全新資料庫，使用 `init-database.py`

---

*文件維護: CK_Missive 開發團隊*
