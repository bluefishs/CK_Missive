# -*- coding: utf-8 -*-
"""
資料庫連接池監控器 (Database Connection Pool Monitor)

監控資料庫連接池健康狀態，提供即時指標和告警機制。

使用範例：
    from app.core.db_monitor import DatabaseMonitor

    # 在應用啟動時設置
    @app.on_event("startup")
    async def startup():
        from app.db.database import engine
        DatabaseMonitor.setup(engine)

    # 取得監控指標
    stats = DatabaseMonitor.get_pool_stats()
"""
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class ConnectionEvent:
    """連接事件記錄"""
    event_type: str  # checkout, checkin, invalidate, overflow
    timestamp: float
    duration: Optional[float] = None


class DatabaseMonitor:
    """
    資料庫連接池監控器

    功能：
    - 追蹤連接池使用狀態
    - 記錄連接事件歷史
    - 提供健康指標
    - 告警機制
    """

    # 監控指標
    _metrics = {
        "active_connections": 0,
        "checkout_count": 0,
        "checkin_count": 0,
        "overflow_count": 0,
        "invalidated_count": 0,
        "timeout_count": 0,
        "error_count": 0,
        "total_checkout_time": 0.0,
        "last_checkout_time": None,
        "last_checkin_time": None,
        "monitor_start_time": None
    }

    # 事件歷史（最近 1000 筆）
    _event_history: deque = deque(maxlen=1000)

    # 活躍連接追蹤
    _active_checkouts: Dict[int, float] = {}

    # 告警閾值
    _thresholds = {
        "max_active_connections": 20,
        "max_checkout_time": 30.0,  # 秒
        "error_rate_threshold": 0.1  # 10%
    }

    # 是否已設置
    _is_setup = False

    @classmethod
    def setup(cls, engine):
        """
        設置連接池監控

        Args:
            engine: SQLAlchemy AsyncEngine 實例
        """
        if cls._is_setup:
            logger.warning("[DB_MONITOR] 監控器已設置，跳過重複設置")
            return

        try:
            from sqlalchemy import event

            # 取得同步引擎用於事件監聽
            sync_engine = engine.sync_engine

            # 註冊事件監聽器
            event.listen(sync_engine, "checkout", cls._on_checkout)
            event.listen(sync_engine, "checkin", cls._on_checkin)
            event.listen(sync_engine, "invalidate", cls._on_invalidate)

            cls._metrics["monitor_start_time"] = datetime.now().isoformat()
            cls._is_setup = True
            logger.info("[DB_MONITOR] 連接池監控器已啟動")

        except Exception as e:
            logger.error(f"[DB_MONITOR] 設置失敗: {e}", exc_info=True)

    @classmethod
    def _on_checkout(cls, dbapi_conn, connection_record, connection_proxy):
        """連接被取出時觸發"""
        now = time.time()
        conn_id = id(dbapi_conn)

        cls._metrics["checkout_count"] += 1
        cls._metrics["active_connections"] += 1
        cls._metrics["last_checkout_time"] = datetime.now().isoformat()
        cls._active_checkouts[conn_id] = now

        cls._event_history.append(ConnectionEvent(
            event_type="checkout",
            timestamp=now
        ))

        # 檢查是否超過閾值
        if cls._metrics["active_connections"] > cls._thresholds["max_active_connections"]:
            logger.warning(
                f"[DB_MONITOR] 活躍連接數過高: {cls._metrics['active_connections']} "
                f"(閾值: {cls._thresholds['max_active_connections']})"
            )

    @classmethod
    def _on_checkin(cls, dbapi_conn, connection_record):
        """連接被歸還時觸發"""
        now = time.time()
        conn_id = id(dbapi_conn)

        cls._metrics["checkin_count"] += 1
        cls._metrics["active_connections"] = max(0, cls._metrics["active_connections"] - 1)
        cls._metrics["last_checkin_time"] = datetime.now().isoformat()

        # 計算使用時間
        checkout_time = cls._active_checkouts.pop(conn_id, None)
        duration = now - checkout_time if checkout_time else None

        if duration:
            cls._metrics["total_checkout_time"] += duration

            # 檢查是否超時
            if duration > cls._thresholds["max_checkout_time"]:
                logger.warning(
                    f"[DB_MONITOR] 連接使用時間過長: {duration:.2f}s "
                    f"(閾值: {cls._thresholds['max_checkout_time']}s)"
                )

        cls._event_history.append(ConnectionEvent(
            event_type="checkin",
            timestamp=now,
            duration=duration
        ))

    @classmethod
    def _on_invalidate(cls, dbapi_conn, connection_record, exception):
        """連接被標記為無效時觸發"""
        now = time.time()
        conn_id = id(dbapi_conn)

        cls._metrics["invalidated_count"] += 1
        cls._metrics["error_count"] += 1
        cls._active_checkouts.pop(conn_id, None)

        cls._event_history.append(ConnectionEvent(
            event_type="invalidate",
            timestamp=now
        ))

        logger.warning(f"[DB_MONITOR] 連接被標記為無效: {exception}")

    @classmethod
    def get_pool_stats(cls) -> Dict[str, Any]:
        """
        取得連接池統計資訊

        Returns:
            包含各項指標的字典
        """
        avg_checkout_time = 0.0
        if cls._metrics["checkin_count"] > 0:
            avg_checkout_time = cls._metrics["total_checkout_time"] / cls._metrics["checkin_count"]

        error_rate = 0.0
        total_operations = cls._metrics["checkout_count"]
        if total_operations > 0:
            error_rate = cls._metrics["error_count"] / total_operations

        return {
            "is_monitoring": cls._is_setup,
            "active_connections": cls._metrics["active_connections"],
            "checkout_count": cls._metrics["checkout_count"],
            "checkin_count": cls._metrics["checkin_count"],
            "invalidated_count": cls._metrics["invalidated_count"],
            "error_count": cls._metrics["error_count"],
            "avg_checkout_time": round(avg_checkout_time, 3),
            "error_rate": round(error_rate, 4),
            "last_checkout_time": cls._metrics["last_checkout_time"],
            "last_checkin_time": cls._metrics["last_checkin_time"],
            "monitor_start_time": cls._metrics["monitor_start_time"],
            "thresholds": cls._thresholds.copy()
        }

    @classmethod
    def get_health_status(cls) -> Dict[str, Any]:
        """
        取得連接池健康狀態

        Returns:
            健康狀態評估
        """
        stats = cls.get_pool_stats()
        issues = []
        status = "healthy"

        # 檢查活躍連接數
        if stats["active_connections"] > cls._thresholds["max_active_connections"]:
            issues.append(f"活躍連接數過高: {stats['active_connections']}")
            status = "warning"

        # 檢查錯誤率
        if stats["error_rate"] > cls._thresholds["error_rate_threshold"]:
            issues.append(f"錯誤率過高: {stats['error_rate']*100:.1f}%")
            status = "critical"

        # 檢查平均使用時間
        if stats["avg_checkout_time"] > cls._thresholds["max_checkout_time"] / 2:
            issues.append(f"平均連接時間偏長: {stats['avg_checkout_time']:.2f}s")
            if status == "healthy":
                status = "warning"

        return {
            "status": status,
            "issues": issues,
            "stats": stats,
            "checked_at": datetime.now().isoformat()
        }

    @classmethod
    def get_recent_events(cls, limit: int = 50) -> list:
        """
        取得最近的連接事件

        Args:
            limit: 返回事件數量上限

        Returns:
            事件列表
        """
        events = list(cls._event_history)[-limit:]
        return [
            {
                "type": e.event_type,
                "timestamp": datetime.fromtimestamp(e.timestamp).isoformat(),
                "duration": round(e.duration, 3) if e.duration else None
            }
            for e in events
        ]

    @classmethod
    def reset_metrics(cls):
        """重置監控指標（用於測試）"""
        cls._metrics = {
            "active_connections": 0,
            "checkout_count": 0,
            "checkin_count": 0,
            "overflow_count": 0,
            "invalidated_count": 0,
            "timeout_count": 0,
            "error_count": 0,
            "total_checkout_time": 0.0,
            "last_checkout_time": None,
            "last_checkin_time": None,
            "monitor_start_time": datetime.now().isoformat()
        }
        cls._event_history.clear()
        cls._active_checkouts.clear()
        logger.info("[DB_MONITOR] 監控指標已重置")

    @classmethod
    def set_threshold(cls, key: str, value: float):
        """
        設定告警閾值

        Args:
            key: 閾值名稱
            value: 閾值數值
        """
        if key in cls._thresholds:
            cls._thresholds[key] = value
            logger.info(f"[DB_MONITOR] 閾值已更新: {key} = {value}")
        else:
            logger.warning(f"[DB_MONITOR] 未知的閾值: {key}")
