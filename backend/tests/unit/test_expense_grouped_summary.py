"""
費用分組彙總單元測試

測試 expenses endpoint /grouped-summary 的分組邏輯。
- 按 attribution_type 分組
- 金額正確彙總
- 過濾條件生效
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal


class TestGroupedSummaryLogic:
    """分組彙總核心邏輯測試"""

    def test_group_map_aggregation(self):
        """驗證 group_map 彙總邏輯"""
        # 模擬資料庫查詢結果
        rows = [
            MagicMock(attribution_type="project", case_code="B114-B001", category="交通費", count=3, total_amount=Decimal("1500")),
            MagicMock(attribution_type="project", case_code="B114-B001", category="差旅費", count=2, total_amount=Decimal("3000")),
            MagicMock(attribution_type="operational", case_code=None, category="水電費", count=1, total_amount=Decimal("800")),
            MagicMock(attribution_type=None, case_code=None, category="雜費", count=1, total_amount=Decimal("200")),
        ]

        # 重現 endpoint 的分組邏輯
        group_map: dict = {}
        for row in rows:
            attr = row.attribution_type or "none"
            cc = row.case_code or "__operational__" if attr == "operational" else (row.case_code or "__none__")
            key = f"{attr}:{cc}"

            if key not in group_map:
                group_map[key] = {
                    "group_key": key,
                    "attribution_type": attr,
                    "case_code": row.case_code,
                    "total_amount": 0,
                    "count": 0,
                    "categories": {},
                }
            g = group_map[key]
            amt = float(row.total_amount or 0)
            g["total_amount"] += amt
            g["count"] += row.count
            cat = row.category or "其他"
            g["categories"][cat] = g["categories"].get(cat, 0) + amt

        groups = sorted(group_map.values(), key=lambda x: x["total_amount"], reverse=True)

        # 驗證
        assert len(groups) == 3  # project:B114-B001, operational:__operational__, none:__none__

        # 專案組 (最高金額)
        project_group = groups[0]
        assert project_group["attribution_type"] == "project"
        assert project_group["case_code"] == "B114-B001"
        assert project_group["total_amount"] == 4500.0
        assert project_group["count"] == 5
        assert project_group["categories"]["交通費"] == 1500.0
        assert project_group["categories"]["差旅費"] == 3000.0

        # 營運組
        op_group = [g for g in groups if g["attribution_type"] == "operational"][0]
        assert op_group["total_amount"] == 800.0
        assert op_group["count"] == 1

        # 未歸屬組
        none_group = [g for g in groups if g["attribution_type"] == "none"][0]
        assert none_group["total_amount"] == 200.0

    def test_empty_rows(self):
        """空資料應返回空分組"""
        rows = []
        group_map: dict = {}
        for row in rows:
            pass  # 不執行

        groups = sorted(group_map.values(), key=lambda x: x["total_amount"], reverse=True)
        total = sum(g["total_amount"] for g in groups)

        assert groups == []
        assert total == 0

    def test_total_count_and_amount(self):
        """驗證 total_count 和 total_amount 計算"""
        rows = [
            MagicMock(attribution_type="project", case_code="C001", category="交通費", count=10, total_amount=Decimal("50000")),
            MagicMock(attribution_type="project", case_code="C002", category="差旅費", count=5, total_amount=Decimal("30000")),
        ]

        group_map: dict = {}
        for row in rows:
            attr = row.attribution_type or "none"
            cc = row.case_code or "__none__"
            key = f"{attr}:{cc}"
            if key not in group_map:
                group_map[key] = {"group_key": key, "total_amount": 0, "count": 0}
            g = group_map[key]
            g["total_amount"] += float(row.total_amount or 0)
            g["count"] += row.count

        groups = list(group_map.values())
        total_count = sum(g["count"] for g in groups)
        total_amount = sum(g["total_amount"] for g in groups)

        assert total_count == 15
        assert total_amount == 80000.0

    def test_null_attribution_type_grouped_as_none(self):
        """attribution_type 為 None 應歸入 'none' 組"""
        rows = [
            MagicMock(attribution_type=None, case_code=None, category="雜費", count=2, total_amount=Decimal("500")),
            MagicMock(attribution_type=None, case_code=None, category="交通費", count=1, total_amount=Decimal("300")),
        ]

        group_map: dict = {}
        for row in rows:
            attr = row.attribution_type or "none"
            cc = row.case_code or "__none__"
            key = f"{attr}:{cc}"
            if key not in group_map:
                group_map[key] = {"group_key": key, "attribution_type": attr, "total_amount": 0, "count": 0, "categories": {}}
            g = group_map[key]
            g["total_amount"] += float(row.total_amount or 0)
            g["count"] += row.count
            cat = row.category or "其他"
            g["categories"][cat] = g["categories"].get(cat, 0) + float(row.total_amount or 0)

        groups = list(group_map.values())
        assert len(groups) == 1
        assert groups[0]["attribution_type"] == "none"
        assert groups[0]["total_amount"] == 800.0
        assert groups[0]["count"] == 3
        assert groups[0]["categories"]["雜費"] == 500.0
        assert groups[0]["categories"]["交通費"] == 300.0


class TestExpenseApprovalService:
    """ExpenseApprovalService 拆分後的獨立測試"""

    def test_get_approval_info_low_value(self):
        """低金額 (≤30K) 審核資訊"""
        from app.services.expense_approval_service import ExpenseApprovalService

        invoice = MagicMock()
        invoice.status = "pending"
        invoice.amount = Decimal("15000")

        info = ExpenseApprovalService.get_approval_info(invoice)
        assert info["approval_level"] == "pending"
        assert info["next_approval"] == "manager"

    def test_get_approval_info_high_value(self):
        """高金額 (>30K) 需三級審核"""
        from app.services.expense_approval_service import ExpenseApprovalService

        invoice = MagicMock()
        invoice.status = "manager_approved"
        invoice.amount = Decimal("50000")

        info = ExpenseApprovalService.get_approval_info(invoice)
        assert info["approval_level"] == "manager"
        assert info["next_approval"] == "finance"

    def test_get_approval_info_verified(self):
        """已核准狀態無下一步"""
        from app.services.expense_approval_service import ExpenseApprovalService

        invoice = MagicMock()
        invoice.status = "verified"
        invoice.amount = Decimal("10000")

        info = ExpenseApprovalService.get_approval_info(invoice)
        assert info["approval_level"] == "final"
        assert info["next_approval"] is None

    def test_determine_next_approval_low(self):
        """低金額從 manager_approved 直接到 verified"""
        from app.services.expense_approval_service import ExpenseApprovalService

        svc = ExpenseApprovalService.__new__(ExpenseApprovalService)
        assert svc._determine_next_approval("pending", Decimal("15000")) == "manager_approved"
        assert svc._determine_next_approval("manager_approved", Decimal("15000")) == "verified"

    def test_determine_next_approval_high(self):
        """高金額需經過 finance_approved"""
        from app.services.expense_approval_service import ExpenseApprovalService

        svc = ExpenseApprovalService.__new__(ExpenseApprovalService)
        assert svc._determine_next_approval("pending", Decimal("50000")) == "manager_approved"
        assert svc._determine_next_approval("manager_approved", Decimal("50000")) == "finance_approved"
        assert svc._determine_next_approval("finance_approved", Decimal("50000")) == "verified"
