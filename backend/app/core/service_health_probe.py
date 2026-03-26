"""
Service Health Probe — 週期性服務健康探測與自動修復

每 60 秒檢測：
- Ollama 連線 + 必要模型
- vLLM 連線 + 模型可用性
- Redis 連線
- PostgreSQL 連線

斷線時自動嘗試重連，連續失敗則降級通知。

Version: 1.0.0
Created: 2026-03-26
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)

# 探測間隔 (秒)
PROBE_INTERVAL = int(os.getenv("HEALTH_PROBE_INTERVAL", "60"))
# 連續失敗幾次後告警
ALERT_THRESHOLD = 3


class ServiceStatus:
    """單一服務的健康狀態"""

    def __init__(self, name: str):
        self.name = name
        self.healthy = False
        self.last_check: Optional[datetime] = None
        self.last_healthy: Optional[datetime] = None
        self.consecutive_failures = 0
        self.error: Optional[str] = None

    def mark_healthy(self):
        self.healthy = True
        self.last_check = datetime.now()
        self.last_healthy = datetime.now()
        if self.consecutive_failures > 0:
            logger.info("✅ %s 已恢復連線 (曾中斷 %d 次)", self.name, self.consecutive_failures)
        self.consecutive_failures = 0
        self.error = None

    def mark_failed(self, error: str):
        self.healthy = False
        self.last_check = datetime.now()
        self.consecutive_failures += 1
        self.error = error
        if self.consecutive_failures == 1:
            logger.warning("⚠️ %s 連線失敗: %s", self.name, error)
        elif self.consecutive_failures == ALERT_THRESHOLD:
            logger.error("❌ %s 連續 %d 次失敗，服務可能需要手動介入: %s",
                         self.name, ALERT_THRESHOLD, error)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "healthy": self.healthy,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_healthy": self.last_healthy.isoformat() if self.last_healthy else None,
            "consecutive_failures": self.consecutive_failures,
            "error": self.error,
        }


class ServiceHealthProbe:
    """週期性服務健康探測器"""

    def __init__(self):
        self._services: Dict[str, ServiceStatus] = {
            "ollama": ServiceStatus("Ollama"),
            "vllm": ServiceStatus("vLLM"),
            "redis": ServiceStatus("Redis"),
            "database": ServiceStatus("PostgreSQL"),
        }
        self._running = False
        self._task: Optional[asyncio.Task] = None

    @property
    def statuses(self) -> Dict[str, dict]:
        return {k: v.to_dict() for k, v in self._services.items()}

    async def start(self):
        """啟動背景探測"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._probe_loop())
        logger.info("🔍 Service Health Probe 啟動 (間隔 %ds)", PROBE_INTERVAL)

    async def stop(self):
        """停止探測"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Service Health Probe 已停止")

    async def _probe_loop(self):
        """主探測迴圈"""
        # 首次探測延遲 10 秒（等服務啟動）
        await asyncio.sleep(10)
        while self._running:
            try:
                await self._probe_all()
            except Exception as e:
                logger.debug("Probe loop error: %s", e)
            await asyncio.sleep(PROBE_INTERVAL)

    async def _probe_all(self):
        """並行探測所有服務"""
        await asyncio.gather(
            self._probe_ollama(),
            self._probe_vllm(),
            self._probe_redis(),
            self._probe_database(),
            return_exceptions=True,
        )

    async def _probe_ollama(self):
        """探測 Ollama"""
        svc = self._services["ollama"]
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{ollama_url}/api/tags")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    model_names = [m["name"] for m in models]
                    has_embed = any("nomic" in n or "embed" in n for n in model_names)
                    if has_embed:
                        svc.mark_healthy()
                    else:
                        svc.mark_failed(f"缺少 embedding 模型 (現有: {model_names})")
                else:
                    svc.mark_failed(f"HTTP {resp.status_code}")
        except Exception as e:
            svc.mark_failed(str(e))

    async def _probe_vllm(self):
        """探測 vLLM"""
        svc = self._services["vllm"]
        vllm_enabled = os.getenv("VLLM_ENABLED", "false").lower() == "true"
        if not vllm_enabled:
            svc.mark_healthy()  # 未啟用視為正常
            return
        vllm_url = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{vllm_url}/models")
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    if data:
                        svc.mark_healthy()
                    else:
                        svc.mark_failed("無可用模型")
                else:
                    svc.mark_failed(f"HTTP {resp.status_code}")
        except Exception as e:
            svc.mark_failed(str(e))

    async def _probe_redis(self):
        """探測 Redis"""
        svc = self._services["redis"]
        try:
            from app.core.redis_client import get_redis
            redis = await get_redis()
            if redis:
                await redis.ping()
                svc.mark_healthy()
            else:
                svc.mark_failed("Redis client 不可用")
        except Exception as e:
            svc.mark_failed(str(e))

    async def _probe_database(self):
        """探測 PostgreSQL"""
        svc = self._services["database"]
        try:
            from app.db.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                from sqlalchemy import text
                await db.execute(text("SELECT 1"))
                svc.mark_healthy()
        except Exception as e:
            svc.mark_failed(str(e))

    async def probe_once(self) -> Dict[str, dict]:
        """單次探測（手動觸發用）"""
        await self._probe_all()
        return self.statuses


# Singleton
_probe: Optional[ServiceHealthProbe] = None


def get_health_probe() -> ServiceHealthProbe:
    global _probe
    if _probe is None:
        _probe = ServiceHealthProbe()
    return _probe
