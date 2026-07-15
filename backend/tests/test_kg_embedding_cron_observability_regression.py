"""Regression: KG embedding cron 第三層根治（2026-07-15 覆盤）

背景：`kg_embedding_backfill` 04:30 排程長期 status=success 但 embedded=0
      （ollama nomic-embed 冷啟動未溫熱），cron_events 只記 duration 不記
      業務產出 → silent success。治本兩不變式，本檔鎖定防回退：

  I1（觀測）：tracked_job 把 job 回傳的 dict 當 detail 寫入 SchedulerTracker
             → cron_events 能看到 embedded/reason，silent success 現形。
  I2（暖機閘門）：backfill_embeddings 於冷啟動（探測回空）時回明確 reason
             "embedding backend not ready"，且不硬跑批次 select。
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# I1：tracked_job 觀測 — dict 結果進 detail
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_tracked_job_records_dict_result_as_detail():
    from app.core.scheduler import tracked_job, SchedulerTracker

    @tracked_job("test_obs_job")
    async def job_returning_metrics():
        return {"processed": 10, "embedded": 7, "skipped": 3, "reason": None}

    await job_returning_metrics()

    rec = SchedulerTracker._records["test_obs_job"]
    assert rec["last_status"] == "success"
    assert rec["last_detail"] == {"processed": 10, "embedded": 7, "skipped": 3, "reason": None}


@pytest.mark.asyncio
async def test_tracked_job_non_dict_result_no_detail():
    """非 dict 回傳（多數既有 job）→ detail=None，行為不變（不回退）。"""
    from app.core.scheduler import tracked_job, SchedulerTracker

    @tracked_job("test_obs_job_none")
    async def job_returning_none():
        return None

    await job_returning_none()
    assert SchedulerTracker._records["test_obs_job_none"]["last_detail"] is None


def test_append_event_serializes_detail_scalars_only(tmp_path):
    """detail 只寫 JSON-safe 純量，過濾 ORM/大物件（防 log 汙染/爆量）。"""
    import json
    from app.core.scheduler import SchedulerTracker

    log = tmp_path / "cron_events.jsonl"
    with patch.object(SchedulerTracker, "_EVENTS_LOG", log):
        SchedulerTracker._append_event(
            "j", "success", 12.3,
            detail={"embedded": 5, "reason": None, "obj": object()},  # obj 應被濾掉
        )
    line = json.loads(log.read_text(encoding="utf-8").strip())
    assert line["detail"] == {"embedded": 5, "reason": None}
    assert "obj" not in line["detail"]


# ---------------------------------------------------------------------------
# I2：backfill_embeddings 暖機閘門 — 冷啟動回明確 reason、不跑批次
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_backfill_warmup_gate_cold_backend_returns_reason():
    from app.services.ai.core.embedding_manager import EmbeddingManager
    from app.services.ai.domain.cross_domain_contribution_service import (
        CrossDomainContributionService,
    )

    db = MagicMock()
    db.execute = AsyncMock()  # 若被呼叫代表閘門失守
    svc = CrossDomainContributionService(db)

    with patch.object(EmbeddingManager, "is_available", return_value=True), \
         patch.object(EmbeddingManager, "get_embeddings_batch",
                      new=AsyncMock(return_value=[None])), \
         patch("app.core.ai_connector.get_ai_connector", return_value=MagicMock()), \
         patch("asyncio.sleep", new=AsyncMock()):  # 略過 3×5s 等待
        result = await svc.backfill_embeddings(batch_size=2000)

    assert result["reason"] == "embedding backend not ready"
    assert result["embedded"] == 0
    # 關鍵：暖機失敗時不得進 DB select 批次
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_backfill_warmup_passes_when_backend_ready():
    """暖機探測回有效向量 → 通過閘門、進入批次（此處批次撈 0 筆即早退，驗證有走到 select）。"""
    from app.services.ai.core.embedding_manager import EmbeddingManager
    from app.services.ai.domain.cross_domain_contribution_service import (
        CrossDomainContributionService,
    )

    empty_scalars = MagicMock()
    empty_scalars.scalars.return_value.all.return_value = []
    db = MagicMock()
    db.execute = AsyncMock(return_value=empty_scalars)
    svc = CrossDomainContributionService(db)

    with patch.object(EmbeddingManager, "is_available", return_value=True), \
         patch.object(EmbeddingManager, "get_embeddings_batch",
                      new=AsyncMock(return_value=[[0.1] * 768])), \
         patch("app.core.ai_connector.get_ai_connector", return_value=MagicMock()), \
         patch("asyncio.sleep", new=AsyncMock()):
        result = await svc.backfill_embeddings(batch_size=2000)

    assert "reason" not in result or result.get("reason") is None
    db.execute.assert_called_once()  # 通過閘門後有跑批次 select
