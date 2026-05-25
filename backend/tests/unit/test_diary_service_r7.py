# -*- coding: utf-8 -*-
"""
R7 (v6.9 / 2026-05-08) — Diary append 失敗 retry + 計數器 regression test

確保 diary_service.append_entry 在以下失敗時不再 silent skip：
  1. file IO 失敗 → retry 1 次
  2. wiki_lookup 失敗 → 主寫入仍進行（非阻塞），但獨立計數
  3. metric_inc 失敗 → 主寫入仍進行（非阻塞），但獨立計數
  4. 連續 file_io 失敗（retry 後仍失敗）→ logger.error + counter +1

防 v3.0 洞察 11「fire-and-forget silent skip」反模式重演。
"""
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest


@pytest.fixture
def diary_service(tmp_path, monkeypatch):
    """每個 test 用獨立 tmp 目錄避免 pollute"""
    from app.services.memory import diary_service as mod

    # 確保 MemoryWikiMetrics 已實例化（counter 註冊到 REGISTRY 的前置條件）
    from app.core.memory_wiki_metrics import get_memory_wiki_metrics
    get_memory_wiki_metrics()

    # 將 DIARY_DIR 重導向到 tmp_path
    monkeypatch.setattr(mod, "DIARY_DIR", tmp_path)

    # 重置 singleton 確保使用新 DIARY_DIR
    mod.DiaryService._instance = None
    return mod.get_diary_service()


def _read_failure_counter(error_type: str) -> float:
    """讀取 memory_diary_append_failures_total{error_type=...} 累計值"""
    from prometheus_client import REGISTRY
    counter = REGISTRY._names_to_collectors.get("memory_diary_append_failures_total")
    if counter is None:
        return 0.0
    samples = [
        s for s in counter.collect()[0].samples
        if s.name.endswith("_total") and s.labels.get("error_type") == error_type
    ]
    return samples[0].value if samples else 0.0


# ============================================================================
# 1. wiki_lookup 失敗：主寫入仍進行，但獨立計數
# ============================================================================

@pytest.mark.asyncio
async def test_wiki_lookup_failure_does_not_block_diary_write(diary_service):
    """wiki search 失敗時 diary 主體仍寫入，但 wiki_lookup error 進計數器"""
    baseline = _read_failure_counter("wiki_lookup")

    with patch.object(
        diary_service.__class__,
        "_lookup_wiki_entities",
        new=AsyncMock(side_effect=RuntimeError("wiki service down")),
    ):
        await diary_service.append_entry(
            question="test question",
            answer="test answer",
            success=True,
        )

    # 主寫入應成功 — read_today 應有內容
    today_content = await diary_service.read_today()
    assert today_content is not None
    assert "test question" in today_content
    assert "test answer" in today_content

    # wiki_lookup 失敗計數 +1
    after = _read_failure_counter("wiki_lookup")
    assert after > baseline


# ============================================================================
# 2. file_io 失敗 retry 1 次後成功 → 不計失敗
# ============================================================================

@pytest.mark.asyncio
async def test_file_io_transient_failure_recovered_by_retry(diary_service):
    """模擬第一次 open() 失敗（OSError），retry 第二次成功"""
    baseline = _read_failure_counter("file_io")

    real_open = Path.open
    call_count = {"n": 0}

    def flaky_open(self, mode="r", *args, **kwargs):
        # append 模式才模擬 transient 失敗（讀檔不影響）
        if "a" in mode:
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise OSError("simulated EAGAIN")
        return real_open(self, mode, *args, **kwargs)

    with patch.object(Path, "open", flaky_open):
        await diary_service.append_entry(
            question="retry test",
            answer="should succeed on second try",
            success=True,
        )

    # 主寫入最終成功
    today_content = await diary_service.read_today()
    assert today_content is not None
    assert "retry test" in today_content

    # retry 成功 → file_io 失敗計數**不**增加（只計最終失敗）
    after = _read_failure_counter("file_io")
    assert after == baseline


# ============================================================================
# 3. file_io 失敗 retry 後仍失敗 → 計數 + log error
# ============================================================================

@pytest.mark.asyncio
async def test_file_io_persistent_failure_logged_and_counted(diary_service, caplog):
    """連續 file IO 失敗（retry 後仍失敗）必須 logger.error + counter.inc"""
    import logging
    baseline = _read_failure_counter("file_io")

    real_open = Path.open

    def always_fail_open(self, mode="r", *args, **kwargs):
        if "a" in mode:
            raise OSError("simulated persistent EBUSY")
        return real_open(self, mode, *args, **kwargs)

    with caplog.at_level(logging.ERROR, logger="app.services.memory.diary_service"):
        with patch.object(Path, "open", always_fail_open):
            # 不會 raise（fire-and-forget 性質保留）
            await diary_service.append_entry(
                question="persistent fail",
                answer="should not block",
                success=True,
            )

    # logger.error 必須有記錄
    error_logs = [
        r for r in caplog.records
        if r.levelno >= logging.ERROR and "Diary append failed" in r.message
    ]
    assert len(error_logs) >= 1, "持續失敗必須 logger.error（取代原 logger.warning）"

    # file_io 失敗計數 +1
    after = _read_failure_counter("file_io")
    assert after > baseline


# ============================================================================
# 4. metric_inc 失敗：不阻斷主流程
# ============================================================================

@pytest.mark.asyncio
async def test_metric_inc_failure_does_not_block_diary_write(diary_service):
    """get_memory_wiki_metrics().diary_appends.inc() 失敗也不該影響 diary 寫入"""
    baseline = _read_failure_counter("metric_inc")

    # patch get_memory_wiki_metrics 拋例外
    with patch(
        "app.core.memory_wiki_metrics.get_memory_wiki_metrics",
        side_effect=RuntimeError("metrics broken"),
    ):
        await diary_service.append_entry(
            question="metric test",
            answer="should still write",
            success=True,
        )

    # 主寫入成功
    content = await diary_service.read_today()
    assert content is not None
    assert "metric test" in content

    # metric_inc 失敗計數 +1
    after = _read_failure_counter("metric_inc")
    assert after > baseline


# ============================================================================
# 5. counter 在 import 時就註冊（避免 first-failure-before-visible silent gap）
# ============================================================================

def test_diary_failures_counter_registered_at_import():
    """memory_diary_append_failures_total counter 必須在 module import 時即註冊。

    與 F19 SYNTHESIS_UNSOURCED_NUMBERS 同 pattern — 啟動就暴露 0 值，
    避免「首次失敗前 alert 看不到 metric」silent gap。
    """
    from prometheus_client import REGISTRY
    import app.core.memory_wiki_metrics  # noqa: F401
    # 確保 MemoryWikiMetrics() 已被實例化（caller 通常 get_memory_wiki_metrics()）
    from app.core.memory_wiki_metrics import get_memory_wiki_metrics
    get_memory_wiki_metrics()

    counter = REGISTRY._names_to_collectors.get("memory_diary_append_failures_total")
    assert counter is not None, (
        "memory_diary_append_failures_total counter 必須在 import + instantiation 時"
        "即註冊（防止 first-failure-before-visible silent gap）"
    )
