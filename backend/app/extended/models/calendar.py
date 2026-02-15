"""
4. 行事曆模組 (Calendar Module)

- DocumentCalendarEvent: 公文行事曆事件
- EventReminder: 事件提醒
"""
from ._base import *


class DocumentCalendarEvent(Base):
    __tablename__ = "document_calendar_events"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey('documents.id', ondelete="SET NULL"), nullable=True, index=True, comment="關聯的公文ID")
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
    status = Column(String(50), default='pending', comment="事件狀態: pending/completed/cancelled")
    google_event_id = Column(String(255), nullable=True, index=True, comment="Google Calendar 事件 ID")
    google_sync_status = Column(String(50), default='pending', comment="同步狀態: pending/synced/failed")

    document = relationship("OfficialDocument", back_populates="calendar_events")
    assigned_user = relationship("User", foreign_keys=[assigned_user_id])
    creator = relationship("User", foreign_keys=[created_by])
    reminders = relationship("EventReminder", back_populates="event", cascade="all, delete-orphan")


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

    recipient_email = Column(String(100), comment="接收者Email")
    notification_type = Column(String(50), nullable=False, default="email", comment="通知類型")
    reminder_minutes = Column(Integer, comment="提前提醒分鐘數")
    title = Column(String(200), comment="提醒標題")
    sent_at = Column(DateTime, nullable=True, comment="發送時間")
    max_retries = Column(Integer, nullable=False, default=3, comment="最大重試次數")

    event = relationship("DocumentCalendarEvent", back_populates="reminders")
    recipient_user = relationship("User", foreign_keys=[recipient_user_id])
