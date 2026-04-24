"""
Regression：agent_orchestrator 的 planner 並行 gather 必須有 hard cap。

事故 2026-04-22：LLM planner 路徑（含 Redis scan、capability_profile、
adaptive few-shot、cross-session learning 注入等多個 await）任一卡住即死鎖，
preprocessing 後 silent gap 直到前端 60s timeout → 用戶「無回應」。
修復：外層 asyncio.wait_for(gather(...), timeout=PLANNER_HARD_CAP=25)。
"""
import re
from pathlib import Path


def _read_orchestrator() -> str:
    p = Path(__file__).resolve().parents[2] / "app" / "services" / "ai" / "agent" / "agent_orchestrator.py"
    return p.read_text(encoding="utf-8")


def test_planner_gather_wrapped_in_wait_for():
    """asyncio.gather(preprocess_question + plan_tools) 必須在 asyncio.wait_for 內"""
    src = _read_orchestrator()
    # 粗粒度但穩健：planner section 必須同時含 wait_for 和 PLANNER_HARD_CAP
    assert "PLANNER_HARD_CAP" in src, "應定義 PLANNER_HARD_CAP 常數"
    assert "asyncio.wait_for" in src
    # 確認 gather 在 wait_for 的 awaitable 內（regex 跨行）
    pattern = re.compile(
        r"asyncio\.wait_for\([\s\S]*?asyncio\.gather\([\s\S]*?preprocess_question",
        re.MULTILINE,
    )
    assert pattern.search(src), (
        "preprocess+plan_tools 並行 gather 必須被 asyncio.wait_for 包住防死鎖"
    )


def test_planner_timeout_logs_warning():
    """timeout 路徑要 log warning 讓事故可觀測"""
    src = _read_orchestrator()
    assert "Planner 整體超時" in src or "planner hard cap" in src.lower()


def test_planner_timeout_falls_back_not_raises():
    """timeout 時必須 hints=None, plan=None 讓後續 stream_fallback_rag 接手，不是 raise"""
    src = _read_orchestrator()
    # 確認 except TimeoutError 後設為 None
    assert re.search(
        r"except\s+asyncio\.TimeoutError[^\n]*\n(?:[^\n]*\n){0,10}?\s*hints,\s*plan\s*=\s*None,\s*None",
        src,
    ), "timeout 必須 fallback 為 (None, None) 讓後續邏輯接手"
