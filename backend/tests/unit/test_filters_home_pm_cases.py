# -*- coding: utf-8 -*-
"""PM 案件：篩選條件只有一個家，列表與摘要共用（2026-09-09 晚，weekly 133 存量清理）。

主機端實跑（2026-09-09）：search=測量 104＝104、staff 6 86＝86、client_name=鎮泓 1＝1、include_converted=False 3＝3。
"""
import inspect

from app.repositories.pm.case_repository import PMCaseRepository


def test_case_filters_cover_list_fields():
    conds = PMCaseRepository.case_filters(year=2026, status="planning", category="02", client_name="x",
                                          search="k", include_converted=False, case_codes={"A"})
    assert len(conds) == 7
    assert PMCaseRepository.case_filters() == []
    # 身分範圍展開成空集合 ⇒ 限縮成無（哨兵），不是「不限縮」
    assert len(PMCaseRepository.case_filters(case_codes=set())) == 1


def test_list_and_summary_share_one_home():
    assert "self.case_filters(" in inspect.getsource(PMCaseRepository.filter_cases)
    src = inspect.getsource(PMCaseRepository.get_summary)
    assert "self.case_filters(" in src
    # 身分解析兩邊都走 CaseStatsScope，檔案裡不得再直接呼叫 case_codes_of_user
    whole = inspect.getsource(PMCaseRepository)
    assert "case_codes_of_user(" not in whole


def test_summary_endpoint_takes_list_schema():
    from app.api.endpoints.pm import cases as ep
    src = inspect.getsource(ep.get_summary)
    assert "req: PMCaseListRequest" in src
    assert "search=req.search or req.keyword" in src
