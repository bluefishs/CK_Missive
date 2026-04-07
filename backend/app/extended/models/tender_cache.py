"""
標案本地快取表 — 持久化外部 API 資料

減少 g0v/ezbid 重複呼叫，支援 DB 查詢和統計分析。

Version: 1.0.0
"""
from ._base import *


class TenderRecord(Base):
    """標案主表 — 快取 g0v + ezbid 資料"""
    __tablename__ = "tender_records"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(String(50), nullable=False, index=True, comment="機關代碼")
    job_number = Column(String(100), nullable=True, index=True, comment="標案案號")
    title = Column(String(500), nullable=False, comment="標案名稱")
    unit_name = Column(String(200), nullable=True, comment="招標機關")
    category = Column(String(50), nullable=True, comment="採購類別")
    tender_type = Column(String(100), nullable=True, comment="招標類型")
    budget = Column(Numeric(15, 2), nullable=True, comment="預算金額")
    award_amount = Column(Numeric(15, 2), nullable=True, comment="決標金額")
    announce_date = Column(Date, nullable=True, index=True, comment="公告日期")
    deadline = Column(String(50), nullable=True, comment="截止日期")
    status = Column(String(50), nullable=True, comment="狀態")
    source = Column(String(20), default="pcc", comment="來源: pcc/ezbid")
    ezbid_id = Column(String(50), nullable=True, unique=True, comment="ezbid ID")
    raw_data = Column(Text, nullable=True, comment="原始 JSON")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_tender_record_uid_jn", "unit_id", "job_number", unique=True,
              postgresql_where=text("job_number IS NOT NULL AND job_number != ''")),
        Index("ix_tender_record_date", "announce_date"),
        Index("ix_tender_record_source", "source"),
    )


class TenderCompanyLink(Base):
    """標案×廠商關聯"""
    __tablename__ = "tender_company_links"

    id = Column(Integer, primary_key=True, index=True)
    tender_record_id = Column(Integer, ForeignKey("tender_records.id", ondelete="CASCADE"), nullable=False, index=True)
    company_name = Column(String(200), nullable=False, index=True, comment="廠商名稱")
    role = Column(String(20), default="bidder", comment="角色: winner/bidder")
    amount = Column(Numeric(15, 2), nullable=True, comment="得標金額")

    __table_args__ = (
        Index("ix_tender_company_name_role", "company_name", "role"),
    )
