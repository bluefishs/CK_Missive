"""
14. 專案管理模組 (PM Module)

獨立於現有公文/派工系統，以 case_code 為跨模組軟參照橋樑。
未來可整包拆分為獨立 FastAPI 服務。

- PMCase: 案件主檔
- PMMilestone: 里程碑
- PMCaseStaff: 案件人員配置

Version: 1.0.0
Created: 2026-03-16
"""
from ._base import *


class PMCase(Base):
    """案件主檔 — PM 模組核心實體"""
    __tablename__ = "pm_cases"

    id = Column(Integer, primary_key=True, index=True)
    case_code = Column(String(50), unique=True, nullable=False, index=True,
                       comment="建案案號 (跨模組橋樑)")
    project_code = Column(String(100), nullable=True, index=True,
                          comment="成案專案編號 (成案後產生，對應 contract_projects.project_code)")
    case_name = Column(String(500), nullable=False, index=True,
                       comment="案名")
    year = Column(Integer, index=True, comment="年度 (民國)")
    category = Column(String(50), comment="計畫類別: 01委辦招標, 02承攬報價")
    case_nature = Column(String(50), nullable=True, comment="作業性質: 01地面測量~11其他類別")

    # 業主資訊
    client_name = Column(String(200), comment="業主/委託單位 (冗餘，供顯示)")
    client_vendor_id = Column(Integer, ForeignKey("partner_vendors.id", ondelete="SET NULL"),
                              nullable=True, index=True, comment="委託單位 FK")
    client_contact = Column(String(100), comment="業主聯絡人")
    client_phone = Column(String(50), comment="業主電話")

    # 合約與金額
    contract_amount = Column(Numeric(15, 2), comment="合約金額")

    # 狀態與進度
    status = Column(String(30), nullable=False, default="planning", index=True,
                    comment="狀態: planning/in_progress/completed/suspended/closed")
    progress = Column(Integer, default=0, comment="進度 (0-100)")

    # 時程
    start_date = Column(Date, comment="開工日期")
    end_date = Column(Date, comment="完工期限")
    actual_end_date = Column(Date, comment="實際完工日期")

    # 其他
    location = Column(String(300), comment="工程地點")
    description = Column(Text, comment="案件說明")
    notes = Column(Text, comment="備註")

    # 建立者 (唯一允許的外部 FK)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                        nullable=True, comment="建立者")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 關聯
    milestones = relationship("PMMilestone", back_populates="pm_case",
                              cascade="all, delete-orphan",
                              order_by="PMMilestone.sort_order")
    # staff_members 已遷移至統一人員表 project_user_assignments (v5.2.0)


class PMMilestone(Base):
    """里程碑"""
    __tablename__ = "pm_milestones"

    id = Column(Integer, primary_key=True, index=True)
    pm_case_id = Column(Integer, ForeignKey("pm_cases.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    milestone_name = Column(String(200), nullable=False, comment="里程碑名稱")
    milestone_type = Column(String(50), index=True,
                            comment="類型: kickoff/design/review/submission/acceptance/warranty/other")
    planned_date = Column(Date, comment="預計日期")
    actual_date = Column(Date, comment="實際完成日期")
    status = Column(String(30), default="pending",
                    comment="狀態: pending/in_progress/completed/overdue/skipped")
    sort_order = Column(Integer, default=0, comment="排序")
    notes = Column(Text, comment="備註")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 關聯
    pm_case = relationship("PMCase", back_populates="milestones")


# PMCaseStaff 已移除 — 資料遷移至 project_user_assignments (v5.2.0)


class PMCaseAttachment(Base):
    """報價紀錄附件 — PM 案件的報價單上傳"""
    __tablename__ = "pm_case_attachments"

    id = Column(Integer, primary_key=True, index=True)
    case_code = Column(String(50), nullable=False, index=True,
                       comment="建案案號 (關聯 pm_cases.case_code)")
    file_name = Column(String(255), nullable=False, comment="檔名")
    file_path = Column(String(500), nullable=False, comment="儲存路徑")
    file_size = Column(Integer, comment="檔案大小 (bytes)")
    mime_type = Column(String(100), comment="MIME 類型")
    original_name = Column(String(255), comment="原始檔名")
    checksum = Column(String(64), index=True, comment="SHA256 校驗碼")
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                         nullable=True, comment="上傳者")
    notes = Column(Text, comment="備註 (如：第一版報價、修正版等)")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
