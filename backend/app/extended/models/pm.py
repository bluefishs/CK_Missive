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
                       comment="案號 (跨模組橋樑)")
    case_name = Column(String(500), nullable=False, index=True,
                       comment="案名")
    year = Column(Integer, index=True, comment="年度 (民國)")
    category = Column(String(50), comment="案件類別")

    # 業主資訊
    client_name = Column(String(200), comment="業主/委託單位")
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
    staff_members = relationship("PMCaseStaff", back_populates="pm_case",
                                 cascade="all, delete-orphan")


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


class PMCaseStaff(Base):
    """案件人員配置"""
    __tablename__ = "pm_case_staff"

    id = Column(Integer, primary_key=True, index=True)
    pm_case_id = Column(Integer, ForeignKey("pm_cases.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                     nullable=True, index=True, comment="系統使用者 (optional)")

    staff_name = Column(String(100), nullable=False, comment="人員姓名")
    role = Column(String(50), nullable=False,
                  comment="角色: project_manager/engineer/surveyor/assistant/other")
    is_primary = Column(Boolean, default=False, comment="是否主要負責人")
    start_date = Column(Date, comment="起始日期")
    end_date = Column(Date, comment="結束日期")
    notes = Column(String(300), comment="備註")

    created_at = Column(DateTime, server_default=func.now())

    # 關聯
    pm_case = relationship("PMCase", back_populates="staff_members")
