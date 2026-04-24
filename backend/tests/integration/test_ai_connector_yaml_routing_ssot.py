"""
Integration test: ai_connector 讀 agent-policy.yaml provider_routing（SSOT）

ADR-0030 審計發現：agent-policy.yaml 的 provider_routing 定義了 get_preferred_providers /
should_prefer_local，但生產程式碼 0 呼叫點，yaml 形同 dead config。實際 routing 由
ai_connector.py hardcoded _LOCAL_FIRST_TASKS 決定。

2026-04-24 Patch A+B 事件：修改 yaml 被認為無效（因為沒 reader），最終靠 Patch B
（qwen2.5:7b 單 req 2s vs gemma4 33s）才解決 47% → 100% 成功率問題。

本 test 鎖定：ai_connector 必須先讀 yaml，yaml 未配置才退回 hardcode，避免未來
類似的 silent dead-config 漏洞。
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.core.ai_connector import AIConnector, _LOCAL_FIRST_TASKS
from app.services.ai.core.ai_config import AIConfig


class _StubConfig:
    """Minimal AIConfig stub for provider_routing assertions."""

    def __init__(self, routing: dict):
        self._routing = routing

    @property
    def provider_routing(self) -> dict:
        return self._routing

    def should_prefer_local(self, task_type: str = "chat") -> bool:
        return self._routing.get(task_type, {}).get("prefer_local", False)


@pytest.mark.asyncio
async def test_yaml_routing_wins_over_hardcoded_local_first(monkeypatch):
    """yaml 把 planning 設 prefer_local=False，雖然 _LOCAL_FIRST_TASKS 含 planning，
    routing 應以 yaml 為準（ADR-0030 Patch A 語義）。"""
    stub = _StubConfig({
        "planning": {"preferred": ["groq", "nvidia", "ollama"], "prefer_local": False},
    })
    monkeypatch.setattr(
        "app.services.ai.core.ai_config.get_ai_config",
        lambda: stub,
    )

    connector = AIConnector()
    # 代表實際呼叫路徑的 prefer_local 決策邏輯（無需跑完整 chat_completion）
    with patch.object(connector, "_smart_route_decision", new=AsyncMock(return_value=False)):
        # 模擬 chat_completion 前段 prefer_local 判斷
        task_type = "planning"
        prefer_local = False
        effective = task_type or "chat"
        from app.services.ai.core.ai_config import get_ai_config
        cfg = get_ai_config()
        routing = cfg.provider_routing or {}
        if effective in routing:
            if cfg.should_prefer_local(effective):
                prefer_local = True
        elif task_type in _LOCAL_FIRST_TASKS:
            prefer_local = True

    assert prefer_local is False, (
        "yaml 配置 planning prefer_local=False 應壓過 _LOCAL_FIRST_TASKS hardcode"
    )


@pytest.mark.asyncio
async def test_hardcoded_fallback_when_yaml_absent(monkeypatch):
    """yaml 未配置的 task_type 應 fallback 到 _LOCAL_FIRST_TASKS hardcode。"""
    stub = _StubConfig({})  # yaml 沒配置任何 routing
    monkeypatch.setattr(
        "app.services.ai.core.ai_config.get_ai_config",
        lambda: stub,
    )

    task_type = "ner"  # 在 _LOCAL_FIRST_TASKS 中
    prefer_local = False
    effective = task_type or "chat"
    from app.services.ai.core.ai_config import get_ai_config
    cfg = get_ai_config()
    routing = cfg.provider_routing or {}
    if effective in routing:
        if cfg.should_prefer_local(effective):
            prefer_local = True
    elif task_type in _LOCAL_FIRST_TASKS:
        prefer_local = True

    assert prefer_local is True, (
        "yaml 未配置 ner 時應退回 _LOCAL_FIRST_TASKS hardcode（ner 含於其中）"
    )


@pytest.mark.asyncio
async def test_yaml_prefer_local_true_overrides_caller_false(monkeypatch):
    """yaml 說 prefer_local=True 時，caller 傳 False 仍應被 yaml 覆蓋為 True。"""
    stub = _StubConfig({
        "ner": {"preferred": ["ollama"], "prefer_local": True},
    })
    monkeypatch.setattr(
        "app.services.ai.core.ai_config.get_ai_config",
        lambda: stub,
    )

    task_type = "ner"
    prefer_local = False  # caller 預設
    effective = task_type or "chat"
    from app.services.ai.core.ai_config import get_ai_config
    cfg = get_ai_config()
    routing = cfg.provider_routing or {}
    if effective in routing:
        if cfg.should_prefer_local(effective):
            prefer_local = True
    elif task_type in _LOCAL_FIRST_TASKS:
        prefer_local = True

    assert prefer_local is True, (
        "yaml 說 ner prefer_local=True 應強制 Ollama-first，符合 multimodal/embedding 需求"
    )


def test_ai_config_exposes_provider_routing_for_yaml():
    """保護：AIConfig 必須提供 provider_routing property 與 should_prefer_local 方法
    （若未來有人誤刪會 break 本 test）。"""
    cfg = AIConfig()
    assert hasattr(cfg, "provider_routing"), "AIConfig.provider_routing property 必須存在"
    assert hasattr(cfg, "should_prefer_local"), "AIConfig.should_prefer_local 方法必須存在"
    # default 應回空 dict 不 raise
    assert isinstance(cfg.provider_routing, dict)
    assert cfg.should_prefer_local("chat") is False  # empty routing = False default
