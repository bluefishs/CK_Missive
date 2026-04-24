"""Regression test ADR-0032: /api/tender/detail response 必含 kind 欄位

防止未來 PCC/ezbid 分支再出現 kind 漏填，前端 discriminated union 會失效。
"""
import inspect

from app.api.endpoints.tender_module import search


def test_get_tender_detail_source_has_kind_pcc_branch():
    src = inspect.getsource(search.get_tender_detail)
    assert 'result["kind"] = "pcc"' in src, (
        "PCC 分支 response 必須標記 kind='pcc'（ADR-0032 discriminated union）"
    )


def test_get_tender_detail_source_has_kind_ezbid_branch():
    src = inspect.getsource(search.get_tender_detail)
    assert '"kind": "ezbid"' in src, (
        "ezbid 分支 response 必須含 kind='ezbid'"
    )


def test_get_tender_detail_ezbid_passthrough_has_kind_pcc():
    """ezbid unit+job_number 補查 PCC 資料時，merged pcc_result 也必須帶 kind"""
    src = inspect.getsource(search.get_tender_detail)
    assert 'pcc_result["kind"] = "pcc"' in src, (
        "ezbid → PCC 補查路徑 response 必須也標 kind='pcc'"
    )
