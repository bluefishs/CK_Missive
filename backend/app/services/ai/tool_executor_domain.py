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

Extracted from agent_tools.py v1.83.0
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
