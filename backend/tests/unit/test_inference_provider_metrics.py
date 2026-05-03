# -*- coding: utf-8 -*-
"""
TDD: Inference Provider Prometheus 指標

驗證：
1. 每次推理記錄 provider + task_type
2. fallback 事件有獨立 counter
3. 可統計 ollama/groq/nvidia 各自用量
"""
import pytest
from prometheus_client import CollectorRegistry


@pytest.fixture
def registry():
    return CollectorRegistry()


@pytest.fixture
def provider_metrics(registry):
    from app.core.inference_provider_metrics import InferenceProviderMetrics
    return InferenceProviderMetrics(registry=registry)


def test_record_provider_usage(provider_metrics, registry):
    """推理完成應記錄 provider counter"""
    provider_metrics.record_completion("ollama", "chat")
    provider_metrics.record_completion("ollama", "ner")
    provider_metrics.record_completion("groq", "chat")

    from app.core.inference_provider_metrics import COMPLETION_METRIC
    c = registry._names_to_collectors.get(COMPLETION_METRIC)
    assert c is not None
    samples = [s for s in c.collect()[0].samples if s.name.endswith("_total")]
    ollama_chat = [s for s in samples if s.labels.get("provider") == "ollama" and s.labels.get("task") == "chat"]
    assert ollama_chat[0].value == 1
    groq_chat = [s for s in samples if s.labels.get("provider") == "groq" and s.labels.get("task") == "chat"]
    assert groq_chat[0].value == 1


def test_record_fallback(provider_metrics, registry):
    """fallback 事件應遞增 fallback counter"""
    provider_metrics.record_fallback("ollama", "groq", "timeout")

    from app.core.inference_provider_metrics import FALLBACK_METRIC
    c = registry._names_to_collectors.get(FALLBACK_METRIC)
    assert c is not None
    samples = [s for s in c.collect()[0].samples if s.name.endswith("_total")]
    assert any(
        s.labels.get("from_provider") == "ollama"
        and s.labels.get("to_provider") == "groq"
        for s in samples
    )


def test_duration_histogram(provider_metrics, registry):
    """推理延遲應記錄到 histogram"""
    provider_metrics.record_duration("ollama", 1.5)

    from app.core.inference_provider_metrics import DURATION_METRIC
    h = registry._names_to_collectors.get(DURATION_METRIC)
    assert h is not None
    count_samples = [s for s in h.collect()[0].samples if s.name.endswith("_count")]
    ollama = [s for s in count_samples if s.labels.get("provider") == "ollama"]
    assert ollama[0].value == 1


# ────────── v6.7 E1（D1-prep）routing_decision soul_section_active label ──────────


def test_record_routing_decision_includes_soul_section_label(provider_metrics, registry):
    """v6.7 E1：routing_decision metric 含 soul_section_active label。"""
    provider_metrics.record_routing_decision(
        source="yaml_config",
        task_type="chat",
        prefer_local=True,
        soul_section_active="belief_stable",
    )
    from app.core.inference_provider_metrics import ROUTING_DECISION_METRIC
    c = registry._names_to_collectors.get(ROUTING_DECISION_METRIC)
    assert c is not None
    samples = [s for s in c.collect()[0].samples if s.name.endswith("_total")]
    matched = [
        s for s in samples
        if s.labels.get("source") == "yaml_config"
        and s.labels.get("task_type") == "chat"
        and s.labels.get("prefer_local") == "true"
        and s.labels.get("soul_section_active") == "belief_stable"
    ]
    assert len(matched) == 1
    assert matched[0].value == 1


def test_record_routing_decision_default_soul_section_is_none(provider_metrics, registry):
    """舊 caller 不傳 soul_section_active → 預設 'none'（向後相容）。"""
    provider_metrics.record_routing_decision(
        source="hardcode_fallback",
        task_type="planning",
        prefer_local=False,
    )
    from app.core.inference_provider_metrics import ROUTING_DECISION_METRIC
    c = registry._names_to_collectors.get(ROUTING_DECISION_METRIC)
    samples = [s for s in c.collect()[0].samples if s.name.endswith("_total")]
    matched = [
        s for s in samples
        if s.labels.get("soul_section_active") == "none"
        and s.labels.get("source") == "hardcode_fallback"
    ]
    assert len(matched) == 1


def test_record_routing_decision_empty_soul_section_falls_back_to_none(provider_metrics, registry):
    """空字串 soul_section_active → 'none'，避免空 label。"""
    provider_metrics.record_routing_decision(
        source="smart_route",
        task_type="ner",
        prefer_local=True,
        soul_section_active="",
    )
    from app.core.inference_provider_metrics import ROUTING_DECISION_METRIC
    c = registry._names_to_collectors.get(ROUTING_DECISION_METRIC)
    samples = [s for s in c.collect()[0].samples if s.name.endswith("_total")]
    matched = [s for s in samples if s.labels.get("soul_section_active") == "none"]
    assert any(s.labels.get("source") == "smart_route" for s in matched)


def test_record_routing_decision_distinguishes_soul_sections(provider_metrics, registry):
    """不同 soul_section_active 應產生不同 sample series。"""
    provider_metrics.record_routing_decision(
        source="yaml_config", task_type="chat", prefer_local=True,
        soul_section_active="identity",
    )
    provider_metrics.record_routing_decision(
        source="yaml_config", task_type="chat", prefer_local=True,
        soul_section_active="belief_reflective",
    )
    from app.core.inference_provider_metrics import ROUTING_DECISION_METRIC
    c = registry._names_to_collectors.get(ROUTING_DECISION_METRIC)
    samples = [s for s in c.collect()[0].samples if s.name.endswith("_total")]
    sections = {
        s.labels.get("soul_section_active") for s in samples
        if s.labels.get("source") == "yaml_config"
    }
    assert "identity" in sections
    assert "belief_reflective" in sections
