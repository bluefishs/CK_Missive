"""
2. 基礎實體 (Core Entities)

- PartnerVendor: 協力廠商
- ContractProject: 承攬案件
- GovernmentAgency: 政府機關
- User: 使用者
"""
from ._base import *


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
    business_type = Column(String(100), comment="業務類型")
    rating = Column(Integer, comment="評等")
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
    project_code = Column(String(100), unique=True, comment="專案編號")
    category = Column(String(50), comment="案件類別")
    case_nature = Column(String(50), comment="案件性質")
    status = Column(String(50), default="執行中", comment="執行狀態")
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
    has_dispatch_management = Column(Boolean, default=False, server_default="false", comment="啟用派工管理功能")
    client_type = Column(String(20), server_default='agency', comment='委託來源: agency=機關 vendor=廠商 other=其他')

    # 關聯關係
    documents = relationship("OfficialDocument", back_populates="contract_project")
    client_agency_ref = relationship("GovernmentAgency", foreign_keys=[client_agency_id])


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
    tax_id = Column(String(20), nullable=True, unique=True, comment="統一編號")
    is_self = Column(Boolean, server_default="false", nullable=False, comment="是否為本公司")
    parent_agency_id = Column(Integer, ForeignKey('government_agencies.id', ondelete='SET NULL'), nullable=True, comment="上級機關 ID")
    source = Column(String(20), server_default="manual", nullable=False, comment="資料來源: manual/auto/import")
    created_at = Column(DateTime, server_default=func.now(), comment="建立時間")
    updated_at = Column(DateTime, server_default=func.now(), comment="更新時間")

    parent_agency = relationship("GovernmentAgency", remote_side="GovernmentAgency.id", foreign_keys=[parent_agency_id])
    sent_documents = relationship("OfficialDocument", foreign_keys="OfficialDocument.sender_agency_id", back_populates="sender_agency", lazy="dynamic")
    received_documents = relationship("OfficialDocument", foreign_keys="OfficialDocument.receiver_agency_id", back_populates="receiver_agency", lazy="dynamic")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    email = Column(String(100), nullable=False, unique=True, index=True)
    password_hash = Column(String(100), nullable=True)
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

    department = Column(String(100), comment="部門名稱")
    position = Column(String(100), comment="職稱")

    # 帳號鎖定
    failed_login_attempts = Column(Integer, default=0, nullable=False, server_default="0", comment="連續登入失敗次數")
    locked_until = Column(DateTime(timezone=True), nullable=True, comment="帳號鎖定到期時間")

    # 密碼重設
    password_reset_token = Column(String(128), nullable=True, comment="密碼重設 token (SHA-256 hash)")
    password_reset_expires = Column(DateTime(timezone=True), nullable=True, comment="密碼重設 token 過期時間")

    # Email 驗證
    email_verification_token = Column(String(128), nullable=True, comment="Email 驗證 token (SHA-256 hash)")
    email_verification_expires = Column(DateTime(timezone=True), nullable=True, comment="Email 驗證 token 過期時間")

    # MFA 雙因素認證
    mfa_enabled = Column(Boolean, default=False, nullable=False, server_default="false", comment="是否啟用 TOTP MFA")
    mfa_secret = Column(String(64), nullable=True, comment="TOTP secret (base32 encoded)")
    mfa_backup_codes = Column(Text, nullable=True, comment="備用碼 (JSON 格式, SHA-256 hashed)")

    # LINE Login 整合
    line_user_id = Column(String(64), unique=True, nullable=True, index=True, comment="LINE User ID (帳號綁定)")
    line_display_name = Column(String(100), nullable=True, comment="LINE 顯示名稱")

    # 證照關聯
    certifications = relationship("StaffCertification", back_populates="user", cascade="all, delete-orphan")

    # 費用報銷 & 帳本
    expense_invoices = relationship("ExpenseInvoice", back_populates="user")
    finance_ledgers = relationship("FinanceLedger", back_populates="user")
