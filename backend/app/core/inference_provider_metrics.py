# -*- coding: utf-8 -*-
"""
Inference Provider Prometheus 指標

追蹤每次 LLM 推理的 provider 使用、fallback 事件和延遲分布。

Metrics:
- inference_completions_total{provider, task}: 推理完成次數
- inference_fallback_total{from_provider, to_provider, reason}: Fallback 事件
- inference_duration_seconds{provider}: 推理延遲 histogram
"""
import logging
from typing import Optional

from prometheus_client import Counter, Histogram, CollectorRegistry, REGISTRY

logger = logging.getLogger(__name__)

COMPLETION_METRIC = "inference_completions_total"
FALLBACK_METRIC = "inference_fallback_total"
DURATION_METRIC = "inference_duration_seconds"
RATE_LIMIT_METRIC = "inference_rate_limit_total"
CONTEXT_ROUTE_METRIC = "inference_context_route_total"


class InferenceProviderMetrics:
    """LLM 推理 provider 指標收集器。"""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        reg = registry or REGISTRY
        self.completions = Counter(
            COMPLETION_METRIC,
            "Total inference completions by provider and task",
            ["provider", "task"],
            registry=reg,
        )
        self.fallbacks = Counter(
            FALLBACK_METRIC,
            "Total inference fallback events",
            ["from_provider", "to_provider", "reason"],
            registry=reg,
        )
        self.duration = Histogram(
            DURATION_METRIC,
            "Inference duration in seconds by provider",
            ["provider"],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
            registry=reg,
        )
        # 2026-04-19: 429/413 等 rate-limit 事件計數（零花費前提下排除 Groq free tier 上限）
        self.rate_limits = Counter(
            RATE_LIMIT_METRIC,
            "Total rate-limit events from LLM providers (429/413 etc.)",
            ["provider", "status_code"],
            registry=reg,
        )
        # 2026-04-19: context-aware routing 決策計數（估 token >閾值直接路由 NVIDIA，繞開 Groq TPM）
        self.context_routes = Counter(
            CONTEXT_ROUTE_METRIC,
            "Context-aware routing decisions (prompt size → provider)",
            ["reason", "target_provider"],
            registry=reg,
        )

    def record_completion(self, provider: str, task: str = "chat"):
        self.completions.labels(provider=provider, task=task).inc()

    def record_fallback(self, from_provider: str, to_provider: str, reason: str = "error"):
        self.fallbacks.labels(
            from_provider=from_provider, to_provider=to_provider, reason=reason,
        ).inc()

    def record_duration(self, provider: str, duration_seconds: float):
        self.duration.labels(provider=provider).observe(duration_seconds)

    def record_rate_limit(self, provider: str, status_code: int):
        """記錄 provider 回 429/413/503 等限流事件（供 Grafana alert）。"""
        self.rate_limits.labels(provider=provider, status_code=str(status_code)).inc()

    def record_context_route(self, reason: str, target_provider: str):
        """記錄 context-aware routing 決策，如 large_prompt → nvidia。"""
        self.context_routes.labels(reason=reason, target_provider=target_provider).inc()


_instance: Optional[InferenceProviderMetrics] = None


def get_inference_provider_metrics() -> InferenceProviderMetrics:
    global _instance
    if _instance is None:
        _instance = InferenceProviderMetrics()
    return _instance
