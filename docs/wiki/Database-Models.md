# 資料庫模型文檔

## 模型總覽

CK_Missive 使用 PostgreSQL 資料庫，透過 SQLAlchemy ORM 管理資料模型。

### 核心資料表

| 資料表 | 模型類別 | 說明 |
|--------|----------|------|
| `documents` | `OfficialDocument` | 公文資料 |
| `contract_projects` | `ContractProject` | 承攬案件 |
| `partner_vendors` | `PartnerVendor` | 協力廠商 |
| `government_agencies` | `GovernmentAgency` | 政府機關 |
| `users` | `User` | 使用者帳號 |

### 關聯資料表

| 資料表 | 說明 |
|--------|------|
| `project_vendor_association` | 案件-廠商關聯 |
| `project_user_assignments` | 案件-使用者指派 |
| `document_calendar_events` | 公文行事曆事件 |
| `document_attachments` | 公文附件 |
| `event_reminders` | 事件提醒 |

### 系統資料表

| 資料表 | 模型類別 | 說明 |
|--------|----------|------|
| `site_navigation_items` | `SiteNavigationItem` | 導航項目 |
| `site_configurations` | `SiteConfiguration` | 系統設定 |
| `system_notifications` | `SystemNotification` | 系統通知 |
| `user_sessions` | `UserSession` | 使用者會話 |

---

## 主要模型定義

### OfficialDocument (公文)
```python
class OfficialDocument(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    doc_number = Column(String(100), nullable=False)  # 公文文號
    doc_type = Column(String(10), nullable=False)      # 類型 (收文/發文)
    subject = Column(String(500), nullable=False)      # 主旨
    sender = Column(String(200))                       # 發文單位
    receiver = Column(String(200))                     # 受文單位
    doc_date = Column(Date)                            # 發文日期
    receive_date = Column(Date)                        # 收文日期
    status = Column(String(50))                        # 處理狀態
    contract_project_id = Column(Integer, ForeignKey('contract_projects.id'))

    # 關聯
    contract_project = relationship("ContractProject", back_populates="documents")
    calendar_events = relationship("DocumentCalendarEvent", cascade="all, delete-orphan")
    attachments = relationship("DocumentAttachment", cascade="all, delete-orphan")
```

### ContractProject (承攬案件)
```python
class ContractProject(Base):
    __tablename__ = "contract_projects"

    id = Column(Integer, primary_key=True)
    project_name = Column(String(500), nullable=False)  # 案件名稱
    year = Column(Integer, nullable=False)               # 年度
    client_agency = Column(String(200))                  # 委託單位
    category = Column(String(50))                        # 案件類別
    project_code = Column(String(100), unique=True)      # 專案編號
    contract_amount = Column(Float)                      # 契約金額
    start_date = Column(Date)                            # 開始日期
    end_date = Column(Date)                              # 結束日期
    status = Column(String(50))                          # 執行狀態
    progress = Column(Integer, default=0)                # 完成進度 (0-100)

    # 關聯
    documents = relationship("OfficialDocument", back_populates="contract_project")
```

### PartnerVendor (協力廠商)
```python
class PartnerVendor(Base):
    __tablename__ = "partner_vendors"

    id = Column(Integer, primary_key=True)
    vendor_name = Column(String(200), nullable=False)  # 廠商名稱
    vendor_code = Column(String(50), unique=True)      # 廠商代碼
    contact_person = Column(String(100))               # 聯絡人
    phone = Column(String(50))                         # 電話
    email = Column(String(100))                        # 電子郵件
    address = Column(String(300))                      # 地址
    business_type = Column(String(100))                # 業務類型
    rating = Column(Integer)                           # 評等
```

### User (使用者)
```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(100))
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    role = Column(String(20), default='user')
    permissions = Column(Text)  # JSON 格式
```

---

## 關聯表結構

### project_vendor_association
```python
project_vendor_association = Table(
    'project_vendor_association',
    Base.metadata,
    Column('project_id', Integer, ForeignKey('contract_projects.id'), primary_key=True),
    Column('vendor_id', Integer, ForeignKey('partner_vendors.id'), primary_key=True),
    Column('role', String(50)),           # 角色 (主承包商/分包商/供應商)
    Column('contract_amount', Float),     # 合約金額
    Column('start_date', Date),           # 開始日期
    Column('end_date', Date),             # 結束日期
    Column('status', String(20)),         # 合作狀態
)
```

---

## 資料庫遷移

使用 Alembic 管理資料庫遷移：

```bash
# 建立新遷移
alembic revision --autogenerate -m "描述"

# 執行遷移
alembic upgrade head

# 回滾遷移
alembic downgrade -1

# 查看當前版本
alembic current
```

---
*檔案位置: `backend/app/extended/models.py`*
