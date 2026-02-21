---
trigger_keywords: [Alembic, 遷移, migration, schema change, DB 變更, autogenerate]
version: "1.0.0"
date: "2026-02-21"
---

# Alembic 遷移管理規範

## 遷移建立流程

### 自動生成 (Autogenerate)

```bash
cd backend

# 1. 確認 DB 連線正常
alembic current

# 2. 自動偵測 ORM 與 DB 差異
alembic revision --autogenerate -m "add_column_to_documents"

# 3. 檢視生成的遷移檔案
# ⚠️ 必須人工審查！autogenerate 無法偵測：
#   - 資料遷移 (data migration)
#   - 欄位重新命名 (會變成 drop + add)
#   - 複雜索引變更

# 4. 執行遷移
alembic upgrade head

# 5. 驗證
alembic current
```

### 手動建立

```bash
# 空白遷移（用於資料遷移或複雜操作）
alembic revision -m "migrate_legacy_data"
```

### 遷移檔案命名規範

```
add_{column}_to_{table}.py     # 新增欄位
create_{table}_table.py        # 新增資料表
add_{index_name}_index.py      # 新增索引
remove_{column}_from_{table}.py # 移除欄位
merge_{description}.py         # 合併 heads
```

## 多 Heads 合併

### 偵測多 heads

```bash
alembic heads
# 若輸出超過 1 行 → 需要合併
```

### 合併方法

```bash
# 自動合併
alembic merge heads -m "merge_feature_x_and_feature_y"

# 指定 heads
alembic merge abc123 def456 -m "merge_branches"
```

### CI 自動檢查

CI 已配置 `migration-check` job，自動偵測多 heads：

```yaml
# .github/workflows/ci.yml
HEADS=$(alembic heads 2>/dev/null | wc -l)
if [ "$HEADS" -gt 1 ]; then
  echo "⚠️ Multiple migration heads detected!"
  exit 1
fi
```

## pgvector 擴展可用性檢查

### 問題背景

`CREATE EXTENSION IF NOT EXISTS vector` 在擴展不可用時會中止 PostgreSQL 交易，即使用 `try/except` 也無法恢復。

### 正確檢查模式

```python
def upgrade() -> None:
    conn = op.get_bind()

    # ✅ 先檢查擴展是否可安裝
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_available_extensions WHERE name = 'vector'"
    ))
    if not result.fetchone():
        print("pgvector extension not available, skipping migration")
        return

    # 安全地建立擴展
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 新增向量欄位
    op.add_column('official_documents',
        sa.Column('embedding', Vector(768), nullable=True)
    )
```

### Feature Flag 配合

```python
# backend/app/core/config.py
PGVECTOR_ENABLED: bool = os.environ.get("PGVECTOR_ENABLED", "false").lower() == "true"

# backend/app/extended/models/_base.py
if settings.PGVECTOR_ENABLED:
    from pgvector.sqlalchemy import Vector
else:
    Vector = None

# ORM 模型中
class OfficialDocument(Base):
    # ... 基礎欄位 ...
    if Vector is not None:
        embedding = Column(Vector(768), nullable=True)
```

## Downgrade 安全操作

### 規則

1. **永遠寫 downgrade**：即使認為不會用到
2. **資料遷移需雙向**：upgrade 轉換格式，downgrade 還原
3. **不可逆操作標註**：若 downgrade 會遺失資料，在函數中加警告

```python
def downgrade() -> None:
    # ⚠️ 此操作會遺失 embedding 向量資料
    op.drop_column('official_documents', 'embedding')
```

### 測試 downgrade

```bash
# 降級一個版本
alembic downgrade -1

# 再升級回來
alembic upgrade head

# 確認沒有遺失
alembic current
```

## 常見陷阱

### 1. asyncpg + Alembic 不相容

```python
# alembic/env.py 中必須用同步連線
# DATABASE_URL: postgresql+asyncpg://... → postgresql://...
url = config.get_main_option("sqlalchemy.url")
url = url.replace("+asyncpg", "")  # 移除 async driver
```

### 2. 索引命名

```python
# ✅ 明確命名索引
op.create_index(
    'ix_documents_type_status_date',
    'official_documents',
    ['doc_type', 'status', 'doc_date']
)

# ❌ 讓資料庫自動命名（跨環境可能不一致）
```

### 3. 大表遷移

```python
# 大表新增 NOT NULL 欄位的安全步驟：
# 1. 先加 nullable=True
op.add_column('large_table', sa.Column('new_col', sa.String, nullable=True))
# 2. 回填資料
op.execute("UPDATE large_table SET new_col = 'default' WHERE new_col IS NULL")
# 3. 再改為 NOT NULL
op.alter_column('large_table', 'new_col', nullable=False)
```

## 參考資源

- 詳細操作指南：`docs/ALEMBIC_MIGRATION_GUIDE.md`
- ORM 模型位置：`backend/app/extended/models.py` (7 模組分區)
- Schema 對照表：`docs/specifications/SCHEMA_DB_MAPPING.md`
