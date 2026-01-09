# -*- coding: utf-8 -*-
"""
背景任務管理器 (Background Task Manager)

提供統一的背景任務處理機制，用於非關鍵操作如審計日誌、通知發送等。

設計原則：
1. 非阻塞 - 不影響主請求回應時間
2. 失敗隔離 - 背景任務失敗不影響主業務
3. 可追蹤 - 記錄任務執行狀態

使用範例：
    from app.core.background_tasks import BackgroundTaskManager

    # 在 endpoint 中使用
    @router.post("/documents/{doc_id}/update")
    async def update_document(
        doc_id: int,
        background_tasks: BackgroundTasks
    ):
        # 主業務邏輯...

        # 添加背景任務
        BackgroundTaskManager.add_audit_task(
            background_tasks,
            table_name="documents",
            record_id=doc_id,
            action="UPDATE",
            changes=changes,
            user_id=user_id
        )
"""
import logging
from typing import Dict, Any, Optional, Callable
from fastapi import BackgroundTasks
from datetime import datetime

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """
    背景任務管理器

    統一管理所有背景任務，提供：
    - 審計日誌任務
    - 通知發送任務
    - 自定義任務
    """

    # 任務統計
    _stats = {
        "total_tasks": 0,
        "completed_tasks": 0,
        "failed_tasks": 0,
        "last_task_time": None
    }

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """取得任務統計資訊"""
        return cls._stats.copy()

    @classmethod
    def _update_stats(cls, success: bool):
        """更新任務統計"""
        cls._stats["total_tasks"] += 1
        cls._stats["last_task_time"] = datetime.now().isoformat()
        if success:
            cls._stats["completed_tasks"] += 1
        else:
            cls._stats["failed_tasks"] += 1

    @classmethod
    def add_audit_task(
        cls,
        background_tasks: BackgroundTasks,
        table_name: str,
        record_id: int,
        action: str,
        changes: Dict[str, Any],
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
        source: str = "API"
    ):
        """
        添加審計日誌背景任務

        Args:
            background_tasks: FastAPI BackgroundTasks 實例
            table_name: 資料表名稱
            record_id: 記錄 ID
            action: 操作類型 (CREATE/UPDATE/DELETE)
            changes: 變更內容
            user_id: 操作者 ID
            user_name: 操作者名稱
            source: 來源
        """
        async def _audit_task():
            try:
                from app.services.audit_service import AuditService
                result = await AuditService.log_change(
                    table_name=table_name,
                    record_id=record_id,
                    action=action,
                    changes=changes,
                    user_id=user_id,
                    user_name=user_name,
                    source=source
                )
                cls._update_stats(success=result)
                if result:
                    logger.debug(f"[BG_TASK] 審計日誌完成: {table_name}#{record_id}")
            except Exception as e:
                cls._update_stats(success=False)
                logger.warning(f"[BG_TASK] 審計日誌失敗: {e}")

        background_tasks.add_task(_audit_task)
        logger.debug(f"[BG_TASK] 已排程審計任務: {table_name}#{record_id} {action}")

    @classmethod
    def add_notification_task(
        cls,
        background_tasks: BackgroundTasks,
        notification_type: str,
        **kwargs
    ):
        """
        添加通知發送背景任務

        Args:
            background_tasks: FastAPI BackgroundTasks 實例
            notification_type: 通知類型 (critical_change/document_deleted/etc.)
            **kwargs: 通知參數
        """
        async def _notification_task():
            try:
                from app.services.notification_service import NotificationService

                if notification_type == "critical_change":
                    result = await NotificationService.safe_notify_critical_change(
                        document_id=kwargs.get("document_id"),
                        field=kwargs.get("field"),
                        old_value=kwargs.get("old_value", ""),
                        new_value=kwargs.get("new_value", ""),
                        user_id=kwargs.get("user_id"),
                        user_name=kwargs.get("user_name"),
                        table_name=kwargs.get("table_name", "documents")
                    )
                elif notification_type == "document_deleted":
                    result = await NotificationService.safe_notify_document_deleted(
                        document_id=kwargs.get("document_id"),
                        doc_number=kwargs.get("doc_number", ""),
                        subject=kwargs.get("subject", ""),
                        user_id=kwargs.get("user_id"),
                        user_name=kwargs.get("user_name")
                    )
                else:
                    logger.warning(f"[BG_TASK] 未知的通知類型: {notification_type}")
                    result = False

                cls._update_stats(success=result)
                if result:
                    logger.debug(f"[BG_TASK] 通知發送完成: {notification_type}")
            except Exception as e:
                cls._update_stats(success=False)
                logger.warning(f"[BG_TASK] 通知發送失敗: {e}")

        background_tasks.add_task(_notification_task)
        logger.debug(f"[BG_TASK] 已排程通知任務: {notification_type}")

    @classmethod
    def add_custom_task(
        cls,
        background_tasks: BackgroundTasks,
        task_func: Callable,
        task_name: str = "custom_task",
        *args,
        **kwargs
    ):
        """
        添加自定義背景任務

        Args:
            background_tasks: FastAPI BackgroundTasks 實例
            task_func: 任務函數（async 或 sync）
            task_name: 任務名稱（用於日誌）
            *args, **kwargs: 傳遞給任務函數的參數
        """
        import asyncio

        async def _custom_task():
            try:
                if asyncio.iscoroutinefunction(task_func):
                    result = await task_func(*args, **kwargs)
                else:
                    result = task_func(*args, **kwargs)

                cls._update_stats(success=True)
                logger.debug(f"[BG_TASK] 自定義任務完成: {task_name}")
                return result
            except Exception as e:
                cls._update_stats(success=False)
                logger.warning(f"[BG_TASK] 自定義任務失敗 ({task_name}): {e}")

        background_tasks.add_task(_custom_task)
        logger.debug(f"[BG_TASK] 已排程自定義任務: {task_name}")


# 便捷函數
def schedule_audit(
    background_tasks: BackgroundTasks,
    table_name: str,
    record_id: int,
    action: str,
    changes: Dict[str, Any],
    user_id: Optional[int] = None,
    user_name: Optional[str] = None
):
    """便捷函數：排程審計日誌任務"""
    BackgroundTaskManager.add_audit_task(
        background_tasks=background_tasks,
        table_name=table_name,
        record_id=record_id,
        action=action,
        changes=changes,
        user_id=user_id,
        user_name=user_name
    )


def schedule_notification(
    background_tasks: BackgroundTasks,
    notification_type: str,
    **kwargs
):
    """便捷函數：排程通知任務"""
    BackgroundTaskManager.add_notification_task(
        background_tasks=background_tasks,
        notification_type=notification_type,
        **kwargs
    )
