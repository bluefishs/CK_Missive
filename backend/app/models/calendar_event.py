"""
[DEPRECATED] Legacy 行事曆事件模型

此模型已被 app.extended.models.DocumentCalendarEvent 取代。
calendar_events 和 calendar_sync_logs 資料表從未在生產環境中建立。
所有 Google Calendar 整合已遷移至使用 DocumentCalendarEvent。

保留此檔案僅供參考，將在下一次大版本更新時移除。

@deprecated 使用 DocumentCalendarEvent (app.extended.models) 替代
@version 1.0.0 (deprecated since 2.0.0, 2026-02-11)
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from app.db.database import Base


class SyncStatus(str, Enum):
    """同步狀態枚舉"""
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"
    CONFLICT = "conflict"


class EventStatus(str, Enum):
    """事件狀態枚舉"""
    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class CalendarEvent(Base):
    """行事曆事件模型"""
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    
    # 基本事件資訊
    title = Column(String(200), nullable=False, comment="事件標題")
    description = Column(Text, comment="事件描述")
    location = Column(String(500), comment="事件地點")
    
    # 時間資訊
    start_datetime = Column(DateTime, nullable=False, comment="開始時間")
    end_datetime = Column(DateTime, nullable=False, comment="結束時間")
    timezone = Column(String(50), default="Asia/Taipei", comment="時區")
    is_all_day = Column(Boolean, default=False, comment="是否為全天事件")
    
    # 重複設定
    recurrence_rule = Column(Text, comment="重複規則 (RFC 5545 RRULE)")
    recurrence_id = Column(String(100), comment="重複事件的父事件ID")
    
    # 提醒設定
    reminders = Column(JSON, comment="提醒設定列表")
    
    # 與會者資訊
    attendees = Column(JSON, comment="與會者列表")
    organizer_email = Column(String(200), comment="主辦人郵箱")
    
    # 狀態資訊
    status = Column(SQLEnum(EventStatus), default=EventStatus.CONFIRMED, comment="事件狀態")
    visibility = Column(String(20), default="private", comment="可見性")
    
    # Google Calendar 整合欄位
    google_event_id = Column(String(200), unique=True, comment="Google 事件 ID")
    google_calendar_id = Column(String(200), comment="Google 行事曆 ID")
    google_sync_status = Column(SQLEnum(SyncStatus), default=SyncStatus.PENDING, comment="Google 同步狀態")
    google_last_synced_at = Column(DateTime, comment="Google 最後同步時間")
    google_etag = Column(String(200), comment="Google ETag for conflict detection")
    
    # 系統欄位
    created_at = Column(DateTime, default=datetime.utcnow, comment="建立時間")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新時間")
    
    # 關聯欄位
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="所屬使用者")
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="建立者")
    
    # 業務關聯 (可選)
    document_id = Column(Integer, ForeignKey("documents.id"), comment="關聯公文")
    contract_case_id = Column(Integer, ForeignKey("contract_projects.id"), comment="關聯承攬案件")
    
    # 關係定義 (暫時移除，避免導入問題)
    # user = relationship("User", foreign_keys=[user_id])
    # created_by = relationship("User", foreign_keys=[created_by_id])
    # document = relationship("Document", foreign_keys=[document_id])
    # contract_case = relationship("ContractCase", foreign_keys=[contract_case_id])

    def __repr__(self):
        return f"<CalendarEvent(id={self.id}, title='{self.title}', start='{self.start_datetime}')>"

    def to_dict(self):
        """轉換為字典格式"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'location': self.location,
            'start_datetime': self.start_datetime.isoformat() if self.start_datetime else None,
            'end_datetime': self.end_datetime.isoformat() if self.end_datetime else None,
            'timezone': self.timezone,
            'is_all_day': self.is_all_day,
            'recurrence_rule': self.recurrence_rule,
            'reminders': self.reminders,
            'attendees': self.attendees,
            'status': self.status.value if self.status else None,
            'visibility': self.visibility,
            'google_event_id': self.google_event_id,
            'google_sync_status': self.google_sync_status.value if self.google_sync_status else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'user_id': self.user_id,
            'document_id': self.document_id,
            'contract_case_id': self.contract_case_id,
        }

    def to_google_event(self):
        """轉換為 Google Calendar 事件格式"""
        google_event = {
            'summary': self.title,
            'description': self.description or '',
            'location': self.location or '',
            'start': {
                'dateTime': self.start_datetime.isoformat(),
                'timeZone': self.timezone,
            },
            'end': {
                'dateTime': self.end_datetime.isoformat(),
                'timeZone': self.timezone,
            },
            'status': 'confirmed' if self.status == EventStatus.CONFIRMED else 'tentative',
            'visibility': self.visibility,
        }
        
        # 全天事件處理
        if self.is_all_day:
            google_event['start'] = {'date': self.start_datetime.date().isoformat()}
            google_event['end'] = {'date': self.end_datetime.date().isoformat()}
        
        # 重複規則
        if self.recurrence_rule:
            google_event['recurrence'] = [self.recurrence_rule]
        
        # 提醒設定
        if self.reminders:
            google_event['reminders'] = {
                'useDefault': False,
                'overrides': self.reminders
            }
        
        # 與會者
        if self.attendees:
            google_event['attendees'] = self.attendees
        
        return google_event

    @classmethod
    def from_google_event(cls, google_event: dict, user_id: int):
        """從 Google Calendar 事件建立物件"""
        start = google_event.get('start', {})
        end = google_event.get('end', {})
        
        # 處理時間格式
        if 'dateTime' in start:
            start_datetime = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            end_datetime = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
            is_all_day = False
        else:
            start_datetime = datetime.fromisoformat(start['date'] + 'T00:00:00')
            end_datetime = datetime.fromisoformat(end['date'] + 'T23:59:59')
            is_all_day = True
        
        return cls(
            title=google_event.get('summary', '無標題'),
            description=google_event.get('description', ''),
            location=google_event.get('location', ''),
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            timezone=start.get('timeZone', 'Asia/Taipei'),
            is_all_day=is_all_day,
            recurrence_rule=google_event.get('recurrence', [None])[0],
            attendees=google_event.get('attendees', []),
            organizer_email=google_event.get('organizer', {}).get('email'),
            status=EventStatus.CONFIRMED if google_event.get('status') == 'confirmed' else EventStatus.TENTATIVE,
            visibility=google_event.get('visibility', 'private'),
            google_event_id=google_event['id'],
            google_calendar_id=google_event.get('calendarId'),
            google_sync_status=SyncStatus.SYNCED,
            google_last_synced_at=datetime.utcnow(),
            google_etag=google_event.get('etag'),
            user_id=user_id,
            created_by_id=user_id,
        )


class CalendarSyncLog(Base):
    """行事曆同步日誌"""
    __tablename__ = "calendar_sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    sync_type = Column(String(50), nullable=False, comment="同步類型")  # pull, push, webhook
    operation = Column(String(50), nullable=False, comment="操作類型")  # create, update, delete
    
    event_id = Column(Integer, ForeignKey("calendar_events.id"), comment="關聯事件")
    google_event_id = Column(String(200), comment="Google 事件 ID")
    
    status = Column(SQLEnum(SyncStatus), nullable=False, comment="同步狀態")
    error_message = Column(Text, comment="錯誤訊息")
    
    sync_data = Column(JSON, comment="同步資料")
    
    created_at = Column(DateTime, default=datetime.utcnow, comment="建立時間")
    
    # 關係
    user = relationship("User")
    event = relationship("CalendarEvent")

    def __repr__(self):
        return f"<CalendarSyncLog(id={self.id}, type='{self.sync_type}', status='{self.status}')>"