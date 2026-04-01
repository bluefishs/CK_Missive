"""
標案訂閱與追蹤模組

- TenderSubscription: 關鍵字訂閱 (每日自動查詢)
- TenderBookmark: 感興趣標案書籤 (截止提醒)

Version: 1.0.0
Created: 2026-04-01
"""
from ._base import *


class TenderSubscription(Base):
    """標案關鍵字訂閱"""
    __tablename__ = "tender_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(100), nullable=False, comment="訂閱關鍵字")
    category = Column(String(20), nullable=True, comment="分類篩選: 工程/勞務/財物")
    is_active = Column(Boolean, default=True, comment="是否啟用")
    user_id = Column(Integer, nullable=True, comment="訂閱者 ID")
    notify_line = Column(Boolean, default=True, comment="LINE 推播")
    notify_system = Column(Boolean, default=True, comment="系統通知")
    last_checked_at = Column(DateTime, nullable=True, comment="最後查詢時間")
    last_count = Column(Integer, default=0, comment="上次查詢結果數")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class TenderBookmark(Base):
    """標案書籤 (追蹤感興趣的標案)"""
    __tablename__ = "tender_bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(String(50), nullable=False, comment="機關代碼")
    job_number = Column(String(50), nullable=False, comment="標案案號")
    title = Column(String(500), nullable=False, comment="標案名稱")
    unit_name = Column(String(200), nullable=True, comment="招標機關")
    budget = Column(String(100), nullable=True, comment="預算金額")
    deadline = Column(String(50), nullable=True, comment="截止日期")
    status = Column(String(20), default="tracking", comment="追蹤狀態: tracking/applied/won/lost")
    case_code = Column(String(50), nullable=True, comment="關聯案號 (建案後)")
    user_id = Column(Integer, nullable=True, comment="建立者 ID")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_tender_bookmark_unit_job", "unit_id", "job_number", unique=True),
    )
