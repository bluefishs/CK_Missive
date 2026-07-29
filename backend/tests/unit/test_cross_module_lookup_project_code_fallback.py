# -*- coding: utf-8 -*-
"""
cross_module_lookup project_code fallback Regression（2026-07-29）

背景（owner 回報）：`/contract-cases/187` 無法進行財務紀錄作業。
  該案 `case_code` 為空、只有 `project_code=CK2026_01_01_006`。

半接通根因：
  前端 FinanceTab 傳 `caseCode || projectCode`（**意圖** fallback），
  但查詢層 `cross_module_lookup` 只比對 `case_code` 欄位 → fallback 從未成立。
  實測 71 筆 erp_quotations 中 **49 筆 case_code ≠ project_code**，
  故對「無 case_code 但有 project_code」的案件必然查不到（L30/L67 家族）。

修法：兩段式查找（case_code 優先 → 找不到才回退 project_code），
      比照同檔 `find_linked_documents` 既有模式。
"""
import pytest

from app.services.contract.case_code import CaseCodeService


class _FakeRepo:
    """依 code 種類回傳假資料，並記錄呼叫順序（驗證「case_code 優先」）。"""

    def __init__(self, by_case: dict | None = None, by_project: dict | None = None):
        self._by_case = by_case or {}
        self._by_project = by_project or {}
        self.calls: list[str] = []

    async def get_lookup_by_case_code(self, code: str):
        self.calls.append(f"case:{code}")
        return self._by_case.get(code)

    async def get_lookup_by_project_code(self, code: str):
        self.calls.append(f"project:{code}")
        return self._by_project.get(code)


def _service(pm_repo, erp_repo) -> CaseCodeService:
    svc = CaseCodeService.__new__(CaseCodeService)  # 免 DB 連線
    svc.pm_repo = pm_repo
    svc.erp_repo = erp_repo
    return svc


@pytest.mark.asyncio
class TestCrossModuleLookupFallback:
    async def test_falls_back_to_project_code_when_case_code_absent(self):
        """187 情境：無 case_code、只有 project_code → 必須查得到 ERP 報價。"""
        erp = _FakeRepo(by_project={"CK2026_01_01_006": {"id": 9, "case_name": "第二期"}})
        pm = _FakeRepo()
        result = await _service(pm, erp).cross_module_lookup("CK2026_01_01_006")

        assert result["erp"] is not None, "project_code fallback 未生效（修法前的 bug）"
        assert result["erp"]["id"] == 9
        assert erp.calls == ["case:CK2026_01_01_006", "project:CK2026_01_01_006"], (
            "必須 case_code 優先、找不到才回退"
        )

    async def test_case_code_hit_does_not_query_project_code(self):
        """正規流程（有 case_code）行為不得改變，且不應多打一次查詢。"""
        erp = _FakeRepo(by_case={"CK2025_FN_01_001": {"id": 1}})
        pm = _FakeRepo(by_case={"CK2025_FN_01_001": {"id": 2}})
        result = await _service(pm, erp).cross_module_lookup("CK2025_FN_01_001")

        assert result["erp"]["id"] == 1
        assert result["pm"]["id"] == 2
        assert erp.calls == ["case:CK2025_FN_01_001"], "命中 case_code 後不應再查 project_code"
        assert pm.calls == ["case:CK2025_FN_01_001"]

    async def test_two_codes_differ_is_the_normal_case(self):
        """實測 71 筆報價中 49 筆兩碼不同值 → 不可假設 case_code == project_code。"""
        erp = _FakeRepo(
            by_case={"CK2025_FN_01_001": {"id": 1}},
            by_project={"CK2026_01_01_006": {"id": 1}},
        )
        by_case = await _service(_FakeRepo(), erp).cross_module_lookup("CK2025_FN_01_001")
        erp2 = _FakeRepo(
            by_case={"CK2025_FN_01_001": {"id": 1}},
            by_project={"CK2026_01_01_006": {"id": 1}},
        )
        by_project = await _service(_FakeRepo(), erp2).cross_module_lookup("CK2026_01_01_006")
        assert by_case["erp"]["id"] == by_project["erp"]["id"] == 1, "兩種碼都應指到同一份報價"

    async def test_neither_code_matches_returns_none(self):
        """兩碼皆無對應（187 目前的真實狀態）→ 回 None，前端顯示引導建立報價。"""
        result = await _service(_FakeRepo(), _FakeRepo()).cross_module_lookup("NOPE")
        assert result == {"case_code": "NOPE", "pm": None, "erp": None}
