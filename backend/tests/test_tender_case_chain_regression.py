# -*- coding: utf-8 -*-
"""Regression — 標案 → 建案 → 成案 → 財務 鏈路（2026-07-31）

對應 docs/architecture/TENDER_TO_FINANCE_CHAIN_REVIEW_20260731.md 的五個斷點。
"""
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (BACKEND / rel).read_text(encoding="utf-8")


def _strip_py_comments(src: str) -> str:
    """移除 # 註解與三引號字串 —— 比對原始碼時必須先做，否則會命中說明文字"""
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    src = re.sub(r"'''[\s\S]*?'''", "", src)
    return re.sub(r"(?m)^\s*#.*$", "", src)


class TestCJKNameMatching:
    """L2 的比對演算法必須對中文有效 —— pg_trgm 不行"""

    def test_similarity_of_identical_chinese_is_one(self):
        from app.services.tender.name_matching import name_similarity
        s = "桃園市公共設施用地設施物調查測量及工程開闢分析規劃第二期"
        assert name_similarity(s, s) == 1.0

    def test_unrelated_chinese_names_score_low(self):
        """pg_trgm 曾把這兩個判為 1.00（只因雙方含 ASCII「115」）"""
        from app.services.tender.name_matching import name_similarity
        a = "115年度圖根點補建、新建作業"
        b = "115學年度八年級戶外教學隔宿露營活動"
        assert name_similarity(a, b) < 0.6

    def test_containment_scores_high(self):
        """「…作業」vs「…作業(開口契約)」是常見同案型態"""
        from app.services.tender.name_matching import name_similarity
        a = "南投縣政府115年度委外辦理圖根點清理及補建新建作業"
        b = "南投縣政府115年度委外辦理圖根點清理及補建新建作業(開口契約)"
        assert name_similarity(a, b) >= 0.8

    def test_normalization_ignores_punctuation_and_width(self):
        from app.services.tender.name_matching import name_similarity
        assert name_similarity("測量作業（第二期）", "測量作業(第二期)") == 1.0

    def test_endpoint_does_not_use_pg_trgm_similarity(self):
        """守住『別再用 pg_trgm 比中文』——它不報錯，只是回假數字

        註：本測試初版忘了剝除註解，命中的是說明文字裡的 `similarity(` → 假紅。
        與同日 finance-drilldown 測試的假綠是同一個陷阱（比對原始碼必須先去註解）。
        """
        src = _strip_py_comments(_read("app/api/endpoints/tender_module/graph_case.py"))
        # 只抓 SQL 的 similarity(...)；不可誤傷自家的 name_similarity(...)
        assert not re.search(r"(?<![\w_])similarity\(", src), (
            "graph_case.py 又用了 SQL similarity()：pg_trgm 對中文恆為 0 且會因 "
            "ASCII 年度數字產生 100% 假性命中"
        )
        assert "name_similarity" in src


class TestCreateCaseEntryAndDedup:
    """L1 入口 + L2 防重複"""

    def test_job_number_is_optional(self):
        """ezbid 37,980 筆 job_number 全為 NULL，必填等於把整個來源擋在鏈路外"""
        src = _read("app/schemas/tender_admin.py")
        m = re.search(r"class TenderCreateCaseRequest.*?(?=\nclass )", src, re.S)
        assert m
        body = m.group(0)
        assert re.search(r"job_number:\s*Optional\[str\]", body), "job_number 必須為選填"

    def test_ezbid_identifier_fallback(self):
        src = _read("app/api/endpoints/tender_module/graph_case.py")
        assert 'f"ezbid:{req.unit_id}"' in src, "無 job_number 時必須有替代識別碼，否則查重會被整段跳過"

    def test_dedup_covers_contract_projects(self):
        """案件 187 型態：直接建立的承攬案件，只查 pm_cases 會漏掉"""
        src = _read("app/api/endpoints/tender_module/graph_case.py")
        assert "ContractProject.project_name == req.title" in src

    def test_dedup_covers_case_name_not_only_job_number(self):
        src = _read("app/api/endpoints/tender_module/graph_case.py")
        assert "PMCase.case_name == req.title" in src


class TestBackLink:
    """L3 回指"""

    def test_models_have_source_tender_id(self):
        assert "source_tender_id" in _read("app/extended/models/pm.py")
        assert "source_tender_id" in _read("app/extended/models/core.py")

    def test_create_case_persists_source_tender_id(self):
        src = _read("app/api/endpoints/tender_module/graph_case.py")
        assert "source_tender_id=req.tender_id" in src

    def test_project_response_exposes_source_tender_id(self):
        src = _read("app/schemas/project.py")
        assert "source_tender_id" in src

    def test_ezbid_detail_returns_tender_id(self):
        """前端要帶 tender_records.id 才能建立回指"""
        src = _read("app/api/endpoints/tender_module/search.py")
        assert '"tender_id": row[13]' in src

    def test_link_endpoint_exists(self):
        src = _read("app/api/endpoints/tender_module/graph_case.py")
        assert '@router.post("/link-case")' in src
        assert '@router.post("/related-cases")' in src
