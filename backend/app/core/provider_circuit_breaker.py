# -*- coding: utf-8 -*-
"""
Provider Circuit Breaker (R6 enhancement, 2026-05-09)

For each LLM provider (groq / nvidia / ollama), track consecutive failures.
After N consecutive failures within window, OPEN circuit for cooldown_s seconds —
during which `is_open(provider)` returns True and ai_connector should skip
that provider directly without paying the retry cost.

Why this matters
----------------
ai_connector.py already has 3-tier Groq → NVIDIA → Ollama fallback (1060L
including 429-no-retry fast-path). But every fallback still costs:
  - 1 connect attempt to dead provider
  - up to MAX_RETRIES wait (Groq) or full cloud_timeout (NVIDIA)
  - cumulative ~5–30s wasted per request when provider is fully down

Circuit breaker eliminates this for sustained outages: after 5 consecutive
failures, skip that provider for 5min until cooldown elapses → HALF_OPEN
(try once); success closes circuit, failure re-opens.

Design
------
- Singleton, in-memory (no Redis dependency).
- Per-provider state: CLOSED / OPEN / HALF_OPEN
- Threadsafe under asyncio (single-thread event loop assumption holds for
  ck-backend since uvicorn runs one worker; for multi-worker setup each
  worker has independent state which is acceptable degradation).
- Metrics: provider_circuit_state gauge (0=closed/1=open/2=half_open) per
  provider, integrated with inference_provider_metrics for alerting.

Example usage in ai_connector
-----------------------------
    from app.core.provider_circuit_breaker import get_circuit_breaker
    cb = get_circuit_breaker()

    # Before attempting Groq
    if cb.is_open("groq"):
        logger.info("Groq circuit OPEN, skip directly to NVIDIA")
    else:
        try:
            result = await self._groq_completion(...)
            cb.record_success("groq")
            return result
        except Exception:
            cb.record_failure("groq")
            # fall through to NVIDIA
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Failing — skip provider for cooldown_s
    HALF_OPEN = "half_open"  # Cooldown elapsed — try once to probe


# Defaults — tunable via constructor
_DEFAULT_FAILURE_THRESHOLD = 5      # N consecutive failures
_DEFAULT_COOLDOWN_S = 300            # 5 min — aligns with Groq TPM reset window
_DEFAULT_FAILURE_WINDOW_S = 60       # failures within 60s count as "consecutive"


@dataclass
class _ProviderState:
    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    first_failure_at: float = 0.0
    opened_at: float = 0.0


class ProviderCircuitBreaker:
    """In-memory circuit breaker for LLM providers.

    Threadsafe under single-threaded asyncio (uvicorn 1-worker default).
    Multi-worker: each worker has independent state, acceptable since
    Groq/NVIDIA rate-limit responses are still deterministic.
    """

    def __init__(
        self,
        failure_threshold: int = _DEFAULT_FAILURE_THRESHOLD,
        cooldown_s: int = _DEFAULT_COOLDOWN_S,
        failure_window_s: int = _DEFAULT_FAILURE_WINDOW_S,
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_s = cooldown_s
        self.failure_window_s = failure_window_s
        self._states: Dict[str, _ProviderState] = {}

    def _get_state(self, provider: str) -> _ProviderState:
        if provider not in self._states:
            self._states[provider] = _ProviderState()
        return self._states[provider]

    def is_open(self, provider: str) -> bool:
        """Return True if the circuit is currently open (skip recommended).

        Auto-transitions OPEN → HALF_OPEN after cooldown_s elapses, allowing
        the next call to probe; on success record_success() closes the circuit.
        """
        st = self._get_state(provider)
        now = time.time()

        if st.state == CircuitState.OPEN:
            if now - st.opened_at >= self.cooldown_s:
                # Cooldown elapsed — allow one probe
                st.state = CircuitState.HALF_OPEN
                logger.info(
                    "Circuit %s: OPEN → HALF_OPEN (cooldown %ds elapsed, probing next call)",
                    provider, self.cooldown_s,
                )
                self._safe_emit_metric(provider, CircuitState.HALF_OPEN)
                return False
            return True

        return False

    def record_success(self, provider: str) -> None:
        """Reset failure counter and close circuit (if was HALF_OPEN/OPEN)."""
        st = self._get_state(provider)
        if st.state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
            logger.info(
                "Circuit %s: %s → CLOSED (probe succeeded)",
                provider, st.state.value,
            )
            self._safe_emit_metric(provider, CircuitState.CLOSED)
        st.state = CircuitState.CLOSED
        st.consecutive_failures = 0
        st.first_failure_at = 0.0
        st.opened_at = 0.0

    def record_failure(self, provider: str) -> None:
        """Increment failure counter; OPEN circuit if threshold reached.

        Failures are "consecutive" only if within failure_window_s of each other —
        sparse failures over hours don't trip the breaker.
        """
        st = self._get_state(provider)
        now = time.time()

        # HALF_OPEN probe failed → re-OPEN
        if st.state == CircuitState.HALF_OPEN:
            st.state = CircuitState.OPEN
            st.opened_at = now
            logger.warning(
                "Circuit %s: HALF_OPEN → OPEN (probe failed, cooldown %ds again)",
                provider, self.cooldown_s,
            )
            self._safe_emit_metric(provider, CircuitState.OPEN)
            return

        # Reset window if last failure too old
        if now - st.first_failure_at > self.failure_window_s:
            st.consecutive_failures = 0
            st.first_failure_at = now

        if st.consecutive_failures == 0:
            st.first_failure_at = now
        st.consecutive_failures += 1

        if st.consecutive_failures >= self.failure_threshold:
            st.state = CircuitState.OPEN
            st.opened_at = now
            logger.warning(
                "Circuit %s: CLOSED → OPEN (%d consecutive failures within %ds, "
                "skip for %ds)",
                provider, st.consecutive_failures, self.failure_window_s,
                self.cooldown_s,
            )
            self._safe_emit_metric(provider, CircuitState.OPEN)

    def get_state(self, provider: str) -> CircuitState:
        """Test helper / introspection."""
        return self._get_state(provider).state

    def reset(self, provider: Optional[str] = None) -> None:
        """Reset to CLOSED. If provider=None, reset all."""
        if provider is None:
            self._states.clear()
        else:
            self._states.pop(provider, None)

    @classmethod
    def _safe_emit_metric(cls, provider: str, state: CircuitState) -> None:
        """Wrapper guaranteeing metric emit failure cannot break circuit logic.

        Even if _emit_metric is patched to raise (test scenario) or metrics
        module is fully broken, the outer wrapper swallows it.
        """
        try:
            cls._emit_metric(provider, state)
        except Exception:
            # Logged elsewhere if metrics module itself logs;
            # circuit breaker logic must remain green.
            pass

    @staticmethod
    def _emit_metric(provider: str, state: CircuitState) -> None:
        """Best-effort emit to inference_provider_metrics gauge.

        State encoding: closed=0, half_open=1, open=2 (rising = worse).
        """
        try:
            from app.core.inference_provider_metrics import get_inference_provider_metrics
            metrics = get_inference_provider_metrics()
            value = {
                CircuitState.CLOSED: 0,
                CircuitState.HALF_OPEN: 1,
                CircuitState.OPEN: 2,
            }[state]
            # Lazy create gauge if not exists
            if not hasattr(metrics, "circuit_state"):
                from prometheus_client import Gauge
                metrics.circuit_state = Gauge(
                    "provider_circuit_state",
                    "Circuit breaker state per provider "
                    "(0=closed, 1=half_open, 2=open)",
                    ["provider"],
                )
            metrics.circuit_state.labels(provider=provider).set(value)
        except Exception:
            # Metrics best-effort — circuit breaker logic must remain functional
            pass


_instance: Optional[ProviderCircuitBreaker] = None


def get_circuit_breaker() -> ProviderCircuitBreaker:
    """Singleton accessor."""
    global _instance
    if _instance is None:
        _instance = ProviderCircuitBreaker()
    return _instance
