"""方案 A 韌性強化 regression（2026-07-04 owner 授權）。

背景：org-ecosystem/company-profile 靠 live openfun 取得廠商/得標資料（本地 DB 無此維度，L77）。
原本 live 空/限流時整頁回 {total:0} → 使用者誤判「查無資料」。方案 A：
  - org_ecosystem: live 空 → 改回本地 tender_records 標案清單（degraded=True，含清單但無廠商分析）。
  - company_profile: live 空 → 明確 degraded 訊息（DB 無 winner 資料，無法 DB 後備）。
本測試鎖定「live 空 → degraded 契約」，防未來回退成裸 {total:0}。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _empty_search_service():
    svc = MagicMock()
    svc.search_by_org = AsyncMock(return_value={"records": []})
    svc.search_by_title = AsyncMock(return_value={"records": []})
    svc.search_by_company = AsyncMock(return_value={"records": []})
    return svc


@pytest.mark.asyncio
async def test_org_ecosystem_live_empty_uses_db_fallback():
    """live openfun 空 → 呼叫 _db_org_fallback、回 degraded 結果（非裸 total:0）。"""
    from app.services.tender import analytics_battle

    svc = _empty_search_service()
    sentinel = {"org_name": "X機關", "total": 42, "degraded": True,
                "top_vendors": [], "recent_tenders": []}
    with patch.object(analytics_battle, "_db_org_fallback",
                      new=AsyncMock(return_value=sentinel)) as fb, \
         patch("app.core.redis_client.get_redis", new=AsyncMock(return_value=None)):
        result = await analytics_battle.org_ecosystem(svc, "X機關", pages=2)

    fb.assert_awaited_once()
    assert result["degraded"] is True
    assert result["total"] == 42


@pytest.mark.asyncio
async def test_company_profile_live_empty_returns_degraded():
    """live openfun 空 → 明確 degraded 訊息（區分限流 vs 真無資料），非裸 total:0。"""
    from app.services.tender import analytics_price

    svc = _empty_search_service()
    with patch("app.core.redis_client.get_redis", new=AsyncMock(return_value=None)):
        result = await analytics_price.company_profile(svc, "某廠商", pages=2)

    assert result["degraded"] is True
    assert result["total"] == 0
    assert "限流" in result["degraded_reason"]
