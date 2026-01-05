"""
擴展數據模型 - 四大功能模組 (已修復級聯刪除)
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean, Table, func
from sqlalchemy.orm import relationship
from datetime import datetime

# 從共享的 database.py 匯入 Base，確保所有模型都使用同一個 metadata
from app.db.database import Base

# 案件與廠商關聯表
project_vendor_association = Table(
    'project_vendor_association',
    Base.metadata,
    Column('project_id', Integer, ForeignKey('contract_projects.id'), primary_key=True),
    Column('vendor_id', Integer, ForeignKey('partner_vendors.id'), primary_key=True),
    Column('role', String(50), comment="廠商在專案中的角色 (主承包商/分包商/供應商)"),
    Column('contract_amount', Float, comment="該廠商的合約金額"),
    Column('start_date', Date, comment="合作開始日期"),
    Column('end_date', Date, comment="合作結束日期"),
    Column('status', String(20), comment="合作狀態"),
    Column('created_at', DateTime, server_default=func.now(), comment="關聯建立時間"),
    Column('updated_at', DateTime, server_default=func.now(), comment="關聯更新時間"),
    extend_existing=True
)

# 移除重複的 Table 定義，改用 class 模型

# 專案使用者關聯表 - 已移到 Class 定義，避免重複
project_user_assignment = Table(
    'project_user_assignments',
    Base.metadata,
    Column('id', Integer, primary_key=True, index=True),
    Column('project_id', Integer, ForeignKey('contract_projects.id'), nullable=False),
    Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
    Column('role', String(50), default='member', comment="角色"),
    Column('is_primary', Boolean, default=False, comment="是否為主要負責人"),
    Column('assignment_date', Date, comment="指派日期"),
    Column('start_date', Date, comment="開始日期"),
    Column('end_date', Date, comment="結束日期"),
    Column('status', String(50), default='active', comment="狀態"),
    Column('notes', Text, comment="備註"),
    extend_existing=True
)

class PartnerVendor(Base):
    """協力廠商模型"""
    __tablename__ = "partner_vendors"

    id = Column(Integer, primary_key=True, index=True)
    vendor_name = Column(String(200), nullable=False, comment="廠商名稱")
    vendor_code = Column(String(50), unique=True, comment="廠商代碼")
    contact_person = Column(String(100), comment="聯絡人")
    phone = Column(String(50), comment="電話")
    email = Column(String(100), comment="電子郵件")
    address = Column(String(300), comment="地址")
    business_type = Column(String(100), comment="業務類型")  # Match database schema
    rating = Column(Integer, comment="評等")  # Match database schema - integer type
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())

class ContractProject(Base):
    __tablename__ = "contract_projects"
    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String(500), nullable=False, comment="案件名稱")
    year = Column(Integer, nullable=False, comment="年度")
    client_agency = Column(String(200), comment="委託單位")
    category = Column(String(50), comment="案件類別: 01委辦案件、02協力計畫、03小額採購、04其他類別")
    contract_doc_number = Column(String(100), comment="契約文號")
    project_code = Column(String(100), unique=True, comment="專案編號: 年度+類別+流水號 (如202501001)")
    contract_amount = Column(Float, comment="契約金額")
    winning_amount = Column(Float, comment="得標金額")
    start_date = Column(Date, comment="開始日期")
    end_date = Column(Date, comment="結束日期")
    status = Column(String(50), comment="執行狀態")
    progress = Column(Integer, default=0, comment="完成進度 (0-100)")
    notes = Column(Text, comment="備註")
    project_path = Column(String(500), comment="專案路徑")
    description = Column(Text, comment="專案描述")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())

    # 關聯關係
    documents = relationship("OfficialDocument", back_populates="contract_project")

class OfficialDocument(Base):
    """
    公文模型
    用於記錄所有收文與發文的公文資料。
    """
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    doc_number = Column(String(100), nullable=False, index=True, comment="公文文號")
    doc_type = Column(String(10), nullable=False, index=True, comment="公文類型 (收文/發文)")
    subject = Column(String(500), nullable=False, comment="主旨")
    sender = Column(String(200), index=True, comment="發文單位")
    receiver = Column(String(200), index=True, comment="受文單位")
    doc_date = Column(Date, index=True, comment="發文日期 (西元)")
    receive_date = Column(Date, comment="收文日期 (西元)")
    status = Column(String(50), index=True, comment="處理狀態 (例如：待處理, 已辦畢)")
    # ... 其他欄位 ...
    contract_project_id = Column(Integer, ForeignKey('contract_projects.id'), nullable=True, comment="關聯的承攬案件ID")
    sender_agency_id = Column(Integer, ForeignKey('government_agencies.id'), nullable=True, comment="發文機關ID")
    receiver_agency_id = Column(Integer, ForeignKey('government_agencies.id'), nullable=True, comment="受文機關ID")

    # 時間戳欄位
    created_at = Column(DateTime, server_default=func.now(), comment="建立時間")
    updated_at = Column(DateTime, server_default=func.now(), comment="更新時間")

    # 建立關聯關係
    contract_project = relationship("ContractProject", back_populates="documents", lazy="select")
    sender_agency = relationship("GovernmentAgency", foreign_keys=[sender_agency_id], back_populates="sent_documents", lazy="select")
    receiver_agency = relationship("GovernmentAgency", foreign_keys=[receiver_agency_id], back_populates="received_documents", lazy="select")

    # **關鍵修復：新增級聯刪除設定**
    calendar_events = relationship(
        "DocumentCalendarEvent", 
        back_populates="document", 
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    attachments = relationship(
        "DocumentAttachment",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True
    )


class GovernmentAgency(Base):
    __tablename__ = "government_agencies"
    id = Column(Integer, primary_key=True, index=True)
    agency_name = Column(String(200), nullable=False, comment="機關名稱")
    agency_short_name = Column(String(100), comment="機關簡稱")
    agency_code = Column(String(50), comment="機關代碼")
    agency_type = Column(String(50), comment="機關類型")
    contact_person = Column(String(100), comment="聯絡人")
    phone = Column(String(50), comment="電話")
    address = Column(String(500), comment="地址")
    email = Column(String(100), comment="電子郵件")
    created_at = Column(DateTime, server_default=func.now(), comment="建立時間")
    updated_at = Column(DateTime, server_default=func.now(), comment="更新時間")

    sent_documents = relationship("OfficialDocument", foreign_keys="OfficialDocument.sender_agency_id", back_populates="sender_agency", lazy="dynamic")
    received_documents = relationship("OfficialDocument", foreign_keys="OfficialDocument.receiver_agency_id", back_populates="receiver_agency", lazy="dynamic")

# ... (PartnerVendor, DocNumberSequence, etc. 保持不變) ...

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    email = Column(String(100), nullable=False, unique=True, index=True)
    password_hash = Column(String(100), nullable=True)  # Match actual database schema
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime)
    is_superuser = Column(Boolean, default=False)
    google_id = Column(String(100))
    avatar_url = Column(String(255))
    auth_provider = Column(String(20), default='email')
    login_count = Column(Integer, default=0)
    permissions = Column(Text)
    role = Column(String(20), default='user')
    updated_at = Column(DateTime, server_default=func.now())
    email_verified = Column(Boolean, default=False)

    # 關聯關係 (暫時移除以解決 SQLAlchemy 衝突)
    # notifications = relationship("SystemNotification", back_populates="user")
    # sessions = relationship("UserSession", back_populates="user")

class DocumentCalendarEvent(Base):
    __tablename__ = "document_calendar_events"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey('documents.id', ondelete="CASCADE"), nullable=False, index=True, comment="關聯的公文ID")
    title = Column(String(500), nullable=False, comment="事件標題")
    description = Column(Text, comment="事件描述")
    start_date = Column(DateTime, nullable=False, comment="開始時間")
    end_date = Column(DateTime, comment="結束時間")
    all_day = Column(Boolean, default=False, comment="全天事件")
    event_type = Column(String(100), default='reminder', comment="事件類型")
    priority = Column(String(50), default='normal', comment="優先級")
    location = Column(String(200), comment="地點")
    assigned_user_id = Column(Integer, ForeignKey('users.id'), comment="指派使用者ID")
    created_by = Column(Integer, ForeignKey('users.id'), comment="建立者ID")
    created_at = Column(DateTime, server_default=func.now(), comment="建立時間")
    updated_at = Column(DateTime, server_default=func.now(), comment="更新時間")

    # 關聯關係
    document = relationship("OfficialDocument", back_populates="calendar_events")
    assigned_user = relationship("User", foreign_keys=[assigned_user_id])
    creator = relationship("User", foreign_keys=[created_by])
    reminders = relationship("EventReminder", back_populates="event", cascade="all, delete-orphan")

# ... (EventReminder, etc. 保持不變) ...

class DocumentAttachment(Base):
    __tablename__ = 'document_attachments'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="附件唯一識別ID")
    document_id = Column(Integer, ForeignKey('documents.id', ondelete="CASCADE"), nullable=False, comment="關聯的公文ID")
    # ... 其他欄位
    # **關鍵修復：新增 relationship 以便 back_populates**
    document = relationship("OfficialDocument", back_populates="attachments")

# ProjectUserAssignment Class 定義暫時移除以避免與 Table 定義衝突

class EventReminder(Base):
    """事件提醒模型"""
    __tablename__ = "event_reminders"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey('document_calendar_events.id', ondelete="CASCADE"), nullable=False, index=True)
    recipient_user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=True, index=True, comment="接收用戶ID")
    reminder_type = Column(String(50), nullable=False, default="email", comment="提醒類型")
    reminder_time = Column(DateTime, nullable=False, index=True, comment="提醒時間")
    message = Column(Text, comment="提醒訊息")
    is_sent = Column(Boolean, default=False, comment="是否已發送")
    status = Column(String(50), default="pending", comment="提醒狀態")
    priority = Column(Integer, default=3, comment="優先級 (1-5, 5最高)")
    next_retry_at = Column(DateTime, nullable=True, comment="下次重試時間")
    retry_count = Column(Integer, default=0, comment="重試次數")
    created_at = Column(DateTime, server_default=func.now(), comment="建立時間")
    updated_at = Column(DateTime, server_default=func.now(), comment="更新時間")

    # 關聯關係
    event = relationship("DocumentCalendarEvent", back_populates="reminders")
    recipient_user = relationship("User", foreign_keys=[recipient_user_id])

class SystemNotification(Base):
    """系統通知模型"""
    __tablename__ = "system_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=True, index=True, comment="接收者ID")
    recipient_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=True, index=True, comment="接收者ID (別名)")
    title = Column(String(200), nullable=False, comment="通知標題")
    message = Column(Text, nullable=False, comment="通知內容")
    notification_type = Column(String(50), default="info", comment="通知類型")
    is_read = Column(Boolean, default=False, index=True, comment="是否已讀")
    created_at = Column(DateTime, server_default=func.now(), index=True, comment="建立時間")
    read_at = Column(DateTime, nullable=True, comment="已讀時間")

    # 關聯關係 (暫時移除 back_populates)
    # user = relationship("User", back_populates="notifications")

class UserSession(Base):
    """使用者會話模型"""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False, index=True)
    token_jti = Column(String(255), unique=True, nullable=False, index=True)  # JWT ID
    refresh_token = Column(String(255), nullable=True)
    ip_address = Column(String(255), nullable=True)
    user_agent = Column(Text, nullable=True)
    device_info = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)
    revoked_at = Column(DateTime, nullable=True)

    # 關聯關係 (暫時移除 back_populates)
    # user = relationship("User", back_populates="sessions")

class SiteNavigationItem(Base):
    """網站導航項目模型"""
    __tablename__ = "site_navigation_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False, comment="導航標題")
    key = Column(String(100), unique=True, nullable=False, comment="導航鍵值")
    path = Column(String(200), comment="路徑")
    icon = Column(String(50), comment="圖標")
    sort_order = Column(Integer, default=0, comment="排序")
    parent_id = Column(Integer, ForeignKey('site_navigation_items.id'), nullable=True, comment="父級ID")
    is_enabled = Column(Boolean, default=True, comment="是否啟用")
    is_visible = Column(Boolean, default=True, comment="是否顯示")
    level = Column(Integer, default=1, comment="層級")
    description = Column(String(500), comment="描述")
    target = Column(String(50), default="_self", comment="打開方式")
    permission_required = Column(Text, comment="所需權限(JSON格式)")
    created_at = Column(DateTime, server_default=func.now(), comment="建立時間")
    updated_at = Column(DateTime, server_default=func.now(), comment="更新時間")

class SiteConfiguration(Base):
    """網站配置模型"""
    __tablename__ = "site_configurations"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, comment="配置鍵")
    value = Column(Text, comment="配置值")
    description = Column(String(200), comment="描述")
    category = Column(String(50), default="general", comment="分類")
    is_active = Column(Boolean, default=True, comment="是否啟用")
    created_at = Column(DateTime, server_default=func.now(), comment="建立時間")
    updated_at = Column(DateTime, server_default=func.now(), comment="更新時間")
