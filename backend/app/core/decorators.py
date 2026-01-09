# -*- coding: utf-8 -*-
"""
通用裝飾器 (Common Decorators)

提供各種實用的裝飾器，用於增強函數行為。

使用範例：
    from app.core.decorators import non_critical, retry_on_failure

    @non_critical
    async def send_notification(...):
        # 此函數失敗不會影響調用方
        pass

    @retry_on_failure(max_retries=3)
    async def call_external_api(...):
        # 此函數會自動重試
        pass
"""
import logging
import functools
import asyncio
from typing import Callable, Any, Optional, TypeVar, ParamSpec

logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')


def non_critical(
    func: Optional[Callable[P, T]] = None,
    *,
    default_return: Any = None,
    log_level: int = logging.WARNING,
    error_message: Optional[str] = None
) -> Callable:
    """
    非關鍵操作裝飾器

    用於包裝非核心業務邏輯（如審計、通知、日誌等），
    確保這些操作失敗時不會影響主業務流程。

    特點：
    1. 捕獲所有異常，防止錯誤傳播
    2. 記錄錯誤到日誌
    3. 返回預設值而非拋出異常
    4. 支援同步和非同步函數

    Args:
        func: 被裝飾的函數
        default_return: 失敗時的預設返回值
        log_level: 錯誤日誌級別
        error_message: 自定義錯誤訊息前綴

    使用範例：
        @non_critical
        async def send_email_notification(user_id: int, message: str):
            # 郵件發送失敗不應影響主操作
            await email_service.send(...)

        @non_critical(default_return=False, log_level=logging.ERROR)
        async def sync_to_external_system(data: dict):
            # 同步失敗時返回 False
            await external_api.sync(data)
    """
    def decorator(fn: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(fn)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await fn(*args, **kwargs)
            except Exception as e:
                msg = error_message or f"非關鍵操作失敗"
                logger.log(log_level, f"[NON_CRITICAL] {msg} - {fn.__name__}: {e}")
                return default_return

        @functools.wraps(fn)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                msg = error_message or f"非關鍵操作失敗"
                logger.log(log_level, f"[NON_CRITICAL] {msg} - {fn.__name__}: {e}")
                return default_return

        if asyncio.iscoroutinefunction(fn):
            return async_wrapper
        return sync_wrapper

    if func is not None:
        return decorator(func)
    return decorator


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> Callable:
    """
    失敗重試裝飾器

    當函數執行失敗時自動重試，支援指數退避。

    Args:
        max_retries: 最大重試次數
        delay: 初始延遲時間（秒）
        backoff: 退避乘數
        exceptions: 需要重試的異常類型
        on_retry: 重試時的回調函數

    使用範例：
        @retry_on_failure(max_retries=3, delay=1.0)
        async def fetch_from_api():
            response = await httpx.get(url)
            return response.json()
    """
    def decorator(fn: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(fn)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return await fn(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        if on_retry:
                            on_retry(e, attempt + 1)
                        logger.warning(
                            f"[RETRY] {fn.__name__} 第 {attempt + 1} 次失敗，"
                            f"{current_delay:.1f}秒後重試: {e}"
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff

            logger.error(f"[RETRY] {fn.__name__} 重試 {max_retries} 次後仍失敗: {last_exception}")
            raise last_exception

        @functools.wraps(fn)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            import time
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        if on_retry:
                            on_retry(e, attempt + 1)
                        logger.warning(
                            f"[RETRY] {fn.__name__} 第 {attempt + 1} 次失敗，"
                            f"{current_delay:.1f}秒後重試: {e}"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff

            logger.error(f"[RETRY] {fn.__name__} 重試 {max_retries} 次後仍失敗: {last_exception}")
            raise last_exception

        if asyncio.iscoroutinefunction(fn):
            return async_wrapper
        return sync_wrapper

    return decorator


def log_execution(
    level: int = logging.INFO,
    include_args: bool = False,
    include_result: bool = False
) -> Callable:
    """
    執行日誌裝飾器

    記錄函數的執行開始、結束和耗時。

    Args:
        level: 日誌級別
        include_args: 是否記錄參數
        include_result: 是否記錄返回值

    使用範例：
        @log_execution(include_args=True)
        async def process_document(doc_id: int):
            # 會記錄: "process_document 開始執行 (doc_id=123)"
            # 會記錄: "process_document 執行完成，耗時 0.05s"
            pass
    """
    def decorator(fn: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(fn)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            import time
            start = time.time()

            args_str = ""
            if include_args:
                args_str = f" (args={args}, kwargs={kwargs})"

            logger.log(level, f"[EXEC] {fn.__name__} 開始執行{args_str}")

            try:
                result = await fn(*args, **kwargs)
                elapsed = time.time() - start

                result_str = ""
                if include_result:
                    result_str = f", result={result}"

                logger.log(level, f"[EXEC] {fn.__name__} 執行完成，耗時 {elapsed:.3f}s{result_str}")
                return result

            except Exception as e:
                elapsed = time.time() - start
                logger.error(f"[EXEC] {fn.__name__} 執行失敗，耗時 {elapsed:.3f}s: {e}")
                raise

        @functools.wraps(fn)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            import time
            start = time.time()

            args_str = ""
            if include_args:
                args_str = f" (args={args}, kwargs={kwargs})"

            logger.log(level, f"[EXEC] {fn.__name__} 開始執行{args_str}")

            try:
                result = fn(*args, **kwargs)
                elapsed = time.time() - start

                result_str = ""
                if include_result:
                    result_str = f", result={result}"

                logger.log(level, f"[EXEC] {fn.__name__} 執行完成，耗時 {elapsed:.3f}s{result_str}")
                return result

            except Exception as e:
                elapsed = time.time() - start
                logger.error(f"[EXEC] {fn.__name__} 執行失敗，耗時 {elapsed:.3f}s: {e}")
                raise

        if asyncio.iscoroutinefunction(fn):
            return async_wrapper
        return sync_wrapper

    return decorator
