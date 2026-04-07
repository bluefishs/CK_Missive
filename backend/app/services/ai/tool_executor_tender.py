"""
標案/圖表工具執行器

拆分自 tool_executor_domain.py v5.5.0

包含工具：
- search_tender: 搜尋政府標案
- auto_tender_to_case: Multi-Agent 標案→建案
- analyze_diagram: 工程圖/測量圖分析 (Gemma 4 Vision)
"""

import logging
import os
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TenderToolExecutor:
    """標案/圖表工具執行器"""

    def __init__(self, db: AsyncSession, ai_connector, embedding_mgr, config):
        self.db = db
        self.ai = ai_connector
        self.embedding_mgr = embedding_mgr
        self.config = config

    async def search_tender(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜尋政府標案"""
        from app.services.tender_search_service import TenderSearchService

        service = TenderSearchService()
        query = params.get("query", "測量")
        page = params.get("page", 1)
        result = await service.search_by_title(query=query, page=page)

        records = result.get("records", [])[:8]
        return {
            "total": result.get("total_records", 0),
            "count": len(records),
            "tenders": [
                {
                    "title": r.get("title", ""),
                    "unit_name": r.get("unit_name", ""),
                    "type": r.get("type", ""),
                    "date": r.get("date", ""),
                    "category": r.get("category", ""),
                    "companies": r.get("company_names", []),
                }
                for r in records
            ],
        }

    async def auto_tender_to_case(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Multi-Agent: 標案搜尋→篩選→自動建案

        流程: 搜尋標案 → 篩選符合乾坤業務的 → 自動建立 PM Case + ERP Quotation
        """
        from app.services.tender_search_service import TenderSearchService
        from app.services.case_code_service import CaseCodeService
        from app.extended.models.pm import PMCase
        from app.extended.models.erp import ERPQuotation
        from datetime import date

        query = params.get("query", "測量")
        max_create = min(params.get("max_create", 3), 5)

        service = TenderSearchService()
        result = await service.search_by_title(query=query, page=1)
        records = result.get("records", [])

        actionable = [
            r for r in records
            if r.get("type", "").startswith(("公開", "限制性")) and r.get("title")
        ][:max_create]

        if not actionable:
            return {"created": 0, "message": f"搜尋「{query}」無可建案的招標公告"}

        code_service = CaseCodeService(self.db)
        created = []
        year = date.today().year

        for r in actionable:
            try:
                existing = await self.db.execute(
                    __import__('sqlalchemy').select(PMCase).where(
                        PMCase.case_name == r["title"][:200]
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                case_code = await code_service.generate_case_code("pm", year, "01")

                pm = PMCase(case_code=case_code, case_name=r["title"][:200], year=year, status="bidding",
                            notes=f"[Agent] 標案: {r.get('job_number', '')} ({r.get('unit_name', '')})")
                self.db.add(pm)
                await self.db.flush()

                q = ERPQuotation(case_code=case_code, case_name=r["title"][:200], year=year,
                                 total_price=0, status="draft",
                                 notes=f"[Agent] {r.get('unit_name', '')} | {r.get('type', '')}")
                self.db.add(q)

                created.append({
                    "case_code": case_code,
                    "title": r["title"][:60],
                    "unit_name": r.get("unit_name", ""),
                })
            except Exception:
                continue

        if created:
            await self.db.commit()

        return {
            "query": query,
            "searched": len(records),
            "actionable": len(actionable),
            "created": len(created),
            "cases": created,
        }

    async def analyze_diagram(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """分析工程圖/測量圖/地籍圖 (Gemma 4 Vision)"""
        from app.services.ai.engineering_diagram_service import EngineeringDiagramService
        from app.extended.models.document import DocumentAttachment
        from sqlalchemy import select

        image_path = params.get("image_path", "")
        diagram_type = params.get("diagram_type", "survey")
        context = params.get("context", "")

        if not image_path:
            return {"error": "缺少 image_path 參數", "count": 0}

        upload_dir = os.getenv("UPLOAD_DIR", "uploads")
        full_path = os.path.join(upload_dir, image_path) if not os.path.isabs(image_path) else image_path

        if not os.path.isfile(full_path):
            stmt = select(DocumentAttachment).where(
                DocumentAttachment.file_name.ilike(f"%{os.path.basename(image_path)}%")
            )
            result = await self.db.execute(stmt)
            att = result.scalar_one_or_none()
            if att and att.file_path:
                full_path = os.path.join(upload_dir, att.file_path)

        if not os.path.isfile(full_path):
            return {"error": f"找不到圖檔: {image_path}", "count": 0}

        with open(full_path, "rb") as f:
            image_bytes = f.read()

        service = EngineeringDiagramService()
        result = await service.analyze_diagram(
            image_bytes=image_bytes,
            diagram_type=diagram_type,
            context=context,
        )
        result["count"] = 1
        return result
