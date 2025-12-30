"""
Pydantic schemas for Document Calendar Integration
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class SyncStatusResponse(BaseModel):
    success: bool
    message: str
    google_event_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class DocumentCalendarEventUpdate(BaseModel):
    """Schema for updating a document calendar event"""
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    all_day: Optional[bool] = None
    event_type: Optional[str] = None
    priority: Optional[int] = None
    assigned_user_id: Optional[int] = None