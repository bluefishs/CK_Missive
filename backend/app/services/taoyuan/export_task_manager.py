"""
ExportTaskManager - 非同步匯出任務管理器

透過 Redis 追蹤匯出進度，支援前端輪詢。
任務結果暫存記憶體 (TTL + 大小限制)，前端下載後自動清理。

@version 1.1.0 - 修復 stale session / 雙重查詢 / 記憶體洩漏 / task_id 驗證
@date 2026-02-25
"""

import asyncio
import logging
import re
import uuid
from datetime import datetime
from io import BytesIO
from typing import Optional, Dict, Any

from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)

# Redis key 前綴
EXPORT_TASK_PREFIX = "export_task:"
TASK_TTL = 1800  # 30 分鐘

# 進度狀態
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

# task_id 格式驗證 (hex, 12 字元)
_TASK_ID_PATTERN = re.compile(r"^[a-f0-9]{12}$")

# 記憶體暫存設定
_MAX_STORE_SIZE = 50  # 最多保留 50 筆結果
_result_store: Dict[str, bytes] = {}
_result_timestamps: Dict[str, float] = {}  # task_id → Unix timestamp


def _validate_task_id(task_id: str) -> bool:
    """驗證 task_id 格式 (防止 Redis key injection)"""
    return bool(_TASK_ID_PATTERN.match(task_id))


def _evict_expired_results() -> None:
    """清除過期或超量的暫存結果"""
    now = datetime.now().timestamp()

    # 1. 清除超過 TTL 的結果
    expired = [
        tid for tid, ts in _result_timestamps.items()
        if now - ts > TASK_TTL
    ]
    for tid in expired:
        _result_store.pop(tid, None)
        _result_timestamps.pop(tid, None)

    # 2. 若仍超過上限，移除最舊的
    while len(_result_store) > _MAX_STORE_SIZE:
        oldest = min(_result_timestamps, key=_result_timestamps.get)
        _result_store.pop(oldest, None)
        _result_timestamps.pop(oldest, None)


class ExportTaskManager:
    """非同步匯出任務管理器"""

    @staticmethod
    async def submit_export(
        db,  # noqa: ANN001 — 僅用於取得 bind URL，不傳入背景任務
        contract_project_id: Optional[int] = None,
        work_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> str:
        """提交非同步匯出任務，回傳 task_id"""
        task_id = uuid.uuid4().hex[:12]

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

        # 啟動背景任務 (使用獨立 session，不依賴請求生命週期)
        asyncio.create_task(
            ExportTaskManager._run_export(
                task_id, contract_project_id, work_type, search
            )
        )

        return task_id

    @staticmethod
    async def get_progress(task_id: str) -> Optional[Dict[str, Any]]:
        """查詢任務進度"""
        if not _validate_task_id(task_id):
            return None

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
        if not _validate_task_id(task_id):
            return None

        result_bytes = _result_store.pop(task_id, None)
        _result_timestamps.pop(task_id, None)
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
        contract_project_id: Optional[int],
        work_type: Optional[str],
        search: Optional[str],
    ) -> None:
        """背景執行匯出 (asyncio task) — 使用獨立 DB session"""
        from app.db.database import AsyncSessionLocal
        from app.services.taoyuan.dispatch_export_service import (
            DispatchExportService,
            MAX_EXPORT_ROWS,
        )

        async with AsyncSessionLocal() as db:
            try:
                await ExportTaskManager._update_progress(
                    task_id, STATUS_RUNNING, message="查詢派工單資料..."
                )

                export_service = DispatchExportService(db)

                # 直接呼叫 export_master_matrix (內含查詢 + 建構 Excel)
                # 避免雙重查詢：不再先 _query_dispatches 再呼叫 export_master_matrix
                await ExportTaskManager._update_progress(
                    task_id, STATUS_RUNNING,
                    progress=30,
                    message="建構 Excel 工作表..."
                )

                output = await export_service.export_master_matrix(
                    contract_project_id=contract_project_id,
                    work_type=work_type,
                    search=search,
                )

                # 儲存結果 (先清理過期項目)
                _evict_expired_results()

                timestamp = datetime.now().strftime('%Y%m%d_%H%M')
                filename = f'dispatch_master_{timestamp}.xlsx'
                result_bytes = output.getvalue()

                _result_store[task_id] = result_bytes
                _result_timestamps[task_id] = datetime.now().timestamp()

                await ExportTaskManager._update_progress(
                    task_id, STATUS_COMPLETED,
                    progress=100,
                    message="匯出完成",
                    filename=filename,
                )

                logger.info(
                    "[ExportTask] %s 完成: %d bytes",
                    task_id, len(result_bytes),
                )

            except ValueError as e:
                # MAX_EXPORT_ROWS 超限等業務錯誤
                logger.warning("[ExportTask] %s 業務錯誤: %s", task_id, e)
                await ExportTaskManager._update_progress(
                    task_id, STATUS_FAILED,
                    message=str(e),
                )
            except Exception:
                logger.exception("[ExportTask] %s 失敗", task_id)
                await ExportTaskManager._update_progress(
                    task_id, STATUS_FAILED,
                    message="匯出過程發生錯誤，請稍後再試",
                )
