"""
擴展數據模型 - 四大功能模組 (已修復級聯刪除)
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean, Table, func
from sqlalchemy.dialects.postgresql import JSONB
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

# 專案使用者關聯表 - 與資料庫 schema 對齊
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
    Column('created_at', DateTime, server_default=func.now(), comment="建立時間"),
    Column('updated_at', DateTime, server_default=func.now(), comment="更新時間"),
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
    """承攬案件模型 - 與資料庫 schema 完整對齊"""
    __tablename__ = "contract_projects"
    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String(500), nullable=False, comment="案件名稱")
    year = Column(Integer, comment="年度")
    client_agency = Column(String(200), comment="委託單位")
    contract_doc_number = Column(String(100), comment="契約文號")
    project_code = Column(String(100), unique=True, comment="專案編號: CK{年度}_{類別}_{性質}_{流水號} (如CK2025_01_01_001)")
    category = Column(String(50), comment="案件類別: 01委辦案件、02協力計畫、03小額採購、04其他類別")
    case_nature = Column(String(50), comment="案件性質: 01測量案、02資訊案、03複合案")
    status = Column(String(50), default="執行中", comment="執行狀態: 執行中、已結案")
    contract_amount = Column(Float, comment="契約金額")
    winning_amount = Column(Float, comment="得標金額")
    start_date = Column(Date, comment="開始日期")
    end_date = Column(Date, comment="結束日期")
    progress = Column(Integer, default=0, comment="完成進度 (0-100)")
    project_path = Column(String(500), comment="專案路徑")
    notes = Column(Text, comment="備註")
    description = Column(Text, comment="專案描述")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())

    # 資料庫新增欄位 - Schema 對齊
    contract_number = Column(String(100), comment="合約編號")
    contract_type = Column(String(50), comment="合約類型")
    location = Column(String(200), comment="專案地點")
    procurement_method = Column(String(100), comment="採購方式")
    completion_date = Column(Date, comment="完工日期")
    acceptance_date = Column(Date, comment="驗收日期")
    completion_percentage = Column(Integer, comment="完成百分比")
    warranty_end_date = Column(Date, comment="保固結束日期")
    contact_person = Column(String(100), comment="聯絡人")
    contact_phone = Column(String(50), comment="聯絡電話")
    client_agency_id = Column(Integer, ForeignKey('government_agencies.id'), nullable=True, comment="委託機關ID")
    agency_contact_person = Column(String(100), comment="機關承辦人")
    agency_contact_phone = Column(String(50), comment="機關承辦電話")
    agency_contact_email = Column(String(100), comment="機關承辦Email")

    # 關聯關係
    documents = relationship("OfficialDocument", back_populates="contract_project")
    client_agency_ref = relationship("GovernmentAgency", foreign_keys=[client_agency_id])

class OfficialDocument(Base):
    """
    公文模型 - 與資料庫 schema 完整對齊
    用於記錄所有收文與發文的公文資料。
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    auto_serial = Column(String(50), index=True, comment="流水序號 (R0001=收文, S0001=發文)")  # 與 DB varchar(50) 對齊
    doc_number = Column(String(100), index=True, comment="公文文號")
    doc_type = Column(String(10), index=True, comment="公文類型 (收文/發文)")
    subject = Column(String(500), comment="主旨")
    sender = Column(String(200), index=True, comment="發文單位")
    receiver = Column(String(200), index=True, comment="受文單位")
    doc_date = Column(Date, index=True, comment="發文日期 (西元)")
    receive_date = Column(Date, comment="收文日期 (西元)")
    status = Column(String(50), index=True, comment="處理狀態 (例如：待處理, 已辦畢)")
    category = Column(String(100), index=True, comment="收發文分類 (收文/發文)")

    # 發文形式與附件欄位
    delivery_method = Column(String(20), index=True, default="電子交換", comment="發文形式 (電子交換/紙本郵寄/電子+紙本)")
    has_attachment = Column(Boolean, default=False, comment="是否含附件")

    # 其他欄位
    contract_project_id = Column(Integer, ForeignKey('contract_projects.id'), nullable=True, comment="關聯的承攬案件ID")
    sender_agency_id = Column(Integer, ForeignKey('government_agencies.id'), nullable=True, comment="發文機關ID")
    receiver_agency_id = Column(Integer, ForeignKey('government_agencies.id'), nullable=True, comment="受文機關ID")

    # 資料庫新增欄位 - Schema 對齊
    send_date = Column(Date, comment="發文日期")
    title = Column(Text, comment="標題")
    content = Column(Text, comment="說明")
    cloud_file_link = Column(String(500), comment="雲端檔案連結")
    dispatch_format = Column(String(20), default="電子", comment="發文形式")

    # 承辦人欄位（支援承案人資功能）
    assignee = Column(String(500), comment="承辦人（多人以逗號分隔）")

    # 備註欄位
    notes = Column(Text, comment="備註")

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

    # 新增欄位 (2026-01-12)
    department = Column(String(100), comment="部門名稱")
    position = Column(String(100), comment="職稱")

    # 關聯關係 (暫時移除以解決 SQLAlchemy 衝突)
    # notifications = relationship("SystemNotification", back_populates="user")
    # sessions = relationship("UserSession", back_populates="user")

    # 證照關聯
    certifications = relationship("StaffCertification", back_populates="user", cascade="all, delete-orphan")

class DocumentCalendarEvent(Base):
    __tablename__ = "document_calendar_events"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey('documents.id', ondelete="SET NULL"), nullable=True, index=True, comment="關聯的公文ID（可為空）")
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

    # Google Calendar 同步欄位
    google_event_id = Column(String(255), nullable=True, index=True, comment="Google Calendar 事件 ID")
    google_sync_status = Column(String(50), default='pending', comment="同步狀態: pending/synced/failed")

    # 關聯關係
    document = relationship("OfficialDocument", back_populates="calendar_events")
    assigned_user = relationship("User", foreign_keys=[assigned_user_id])
    creator = relationship("User", foreign_keys=[created_by])
    reminders = relationship("EventReminder", back_populates="event", cascade="all, delete-orphan")

# ... (EventReminder, etc. 保持不變) ...

class DocumentAttachment(Base):
    """
    公文附件模型 - 與資料庫實際 schema 對齊

    變更記錄：
    - 2026-01-06: 新增 storage_type, original_name, checksum, uploaded_by 欄位
    """
    __tablename__ = 'document_attachments'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="附件唯一識別ID")
    document_id = Column(Integer, ForeignKey('documents.id', ondelete="CASCADE"), nullable=False, comment="關聯的公文ID")

    # 附件資訊（與資料庫欄位名稱對齊）
    file_name = Column(String(255), comment="檔案名稱")
    file_path = Column(String(500), comment="檔案路徑")
    file_size = Column(Integer, comment="檔案大小(bytes)")
    mime_type = Column(String(100), comment="MIME類型")

    # 擴充欄位 (2026-01-06 新增)
    storage_type = Column(String(20), default='local', comment="儲存類型: local/network/s3")
    original_name = Column(String(255), comment="原始檔案名稱")
    checksum = Column(String(64), index=True, comment="SHA256 校驗碼")
    uploaded_by = Column(Integer, ForeignKey('users.id', ondelete="SET NULL"), comment="上傳者 ID")

    # 系統欄位
    created_at = Column(DateTime, server_default=func.now(), comment="建立時間")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新時間")

    # 關聯關係
    document = relationship("OfficialDocument", back_populates="attachments")
    # uploader relationship 暫時移除 (因循環引用問題)
    # 若需取得上傳者資訊，可透過 uploaded_by 查詢 User

    # 屬性別名（向後相容 files.py API）
    @property
    def filename(self):
        return self.file_name

    @filename.setter
    def filename(self, value):
        self.file_name = value

    @property
    def content_type(self):
        return self.mime_type

    @content_type.setter
    def content_type(self, value):
        self.mime_type = value

    # 虛擬屬性（files.py API 使用，但資料庫沒有這些欄位）
    @property
    def is_deleted(self):
        return False

    @property
    def uploaded_at(self):
        return self.created_at

    # uploaded_by 已是 Column 定義，不需要 property 覆蓋

# ProjectUserAssignment Class 定義暫時移除以避免與 Table 定義衝突

class EventReminder(Base):
    """事件提醒模型 - 與資料庫 schema 完整對齊"""
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

    # 資料庫新增欄位 - Schema 對齊
    recipient_email = Column(String(100), comment="接收者Email")
    notification_type = Column(String(50), nullable=False, default="email", comment="通知類型")
    reminder_minutes = Column(Integer, comment="提前提醒分鐘數")
    title = Column(String(200), comment="提醒標題")
    sent_at = Column(DateTime, nullable=True, comment="發送時間")
    max_retries = Column(Integer, nullable=False, default=3, comment="最大重試次數")

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
    data = Column(JSONB, nullable=True, comment="附加資料 (severity, source_table, source_id, changes, user_name)")

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


class ProjectAgencyContact(Base):
    """專案機關承辦模型 - 記錄委託單位的承辦人資訊"""
    __tablename__ = "project_agency_contacts"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('contract_projects.id', ondelete="CASCADE"), nullable=False, index=True, comment="關聯的專案ID")
    contact_name = Column(String(100), nullable=False, comment="承辦人姓名")
    position = Column(String(100), comment="職稱")
    department = Column(String(200), comment="單位/科室")
    phone = Column(String(50), comment="電話")
    mobile = Column(String(50), comment="手機")
    email = Column(String(100), comment="電子郵件")
    is_primary = Column(Boolean, default=False, comment="是否為主要承辦人")
    notes = Column(Text, comment="備註")
    created_at = Column(DateTime, server_default=func.now(), comment="建立時間")
    updated_at = Column(DateTime, server_default=func.now(), comment="更新時間")

    # 關聯關係
    project = relationship("ContractProject", backref="agency_contacts")


class StaffCertification(Base):
    """
    承辦同仁證照紀錄模型
    支援三種類型：核發證照、評量證書、訓練證明
    """
    __tablename__ = "staff_certifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False, index=True, comment="關聯的使用者ID")

    # 證照分類
    cert_type = Column(String(50), nullable=False, comment="證照類型: 核發證照/評量證書/訓練證明")
    cert_name = Column(String(200), nullable=False, comment="證照名稱")

    # 核發資訊
    issuing_authority = Column(String(200), comment="核發機關")
    cert_number = Column(String(100), comment="證照編號")
    issue_date = Column(Date, comment="核發日期")
    expiry_date = Column(Date, comment="有效期限（可為空表示永久有效）")

    # 狀態與備註
    status = Column(String(50), default="有效", comment="狀態: 有效/已過期/已撤銷")
    notes = Column(Text, comment="備註")

    # 附件
    attachment_path = Column(String(500), comment="證照掃描檔路徑")

    # 時間戳
    created_at = Column(DateTime, server_default=func.now(), comment="建立時間")
    updated_at = Column(DateTime, server_default=func.now(), comment="更新時間")

    # 關聯關係
    user = relationship("User", back_populates="certifications")
