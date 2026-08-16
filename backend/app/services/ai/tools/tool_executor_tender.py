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
        from app.services.tender.search import TenderSearchService

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
        """Multi-Agent: 標案自動批次建案。

        2026-08-16：本方法原本自己寫了一份建案邏輯，與一鍵建案分歧到
        **業務規則相反**的程度（詳見 `services/tender/case_creation.py` 檔頭）。
        現在共用同一份實作，因此自動繼承 5 道查重、委託單位建立、金額帶入、
        來源標案回指，以及「邀標階段不建報價單」這條規則。
        """
        from app.services.tender.search import TenderSearchService
        from app.services.tender.case_creation import (
            TenderCaseCreationService,
            TenderCaseDuplicateError,
        )

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
            return {
                "success": True, "created": [], "skipped": [],
                "message": f"找到 {len(records)} 筆標案，但沒有符合條件的公開/限制性招標",
            }

        creator = TenderCaseCreationService(self.db)
        created, skipped = [], []

        for r in actionable:
            try:
                res = await creator.create_from_tender(
                    title=r["title"],
                    unit_id=str(r.get("unit_id") or ""),
                    unit_name=r.get("unit_name", ""),
                    job_number=r.get("job_number"),
                    budget=r.get("budget"),
                    tender_id=r.get("id") or r.get("tender_id"),
                    source_label="政府標案[Agent]",
                )
                created.append({
                    "case_code": res["case_code"],
                    "title": r["title"][:60],
                    "unit_name": r.get("unit_name", ""),
                    "contract_amount": res["contract_amount"],
                })
            except TenderCaseDuplicateError as e:
                skipped.append({"title": r["title"][:40], "reason": str(e)})
            except Exception as e:
                # 原本是 `except Exception: continue` —— 建案失敗完全不留痕跡，
                # 而回傳的 created 清單看起來一切正常（沉默成功）。
                logger.warning(
                    "[Agent] 建案失敗 title=%r: %s: %s",
                    r["title"][:40], type(e).__name__, e,
                )
                skipped.append({"title": r["title"][:40], "reason": f"{type(e).__name__}: {e}"})

        if created:
            await self.db.commit()

        no_amount = [c["case_code"] for c in created if c["contract_amount"] is None]
        msg = f"已建立 {len(created)} 筆案件"
        if skipped:
            msg += f"，跳過 {len(skipped)} 筆"
        if no_amount:
            msg += f"。⚠️ {len(no_amount)} 筆來源標案無預算金額，需人工補填合約金額才能成案"

        return {"success": True, "created": created, "skipped": skipped, "message": msg}

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
