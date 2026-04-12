"""
公文 → Wiki 結構化編譯器 (ADR-0013 + Karpathy Phase 2 Compile)

v1.0: SQL + Template 結構化編譯（無 LLM 呼叫，即時產出）
- 按機關編譯：往來公文統計 + 關聯案件 + 時間軸
- 按案件編譯：案件完整 profile (公文/派工/財務/人員)
- 按類別編譯：收文/發文年度分佈

後續 v2: 加 LLM narrative summary (Gemma 4 8B)

Version: 1.0.0
Created: 2026-04-13
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, desc, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.wiki_service import get_wiki_service, WikiService

logger = logging.getLogger(__name__)


class WikiCompiler:
    """公文 → Wiki 結構化編譯器"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.wiki = get_wiki_service()

    async def compile_all(self, min_doc_count: int = 5) -> Dict[str, Any]:
        """全量編譯：機關 + 案件 + 總覽"""
        results = {
            "agencies": await self.compile_agencies(min_doc_count),
            "projects": await self.compile_projects(min_doc_count),
            "overview": await self.compile_overview(),
        }
        await self.wiki.rebuild_index()
        logger.info(
            "Wiki compile_all done: %d agencies, %d projects",
            results["agencies"]["compiled"],
            results["projects"]["compiled"],
        )
        return results

    # =========================================================================
    # 機關編譯
    # =========================================================================

    async def compile_agencies(self, min_doc_count: int = 5) -> Dict[str, Any]:
        """編譯所有機關的往來 wiki 頁面"""
        from app.extended.models import GovernmentAgency, OfficialDocument

        # 查詢有足夠公文的機關
        stmt = (
            select(
                GovernmentAgency.id,
                GovernmentAgency.agency_name,
                GovernmentAgency.agency_code,
                GovernmentAgency.agency_type,
                func.count(OfficialDocument.id).label("doc_count"),
                func.count(OfficialDocument.id).filter(
                    OfficialDocument.category == "收文"
                ).label("received"),
                func.count(OfficialDocument.id).filter(
                    OfficialDocument.category == "發文"
                ).label("sent"),
                func.min(OfficialDocument.doc_date).label("earliest"),
                func.max(OfficialDocument.doc_date).label("latest"),
            )
            .join(
                OfficialDocument,
                or_(
                    OfficialDocument.sender_agency_id == GovernmentAgency.id,
                    OfficialDocument.receiver_agency_id == GovernmentAgency.id,
                ),
            )
            .where(GovernmentAgency.is_self.is_(False))
            .group_by(GovernmentAgency.id)
            .having(func.count(OfficialDocument.id) >= min_doc_count)
            .order_by(desc("doc_count"))
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        compiled = 0
        for row in rows:
            # 查詢關聯的承攬案件
            projects = await self._get_agency_projects(row.id)

            # 查詢最近 5 筆公文主旨
            recent_docs = await self._get_recent_docs_for_agency(row.id, limit=5)

            # 編譯成 wiki 頁面
            description = self._build_agency_description(row, projects, recent_docs)

            await self.wiki.ingest_entity(
                name=row.agency_name,
                entity_type="org",
                description=description,
                sources=[f"documents (auto-compiled, {row.doc_count} docs)"],
                tags=["機關", row.agency_type or "government"],
                related_entities=[p["name"] for p in projects[:5]],
                confidence="high" if row.doc_count >= 20 else "medium",
            )
            compiled += 1

        return {"compiled": compiled, "skipped_below_threshold": 0}

    async def _get_agency_projects(self, agency_id: int) -> List[Dict]:
        """取得機關關聯的承攬案件"""
        from app.extended.models import ContractProject

        stmt = (
            select(
                ContractProject.project_name,
                ContractProject.project_code,
                ContractProject.status,
                ContractProject.year,
            )
            .where(ContractProject.client_agency_id == agency_id)
            .order_by(desc(ContractProject.year))
            .limit(10)
        )
        result = await self.db.execute(stmt)
        return [
            {
                "name": r.project_name,
                "code": r.project_code or "",
                "status": r.status or "",
                "year": r.year,
            }
            for r in result.all()
        ]

    async def _get_recent_docs_for_agency(
        self, agency_id: int, limit: int = 5
    ) -> List[Dict]:
        """取得機關最近公文"""
        from app.extended.models import OfficialDocument

        stmt = (
            select(
                OfficialDocument.subject,
                OfficialDocument.doc_number,
                OfficialDocument.doc_date,
                OfficialDocument.category,
            )
            .where(
                or_(
                    OfficialDocument.sender_agency_id == agency_id,
                    OfficialDocument.receiver_agency_id == agency_id,
                )
            )
            .order_by(desc(OfficialDocument.doc_date))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [
            {
                "subject": r.subject,
                "doc_number": r.doc_number or "",
                "date": str(r.doc_date) if r.doc_date else "",
                "category": r.category or "",
            }
            for r in result.all()
        ]

    def _build_agency_description(self, row, projects, recent_docs) -> str:
        """建構機關 wiki 描述"""
        lines = [
            f"**機關代碼**: {row.agency_code or '(未登錄)'}",
            f"**機關類型**: {row.agency_type or '(未分類)'}",
            f"**往來期間**: {row.earliest} ~ {row.latest}",
            f"**公文統計**: 共 {row.doc_count} 件 (收文 {row.received} / 發文 {row.sent})",
            "",
        ]

        if projects:
            lines.append("## 關聯承攬案件")
            lines.append("")
            lines.append("| 案名 | 案號 | 年度 | 狀態 |")
            lines.append("|------|------|------|------|")
            for p in projects:
                lines.append(
                    f"| {p['name'][:40]} | {p['code']} | {p['year'] or ''} | {p['status']} |"
                )
            lines.append("")

        if recent_docs:
            lines.append("## 最近公文")
            lines.append("")
            for d in recent_docs:
                lines.append(
                    f"- [{d['category']}] {d['date']} {d['subject'][:60]}"
                )
            lines.append("")

        return "\n".join(lines)

    # =========================================================================
    # 案件編譯
    # =========================================================================

    async def compile_projects(self, min_doc_count: int = 5) -> Dict[str, Any]:
        """編譯所有案件的完整 profile wiki 頁面"""
        from app.extended.models import ContractProject, OfficialDocument

        stmt = (
            select(
                ContractProject.id,
                ContractProject.project_name,
                ContractProject.project_code,
                ContractProject.status,
                ContractProject.year,
                ContractProject.category,
                ContractProject.contract_amount,
                ContractProject.location,
                func.count(OfficialDocument.id).label("doc_count"),
            )
            .outerjoin(
                OfficialDocument,
                OfficialDocument.contract_project_id == ContractProject.id,
            )
            .group_by(ContractProject.id)
            .having(func.count(OfficialDocument.id) >= min_doc_count)
            .order_by(desc("doc_count"))
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        compiled = 0
        for row in rows:
            recent_docs = await self._get_project_recent_docs(row.id, limit=10)
            financial = await self._get_project_financial(row.project_code)

            description = self._build_project_description(row, recent_docs, financial)

            await self.wiki.ingest_entity(
                name=row.project_name[:80],
                entity_type="project",
                description=description,
                sources=[f"contract_projects #{row.id}, {row.doc_count} docs"],
                tags=["案件", row.status or "unknown", f"Y{row.year}" if row.year else ""],
                confidence="high" if row.doc_count >= 20 else "medium",
            )
            compiled += 1

        return {"compiled": compiled}

    async def _get_project_recent_docs(
        self, project_id: int, limit: int = 10
    ) -> List[Dict]:
        """取得案件關聯公文"""
        from app.extended.models import OfficialDocument

        stmt = (
            select(
                OfficialDocument.subject,
                OfficialDocument.doc_number,
                OfficialDocument.doc_date,
                OfficialDocument.category,
                OfficialDocument.doc_type,
            )
            .where(OfficialDocument.contract_project_id == project_id)
            .order_by(desc(OfficialDocument.doc_date))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [
            {
                "subject": r.subject,
                "doc_number": r.doc_number or "",
                "date": str(r.doc_date) if r.doc_date else "",
                "category": r.category or "",
                "doc_type": r.doc_type or "",
            }
            for r in result.all()
        ]

    async def _get_project_financial(
        self, project_code: Optional[str]
    ) -> Dict[str, Any]:
        """取得案件財務摘要"""
        if not project_code:
            return {}

        from app.extended.models.erp import ERPQuotation

        stmt = (
            select(
                func.count(ERPQuotation.id).label("quote_count"),
                func.sum(ERPQuotation.total_price).label("total_price"),
            )
            .where(
                ERPQuotation.project_code == project_code,
                ERPQuotation.deleted_at.is_(None),
            )
        )
        result = await self.db.execute(stmt)
        row = result.first()
        if not row or not row.quote_count:
            return {}

        return {
            "quote_count": row.quote_count,
            "total_quoted": float(row.total_price) if row.total_price else 0,
        }

    def _build_project_description(self, row, recent_docs, financial) -> str:
        """建構案件 wiki 描述"""
        amount_str = (
            f"${row.contract_amount:,.0f}" if row.contract_amount else "(未登錄)"
        )
        lines = [
            f"**案號**: {row.project_code or '(未指派)'}",
            f"**狀態**: {row.status or '(未設定)'}",
            f"**年度**: {row.year or '(未設定)'}",
            f"**合約金額**: {amount_str}",
            f"**地點**: {row.location or '(未登錄)'}",
            f"**關聯公文**: {row.doc_count} 件",
            "",
        ]

        if financial:
            lines.append("## 財務摘要")
            lines.append(
                f"- 報價紀錄 {financial['quote_count']} 筆, "
                f"合計 ${financial['total_quoted']:,.0f}"
            )
            lines.append("")

        if recent_docs:
            lines.append("## 最近公文 (前 10 筆)")
            lines.append("")
            lines.append("| 日期 | 類別 | 文號 | 主旨 |")
            lines.append("|------|------|------|------|")
            for d in recent_docs:
                lines.append(
                    f"| {d['date']} | {d['category']} | {d['doc_number'][:15]} | {d['subject'][:40]} |"
                )
            lines.append("")

        return "\n".join(lines)

    # =========================================================================
    # 總覽
    # =========================================================================

    async def compile_overview(self) -> Dict[str, Any]:
        """編譯知識庫總覽 wiki 頁面"""
        from app.extended.models import (
            OfficialDocument,
            ContractProject,
            GovernmentAgency,
        )

        # 基礎統計
        doc_count = await self.db.scalar(select(func.count(OfficialDocument.id)))
        project_count = await self.db.scalar(select(func.count(ContractProject.id)))
        agency_count = await self.db.scalar(select(func.count(GovernmentAgency.id)))

        # 年度分佈
        year_dist = await self.db.execute(
            select(
                func.extract("year", OfficialDocument.doc_date).label("year"),
                func.count().label("count"),
            )
            .where(OfficialDocument.doc_date.isnot(None))
            .group_by("year")
            .order_by("year")
        )
        year_rows = year_dist.all()

        # 類別分佈
        cat_dist = await self.db.execute(
            select(
                OfficialDocument.category,
                func.count().label("count"),
            )
            .group_by(OfficialDocument.category)
        )
        cat_rows = cat_dist.all()

        description = self._build_overview(
            doc_count, project_count, agency_count, year_rows, cat_rows
        )

        # 存為 topic 頁面
        slug = "公文管理系統總覽"
        page_path = self.wiki.root / "topics" / f"{slug}.md"
        content = f"""---
title: {slug}
type: topic
created: {datetime.now().strftime('%Y-%m-%d')}
sources: [compiled from database]
tags: [總覽, 統計]
confidence: high
---

# {slug}

{description}
"""
        page_path.write_text(content, encoding="utf-8")
        self.wiki._append_log("compile", f"topic | {slug}")

        return {
            "documents": doc_count,
            "projects": project_count,
            "agencies": agency_count,
        }

    def _build_overview(self, doc_count, project_count, agency_count, year_rows, cat_rows) -> str:
        lines = [
            f"**公文總數**: {doc_count} 件",
            f"**承攬案件**: {project_count} 件",
            f"**機關數**: {agency_count}",
            f"**編譯時間**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 年度公文分佈",
            "",
            "| 年度 | 件數 |",
            "|------|------|",
        ]
        for r in year_rows:
            lines.append(f"| {int(r.year)} | {r.count} |")

        lines.extend([
            "",
            "## 類別分佈",
            "",
        ])
        for r in cat_rows:
            lines.append(f"- **{r.category or '(未分類)'}**: {r.count} 件")

        return "\n".join(lines)
