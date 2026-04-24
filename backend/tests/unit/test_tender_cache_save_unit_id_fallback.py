"""Regression test (2026-04-24):
tender_cache_service.save_search_results — ezbid 源 unit_id 空時必須
用 ezbid_id 回填，防止 DB 累積 unit_id='' 壞資料（會造成 React rowKey 重複 +
/tender/ detail URL 404）。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.tender_cache_service import save_search_results


@pytest.mark.asyncio
async def test_save_search_results_ezbid_unit_id_fallback():
    """ezbid record with empty unit_id should be backfilled from ezbid_id."""
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    # Simulate: (SELECT existing ID) returns None -> not existing; then INSERT + lastval
    exec_result = MagicMock()
    exec_result.scalar.return_value = None  # not existing
    lastval_result = MagicMock()
    lastval_result.scalar.return_value = 999
    db.execute.side_effect = [
        exec_result,     # SELECT existing
        MagicMock(),     # INSERT
        lastval_result,  # lastval
    ]

    records = [{
        "unit_id": "",          # ← blank (the bug)
        "job_number": "",
        "ezbid_id": "2229486",  # ← only this is populated
        "title": "2026年應用AI爭取海外商機輔導案",
        "unit_name": "經濟部",
        "source": "ezbid",
    }]

    saved = await save_search_results(db, records, source="ezbid")
    assert saved == 1

    # Find the INSERT call, check uid param was filled from ezbid_id
    insert_call = [c for c in db.execute.call_args_list
                   if "INSERT INTO tender_records" in str(c.args[0])][0]
    params = insert_call.args[1]
    assert params["uid"] == "2229486", (
        f"Expected unit_id backfill from ezbid_id, got uid={params['uid']!r}"
    )


@pytest.mark.asyncio
async def test_save_search_results_pcc_unit_id_preserved():
    """PCC record with valid unit_id should not be altered."""
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    exec_result = MagicMock()
    exec_result.scalar.return_value = None
    lastval_result = MagicMock()
    lastval_result.scalar.return_value = 999
    db.execute.side_effect = [exec_result, MagicMock(), lastval_result]

    records = [{
        "unit_id": "A.19.4.8",
        "job_number": "115-1528-02",
        "title": "某PCC案",
        "unit_name": "某機關",
        "source": "pcc",
    }]

    await save_search_results(db, records, source="pcc")
    insert_call = [c for c in db.execute.call_args_list
                   if "INSERT INTO tender_records" in str(c.args[0])][0]
    params = insert_call.args[1]
    assert params["uid"] == "A.19.4.8"
