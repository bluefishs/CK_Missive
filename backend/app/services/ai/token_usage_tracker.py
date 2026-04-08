# -*- coding: utf-8 -*-
"""
Token 使用追蹤器 — LLM 呼叫計量 + 預算控制 + 告警

追蹤每次 LLM 呼叫的 input/output tokens，按 provider/model/feature 分類。
支援日/月預算限額，超額時自動 Telegram 告警並可選降級。

Redis 持久化結構:
  token:usage:daily:{date}:{provider}    — Hash: input/output/count/cost
  token:usage:monthly:{month}:{provider} — Hash: input/output/count/cost
  token:budget:daily                     — String: daily limit (tokens)
  token:budget:monthly                   — String: monthly limit (tokens)

Version: 1.0.0
Created: 2026-04-08
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# 預設 Token 單價 (USD per 1K tokens) — 可透過 .env 覆蓋
DEFAULT_PRICING = {
    "ollama": {"input": 0.0, "output": 0.0},           # 本地免費
    "gemma4": {"input": 0.0, "output": 0.0},            # 本地免費
    "groq": {"input": 0.00006, "output": 0.00006},      # Groq free tier / estimate
    "openclaw": {"input": 0.00025, "output": 0.00125},  # Claude Haiku estimate
    "nvidia": {"input": 0.00012, "output": 0.00012},    # NVIDIA NIM estimate
}

# 預設預算 (tokens)
DEFAULT_DAILY_BUDGET = int(os.getenv("TOKEN_DAILY_BUDGET", "500000"))    # 50 萬 tokens/日
DEFAULT_MONTHLY_BUDGET = int(os.getenv("TOKEN_MONTHLY_BUDGET", "10000000"))  # 1000 萬 tokens/月


class TokenUsageTracker:
    """Token 使用追蹤器 (Redis 持久化 + 本地 fallback)"""

    PREFIX = "token:usage"
    BUDGET_PREFIX = "token:budget"

    def __init__(self):
        self._redis = None
        self._local_usage: Dict[str, Dict[str, int]] = {}
        self._alert_sent_today = False

    async def _get_redis(self):
        if self._redis is None:
            try:
                from app.core.redis_client import get_redis
                self._redis = await get_redis()
            except Exception:
                return None
        return self._redis

    async def record(
        self,
        provider: str,
        model: str,
        feature: str,
        input_tokens: int,
        output_tokens: int,
    ) -> Dict[str, Any]:
        """
        記錄一次 LLM 呼叫的 token 用量。

        Returns:
            {"recorded": True, "budget_exceeded": bool, "usage_pct": float}
        """
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")
        total_tokens = input_tokens + output_tokens

        # 計算成本
        pricing = DEFAULT_PRICING.get(provider, DEFAULT_PRICING.get(model, {"input": 0, "output": 0}))
        cost_usd = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1000

        # 寫入 Redis
        try:
            r = await self._get_redis()
            if r:
                pipe = r.pipeline()

                # 日統計
                daily_key = f"{self.PREFIX}:daily:{today}:{provider}"
                pipe.hincrby(daily_key, "input_tokens", input_tokens)
                pipe.hincrby(daily_key, "output_tokens", output_tokens)
                pipe.hincrby(daily_key, "count", 1)
                pipe.hincrbyfloat(daily_key, "cost_usd", cost_usd)
                pipe.expire(daily_key, 86400 * 7)  # 保留 7 天

                # 月統計
                monthly_key = f"{self.PREFIX}:monthly:{month}:{provider}"
                pipe.hincrby(monthly_key, "input_tokens", input_tokens)
                pipe.hincrby(monthly_key, "output_tokens", output_tokens)
                pipe.hincrby(monthly_key, "count", 1)
                pipe.hincrbyfloat(monthly_key, "cost_usd", cost_usd)
                pipe.expire(monthly_key, 86400 * 35)  # 保留 35 天

                # Feature 統計 (日)
                feature_key = f"{self.PREFIX}:daily:{today}:feature:{feature}"
                pipe.hincrby(feature_key, "tokens", total_tokens)
                pipe.hincrby(feature_key, "count", 1)
                pipe.expire(feature_key, 86400 * 7)

                await pipe.execute()
        except Exception as e:
            logger.debug("Token usage Redis write failed: %s", e)
            self._redis = None

        # 本地 fallback
        local_key = f"{today}:{provider}"
        if local_key not in self._local_usage:
            self._local_usage[local_key] = {"input": 0, "output": 0, "count": 0, "cost": 0.0}
        self._local_usage[local_key]["input"] += input_tokens
        self._local_usage[local_key]["output"] += output_tokens
        self._local_usage[local_key]["count"] += 1
        self._local_usage[local_key]["cost"] += cost_usd

        # 預算檢查
        budget_result = await self._check_budget(today, month)

        return {
            "recorded": True,
            "tokens": total_tokens,
            "cost_usd": round(cost_usd, 6),
            **budget_result,
        }

    async def _check_budget(self, today: str, month: str) -> Dict[str, Any]:
        """檢查是否超過預算，超額時發送 Telegram 告警"""
        daily_total = await self._get_daily_total(today)
        monthly_total = await self._get_monthly_total(month)

        daily_pct = daily_total / DEFAULT_DAILY_BUDGET * 100 if DEFAULT_DAILY_BUDGET > 0 else 0
        monthly_pct = monthly_total / DEFAULT_MONTHLY_BUDGET * 100 if DEFAULT_MONTHLY_BUDGET > 0 else 0

        budget_exceeded = daily_pct >= 100 or monthly_pct >= 100
        budget_warning = daily_pct >= 80 or monthly_pct >= 80

        if (budget_exceeded or budget_warning) and not self._alert_sent_today:
            self._alert_sent_today = True
            await self._send_budget_alert(daily_total, monthly_total, daily_pct, monthly_pct)

        return {
            "budget_exceeded": budget_exceeded,
            "daily_usage_pct": round(daily_pct, 1),
            "monthly_usage_pct": round(monthly_pct, 1),
        }

    async def _get_daily_total(self, today: str) -> int:
        """取得當日所有 provider 的 token 總量"""
        try:
            r = await self._get_redis()
            if r:
                total = 0
                async for key in r.scan_iter(f"{self.PREFIX}:daily:{today}:*"):
                    if ":feature:" in key:
                        continue
                    data = await r.hgetall(key)
                    total += int(data.get("input_tokens", 0)) + int(data.get("output_tokens", 0))
                return total
        except Exception:
            pass
        # fallback
        return sum(
            v["input"] + v["output"]
            for k, v in self._local_usage.items()
            if k.startswith(today)
        )

    async def _get_monthly_total(self, month: str) -> int:
        """取得當月所有 provider 的 token 總量"""
        try:
            r = await self._get_redis()
            if r:
                total = 0
                async for key in r.scan_iter(f"{self.PREFIX}:monthly:{month}:*"):
                    data = await r.hgetall(key)
                    total += int(data.get("input_tokens", 0)) + int(data.get("output_tokens", 0))
                return total
        except Exception:
            pass
        return 0

    async def _send_budget_alert(
        self, daily: int, monthly: int, daily_pct: float, monthly_pct: float,
    ) -> None:
        """預算告警推播至 Telegram"""
        admin_chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
        if not admin_chat_id:
            return

        status = "🚨 超額" if daily_pct >= 100 or monthly_pct >= 100 else "⚠️ 接近上限"
        msg = (
            f"{status} Token 用量警報\n\n"
            f"日用量: {daily:,} / {DEFAULT_DAILY_BUDGET:,} ({daily_pct:.1f}%)\n"
            f"月用量: {monthly:,} / {DEFAULT_MONTHLY_BUDGET:,} ({monthly_pct:.1f}%)\n"
            f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        try:
            from app.services.telegram_bot_service import get_telegram_bot_service
            await get_telegram_bot_service().push_message(int(admin_chat_id), msg)
            logger.info("Token budget alert sent to Telegram")
        except Exception as e:
            logger.error("Failed to send token budget alert: %s", e)

    async def get_usage_report(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        取得 token 用量報告。

        Args:
            date: 指定日期 (YYYY-MM-DD)，None 為今天
        """
        today = date or datetime.now().strftime("%Y-%m-%d")
        month = today[:7]

        providers = {}
        try:
            r = await self._get_redis()
            if r:
                async for key in r.scan_iter(f"{self.PREFIX}:daily:{today}:*"):
                    if ":feature:" in key:
                        continue
                    provider = key.split(":")[-1]
                    data = await r.hgetall(key)
                    providers[provider] = {
                        "input_tokens": int(data.get("input_tokens", 0)),
                        "output_tokens": int(data.get("output_tokens", 0)),
                        "count": int(data.get("count", 0)),
                        "cost_usd": round(float(data.get("cost_usd", 0)), 4),
                    }
        except Exception:
            pass

        daily_total = sum(p["input_tokens"] + p["output_tokens"] for p in providers.values())
        daily_cost = sum(p["cost_usd"] for p in providers.values())
        monthly_total = await self._get_monthly_total(month)

        return {
            "date": today,
            "month": month,
            "daily": {
                "total_tokens": daily_total,
                "total_cost_usd": round(daily_cost, 4),
                "budget_tokens": DEFAULT_DAILY_BUDGET,
                "usage_pct": round(daily_total / DEFAULT_DAILY_BUDGET * 100, 1) if DEFAULT_DAILY_BUDGET > 0 else 0,
                "by_provider": providers,
            },
            "monthly": {
                "total_tokens": monthly_total,
                "budget_tokens": DEFAULT_MONTHLY_BUDGET,
                "usage_pct": round(monthly_total / DEFAULT_MONTHLY_BUDGET * 100, 1) if DEFAULT_MONTHLY_BUDGET > 0 else 0,
            },
        }


# Singleton
_tracker: Optional[TokenUsageTracker] = None


def get_token_tracker() -> TokenUsageTracker:
    global _tracker
    if _tracker is None:
        _tracker = TokenUsageTracker()
    return _tracker
