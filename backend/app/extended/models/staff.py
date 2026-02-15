"""
6. 專案人員模組 (Project Staff Module)

- ProjectAgencyContact: 專案機關承辦
- StaffCertification: 承辦同仁證照
"""
from ._base import *


class ProjectAgencyContact(Base):
    """專案機關承辦模型 - 記錄委託單位的承辦人資訊（含桃園專案通訊錄擴充欄位）"""
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

    # 桃園專案通訊錄擴充欄位
    line_name = Column(String(100), comment="LINE名稱")
    org_short_name = Column(String(100), comment="單位簡稱")
    category = Column(String(50), comment="類別(機關/乾坤/廠商)")
    cloud_path = Column(String(500), comment="專案雲端路徑")
    related_project_name = Column(String(500), comment="對應工程名稱")

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
