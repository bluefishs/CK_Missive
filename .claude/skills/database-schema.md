# 資料庫結構領域知識 (Database Schema Domain)

> **觸發關鍵字**: schema, 資料庫, PostgreSQL, model, 模型, table, 資料表
> **適用範圍**: 資料庫設計、模型定義、遷移管理

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
backend/app/models/
├── document.py           # Document, DocumentAttachment
├── agency.py             # Agency
├── contract_project.py   # ContractProject
├── calendar_event.py     # DocumentCalendarEvent
├── user.py               # User
└── base.py               # Base 類別
```

### 模型範例
```python
# backend/app/models/document.py
from sqlalchemy import Column, Integer, String, Text, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    doc_number = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(20))
    doc_type = Column(String(50))
    subject = Column(Text, nullable=False)
    # ...

    # 關聯
    sender_agency = relationship("Agency", foreign_keys=[sender_agency_id])
    receiver_agency = relationship("Agency", foreign_keys=[receiver_agency_id])
    contract_project = relationship("ContractProject", back_populates="documents")
    attachments = relationship("DocumentAttachment", back_populates="document", cascade="all, delete-orphan")
```

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
