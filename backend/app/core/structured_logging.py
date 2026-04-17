# -*- coding: utf-8 -*-
"""
結構化日誌配置模組

整合 structlog 提供 JSON 格式的結構化日誌輸出，
便於日誌分析和監控系統整合。

@version 1.0.0
@date 2026-01-15
"""

import logging
import sys
import structlog
from typing import Any, Dict, Optional
from datetime import datetime

from app.core.config import settings


def add_app_context(
    logger: logging.Logger,
    method_name: str,
    event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    添加應用程式上下文資訊到日誌

    自動加入版本、環境等資訊。
    """
    event_dict["app_name"] = "CK_Missive"
    event_dict["version"] = "3.0.1"
    event_dict["environment"] = "development" if settings.DEVELOPMENT_MODE else "production"
    return event_dict


def add_timestamp(
    logger: logging.Logger,
    method_name: str,
    event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    添加 ISO 格式時間戳記
    """
    event_dict["timestamp"] = datetime.now().isoformat()
    return event_dict


def configure_structlog(
    json_format: bool = True,
    log_level: str = "INFO"
) -> None:
    """
    配置 structlog + 橋接 stdlib logging。

    全 backend 統一策略：
    - structlog.get_logger() 直接走 structlog pipeline
    - logging.getLogger() (239+ service 檔案) 經由 stdlib integration
      自動被 structlog ProcessorFormatter 格式化
    - 開發環境: colored console 輸出
    - 生產環境: JSON 單行輸出（Loki / ELK 友善）

    Args:
        json_format: 是否使用 JSON 格式輸出 (生產環境建議啟用)
        log_level: 日誌等級
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # 共用前處理器（structlog native + stdlib 共用）
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        add_timestamp,
        add_app_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_format:
        renderer = structlog.processors.JSONRenderer(ensure_ascii=False)
        final_processors = shared_processors + [
            structlog.processors.format_exc_info,
            renderer,
        ]
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)
        final_processors = shared_processors + [renderer]

    # --- 1) 配置 structlog native loggers ---
    structlog.configure(
        processors=final_processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # --- 2) 橋接 stdlib logging → structlog 格式化 ---
    # 讓既有 logging.getLogger(__name__) 的輸出也走 structlog pipeline
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            add_timestamp,
            add_app_context,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            structlog.processors.format_exc_info,
        ],
    )

    # 替換 root logger 的所有 handler formatter
    root = logging.getLogger()
    root.setLevel(numeric_level)

    # 確保至少有 stderr handler
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        root.addHandler(handler)

    for handler in root.handlers:
        handler.setFormatter(formatter)

    # 降低 noisy 第三方庫的 log level
    for noisy in ("httpcore", "httpx", "watchfiles", "asyncio", "multipart"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """
    取得結構化日誌記錄器

    Args:
        name: 記錄器名稱

    Returns:
        structlog.BoundLogger: 結構化日誌記錄器

    Usage:
        logger = get_logger(__name__)
        logger.info("使用者登入", user_id=123, ip="192.168.1.1")
    """
    return structlog.get_logger(name)


class StructuredLogger:
    """
    結構化日誌包裝類別

    提供與現有日誌系統相容的介面，同時輸出結構化日誌。
    """

    def __init__(self, name: str = "app"):
        self.logger = get_logger(name)
        self._context: Dict[str, Any] = {}

    def bind(self, **kwargs) -> "StructuredLogger":
        """
        綁定上下文資訊

        綁定的資訊會自動加入到後續所有日誌中。
        """
        self._context.update(kwargs)
        self.logger = self.logger.bind(**kwargs)
        return self

    def unbind(self, *keys) -> "StructuredLogger":
        """
        解除綁定的上下文資訊
        """
        for key in keys:
            self._context.pop(key, None)
        self.logger = self.logger.unbind(*keys)
        return self

    def debug(self, message: str, **kwargs) -> None:
        """記錄 DEBUG 級別日誌"""
        self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """記錄 INFO 級別日誌"""
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """記錄 WARNING 級別日誌"""
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """記錄 ERROR 級別日誌"""
        self.logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """記錄 CRITICAL 級別日誌"""
        self.logger.critical(message, **kwargs)

    def exception(self, message: str, **kwargs) -> None:
        """記錄例外資訊"""
        self.logger.exception(message, **kwargs)


# 預設配置
# v5.6.0: 統一 JSON 格式（Loki 觀測棧需求，ADR-0019）
# 開發環境亦使用 JSON 確保 Loki 可解析；如需 console 可設 STRUCTLOG_CONSOLE=1
import os as _os
_json_format = _os.getenv("STRUCTLOG_CONSOLE") != "1"
configure_structlog(json_format=_json_format, log_level=settings.LOG_LEVEL)

# 全域日誌實例
structured_logger = StructuredLogger("ck_missive")


# 便捷函數
def log_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **extra
) -> None:
    """
    記錄 API 請求日誌

    Args:
        method: HTTP 方法
        path: 請求路徑
        status_code: 回應狀態碼
        duration_ms: 處理時間 (毫秒)
        **extra: 額外資訊
    """
    structured_logger.info(
        "api_request",
        http_method=method,
        path=path,
        status_code=status_code,
        duration_ms=round(duration_ms, 2),
        **extra
    )


def log_db_operation(
    operation: str,
    table: str,
    duration_ms: float,
    affected_rows: Optional[int] = None,
    **extra
) -> None:
    """
    記錄資料庫操作日誌

    Args:
        operation: 操作類型 (SELECT, INSERT, UPDATE, DELETE)
        table: 表格名稱
        duration_ms: 執行時間 (毫秒)
        affected_rows: 影響的列數
        **extra: 額外資訊
    """
    structured_logger.info(
        "db_operation",
        operation=operation,
        table=table,
        duration_ms=round(duration_ms, 2),
        affected_rows=affected_rows,
        **extra
    )


def log_auth_event(
    event: str,
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    success: bool = True,
    **extra
) -> None:
    """
    記錄認證事件日誌

    Args:
        event: 事件類型 (login, logout, token_refresh, etc.)
        user_id: 使用者 ID
        email: 使用者 Email
        success: 是否成功
        **extra: 額外資訊
    """
    log_func = structured_logger.info if success else structured_logger.warning
    log_func(
        "auth_event",
        event=event,
        user_id=user_id,
        email=email,
        success=success,
        **extra
    )


def log_error_event(
    error_type: str,
    message: str,
    exc_info: Optional[Exception] = None,
    **extra
) -> None:
    """
    記錄錯誤事件日誌

    Args:
        error_type: 錯誤類型
        message: 錯誤訊息
        exc_info: 例外資訊
        **extra: 額外資訊
    """
    if exc_info:
        structured_logger.exception(
            "error_event",
            error_type=error_type,
            error_message=message,
            **extra
        )
    else:
        structured_logger.error(
            "error_event",
            error_type=error_type,
            error_message=message,
            **extra
        )
