# 資料庫效能優化指南 (Database Performance Guide)

> **觸發關鍵字**: 慢查詢, N+1, 索引, index, 資料庫效能, 查詢優化, slow query
> **適用範圍**: 後端資料庫操作、ORM 查詢優化
> **版本**: 1.0.0
> **最後更新**: 2026-01-22

---

## 架構概述

本指南涵蓋 PostgreSQL + SQLAlchemy 環境下的效能優化最佳實踐。

---

## 1. N+1 查詢問題

### 問題定義

N+1 查詢發生在遍歷關聯資料時，對每個主記錄發出額外的查詢。

### ❌ 問題範例

```python
# 取得所有專案
projects = await db.execute(select(Project))
for project in projects.scalars():
    # 每次迭代都會發出一個額外的查詢！
    print(project.vendors)  # N 次額外查詢
```

### ✅ 正確做法：使用 selectinload

```python
from sqlalchemy.orm import selectinload

# 一次性載入所有關聯資料
stmt = select(Project).options(
    selectinload(Project.vendors),
    selectinload(Project.documents)
)
projects = await db.execute(stmt)
for project in projects.scalars():
    print(project.vendors)  # 不會發出額外查詢
```

### ✅ 多層關聯載入

```python
stmt = select(TaoyuanDispatchOrder).options(
    selectinload(TaoyuanDispatchOrder.project_links)
        .selectinload(TaoyuanDispatchProjectLink.project),
    selectinload(TaoyuanDispatchOrder.document_links)
        .selectinload(TaoyuanDispatchDocumentLink.document)
)
```

---

## 2. 索引設計最佳實踐

### 常見索引場景

| 場景 | 索引類型 | 範例 |
|------|---------|------|
| 主鍵查詢 | PRIMARY KEY | `id` (自動建立) |
| 外鍵查詢 | INDEX | `contract_project_id` |
| 搜尋/篩選 | INDEX | `doc_number`, `agency_name` |
| 排序欄位 | INDEX | `created_at`, `updated_at` |
| 複合條件 | COMPOSITE INDEX | `(contract_project_id, status)` |

### 索引建立範例

```python
# Alembic 遷移中建立索引
def upgrade():
    op.create_index(
        'ix_documents_doc_number',
        'official_documents',
        ['doc_number']
    )

    # 複合索引
    op.create_index(
        'ix_dispatch_orders_project_status',
        'taoyuan_dispatch_orders',
        ['contract_project_id', 'work_type']
    )
```

### 何時不需要索引

- 資料量小於 1000 筆的表
- 很少用於 WHERE 條件的欄位
- 高頻更新的欄位（索引維護成本高）

---

## 3. 查詢執行計畫分析

### 使用 EXPLAIN 分析

```sql
EXPLAIN ANALYZE SELECT * FROM official_documents
WHERE contract_project_id = 1
ORDER BY created_at DESC
LIMIT 20;
```

### 關鍵指標

| 指標 | 良好值 | 警戒值 |
|------|--------|--------|
| Seq Scan | 小表可接受 | 大表應避免 |
| Index Scan | 優先使用 | - |
| Rows | 接近預估值 | 差異 >10x 需調整統計 |
| Cost | 越低越好 | - |

### Python 中執行 EXPLAIN

```python
from sqlalchemy import text

explain_result = await db.execute(
    text("EXPLAIN ANALYZE " + str(query.compile(compile_kwargs={"literal_binds": True})))
)
for row in explain_result:
    print(row[0])
```

---

## 4. 常見效能反模式

### ❌ 在迴圈中執行查詢

```python
# 錯誤：每次迭代都發出查詢
for doc_id in document_ids:
    doc = await db.execute(select(Document).where(Document.id == doc_id))
```

### ✅ 使用 IN 子句批次查詢

```python
# 正確：一次查詢取得所有資料
docs = await db.execute(
    select(Document).where(Document.id.in_(document_ids))
)
```

### ❌ SELECT * 取得所有欄位

```python
# 錯誤：取得不需要的欄位
result = await db.execute(select(LargeTable))
```

### ✅ 只選取需要的欄位

```python
# 正確：只取需要的欄位
result = await db.execute(
    select(LargeTable.id, LargeTable.name, LargeTable.status)
)
```

### ❌ 不使用分頁

```python
# 錯誤：取得所有資料
all_docs = await db.execute(select(Document))
```

### ✅ 使用分頁

```python
# 正確：使用 LIMIT/OFFSET
paginated = await db.execute(
    select(Document).offset(skip).limit(limit)
)
```

---

## 5. 連線池配置

### SQLAlchemy 連線池設定

```python
# config.py
SQLALCHEMY_DATABASE_URL = "postgresql+asyncpg://..."

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=5,           # 常駐連線數
    max_overflow=10,       # 最大額外連線
    pool_timeout=30,       # 等待連線逾時（秒）
    pool_recycle=1800,     # 連線回收時間（秒）
    pool_pre_ping=True,    # 連線前檢查
)
```

---

## 6. 檢測腳本

### 手動執行 N+1 檢測

```bash
# 啟用 SQLAlchemy 查詢日誌
export SQLALCHEMY_ECHO=True

# 或在 Python 中
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### 搜尋潛在 N+1 模式

```bash
# 搜尋迴圈中的 db 操作
grep -rn "for .* in.*:" backend/app/api/ | \
  xargs grep -l "await db\."
```

---

## 參考文件

- [SQLAlchemy Loading Techniques](https://docs.sqlalchemy.org/en/20/orm/loading_relationships.html)
- [PostgreSQL EXPLAIN](https://www.postgresql.org/docs/current/sql-explain.html)
- `.claude/skills/api-serialization.md` - API 序列化相關
