"""
PM/ERP 領域工具執行器

包含工具：
- search_projects: 搜尋承攬案件
- get_project_detail: 取得案件詳情
- get_project_progress: 取得案件進度
- search_vendors: 搜尋協力廠商
- get_vendor_detail: 取得廠商詳情
- get_contract_summary: 取得合約金額統計
- get_overdue_milestones: 查詢逾期里程碑
- get_unpaid_billings: 查詢未收款/逾期請款
- get_financial_summary: 查詢專案/公司財務總覽
- get_expense_overview: 查詢費用報銷總覽
- check_budget_alert: 預算超支警報檢查

Extracted from agent_tools.py v1.83.0
Updated v5.1.1: 財務工具整合 (Phase 3-1/3-2)
"""

import logging
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DomainToolExecutor:
    """PM/ERP 領域工具執行器"""

    def __init__(self, db: AsyncSession, ai_connector, embedding_mgr, config):
        self.db = db
        self.ai = ai_connector
        self.embedding_mgr = embedding_mgr
        self.config = config

    async def search_projects(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜尋承攬案件"""
        from app.services.ai.pm_query_service import PMQueryService

        keywords = params.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [keywords]

        svc = PMQueryService(self.db)
        return await svc.search_projects(
            keywords=keywords or None,
            status=params.get("status"),
            year=params.get("year"),
            client_agency=params.get("client_agency"),
            limit=min(int(params.get("limit", 10)), 20),
        )

    async def get_project_detail(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """取得案件詳情"""
        from app.services.ai.pm_query_service import PMQueryService

        project_id = params.get("project_id")
        if not project_id:
            return {"error": "需要提供 project_id 參數", "count": 0}

        svc = PMQueryService(self.db)
        return await svc.get_project_detail(int(project_id))

    async def get_project_progress(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """取得案件進度"""
        from app.services.ai.pm_query_service import PMQueryService

        project_id = params.get("project_id")
        if not project_id:
            return {"error": "需要提供 project_id 參數", "count": 0}

        svc = PMQueryService(self.db)
        return await svc.get_project_progress(int(project_id))

    async def search_vendors(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜尋協力廠商"""
        from app.services.ai.erp_query_service import ERPQueryService

        keywords = params.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [keywords]

        svc = ERPQueryService(self.db)
        return await svc.search_vendors(
            keywords=keywords or None,
            business_type=params.get("business_type"),
            limit=min(int(params.get("limit", 10)), 20),
        )

    async def get_vendor_detail(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """取得廠商詳情"""
        from app.services.ai.erp_query_service import ERPQueryService

        vendor_id = params.get("vendor_id")
        if not vendor_id:
            return {"error": "需要提供 vendor_id 參數", "count": 0}

        svc = ERPQueryService(self.db)
        return await svc.get_vendor_detail(int(vendor_id))

    async def get_contract_summary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """取得合約金額統計"""
        from app.services.ai.erp_query_service import ERPQueryService

        svc = ERPQueryService(self.db)
        return await svc.get_contract_summary(
            year=params.get("year"),
            status=params.get("status"),
        )

    async def get_overdue_milestones(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """查詢逾期里程碑"""
        from app.services.ai.pm_query_service import PMQueryService

        svc = PMQueryService(self.db)
        return await svc.get_overdue_milestones(
            limit=min(int(params.get("limit", 20)), 50),
        )

    async def get_unpaid_billings(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """查詢未收款/逾期請款"""
        from app.services.ai.erp_query_service import ERPQueryService

        svc = ERPQueryService(self.db)
        return await svc.get_unpaid_billings(
            limit=min(int(params.get("limit", 20)), 50),
        )

    # === Finance Tools (Phase 3, v5.1.1) ===

    async def get_financial_summary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """查詢專案或公司財務總覽"""
        from app.services.financial_summary_service import FinancialSummaryService

        case_code = params.get("case_code")
        year = params.get("year")
        top_n = min(int(params.get("top_n", 10)), 50)

        svc = FinancialSummaryService(self.db)

        if case_code:
            result = await svc.get_project_summary(case_code)
            return {"type": "project", "summary": result, "count": 1}
        else:
            result = await svc.get_company_overview(year=year, top_n=top_n)
            return {"type": "company", "summary": result, "count": 1}

    async def get_expense_overview(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """查詢費用報銷總覽"""
        from app.schemas.erp.expense import ExpenseInvoiceQuery
        from app.services.expense_invoice_service import ExpenseInvoiceService

        limit = min(int(params.get("limit", 20)), 50)
        query = ExpenseInvoiceQuery(
            case_code=params.get("case_code"),
            status=params.get("status"),
            skip=0,
            limit=limit,
        )

        svc = ExpenseInvoiceService(self.db)
        items, total = await svc.query(query)

        return {
            "items": [
                {
                    "id": inv.id,
                    "inv_num": inv.inv_num,
                    "date": str(inv.date) if inv.date else None,
                    "amount": float(inv.amount) if inv.amount else 0,
                    "category": inv.category,
                    "status": inv.status,
                    "case_code": inv.case_code,
                    "description": inv.description,
                }
                for inv in items
            ],
            "total": total,
            "count": len(items),
        }

    async def check_budget_alert(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """預算超支警報檢查"""
        from app.services.financial_summary_service import FinancialSummaryService

        threshold_pct = min(float(params.get("threshold_pct", 80)), 100)
        year = params.get("year")

        svc = FinancialSummaryService(self.db)
        overview = await svc.get_company_overview(year=year, top_n=50)

        alerts = []
        for proj in overview.get("top_projects", []):
            revenue = float(proj.get("revenue", 0) or 0)
            expenses = float(proj.get("expenses", 0) or 0)
            if revenue > 0:
                usage_pct = (expenses / revenue) * 100
                if usage_pct >= threshold_pct:
                    alerts.append({
                        "case_code": proj.get("case_code"),
                        "revenue": revenue,
                        "expenses": expenses,
                        "usage_pct": round(usage_pct, 1),
                        "level": "critical" if usage_pct >= 100 else "warning",
                    })

        return {
            "threshold_pct": threshold_pct,
            "alerts": alerts,
            "count": len(alerts),
        }
