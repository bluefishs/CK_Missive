"""
公開 API 端點 - 無需認證
"""
from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/calendar-status")
async def get_public_calendar_status():
    """取得行事曆服務狀態（公開端點，無需認證）"""
    
    from app.core.config import settings
    from app.integrations.google_calendar.client import GOOGLE_AVAILABLE
    
    try:
        # 檢查 Google Calendar 配置
        google_configured = bool(
            getattr(settings, 'GOOGLE_CLIENT_ID', None) and 
            getattr(settings, 'GOOGLE_CLIENT_SECRET', None)
        )
        
        google_calendar_status = {
            "available": GOOGLE_AVAILABLE,
            "configured": google_configured,
        }
        
        return {
            "calendar_available": True,
            "google_calendar_integration": google_configured and GOOGLE_AVAILABLE,
            "google_status": google_calendar_status,
            "message": "基本行事曆功能可用" + (", Google 整合已配置" if google_configured and GOOGLE_AVAILABLE else ", Google 整合需另外設定"),
            "features": [
                "本地事件儲存",
                "基本行事曆檢視", 
                "事件提醒"
            ],
            "endpoint_type": "public"
        }
    except Exception as e:
        logger.error(f"Error getting public calendar status: {e}")
        return {
            "calendar_available": False,
            "google_calendar_integration": False,
            "message": f"行事曆服務發生錯誤: {str(e)}",
            "error": True,
            "endpoint_type": "public"
        }

@router.get("/system-info")
async def get_public_system_info():
    """取得系統基本資訊（公開端點，無需認證）"""

    from app.core.config import settings

    return {
        "app_name": settings.APP_NAME,
        "message": "系統運行中",
        "endpoint_type": "public"
    }