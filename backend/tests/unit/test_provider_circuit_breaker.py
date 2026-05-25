# -*- coding: utf-8 -*-
"""
R6 (v6.9 / 2026-05-09) — ProviderCircuitBreaker unit tests

Coverage:
  1. Initial state CLOSED, is_open=False
  2. N consecutive failures → OPEN, is_open=True
  3. Cooldown elapsed → HALF_OPEN, is_open=False (probe)
  4. HALF_OPEN + success → CLOSED
  5. HALF_OPEN + failure → re-OPEN
  6. Sparse failures (outside window) → reset counter, no OPEN
  7. Per-provider isolation
  8. record_success on CLOSED is no-op (idempotent)
  9. reset() clears state
"""
import time
from unittest.mock import patch

import pytest

from app.core.provider_circuit_breaker import (
    CircuitState,
    ProviderCircuitBreaker,
    get_circuit_breaker,
)


@pytest.fixture
def cb():
    """Fresh CB with short cooldown for fast tests"""
    return ProviderCircuitBreaker(
        failure_threshold=3,
        cooldown_s=1,           # 1s cooldown for testing
        failure_window_s=10,    # 10s window
    )


# ============================================================================
# 1. Initial state
# ============================================================================

def test_initial_state_is_closed(cb):
    assert cb.get_state("groq") == CircuitState.CLOSED
    assert cb.is_open("groq") is False


def test_unknown_provider_returns_closed(cb):
    assert cb.is_open("never_seen") is False


# ============================================================================
# 2. N consecutive failures → OPEN
# ============================================================================

def test_n_consecutive_failures_opens_circuit(cb):
    cb.record_failure("groq")
    assert cb.get_state("groq") == CircuitState.CLOSED
    cb.record_failure("groq")
    assert cb.get_state("groq") == CircuitState.CLOSED
    cb.record_failure("groq")  # 3rd → OPEN (threshold=3)
    assert cb.get_state("groq") == CircuitState.OPEN
    assert cb.is_open("groq") is True


def test_open_skips_calls_during_cooldown(cb):
    for _ in range(3):
        cb.record_failure("groq")
    assert cb.is_open("groq") is True

    # Repeated is_open() calls during cooldown — still True
    for _ in range(5):
        assert cb.is_open("groq") is True


# ============================================================================
# 3. Cooldown elapsed → HALF_OPEN
# ============================================================================

def test_cooldown_elapsed_transitions_to_half_open(cb):
    for _ in range(3):
        cb.record_failure("groq")
    assert cb.get_state("groq") == CircuitState.OPEN

    # Wait cooldown
    time.sleep(1.1)

    # is_open() check should auto-transition to HALF_OPEN
    assert cb.is_open("groq") is False  # HALF_OPEN allows probe
    assert cb.get_state("groq") == CircuitState.HALF_OPEN


# ============================================================================
# 4. HALF_OPEN + success → CLOSED
# ============================================================================

def test_half_open_success_closes_circuit(cb):
    for _ in range(3):
        cb.record_failure("groq")
    time.sleep(1.1)
    cb.is_open("groq")  # transition to HALF_OPEN

    cb.record_success("groq")
    assert cb.get_state("groq") == CircuitState.CLOSED
    assert cb.is_open("groq") is False


# ============================================================================
# 5. HALF_OPEN + failure → re-OPEN
# ============================================================================

def test_half_open_failure_reopens(cb):
    for _ in range(3):
        cb.record_failure("groq")
    time.sleep(1.1)
    cb.is_open("groq")  # → HALF_OPEN

    cb.record_failure("groq")
    assert cb.get_state("groq") == CircuitState.OPEN
    assert cb.is_open("groq") is True


# ============================================================================
# 6. Sparse failures (outside window) don't open
# ============================================================================

def test_sparse_failures_outside_window_dont_open():
    """failure_window_s=2 — sleep > window between failures should reset counter"""
    cb = ProviderCircuitBreaker(
        failure_threshold=3, cooldown_s=10, failure_window_s=1,
    )
    cb.record_failure("groq")
    time.sleep(1.2)  # > window
    cb.record_failure("groq")
    time.sleep(1.2)
    cb.record_failure("groq")
    # Each failure is "first" because window expires between them
    # → still CLOSED
    assert cb.get_state("groq") == CircuitState.CLOSED


# ============================================================================
# 7. Per-provider isolation
# ============================================================================

def test_per_provider_isolation(cb):
    for _ in range(3):
        cb.record_failure("groq")
    assert cb.get_state("groq") == CircuitState.OPEN
    assert cb.get_state("nvidia") == CircuitState.CLOSED
    assert cb.is_open("nvidia") is False


# ============================================================================
# 8. record_success on CLOSED is no-op
# ============================================================================

def test_record_success_on_closed_is_idempotent(cb):
    assert cb.get_state("groq") == CircuitState.CLOSED
    cb.record_success("groq")
    cb.record_success("groq")
    assert cb.get_state("groq") == CircuitState.CLOSED


def test_record_success_resets_failure_counter(cb):
    cb.record_failure("groq")
    cb.record_failure("groq")
    cb.record_success("groq")  # resets

    cb.record_failure("groq")
    cb.record_failure("groq")
    # Only 2 since reset → still CLOSED
    assert cb.get_state("groq") == CircuitState.CLOSED


# ============================================================================
# 9. reset()
# ============================================================================

def test_reset_specific_provider(cb):
    for _ in range(3):
        cb.record_failure("groq")
    assert cb.is_open("groq")

    cb.reset("groq")
    assert cb.get_state("groq") == CircuitState.CLOSED
    assert cb.is_open("groq") is False


def test_reset_all_providers(cb):
    for _ in range(3):
        cb.record_failure("groq")
    for _ in range(3):
        cb.record_failure("nvidia")
    assert cb.is_open("groq")
    assert cb.is_open("nvidia")

    cb.reset()
    assert cb.get_state("groq") == CircuitState.CLOSED
    assert cb.get_state("nvidia") == CircuitState.CLOSED


# ============================================================================
# 10. Singleton accessor
# ============================================================================

def test_singleton_accessor():
    cb1 = get_circuit_breaker()
    cb2 = get_circuit_breaker()
    assert cb1 is cb2


# ============================================================================
# 11. Metric emission (best-effort)
# ============================================================================

def test_metric_emission_does_not_break_logic(cb):
    """Even if metrics module fails, circuit breaker logic must work.

    `_safe_emit_metric` wraps `_emit_metric` with outer try/except so that
    even if test patches _emit_metric to raise, state transitions complete.
    """
    with patch.object(
        ProviderCircuitBreaker, "_emit_metric",
        side_effect=RuntimeError("metrics broken"),
    ):
        # State transitions should complete despite metric failure
        for _ in range(3):
            cb.record_failure("groq")
        assert cb.get_state("groq") == CircuitState.OPEN
        assert cb.is_open("groq") is True
