# -*- coding: utf-8 -*-
"""
R6 (v6.9 / 2026-05-09) — ai_connector.AIConnector × CircuitBreaker integration

Tests:
  1. Groq 連續失敗 N 次 → circuit OPEN → 下次 request 直接 skip 走 NVIDIA
  2. Groq 成功 → record_success → circuit 維持 CLOSED
  3. NVIDIA OPEN → skip 走 Ollama
  4. Circuit breaker 失效（patch raise）不破壞既有 fallback
"""
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def reset_circuit_breaker():
    """每個 test 前重置 circuit breaker 避免 cross-test 污染"""
    from app.core.provider_circuit_breaker import get_circuit_breaker
    get_circuit_breaker().reset()
    yield
    get_circuit_breaker().reset()


@pytest.fixture
def connector():
    from app.core.ai_connector import AIConnector
    # 強制提供 keys（測試 fallback 路徑分支）
    c = AIConnector(
        groq_api_key="test_groq_key",
        nvidia_api_key="test_nvidia_key",
    )
    # 強制走 cloud-first（測試 R6 整合，不打真 Ollama）
    # _smart_route_decision 在 prod 會根據 prompt 自動判斷 prefer_local；
    # test 場景固定 False 以隔離 routing decision 變數
    c._smart_route_decision = AsyncMock(return_value=False)
    return c


# ============================================================================
# 1. Groq 連續失敗 → OPEN → 下次 skip
# ============================================================================

@pytest.mark.asyncio
async def test_groq_consecutive_failures_open_circuit(connector):
    """模擬 Groq 5 次連續失敗（threshold=5），第 6 次 request 應 skip 直接走 NVIDIA"""
    from app.core.provider_circuit_breaker import get_circuit_breaker, CircuitState

    cb = get_circuit_breaker()

    # 模擬 5 次 Groq 失敗
    with patch.object(connector, "_groq_completion", new=AsyncMock(side_effect=RuntimeError("groq down"))), \
         patch.object(connector, "_nvidia_completion", new=AsyncMock(return_value="nvidia answer")):
        for _ in range(5):
            result = await connector.chat_completion(
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=10,
            )
            # 每次都會 fallback NVIDIA
            assert result == "nvidia answer"

    # 5 次失敗後 → OPEN
    assert cb.get_state("groq") == CircuitState.OPEN
    assert cb.is_open("groq") is True


@pytest.mark.asyncio
async def test_groq_open_circuit_skips_directly_to_nvidia(connector):
    """已 OPEN 狀態下，下次 request 不該嘗試 Groq（不該呼叫 _groq_completion）"""
    from app.core.provider_circuit_breaker import get_circuit_breaker

    cb = get_circuit_breaker()
    # 手動把 Groq 設為 OPEN
    for _ in range(5):
        cb.record_failure("groq")
    assert cb.is_open("groq")

    groq_mock = AsyncMock(side_effect=RuntimeError("should not be called"))
    nvidia_mock = AsyncMock(return_value="nvidia answer")

    with patch.object(connector, "_groq_completion", new=groq_mock), \
         patch.object(connector, "_nvidia_completion", new=nvidia_mock):
        result = await connector.chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=10,
        )

    # Groq 完全沒被呼叫 — circuit OPEN 直接 skip
    assert groq_mock.call_count == 0
    assert nvidia_mock.call_count == 1
    assert result == "nvidia answer"


# ============================================================================
# 2. Groq 成功 → record_success → circuit 保持 CLOSED
# ============================================================================

@pytest.mark.asyncio
async def test_groq_success_keeps_circuit_closed(connector):
    """Groq 成功時不該觸發 circuit OPEN，failure 計數歸零"""
    from app.core.provider_circuit_breaker import get_circuit_breaker, CircuitState

    cb = get_circuit_breaker()

    with patch.object(connector, "_groq_completion", new=AsyncMock(return_value="groq answer")):
        for _ in range(10):
            result = await connector.chat_completion(
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=10,
            )
            assert result == "groq answer"

    assert cb.get_state("groq") == CircuitState.CLOSED
    assert cb.is_open("groq") is False


# ============================================================================
# 3. NVIDIA OPEN → skip 走 Ollama
# ============================================================================

@pytest.mark.asyncio
async def test_nvidia_open_skips_to_ollama(connector):
    """NVIDIA circuit OPEN 時，request 應走 Groq 失敗 → 跳過 NVIDIA → Ollama"""
    from app.core.provider_circuit_breaker import get_circuit_breaker

    cb = get_circuit_breaker()
    # 預先把 NVIDIA 設為 OPEN
    for _ in range(5):
        cb.record_failure("nvidia")
    assert cb.is_open("nvidia")

    # 同時 Groq 失敗 → 應跳過 NVIDIA → Ollama 接手
    groq_mock = AsyncMock(side_effect=RuntimeError("groq down"))
    nvidia_mock = AsyncMock(side_effect=RuntimeError("should not be called"))
    ollama_mock = AsyncMock(return_value="ollama answer")

    with patch.object(connector, "_groq_completion", new=groq_mock), \
         patch.object(connector, "_nvidia_completion", new=nvidia_mock), \
         patch.object(connector, "_ollama_completion", new=ollama_mock):
        result = await connector.chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=10,
        )

    # NVIDIA 因 OPEN 完全沒被呼叫
    assert nvidia_mock.call_count == 0
    # Ollama 接手
    assert ollama_mock.call_count == 1
    assert result == "ollama answer"


# ============================================================================
# 4. Circuit breaker 失效不破壞既有 fallback
# ============================================================================

@pytest.mark.asyncio
async def test_circuit_breaker_failure_does_not_break_fallback(connector):
    """即使 circuit breaker module 整個壞掉，ai_connector fallback 仍應正常運作"""

    # patch get_circuit_breaker 拋例外（模擬 module 故障）
    with patch(
        "app.core.provider_circuit_breaker.get_circuit_breaker",
        side_effect=RuntimeError("CB broken"),
    ), \
    patch.object(connector, "_groq_completion", new=AsyncMock(return_value="groq answer")):
        result = await connector.chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=10,
        )

    # 即便 CB 失效，Groq 路徑仍正常
    assert result == "groq answer"
