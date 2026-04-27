"""Timeout & SLO contracts (SSOT for ADR-0028 / ADR-0030).

This module is the canonical lookup for all timeout values across the codebase.
It does NOT duplicate definitions — it re-exports from `ai_config` (the
authoritative dataclass) and adds derived SLO targets used by Prometheus
alert rules and Hermes GO/NO-GO evaluation.

Why this exists
---------------
- ADR-0028 promised a single `core/timeouts.py` SSOT but it was never built;
  values were left scattered in `ai_config.AIConfig` field defaults, leading
  to the `dead config` smell that ADR-0028 itself warned about.
- ADR-0030 (Hermes GO/NO-GO) needs concrete P95 numbers tied to actual
  enforced timeouts to avoid arbitrary thresholds.

Usage
-----
    from app.core.timeouts import TIMEOUTS, SLO

    async with asyncio.timeout(TIMEOUTS.tool_execution):
        ...

    # In Prometheus alert rule generation:
    threshold = SLO.e2e_p95_seconds

This module is intentionally thin. The SOT remains `ai_config.AIConfig`.
If you need a new timeout, add it to AIConfig and re-export here.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.ai.core.ai_config import AIConfig


_cfg = AIConfig.from_env()


@dataclass(frozen=True)
class TimeoutContract:
    """All timeouts in seconds. Frozen — runtime mutation forbidden."""

    # LLM provider calls
    cloud_llm: int = _cfg.cloud_timeout              # 30s — Groq/NVIDIA
    local_llm: int = _cfg.local_timeout              # 60s — Ollama

    # Search & RAG pipeline
    search_intent: int = _cfg.search_intent_timeout  # 10s
    search_query: int = _cfg.search_query_timeout    # 20s

    # Agent orchestration (per ADR-0028 §timeout contract)
    tool_execution: int = _cfg.agent_tool_timeout    # 15s — single tool call
    stream_e2e: int = _cfg.agent_stream_timeout      # 60s — multi-tool SSE end-to-end
    sync_query: int = _cfg.agent_sync_query_timeout  # 90s — MCP/LINE blocking
    self_reflect: int = _cfg.self_reflect_timeout    # 5s

    # Compaction
    compaction_tier1: int = _cfg.compaction_tier1_timeout  # 10s

    # Database (rooted in core.config.STATEMENT_TIMEOUT, ms → s)
    db_statement: int = 30                            # mirrors STATEMENT_TIMEOUT=30000ms

    @property
    def synthesis(self) -> int:
        """Synthesis = single LLM call producing final answer.

        Bounded by cloud_llm timeout (30s) but Hermes baseline observed
        synthesis at ~10-30s typical. P95 target derived from this.
        """
        return self.cloud_llm  # 30s


@dataclass(frozen=True)
class SLOContract:
    """Service-Level Objectives derived from TimeoutContract.

    Used by:
    - Prometheus alert rule generation (configs/prometheus/alerts.yml)
    - ADR-0030 GO/NO-GO Hermes evaluation
    - Synthetic baseline tests (scripts/checks/synthetic-baseline-inject.py)
    """

    # Single-call SLO (simple Q&A, no tools)
    single_call_p50_seconds: int = 3
    single_call_p95_seconds: int = 8
    single_call_p99_seconds: int = 15

    # Multi-tool agent loop SLO (ADR-0030 #5 P95 proposal)
    e2e_p50_seconds: int = 15
    e2e_p95_seconds: int = 60   # aligned to TIMEOUTS.stream_e2e
    e2e_p99_seconds: int = 90   # aligned to TIMEOUTS.sync_query

    # Per-tool SLO
    tool_call_p95_seconds: int = 15  # aligned to TIMEOUTS.tool_execution

    # Error budget
    error_rate_max_percent: int = 5  # ADR-0030 GO #4
    soul_fidelity_min_percent: int = 70  # ADR-0030 GO #3

    # Composite SLO budget (proposal C: tiered)
    composite_fast_pct: int = 50    # 50% of queries must be < 15s
    composite_slow_pct: int = 95    # 95% of queries must be < 60s


TIMEOUTS = TimeoutContract()
SLO = SLOContract()


__all__ = ["TIMEOUTS", "SLO", "TimeoutContract", "SLOContract"]
