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

    def record_completion(self, provider: str, task: str = "chat"):
        self.completions.labels(provider=provider, task=task).inc()

    def record_fallback(self, from_provider: str, to_provider: str, reason: str = "error"):
        self.fallbacks.labels(
            from_provider=from_provider, to_provider=to_provider, reason=reason,
        ).inc()

    def record_duration(self, provider: str, duration_seconds: float):
        self.duration.labels(provider=provider).observe(duration_seconds)


_instance: Optional[InferenceProviderMetrics] = None


def get_inference_provider_metrics() -> InferenceProviderMetrics:
    global _instance
    if _instance is None:
        _instance = InferenceProviderMetrics()
    return _instance
