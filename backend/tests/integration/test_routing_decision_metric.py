"""
Integration test: routing_decisions Prometheus counter（R6 / ADR-0030 SSOT 審計配套）

解答：「yaml config 到底接管了多少 routing 決策？」
"""
import pytest
from prometheus_client import CollectorRegistry

from app.core.inference_provider_metrics import (
    InferenceProviderMetrics,
    ROUTING_DECISION_METRIC,
)

# prometheus_client 規則：counter 若建立名稱已含 `_total` 後綴，sample 名稱不再疊加
SAMPLE_NAME = ROUTING_DECISION_METRIC


def test_record_routing_decision_yaml_config():
    reg = CollectorRegistry()
    m = InferenceProviderMetrics(registry=reg)
    m.record_routing_decision("yaml_config", "chat", prefer_local=False)
    m.record_routing_decision("yaml_config", "chat", prefer_local=False)

    val = reg.get_sample_value(
        SAMPLE_NAME,
        {"source": "yaml_config", "task_type": "chat", "prefer_local": "false"},
    )
    assert val == 2


def test_record_routing_decision_hardcode_fallback():
    reg = CollectorRegistry()
    m = InferenceProviderMetrics(registry=reg)
    m.record_routing_decision("hardcode_fallback", "ner", prefer_local=True)

    val = reg.get_sample_value(
        SAMPLE_NAME,
        {"source": "hardcode_fallback", "task_type": "ner", "prefer_local": "true"},
    )
    assert val == 1


def test_record_routing_decision_sources_distinct():
    """5 種 source 應各自獨立計量。"""
    reg = CollectorRegistry()
    m = InferenceProviderMetrics(registry=reg)
    for src in ("yaml_config", "hardcode_fallback", "vision", "smart_route", "caller_explicit"):
        m.record_routing_decision(src, "chat", prefer_local=True)

    for src in ("yaml_config", "hardcode_fallback", "vision", "smart_route", "caller_explicit"):
        val = reg.get_sample_value(
            SAMPLE_NAME,
            {"source": src, "task_type": "chat", "prefer_local": "true"},
        )
        assert val == 1, f"source={src} 應有 1 筆"


def test_empty_task_type_falls_back_to_unknown():
    reg = CollectorRegistry()
    m = InferenceProviderMetrics(registry=reg)
    m.record_routing_decision("yaml_config", "", prefer_local=False)

    val = reg.get_sample_value(
        SAMPLE_NAME,
        {"source": "yaml_config", "task_type": "unknown", "prefer_local": "false"},
    )
    assert val == 1, "空 task_type 應 normalized 為 'unknown'"
