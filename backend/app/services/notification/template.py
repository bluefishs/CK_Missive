# -*- coding: utf-8 -*-
"""
通知模板服務
Notification Template Service

提供統一的通知模板管理與渲染功能。
"""
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """通知類型枚舉"""
    # 行事曆相關
    CALENDAR_EVENT_CREATED = "calendar_event_created"
    CALENDAR_EVENT_UPDATED = "calendar_event_updated"
    CALENDAR_EVENT_DELETED = "calendar_event_deleted"
    CALENDAR_REMINDER = "calendar_reminder"

    # 公文相關
    DOCUMENT_ASSIGNED = "document_assigned"
    DOCUMENT_STATUS_CHANGED = "document_status_changed"
    DOCUMENT_DEADLINE_APPROACHING = "document_deadline_approaching"
    DOCUMENT_OVERDUE = "document_overdue"

    # 專案相關
    PROJECT_CREATED = "project_created"
    PROJECT_STATUS_CHANGED = "project_status_changed"
    PROJECT_MEMBER_ADDED = "project_member_added"
    PROJECT_DEADLINE_APPROACHING = "project_deadline_approaching"

    # 系統相關
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    SYSTEM_MAINTENANCE = "system_maintenance"


class NotificationPriority(int, Enum):
    """通知優先級"""
    CRITICAL = 1  # 緊急
    HIGH = 2      # 高
    NORMAL = 3    # 一般
    LOW = 4       # 低


@dataclass
class NotificationTemplate:
    """通知模板"""
    notification_type: NotificationType
    title_template: str
    message_template: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    icon: str = "📢"
    action_url_template: Optional[str] = None


# 預設通知模板
DEFAULT_TEMPLATES: Dict[NotificationType, NotificationTemplate] = {
    NotificationType.CALENDAR_EVENT_CREATED: NotificationTemplate(
        notification_type=NotificationType.CALENDAR_EVENT_CREATED,
        title_template="📅 新事件: {event_title}",
        message_template="新的行事曆事件已建立\n時間: {event_time}\n類型: {event_type}",
        priority=NotificationPriority.NORMAL,
        icon="📅",
        action_url_template="/calendar?event={event_id}"
    ),
    NotificationType.CALENDAR_EVENT_UPDATED: NotificationTemplate(
        notification_type=NotificationType.CALENDAR_EVENT_UPDATED,
        title_template="📅 事件更新: {event_title}",
        message_template="行事曆事件已更新\n時間: {event_time}\n更新者: {updated_by}",
        priority=NotificationPriority.NORMAL,
        icon="📅",
        action_url_template="/calendar?event={event_id}"
    ),
    NotificationType.CALENDAR_REMINDER: NotificationTemplate(
        notification_type=NotificationType.CALENDAR_REMINDER,
        title_template="⏰ 事件提醒: {event_title}",
        message_template="即將開始的事件提醒\n時間: {event_time}\n距離開始: {time_remaining}",
        priority=NotificationPriority.HIGH,
        icon="⏰",
        action_url_template="/calendar?event={event_id}"
    ),
    NotificationType.DOCUMENT_ASSIGNED: NotificationTemplate(
        notification_type=NotificationType.DOCUMENT_ASSIGNED,
        title_template="📋 公文指派: {doc_number}",
        message_template="您有新的公文指派\n主旨: {doc_subject}\n指派者: {assignee}",
        priority=NotificationPriority.HIGH,
        icon="📋",
        action_url_template="/documents/{doc_id}"
    ),
    NotificationType.DOCUMENT_STATUS_CHANGED: NotificationTemplate(
        notification_type=NotificationType.DOCUMENT_STATUS_CHANGED,
        title_template="📝 公文狀態更新: {doc_number}",
        message_template="公文狀態已變更\n主旨: {doc_subject}\n新狀態: {new_status}",
        priority=NotificationPriority.NORMAL,
        icon="📝",
        action_url_template="/documents/{doc_id}"
    ),
    NotificationType.DOCUMENT_DEADLINE_APPROACHING: NotificationTemplate(
        notification_type=NotificationType.DOCUMENT_DEADLINE_APPROACHING,
        title_template="⚠️ 公文即將到期: {doc_number}",
        message_template="公文即將到期\n主旨: {doc_subject}\n到期日: {deadline}\n剩餘時間: {time_remaining}",
        priority=NotificationPriority.HIGH,
        icon="⚠️",
        action_url_template="/documents/{doc_id}"
    ),
    NotificationType.DOCUMENT_OVERDUE: NotificationTemplate(
        notification_type=NotificationType.DOCUMENT_OVERDUE,
        title_template="🚨 公文逾期: {doc_number}",
        message_template="公文已逾期\n主旨: {doc_subject}\n逾期天數: {overdue_days}天",
        priority=NotificationPriority.CRITICAL,
        icon="🚨",
        action_url_template="/documents/{doc_id}"
    ),
    NotificationType.PROJECT_CREATED: NotificationTemplate(
        notification_type=NotificationType.PROJECT_CREATED,
        title_template="🆕 新專案: {project_name}",
        message_template="您已被加入專案\n專案名稱: {project_name}\n角色: {role}",
        priority=NotificationPriority.NORMAL,
        icon="🆕",
        action_url_template="/projects/{project_id}"
    ),
    NotificationType.PROJECT_MEMBER_ADDED: NotificationTemplate(
        notification_type=NotificationType.PROJECT_MEMBER_ADDED,
        title_template="👤 專案成員新增: {project_name}",
        message_template="新成員加入專案\n專案名稱: {project_name}\n新成員: {member_name}",
        priority=NotificationPriority.LOW,
        icon="👤",
        action_url_template="/projects/{project_id}"
    ),
    NotificationType.PROJECT_DEADLINE_APPROACHING: NotificationTemplate(
        notification_type=NotificationType.PROJECT_DEADLINE_APPROACHING,
        title_template="⏳ 專案即將到期: {project_name}",
        message_template="專案即將到期\n專案名稱: {project_name}\n到期日: {deadline}\n剩餘時間: {time_remaining}",
        priority=NotificationPriority.HIGH,
        icon="⏳",
        action_url_template="/projects/{project_id}"
    ),
    NotificationType.SYSTEM_ANNOUNCEMENT: NotificationTemplate(
        notification_type=NotificationType.SYSTEM_ANNOUNCEMENT,
        title_template="📢 系統公告: {title}",
        message_template="{message}",
        priority=NotificationPriority.NORMAL,
        icon="📢"
    ),
    NotificationType.SYSTEM_MAINTENANCE: NotificationTemplate(
        notification_type=NotificationType.SYSTEM_MAINTENANCE,
        title_template="🔧 系統維護通知",
        message_template="系統將於 {start_time} 進行維護\n預計結束時間: {end_time}\n說明: {description}",
        priority=NotificationPriority.CRITICAL,
        icon="🔧"
    ),
}


@dataclass
class RenderedNotification:
    """渲染後的通知"""
    title: str
    message: str
    notification_type: str
    priority: int
    icon: str
    action_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationTemplateService:
    """
    通知模板服務

    提供通知模板的管理與渲染功能。

    Usage:
        service = NotificationTemplateService()

        # 渲染通知
        notification = service.render(
            NotificationType.CALENDAR_EVENT_CREATED,
            event_title="專案會議",
            event_time="2026-01-10 10:00",
            event_type="會議",
            event_id=123
        )
    """

    def __init__(self, custom_templates: Optional[Dict[NotificationType, NotificationTemplate]] = None):
        """
        初始化通知模板服務

        Args:
            custom_templates: 自訂模板，會覆蓋預設模板
        """
        self._templates = DEFAULT_TEMPLATES.copy()
        if custom_templates:
            self._templates.update(custom_templates)

    def register_template(self, template: NotificationTemplate) -> None:
        """
        註冊自訂模板

        Args:
            template: 通知模板
        """
        self._templates[template.notification_type] = template
        logger.info(f"已註冊通知模板: {template.notification_type}")

    def get_template(self, notification_type: NotificationType) -> Optional[NotificationTemplate]:
        """
        獲取模板

        Args:
            notification_type: 通知類型

        Returns:
            通知模板，不存在時回傳 None
        """
        return self._templates.get(notification_type)

    def render(
        self,
        notification_type: NotificationType,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[RenderedNotification]:
        """
        渲染通知

        Args:
            notification_type: 通知類型
            metadata: 額外元資料
            **kwargs: 模板變數

        Returns:
            渲染後的通知，模板不存在時回傳 None
        """
        template = self._templates.get(notification_type)
        if not template:
            logger.warning(f"找不到通知模板: {notification_type}")
            return None

        try:
            # 渲染標題和訊息
            title = self._safe_format(template.title_template, kwargs)
            message = self._safe_format(template.message_template, kwargs)

            # 渲染操作 URL
            action_url = None
            if template.action_url_template:
                action_url = self._safe_format(template.action_url_template, kwargs)

            return RenderedNotification(
                title=title,
                message=message,
                notification_type=notification_type.value,
                priority=template.priority.value,
                icon=template.icon,
                action_url=action_url,
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"渲染通知模板失敗: {e}", exc_info=True)
            return None

    def _safe_format(self, template: str, values: Dict[str, Any]) -> str:
        """
        安全的字串格式化

        Args:
            template: 模板字串
            values: 變數值

        Returns:
            格式化後的字串
        """
        try:
            return template.format(**values)
        except KeyError as e:
            # 若有缺少的變數，使用預設值
            logger.warning(f"模板變數缺失: {e}")
            return template.format_map(SafeDict(values))


class SafeDict(dict):
    """
    安全字典

    用於 str.format_map，缺少 key 時回傳佔位符。
    """
    def __missing__(self, key):
        return f'{{{key}}}'


# 全域單例
_notification_template_service: Optional[NotificationTemplateService] = None


def get_notification_template_service() -> NotificationTemplateService:
    """獲取通知模板服務單例"""
    global _notification_template_service
    if _notification_template_service is None:
        _notification_template_service = NotificationTemplateService()
    return _notification_template_service
