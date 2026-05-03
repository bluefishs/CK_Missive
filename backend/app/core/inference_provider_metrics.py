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
ROUTING_DECISION_METRIC = "inference_routing_decision_total"


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
        # 2026-04-25 (R6): prefer_local routing 決策源觀測（SSOT 審計配套）
        # 解答：「yaml config 到底接管了多少 routing 決策？」
        # v6.7 E1（D1-prep）：加 soul_section_active label
        # 為 5/20 後 ADR-0030 GO/NO-GO 提供「routing 切換 × SOUL section 啟用」交叉資料
        self.routing_decisions = Counter(
            ROUTING_DECISION_METRIC,
            "prefer_local routing decision source (SSOT audit + SOUL mapping)",
            # source: yaml_config / hardcode_fallback / vision / smart_route / caller_explicit
            # prefer_local: true / false (final outcome)
            # soul_section_active: identity / belief_stable / belief_transparent / belief_reflective
            #                      / mixed / none (planner inject 期間哪段 SOUL section 主導)
            ["source", "task_type", "prefer_local", "soul_section_active"],
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

    def record_routing_decision(
        self,
        source: str,
        task_type: str,
        prefer_local: bool,
        soul_section_active: str = "none",
    ):
        """記錄 prefer_local 決策源（R6 / ADR-0030 SSOT 審計配套）。

        Args:
            source: 'yaml_config' | 'hardcode_fallback' | 'vision' | 'smart_route' | 'caller_explicit'
            task_type: chat / planning / ner / classify / ... (空字串回退為 'unknown')
            prefer_local: 最終 prefer_local 結果 (True / False)
            soul_section_active: v6.7 E1（D1-prep）— 'identity' / 'belief_stable' /
                'belief_transparent' / 'belief_reflective' / 'mixed' / 'none'。
                planner inject 期間哪段 SOUL section 主導當下決策；fallback 切 provider
                時可看「人格段落 × routing」交叉趨勢，作為 5/20 後 provider-aware
                persona 校準的測量基線。預設 'none' 兼容舊 callsite。
        """
        self.routing_decisions.labels(
            source=source,
            task_type=task_type or "unknown",
            prefer_local=str(prefer_local).lower(),
            soul_section_active=soul_section_active or "none",
        ).inc()


_instance: Optional[InferenceProviderMetrics] = None


def get_inference_provider_metrics() -> InferenceProviderMetrics:
    global _instance
    if _instance is None:
        _instance = InferenceProviderMetrics()
    return _instance
