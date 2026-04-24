"""Regression test — synthesis model 支援 SYNTHESIS_MODEL env 切換

Phase 1 零成本 Qwen 整合：環境變數可將 synthesis 從 llama-3.3-70b 切到
qwen/qwen3-32b（重用 GROQ_API_KEY）。預設未設時不變。
"""
import inspect

from app.services.ai.agent import agent_synthesis


def test_synthesis_uses_env_var_for_model():
    src = inspect.getsource(agent_synthesis)
    assert 'os.getenv("SYNTHESIS_MODEL"' in src, (
        "agent_synthesis 必須支援 SYNTHESIS_MODEL env 切換，"
        "配合 docs/evaluations/qwen3-6-27b-hermes-primary.md 附錄 B"
    )


def test_synthesis_default_is_llama_70b():
    """未設 env 時保持 llama-3.3-70b backward compat（零副作用）"""
    src = inspect.getsource(agent_synthesis)
    assert 'os.getenv("SYNTHESIS_MODEL", "llama-3.3-70b-versatile")' in src, (
        "預設 fallback 必須保留 llama-3.3-70b-versatile，"
        "避免未設 env 時行為改變"
    )


def test_synthesis_logs_resolved_model():
    """synthesis_start log 必須記錄實際使用的 model 以供 shadow baseline 比對"""
    src = inspect.getsource(agent_synthesis)
    # 找 synthesis_start log 行
    lines = [ln for ln in src.splitlines() if "synthesis_start" in ln]
    assert lines, "synthesis_start log 消失"
    # 應該用 %s 或 {synthesis_model} 動態 render 而非 hardcode
    log_line = "\n".join(lines[:2])
    assert "llama-3.3-70b" not in log_line, (
        "synthesis_start log 不應再 hardcode 模型名，否則 shadow baseline 無法區分 provider"
    )
