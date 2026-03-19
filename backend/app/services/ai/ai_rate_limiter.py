"""
AI 速率限制器

從 base_ai_service.py 拆分 (v3.1.0)
提供滑動窗口速率限制，支援 asyncio-safe 操作。
"""

import asyncio
import time
from collections import deque
from typing import Deque, Optional


class RateLimiter:
    """滑動窗口速率限制器（asyncio-safe）"""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Deque[float] = deque()
        self._lock: Optional[asyncio.Lock] = None

    def _get_lock(self) -> asyncio.Lock:
        """Lazy-init lock within the running event loop"""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def _cleanup(self) -> None:
        """清除過期的請求記錄（需在 lock 內呼叫）"""
        now = time.time()
        while self.requests and self.requests[0] < now - self.window_seconds:
            self.requests.popleft()

    def can_proceed(self) -> bool:
        """檢查是否可以繼續請求（同步，向下相容）"""
        self._cleanup()
        return len(self.requests) < self.max_requests

    def record_request(self) -> None:
        """記錄請求（同步，向下相容）"""
        self.requests.append(time.time())

    async def acquire(self) -> tuple:
        """
        原子性檢查並記錄請求（async-safe）

        Returns:
            (allowed: bool, wait_seconds: float)
        """
        async with self._get_lock():
            self._cleanup()
            if len(self.requests) < self.max_requests:
                self.requests.append(time.time())
                return True, 0.0
            oldest = self.requests[0]
            wait = max(0.0, oldest + self.window_seconds - time.time())
            return False, wait

    def get_wait_time(self) -> float:
        """取得需要等待的時間（秒）"""
        self._cleanup()
        if len(self.requests) < self.max_requests:
            return 0.0
        oldest = self.requests[0]
        return max(0.0, oldest + self.window_seconds - time.time())
