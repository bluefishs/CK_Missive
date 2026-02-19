# 資料庫結構領域知識 (Database Schema Domain)

> **觸發關鍵字**: schema, 資料庫, PostgreSQL, model, 模型, table, 資料表, pgvector, feature flag
> **適用範圍**: 資料庫設計、模型定義、遷移管理、Feature Flags
> **版本**: 1.3.0
> **最後更新**: 2026-02-19

---

## 資料庫配置

### 連線資訊
```
Host: localhost (Docker)
Port: 5432
Database: ck_documents
User: ck_user
```

### 連線方式
```bash
# Docker 容器內連線
docker exec -it ck_missive_postgres_dev psql -U ck_user -d ck_documents
```

---

## 模型定義位置

**重要**: 所有 SQLAlchemy 模型定義在單一檔案中：

```
backend/app/extended/models.py    ← 所有模型的唯一來源
```

### 模型清單

| 模型 | 資料表 | 說明 |
|------|--------|------|
| `OfficialDocument` | `documents` | 公文 |
| `DocumentAttachment` | `document_attachments` | 公文附件 |
| `GovernmentAgency` | `government_agencies` | 機關 |
| `ContractProject` | `contract_projects` | 承攬專案 |
| `PartnerVendor` | `partner_vendors` | 合作廠商 |
| `DocumentCalendarEvent` | `document_calendar_events` | 行事曆事件 |
| `User` | `users` | 使用者 |
| `NavigationItem` | `navigation_items` | 導覽項目 |
| `SiteConfiguration` | `site_configurations` | 網站設定 |

### 關聯表

| 關聯表 | 說明 |
|--------|------|
| `project_user_assignment` | 專案-使用者配置 (多對多) |
| `project_vendor_association` | 專案-廠商關聯 (多對多) |

---

## 核心資料表

### documents (公文)
```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    doc_number VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(20),          -- 收文/發文
    doc_type VARCHAR(50),          -- 函/開會通知單/會勘通知單
    subject TEXT NOT NULL,
    sender VARCHAR(255),
    receiver VARCHAR(255),
    doc_date DATE,
    receive_date DATE,             -- 收文日期
    send_date DATE,                -- 發文日期
    status VARCHAR(50),
    auto_serial VARCHAR(20) UNIQUE, -- 流水序號 R0001/S0001
    sender_agency_id INTEGER REFERENCES agencies(id),
    receiver_agency_id INTEGER REFERENCES agencies(id),
    contract_project_id INTEGER REFERENCES contract_projects(id),
    assignee VARCHAR(100),
    notes TEXT,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_documents_doc_number ON documents(doc_number);
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_doc_date ON documents(doc_date);
CREATE INDEX idx_documents_contract_project_id ON documents(contract_project_id);
```

### document_attachments (公文附件)
```sql
CREATE TABLE document_attachments (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    file_path VARCHAR(500),
    file_size BIGINT,
    content_type VARCHAR(100),
    storage_type VARCHAR(50) DEFAULT 'local',
    checksum VARCHAR(64),
    uploaded_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### agencies (機關)
```sql
CREATE TABLE agencies (
    id SERIAL PRIMARY KEY,
    agency_name VARCHAR(255) NOT NULL,
    agency_short_name VARCHAR(100),
    agency_code VARCHAR(50),
    agency_type VARCHAR(50),       -- 中央機關/地方機關/民間單位
    contact_person VARCHAR(100),
    phone VARCHAR(50),
    email VARCHAR(100),
    address TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### contract_projects (承攬專案)
```sql
CREATE TABLE contract_projects (
    id SERIAL PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL,
    project_code VARCHAR(100),
    year INTEGER,
    client_agency VARCHAR(255),
    category VARCHAR(50),
    contract_amount DECIMAL(15,2),
    winning_amount DECIMAL(15,2),
    start_date DATE,
    end_date DATE,
    status VARCHAR(50) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    notes TEXT,
    project_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### document_calendar_events (公文行事曆事件)
```sql
CREATE TABLE document_calendar_events (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    all_day BOOLEAN DEFAULT FALSE,
    event_type VARCHAR(50),
    priority VARCHAR(20),
    location VARCHAR(255),
    assigned_user_id INTEGER REFERENCES users(id),
    google_event_id VARCHAR(255),
    sync_status VARCHAR(50),
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## SQLAlchemy 模型

### 模型位置
```
backend/app/extended/models.py    ← 所有模型的唯一來源 (單一檔案)
```

### 關聯表定義
```python
# project_user_assignment - 專案與使用者的多對多關聯
project_user_assignment = Table(
    'project_user_assignments',
    Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('project_id', Integer, ForeignKey('contract_projects.id'), nullable=False),
    Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
    Column('role', String(50)),           # 專案角色
    Column('is_primary', Boolean, default=False),  # 是否為主要負責人
    Column('start_date', Date),
    Column('end_date', Date),
    Column('status', String(20), default='active'),  # active/inactive
    Column('notes', Text)
)
```

### 模型範例
```python
# backend/app/extended/models.py
from sqlalchemy import Column, Integer, String, Text, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class OfficialDocument(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    doc_number = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(20))
    doc_type = Column(String(50))
    subject = Column(Text, nullable=False)
    # ...

    # 關聯
    sender_agency = relationship("GovernmentAgency", foreign_keys=[sender_agency_id])
    receiver_agency = relationship("GovernmentAgency", foreign_keys=[receiver_agency_id])
    contract_project = relationship("ContractProject", back_populates="documents")
    attachments = relationship("DocumentAttachment", back_populates="document", cascade="all, delete-orphan")
```

---

## Row-Level Security (RLS)

### 權限過濾邏輯

系統使用統一的 RLS 過濾器 (`app/core/rls_filter.py`)：

```python
from app.core.rls_filter import RLSFilter

# 取得使用者可存取的專案 ID 子查詢
project_ids_query = RLSFilter.get_user_accessible_project_ids(user_id)

# 檢查使用者是否有權限存取特定專案
has_access = await RLSFilter.check_user_project_access(db, user_id, project_id)

# 套用公文查詢的 RLS 過濾
query = RLSFilter.apply_document_rls(query, Document, user_id, is_admin)
```

### 權限規則

| 角色 | 公文權限 | 專案權限 |
|------|---------|---------|
| superuser | 全部 | 全部 |
| admin | 全部 | 全部 |
| 一般使用者 | 關聯專案的公文 + 無專案關聯的公文 | 關聯的專案 |

### 專案配置表

使用者透過 `project_user_assignments` 關聯到專案：
- `status = 'active'` 或 `null` 時視為有效配置
- `is_primary = true` 表示主要負責人

---

## 遷移管理 (Alembic)

### 目錄結構
```
backend/alembic/
├── versions/             # 遷移檔案
├── env.py                # 環境配置
└── alembic.ini          # 配置檔
```

### 常用命令
```bash
# 產生遷移
cd backend && alembic revision --autogenerate -m "描述"

# 執行遷移
alembic upgrade head

# 回滾
alembic downgrade -1

# 查看歷史
alembic history
```

---

## 查詢優化

### N+1 問題解決
使用 `selectinload` 預載入關聯：
```python
from sqlalchemy.orm import selectinload

query = select(Document).options(
    selectinload(Document.sender_agency),
    selectinload(Document.receiver_agency),
    selectinload(Document.attachments)
)
```

### 常用索引
```sql
-- 公文查詢優化
CREATE INDEX idx_documents_category_doc_date ON documents(category, doc_date DESC);

-- 行事曆查詢優化
CREATE INDEX idx_calendar_events_start_date ON document_calendar_events(start_date);
```

---

## 資料驗證

### 公文類別連動規則
```python
if category == '收文':
    # 必填: receiver, receive_date
    # 預設: receiver = '本公司'
elif category == '發文':
    # 必填: sender, send_date
    # 預設: sender = '本公司'
```

### 字串清理
```python
def clean_db_string(value) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in ('none', 'null', ''):
        return None
    return text
```

---

## Feature Flags 與可選欄位 (v1.2.0 新增)

### pgvector 嵌入欄位

`OfficialDocument` 模型支援可選的 `embedding` 欄位，由 `PGVECTOR_ENABLED` 環境變數控制：

```python
# backend/app/extended/models.py
import os

try:
    if os.environ.get("PGVECTOR_ENABLED", "").lower() == "true":
        from pgvector.sqlalchemy import Vector
    else:
        Vector = None
except ImportError:
    Vector = None

class OfficialDocument(Base):
    __tablename__ = "documents"
    # ... 標準欄位 ...

    # 可選：pgvector 語意搜尋嵌入 (nomic-embed-text 輸出 768 維)
    if Vector is not None:
        embedding = Column(Vector(768), nullable=True)
```

### Feature Flag 規則

| 旗標 | 控制範圍 | `.env` 預設 |
|------|---------|------------|
| `PGVECTOR_ENABLED` | ORM embedding Column 是否定義 | `false` |
| `MFA_ENABLED` | MFA 路由與服務是否啟用 | `false` |

**重要規則**:
- **禁止**使用 `deferred()` 控制可選欄位 — subquery 中 deferred 會被展開
- 必須用環境變數完全控制 Column 是否存在於 ORM 定義中
- Feature Flag 為 `false` 時，系統必須正常運作

### 連線池配置

```python
# backend/app/db/database.py v2.0.0
engine = create_async_engine(
    async_db_url,
    pool_size=settings.POOL_SIZE,           # 預設 10
    max_overflow=settings.MAX_OVERFLOW,     # 預設 20
    pool_recycle=settings.POOL_RECYCLE,     # 預設 180s
    connect_args={
        "server_settings": {
            "statement_timeout": str(settings.STATEMENT_TIMEOUT),  # 30000ms
        },
        "command_timeout": 60,
    }
)
```

### Alembic pgvector 遷移安全

```python
# 遷移中先檢查 extension 是否可用
def upgrade():
    conn = op.get_bind()
    result = conn.execute(text(
        "SELECT 1 FROM pg_available_extensions WHERE name = 'vector'"
    ))
    if not result.fetchone():
        print("pgvector extension not available, skipping migration")
        return
    # 安全地建立 extension 和 column
```
