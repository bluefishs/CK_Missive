"""
ExportTaskManager - 非同步匯出任務管理器

透過 Redis 追蹤匯出進度，支援前端輪詢。
任務結果暫存 Redis (TTL=30min)，前端下載後自動清理。

@version 1.0.0
@date 2026-02-25
"""

import asyncio
import logging
import uuid
from datetime import datetime
from io import BytesIO
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)

# Redis key 前綴
EXPORT_TASK_PREFIX = "export_task:"
EXPORT_RESULT_PREFIX = "export_result:"
TASK_TTL = 1800  # 30 分鐘

# 進度狀態
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

# 記憶體暫存 (Redis 不存二進位大物件，改用本地字典)
_result_store: Dict[str, bytes] = {}


class ExportTaskManager:
    """非同步匯出任務管理器"""

    @staticmethod
    async def submit_export(
        db: AsyncSession,
        contract_project_id: Optional[int] = None,
        work_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> str:
        """提交非同步匯出任務，回傳 task_id"""
        task_id = str(uuid.uuid4())[:12]

        redis = await get_redis()
        if redis:
            await redis.hset(f"{EXPORT_TASK_PREFIX}{task_id}", mapping={
                "status": STATUS_PENDING,
                "progress": "0",
                "total": "0",
                "message": "排隊中...",
                "created_at": datetime.now().isoformat(),
            })
            await redis.expire(f"{EXPORT_TASK_PREFIX}{task_id}", TASK_TTL)

        # 啟動背景任務
        asyncio.create_task(
            ExportTaskManager._run_export(
                task_id, db, contract_project_id, work_type, search
            )
        )

        return task_id

    @staticmethod
    async def get_progress(task_id: str) -> Optional[Dict[str, Any]]:
        """查詢任務進度"""
        redis = await get_redis()
        if not redis:
            return None

        data = await redis.hgetall(f"{EXPORT_TASK_PREFIX}{task_id}")
        if not data:
            return None

        return {
            "task_id": task_id,
            "status": data.get("status", STATUS_PENDING),
            "progress": int(data.get("progress", 0)),
            "total": int(data.get("total", 0)),
            "message": data.get("message", ""),
            "filename": data.get("filename", ""),
        }

    @staticmethod
    async def get_result(task_id: str) -> Optional[BytesIO]:
        """取得完成的匯出結果 (取後即刪)"""
        result_bytes = _result_store.pop(task_id, None)
        if result_bytes is None:
            return None

        # 清理 Redis 中的任務記錄
        redis = await get_redis()
        if redis:
            await redis.delete(f"{EXPORT_TASK_PREFIX}{task_id}")

        output = BytesIO(result_bytes)
        output.seek(0)
        return output

    @staticmethod
    async def _update_progress(
        task_id: str,
        status: str,
        progress: int = 0,
        total: int = 0,
        message: str = "",
        filename: str = "",
    ) -> None:
        """更新 Redis 中的任務進度"""
        redis = await get_redis()
        if not redis:
            return

        mapping: Dict[str, str] = {
            "status": status,
            "progress": str(progress),
            "total": str(total),
            "message": message,
        }
        if filename:
            mapping["filename"] = filename

        await redis.hset(f"{EXPORT_TASK_PREFIX}{task_id}", mapping=mapping)

    @staticmethod
    async def _run_export(
        task_id: str,
        db: AsyncSession,
        contract_project_id: Optional[int],
        work_type: Optional[str],
        search: Optional[str],
    ) -> None:
        """背景執行匯出 (asyncio task)"""
        from app.services.taoyuan.dispatch_export_service import DispatchExportService

        try:
            await ExportTaskManager._update_progress(
                task_id, STATUS_RUNNING, message="查詢派工單資料..."
            )

            export_service = DispatchExportService(db)

            # Step 1: 查詢資料
            dispatches = await export_service._query_dispatches(
                contract_project_id=contract_project_id,
                work_type=work_type,
                search=search,
            )
            total = len(dispatches)

            await ExportTaskManager._update_progress(
                task_id, STATUS_RUNNING,
                progress=20, total=total,
                message=f"已查詢 {total} 筆派工單..."
            )

            if total > export_service.__class__.__dict__.get(
                'MAX_EXPORT_ROWS',
                getattr(
                    __import__('app.services.taoyuan.dispatch_export_service', fromlist=['MAX_EXPORT_ROWS']),
                    'MAX_EXPORT_ROWS', 2000
                )
            ):
                await ExportTaskManager._update_progress(
                    task_id, STATUS_FAILED,
                    total=total,
                    message=f"匯出上限 2000 筆，目前 {total} 筆"
                )
                return

            # Step 2: 查詢作業紀錄
            await ExportTaskManager._update_progress(
                task_id, STATUS_RUNNING,
                progress=40, total=total,
                message="查詢作業紀錄..."
            )

            dispatch_ids = [d.id for d in dispatches]
            work_records = await export_service._query_work_records(dispatch_ids) if dispatch_ids else []

            # Step 3: 建構 Excel
            await ExportTaskManager._update_progress(
                task_id, STATUS_RUNNING,
                progress=60, total=total,
                message="建構 Excel 工作表..."
            )

            # 使用完整的 export_master_matrix 流程 (重用內部邏輯)
            output = await export_service.export_master_matrix(
                contract_project_id=contract_project_id,
                work_type=work_type,
                search=search,
            )

            # Step 4: 儲存結果
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            filename = f'dispatch_master_{timestamp}.xlsx'

            _result_store[task_id] = output.getvalue()

            await ExportTaskManager._update_progress(
                task_id, STATUS_COMPLETED,
                progress=100, total=total,
                message="匯出完成",
                filename=filename,
            )

            logger.info(f"[ExportTask] {task_id} 完成: {total} 筆, {len(_result_store[task_id])} bytes")

        except Exception as e:
            logger.exception(f"[ExportTask] {task_id} 失敗")
            await ExportTaskManager._update_progress(
                task_id, STATUS_FAILED,
                message=f"匯出失敗: {str(e)[:200]}"
            )
