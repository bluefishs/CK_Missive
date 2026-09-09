# -*- coding: utf-8 -*-
"""篩選條件只有一個家：資產與營運帳目的列表與統計必須從同一支建構器拿條件（2026-09-09，weekly 133 存量清理）。

owner：「統計與篩選中心服務化請盡快完善」。此前資產頁列表四個條件、統計只認 keyword；
營運帳目列表四個、統計兩個 —— 選了類別／狀態，卡片不跟（FLOW_REVIEW §二 早就列著）。
"""
import inspect

from app.repositories.erp.asset_repository import AssetRepository
from app.repositories.erp.operational_repository import OperationalAccountRepository


def test_asset_filters_cover_all_list_fields():
    conds = AssetRepository.filters(category="equipment", status="in_use", keyword="x", case_code="C1")
    assert len(conds) == 4
    assert AssetRepository.filters() == []


def test_asset_list_and_stats_use_the_same_home():
    assert "self.filters(" in inspect.getsource(AssetRepository.list_assets)
    src = inspect.getsource(AssetRepository.get_asset_stats)
    assert "self.filters(" in src
    # status 是卡片自己（各狀態計數），統計刻意不收
    assert "status=None" in src


def test_operational_filters_cover_all_list_fields():
    repo = OperationalAccountRepository.__new__(OperationalAccountRepository)
    from app.extended.models.operational import OperationalAccount
    repo.model = OperationalAccount
    conds = repo.account_filters(fiscal_year=2026, keyword="k", category="c", status="active")
    assert len(conds) == 4
    assert repo.account_filters() == []


def test_operational_list_and_stats_use_the_same_home():
    assert "self.account_filters(" in inspect.getsource(OperationalAccountRepository.list_filtered)
    assert "self.account_filters(" in inspect.getsource(OperationalAccountRepository.get_stats)


def test_stats_endpoints_take_list_schema():
    from app.api.endpoints.erp import assets, operational
    assert "params: AssetListRequest" in inspect.getsource(assets.get_asset_stats)
    assert "params: OperationalAccountListRequest" in inspect.getsource(operational.get_stats)
