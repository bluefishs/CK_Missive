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
        from app.services.ai.document.engineering_diagram_service import EngineeringDiagramService
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

    # ── 跨圖譜工具 (v5.5.4) ──

    async def search_across_graphs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """7 大圖譜統一搜尋"""
        query = params.get("query", "")
        limit = params.get("limit", 5)
        if not query:
            return {"error": "query 為必填", "count": 0}

        from app.services.ai.graph.graph_query_service import GraphQueryService
        from app.services.ai.graph.erp_graph_types import ERP_ENTITY_TYPES
        from app.extended.models.knowledge_graph import CanonicalEntity
        from app.extended.models.tender_cache import TenderRecord
        from sqlalchemy import select
        import re

        results = []
        escaped = re.sub(r'([%_\\])', r'\\\1', query)

        # KG-1: 知識圖譜
        try:
            svc = GraphQueryService(self.db)
            kg_entities = await svc.search_entities(query=query, limit=limit)
            for e in kg_entities:
                results.append({
                    "source": "kg", "type": e.get("entity_type", ""),
                    "name": e.get("canonical_name", ""),
                    "detail": e.get("description", ""),
                })
        except Exception as ex:
            logger.debug("KG search failed: %s", ex)

        # KG-5: 標案
        try:
            stmt = (
                select(TenderRecord.title, TenderRecord.unit_name, TenderRecord.budget)
                .where(TenderRecord.title.ilike(f"%{escaped}%"))
                .limit(limit)
            )
            for row in (await self.db.execute(stmt)).all():
                results.append({
                    "source": "tender", "type": "tender_record",
                    "name": row[0] or "", "detail": f"機關: {row[1]} | 預算: {row[2]}",
                })
        except Exception as ex:
            logger.debug("Tender search failed: %s", ex)

        # KG-7: ERP
        try:
            stmt = (
                select(CanonicalEntity.canonical_name, CanonicalEntity.entity_type, CanonicalEntity.description)
                .where(CanonicalEntity.entity_type.in_(ERP_ENTITY_TYPES))
                .where(CanonicalEntity.canonical_name.ilike(f"%{escaped}%"))
                .limit(limit)
            )
            for row in (await self.db.execute(stmt)).all():
                results.append({
                    "source": "erp", "type": row[1],
                    "name": row[0], "detail": row[2] if isinstance(row[2], str) else "",
                })
        except Exception as ex:
            logger.debug("ERP search failed: %s", ex)

        return {"results": results, "count": len(results), "graphs_searched": 3}

    async def search_erp_entities(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """ERP 財務圖譜搜尋"""
        query = params.get("query", "")
        entity_type = params.get("entity_type")
        if not query:
            return {"error": "query 為必填", "count": 0}

        from app.services.ai.graph.erp_graph_types import ERP_ENTITY_TYPES
        from app.extended.models.knowledge_graph import CanonicalEntity
        from sqlalchemy import select
        import re

        escaped = re.sub(r'([%_\\])', r'\\\1', query)
        types = {entity_type} if entity_type and entity_type in ERP_ENTITY_TYPES else ERP_ENTITY_TYPES

        stmt = (
            select(
                CanonicalEntity.canonical_name,
                CanonicalEntity.entity_type,
                CanonicalEntity.description,
                CanonicalEntity.external_id,
            )
            .where(CanonicalEntity.entity_type.in_(types))
            .where(CanonicalEntity.canonical_name.ilike(f"%{escaped}%"))
            .order_by(CanonicalEntity.mention_count.desc())
            .limit(10)
        )
        rows = (await self.db.execute(stmt)).all()

        results = []
        for r in rows:
            results.append({
                "name": r[0], "type": r[1],
                "detail": r[2] if isinstance(r[2], str) else "",
                "case_code": r[3] or "",
            })

        return {"results": results, "count": len(results)}
