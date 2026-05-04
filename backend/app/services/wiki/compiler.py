"""
公文 → Wiki 結構化編譯器 (ADR-0013 + Karpathy Phase 2 Compile)

v1.1: 增量編譯 — 記錄上次時間戳，只重編有新公文的機關/案件
v1.0: SQL + Template 結構化編譯（無 LLM 呼叫，即時產出）

後續 v2: 加 LLM narrative summary (Gemma 4 8B)

Version: 1.1.0
Created: 2026-04-13
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, desc, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from .service import get_wiki_service, WikiService, WIKI_ROOT, _slugify
from .formatter import WikiFormatter

logger = logging.getLogger(__name__)

# 增量編譯 checkpoint
_CHECKPOINT_FILE = WIKI_ROOT / ".compile_checkpoint.json"


def _load_checkpoint() -> dict:
    if _CHECKPOINT_FILE.exists():
        try:
            return json.loads(_CHECKPOINT_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_checkpoint(data: dict):
    _CHECKPOINT_FILE.write_text(
        json.dumps(data, default=str, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class WikiCompiler:
    """公文 → Wiki 結構化編譯器"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.wiki = get_wiki_service()
        self._kg_cache: Dict[str, Optional[int]] = {}
        self._pre_snapshot: Dict[str, int] = {}  # path → file_size

    def _snapshot_pages(self) -> Dict[str, int]:
        """快照所有 wiki 頁面 (path → 檔案大小)"""
        snap: Dict[str, int] = {}
        for subdir in ["entities", "topics", "sources", "synthesis"]:
            d = self.wiki.root / subdir
            if not d.exists():
                continue
            for f in d.glob("*.md"):
                snap[f"{subdir}/{f.name}"] = f.stat().st_size
        return snap

    def _compute_diff(self, before: Dict[str, int], after: Dict[str, int]) -> Dict[str, Any]:
        """比對前後快照，產出 diff 摘要"""
        b_set, a_set = set(before.keys()), set(after.keys())
        added = sorted(a_set - b_set)
        removed = sorted(b_set - a_set)
        updated = sorted(
            p for p in (b_set & a_set) if before[p] != after[p]
        )
        return {
            "added": len(added),
            "updated": len(updated),
            "removed": len(removed),
            "unchanged": len(b_set & a_set) - len(updated),
            "added_pages": added[:20],
            "updated_pages": updated[:20],
            "removed_pages": removed[:10],
        }

    async def _lookup_kg_id(self, name: str) -> Optional[int]:
        """查詢 KG canonical_entity ID (exact → LIKE fallback，帶快取)"""
        if name in self._kg_cache:
            return self._kg_cache[name]
        try:
            from app.extended.models.knowledge_graph import CanonicalEntity

            # 1. Exact match
            result = await self.db.execute(
                select(CanonicalEntity.id)
                .where(
                    CanonicalEntity.canonical_name == name,
                    CanonicalEntity.graph_domain == "knowledge",
                )
                .limit(1)
            )
            row = result.first()
            if row:
                self._kg_cache[name] = row.id
                return row.id

            # 2. LIKE fallback — 前 20 字匹配 (案件名稱常被截斷或帶括號差異)
            if len(name) >= 10:
                prefix = name[:20].replace("(", "%").replace(")", "%")
                result2 = await self.db.execute(
                    select(CanonicalEntity.id)
                    .where(
                        CanonicalEntity.canonical_name.like(f"{prefix}%"),
                        CanonicalEntity.graph_domain == "knowledge",
                    )
                    .limit(1)
                )
                row2 = result2.first()
                if row2:
                    self._kg_cache[name] = row2.id
                    return row2.id

            self._kg_cache[name] = None
            return None
        except Exception:
            return None

    async def compile_incremental(self, min_doc_count: int = 5) -> Dict[str, Any]:
        """增量編譯：只處理上次編譯後有新/更新公文的機關和案件。

        若無 checkpoint (首次) 則退回全量編譯。
        """
        from app.extended.models import OfficialDocument

        ckpt = _load_checkpoint()
        last_ts = ckpt.get("last_full_compile") or ckpt.get("last_incremental")
        if not last_ts:
            logger.info("Wiki incremental: no checkpoint, falling back to full compile")
            return await self.compile_all(min_doc_count)

        since = datetime.fromisoformat(last_ts)
        logger.info("Wiki incremental since %s", since)

        # 找出有新公文的機關 IDs
        agency_ids = set()
        stmt_agencies = (
            select(OfficialDocument.sender_agency_id, OfficialDocument.receiver_agency_id)
            .where(OfficialDocument.updated_at > since)
        )
        rows = (await self.db.execute(stmt_agencies)).all()
        for r in rows:
            if r.sender_agency_id:
                agency_ids.add(r.sender_agency_id)
            if r.receiver_agency_id:
                agency_ids.add(r.receiver_agency_id)

        # 找出有新公文的案件 IDs
        project_ids = set()
        stmt_projects = (
            select(OfficialDocument.contract_project_id)
            .where(
                OfficialDocument.updated_at > since,
                OfficialDocument.contract_project_id.isnot(None),
            )
        )
        p_rows = (await self.db.execute(stmt_projects)).all()
        for r in p_rows:
            project_ids.add(r.contract_project_id)

        before = self._snapshot_pages()

        results = {
            "mode": "incremental",
            "since": str(since),
            "agencies": {"compiled": 0, "affected_ids": list(agency_ids)},
            "projects": {"compiled": 0, "affected_ids": list(project_ids)},
        }

        # 重編受影響的機關
        if agency_ids:
            result = await self.compile_agencies(
                min_doc_count, agency_id_filter=agency_ids
            )
            results["agencies"]["compiled"] = result["compiled"]

        # 重編受影響的案件
        if project_ids:
            result = await self.compile_projects(
                min_doc_count, project_id_filter=project_ids
            )
            results["projects"]["compiled"] = result["compiled"]

        # 總覽 + interest signals 永遠更新
        results["overview"] = await self.compile_overview()
        results["interest"] = await self.compile_interest_signals(days=7)
        await self.wiki.rebuild_index()

        after = self._snapshot_pages()
        diff = self._compute_diff(before, after)
        results["diff"] = diff

        _save_checkpoint({
            **ckpt,
            "last_incremental": datetime.now().isoformat(),
            "last_affected_agencies": len(agency_ids),
            "last_affected_projects": len(project_ids),
            "diff": diff,
        })

        logger.info(
            "Wiki incremental: %d agencies, %d projects (since %s) | diff: +%d ~%d -%d",
            results["agencies"]["compiled"],
            results["projects"]["compiled"],
            since, diff["added"], diff["updated"], diff["removed"],
        )
        return results

    async def compile_all(self, min_doc_count: int = 5) -> Dict[str, Any]:
        """全量編譯：機關 + 案件 + 總覽 + diff"""
        before = self._snapshot_pages()

        results = {
            "agencies": await self.compile_agencies(min_doc_count),
            "projects": await self.compile_projects(min_doc_count),
            "overview": await self.compile_overview(),
        }
        await self.wiki.rebuild_index()

        after = self._snapshot_pages()
        diff = self._compute_diff(before, after)
        results["diff"] = diff

        _save_checkpoint({
            "last_full_compile": datetime.now().isoformat(),
            "agencies": results["agencies"]["compiled"],
            "projects": results["projects"]["compiled"],
            "diff": diff,
        })
        logger.info(
            "Wiki compile_all: %d agencies, %d projects | diff: +%d ~%d -%d",
            results["agencies"]["compiled"],
            results["projects"]["compiled"],
            diff["added"], diff["updated"], diff["removed"],
        )
        return results

    # =========================================================================
    # 機關編譯
    # =========================================================================

    async def compile_agencies(
        self, min_doc_count: int = 5, agency_id_filter: Optional[set] = None,
    ) -> Dict[str, Any]:
        """編譯機關往來 wiki 頁面。agency_id_filter 可限定只編譯���定 IDs (增量模式)。"""
        from app.extended.models import GovernmentAgency, OfficialDocument

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
        if agency_id_filter:
            stmt = stmt.where(GovernmentAgency.id.in_(agency_id_filter))
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

            kg_id = await self._lookup_kg_id(row.agency_name)
            await self.wiki.ingest_entity(
                name=row.agency_name,
                entity_type="org",
                description=description,
                sources=[f"documents (auto-compiled, {row.doc_count} docs)"],
                tags=["機關", row.agency_type or "government"],
                related_entities=[
                    p["name"] for p in projects[:5]
                    if (self.wiki.root / "entities" / f"{_slugify(p['name'][:80])}.md").exists()
                ],
                confidence="high" if row.doc_count >= 20 else "medium",
                kg_entity_id=kg_id,
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
        """建構機關 wiki 描述 (委派 WikiFormatter)"""
        return WikiFormatter.build_agency_description(row, projects, recent_docs)

    # =========================================================================
    # 案件編譯
    # =========================================================================

    async def compile_projects(
        self, min_doc_count: int = 5, project_id_filter: Optional[set] = None,
    ) -> Dict[str, Any]:
        """編譯案件 profile wiki 頁面。project_id_filter 可限定只編譯指定 IDs (增量模式)。"""
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
        if project_id_filter:
            stmt = stmt.where(ContractProject.id.in_(project_id_filter))
        result = await self.db.execute(stmt)
        rows = result.all()

        compiled = 0
        dispatch_compiled = 0
        for row in rows:
            all_docs = await self._get_project_all_docs(row.id)
            financial = await self._get_project_financial(row.project_code)
            dispatches = await self._get_project_dispatches(row.id)
            agencies = await self._get_project_agencies(row.id)
            engineering = await self._get_project_engineering(row.id)

            description = self._build_project_description_v2(
                row, all_docs, financial, dispatches, agencies, engineering
            )

            related = [a["name"] for a in agencies[:5]]
            # 工程名稱不加入 related (無對應 wiki 頁面，會產生 broken link)
            # 已在描述的「工程名稱」表格中呈現

            kg_id = await self._lookup_kg_id(row.project_name)
            await self.wiki.ingest_entity(
                name=row.project_name[:80],
                entity_type="project",
                description=description,
                sources=[f"contract_projects #{row.id}, {row.doc_count} docs"],
                tags=["案件", row.status or "unknown", f"Y{row.year}" if row.year else ""],
                related_entities=related,
                confidence="high" if row.doc_count >= 20 else "medium",
                kg_entity_id=kg_id,
            )
            compiled += 1

            # 每張派工單產出獨立 wiki 頁
            for d in dispatches:
                dc = await self._compile_dispatch_page(d, row)
                if dc:
                    dispatch_compiled += 1

        return {"compiled": compiled, "dispatch_pages": dispatch_compiled}

    async def _get_project_all_docs(self, project_id: int) -> List[Dict]:
        """取得案件所有關聯公文"""
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

    async def _get_project_dispatches(self, project_id: int) -> List[Dict]:
        """取得案件的派工單"""
        try:
            from app.extended.models.taoyuan import TaoyuanDispatchOrder
            stmt = (
                select(
                    TaoyuanDispatchOrder.id.label("dispatch_order_id"),
                    TaoyuanDispatchOrder.dispatch_no,
                    TaoyuanDispatchOrder.project_name,  # 工程名稱
                    TaoyuanDispatchOrder.work_type,
                    TaoyuanDispatchOrder.deadline,
                    TaoyuanDispatchOrder.case_handler,
                )
                .where(TaoyuanDispatchOrder.contract_project_id == project_id)
                .order_by(TaoyuanDispatchOrder.id)
            )
            result = await self.db.execute(stmt)
            return [
                {
                    "dispatch_order_id": r.dispatch_order_id,
                    "dispatch_no": r.dispatch_no,
                    "project_name": r.project_name or "",
                    "work_type": r.work_type or "",
                    "deadline": r.deadline or "",
                    "handler": r.case_handler or "",
                    "date": "",
                    "status": "",
                }
                for r in result.all()
            ]
        except Exception:
            return []

    async def _get_project_agencies(self, project_id: int) -> List[Dict]:
        """取得案件往來的所有機關 (從公文 sender/receiver 統計)"""
        from app.extended.models import OfficialDocument, GovernmentAgency

        # sender agencies
        stmt = (
            select(
                GovernmentAgency.agency_name,
                func.count().label("doc_count"),
            )
            .join(OfficialDocument, or_(
                OfficialDocument.sender_agency_id == GovernmentAgency.id,
                OfficialDocument.receiver_agency_id == GovernmentAgency.id,
            ))
            .where(
                OfficialDocument.contract_project_id == project_id,
                GovernmentAgency.is_self.is_(False),
            )
            .group_by(GovernmentAgency.agency_name)
            .order_by(desc("doc_count"))
            .limit(10)
        )
        result = await self.db.execute(stmt)
        return [{"name": r.agency_name, "doc_count": r.doc_count} for r in result.all()]

    async def _get_project_engineering(self, project_id: int) -> List[Dict]:
        """取得案件下的工程名稱 (taoyuan_projects)"""
        try:
            from app.extended.models.taoyuan import TaoyuanProject
            stmt = (
                select(
                    TaoyuanProject.project_name,
                    TaoyuanProject.district,
                    TaoyuanProject.start_point,
                    TaoyuanProject.end_point,
                )
                .where(TaoyuanProject.contract_project_id == project_id)
                .order_by(TaoyuanProject.id)
            )
            result = await self.db.execute(stmt)
            return [
                {
                    "name": r.project_name or "",
                    "district": r.district or "",
                    "start_point": r.start_point or "",
                    "end_point": r.end_point or "",
                }
                for r in result.all()
            ]
        except Exception:
            return []

    async def _compile_dispatch_page(self, dispatch: Dict, project_row) -> bool:
        """為單張派工單建立 wiki 頁面 — 含完整公文時間軸"""
        dispatch_no = dispatch.get("dispatch_no", "")
        dispatch_id = dispatch.get("dispatch_order_id")
        if not dispatch_no or not dispatch_id:
            return False

        # 取得派工單關聯的公文
        from app.extended.models import OfficialDocument
        from app.extended.models.taoyuan import TaoyuanDispatchDocumentLink

        stmt = (
            select(
                OfficialDocument.subject,
                OfficialDocument.doc_number,
                OfficialDocument.doc_date,
                OfficialDocument.category,
            )
            .join(
                TaoyuanDispatchDocumentLink,
                TaoyuanDispatchDocumentLink.document_id == OfficialDocument.id,
            )
            .where(TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id)
            .order_by(OfficialDocument.doc_date)
        )
        result = await self.db.execute(stmt)
        docs = [
            {
                "subject": r.subject,
                "doc_number": r.doc_number or "",
                "date": str(r.doc_date) if r.doc_date else "",
                "category": r.category or "",
            }
            for r in result.all()
        ]

        # 取得工程名稱 (從 taoyuan_projects via dispatch link)
        eng_names = []
        try:
            from app.extended.models.taoyuan import (
                TaoyuanDispatchProjectLink, TaoyuanProject,
            )
            eng_stmt = (
                select(TaoyuanProject.project_name, TaoyuanProject.district)
                .join(
                    TaoyuanDispatchProjectLink,
                    TaoyuanDispatchProjectLink.taoyuan_project_id == TaoyuanProject.id,
                )
                .where(TaoyuanDispatchProjectLink.dispatch_order_id == dispatch_id)
            )
            eng_result = await self.db.execute(eng_stmt)
            eng_names = [
                {"name": r.project_name, "district": r.district or ""}
                for r in eng_result.all()
            ]
        except Exception:
            pass

        lines = [
            f"**所屬案件**: [[entities/{project_row.project_name[:80]}|{project_row.project_name[:40]}]]",
            f"**案號**: {project_row.project_code or ''}",
            f"**作業類別**: {dispatch.get('work_type', '')}",
            f"**狀態**: {dispatch.get('status', '')}",
            f"**派工日期**: {dispatch.get('date', '')}",
            f"**關聯公文**: {len(docs)} 件",
            "",
        ]

        if eng_names:
            lines.append("## 工程名稱")
            lines.append("")
            for eng in eng_names:
                lines.append(f"- {eng['name']} ({eng['district']})" if eng['district'] else f"- {eng['name']}")
            lines.append("")

        if docs:
            lines.append(f"## 公文時間軸 ({len(docs)} 件)")
            lines.append("")
            lines.append("| 日期 | 類別 | 文號 | 主旨 |")
            lines.append("|------|------|------|------|")
            for d in docs:
                lines.append(
                    f"| {d['date']} | {d['category']} | {d['doc_number'][:18]} | {d['subject'][:45]} |"
                )
            lines.append("")

        await self.wiki.ingest_entity(
            name=dispatch_no,
            entity_type="dispatch",
            description="\n".join(lines),
            sources=[f"dispatch #{dispatch_id}, {len(docs)} docs"],
            tags=["派工單", dispatch.get("work_type", ""), dispatch.get("status", "")],
            related_entities=[project_row.project_name[:80]],
            confidence="high" if len(docs) >= 3 else "medium",
        )
        return True

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

    def _build_project_description_v2(
        self, row, all_docs, financial, dispatches, agencies, engineering=None,
    ) -> str:
        """建構案件 wiki 描述 (委派 WikiFormatter)"""
        return WikiFormatter.build_project_description_v2(
            row, all_docs, financial, dispatches, agencies, engineering,
        )

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

        # 自動建立索引頁 — 所有 entity 頁面至少有一個入站連結 (解決 orphan)
        await self._build_index_pages()

        # v6.6 Phase B1（I5）：自動聚合 topics（5 篇跨 entity 主題）
        # 補 wiki/topics/ 從 4 → 9 篇（總覽 + 3 索引 + 1 interest + 5 聚合）
        try:
            await self._compile_aggregate_topics()
        except Exception as e:
            logger.warning("Aggregate topics compile failed (non-blocking): %s", e)

        return {
            "documents": doc_count,
            "projects": project_count,
            "agencies": agency_count,
        }

    async def _build_index_pages(self):
        """建立機關/案件/派工索引 topic 頁，為所有 entity 建立入站連結 (消除 orphan)"""
        from .service import _slugify as _slug

        entities_dir = self.wiki.root / "entities"
        if not entities_dir.exists():
            return

        # 按 entity_type 分組
        import re
        groups: Dict[str, List[str]] = {"org": [], "project": [], "dispatch": []}
        for f in sorted(entities_dir.glob("*.md")):
            try:
                head = f.read_text(encoding="utf-8")[:300]
                et_m = re.search(r'^entity_type:\s*(.+)$', head, re.MULTILINE)
                et = et_m.group(1).strip() if et_m else "unknown"
                title_m = re.search(r'^title:\s*(.+)$', head, re.MULTILINE)
                title = title_m.group(1).strip() if title_m else f.stem
                if et in groups:
                    groups[et].append(title)
            except Exception:
                pass

        labels = {"org": "機關索引", "project": "案件索引", "dispatch": "派工單索引"}
        for et, titles in groups.items():
            if not titles:
                continue
            label = labels[et]
            lines = [
                f"**數量**: {len(titles)}",
                f"**編譯時間**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "",
            ]
            for t in titles:
                lines.append(f"- [[entities/{_slug(t)}|{t[:50]}]]")

            idx_path = self.wiki.root / "topics" / f"{label}.md"
            idx_content = f"""---
title: {label}
type: topic
created: {datetime.now().strftime('%Y-%m-%d')}
tags: [索引, {et}]
confidence: high
---

# {label}

{chr(10).join(lines)}
"""
            idx_path.write_text(idx_content, encoding="utf-8")

    def _build_overview(self, doc_count, project_count, agency_count, year_rows, cat_rows) -> str:
        """建構總覽 wiki 描述 (委派 WikiFormatter)"""
        return WikiFormatter.build_overview(doc_count, project_count, agency_count, year_rows, cat_rows)

    # =========================================================================
    # Aggregate Topics (v6.6 Phase B1, I5) — 跨 entity 聚合主題（純 SQL）
    # =========================================================================

    async def _compile_aggregate_topics(self) -> Dict[str, Any]:
        """產出 5 個跨 entity 聚合 topic（純 SQL，不碰 LLM）。

        補 wiki/topics/ 從 4 → 9 篇（topics 不再貧瘠）。每篇都是
        「跨 entity 聚合主題」，與 entities/（單一實體）和 synthesis/（綜合）區分。

        包含：
        - 高頻機關 Top 10（公文 sender + receiver 累計）
        - 逾期公文 Top 20（截止日已過但未結案）
        - 月派工量趨勢（過去 12 月）
        - KG 高 degree entities Top 10
        - 資料品質快照（無 KG 連結 wiki / 無 doc agency）
        """
        results = {}
        for name, fn in [
            ("top_agencies", self._topic_top_agencies),
            ("overdue_docs", self._topic_overdue_docs),
            ("monthly_dispatch_volume", self._topic_monthly_dispatch_volume),
            ("kg_top_degree", self._topic_kg_top_degree),
            ("data_quality_snapshot", self._topic_data_quality_snapshot),
            # I5+ phase 1 (5/04 v3.0 覆盤派生): 第一個新增 topic
            ("top_vendors", self._topic_top_vendors),
            # I5+ phase 2: 每週工作流量熱圖
            ("weekly_work_heatmap", self._topic_weekly_work_heatmap),
            # I5+ phase 3: ADR active 索引（純檔案掃描，無需 DB）
            ("adr_active_index", self._topic_adr_active_index),
            # I5+ phase 4: ERP 月度趨勢（報價+開票+請款）
            ("erp_monthly_trend", self._topic_erp_monthly_trend),
            # I5+ phase 5: lessons registry 索引（純檔案掃描）
            ("lessons_registry_index", self._topic_lessons_registry),
        ]:
            try:
                results[name] = await fn()
            except Exception as e:
                logger.warning("Aggregate topic %s failed: %s", name, e)
                results[name] = {"compiled": False, "error": str(e)[:100]}
        return results

    async def _topic_top_agencies(self) -> Dict[str, Any]:
        """高頻往來機關 Top 10（公文 sender 與 receiver 累計次數）。"""
        from app.extended.models import OfficialDocument
        # sender + receiver 各算
        s_rows = (await self.db.execute(
            select(OfficialDocument.sender, func.count().label("c"))
            .where(OfficialDocument.sender.isnot(None))
            .group_by(OfficialDocument.sender)
        )).all()
        r_rows = (await self.db.execute(
            select(OfficialDocument.receiver, func.count().label("c"))
            .where(OfficialDocument.receiver.isnot(None))
            .group_by(OfficialDocument.receiver)
        )).all()
        merged: Dict[str, int] = {}
        for name, c in s_rows:
            if name:
                merged[name] = merged.get(name, 0) + c
        for name, c in r_rows:
            if name:
                merged[name] = merged.get(name, 0) + c
        top = sorted(merged.items(), key=lambda x: -x[1])[:10]
        if not top:
            return {"compiled": False, "reason": "no agency data"}

        lines = [
            f"**統計來源**: official_documents.sender + receiver 累計",
            f"**編譯時間**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "| 排名 | 機關 | 公文累計 |",
            "|------|------|----------|",
        ]
        for i, (name, c) in enumerate(top, 1):
            lines.append(f"| {i} | [[entities/{_slugify(name)}|{name[:40]}]] | {c} |")

        slug = "高頻往來機關 Top 10"
        page_path = self.wiki.root / "topics" / f"{slug}.md"
        content = (
            f"---\ntitle: {slug}\ntype: topic\n"
            f"created: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"sources: [official_documents]\ntags: [統計, 機關, auto-compiled]\n"
            f"confidence: high\n---\n\n# {slug}\n\n" + "\n".join(lines) + "\n"
        )
        page_path.write_text(content, encoding="utf-8")
        self.wiki._append_log("compile", f"topic | {slug} ({len(top)} agencies)")
        return {"compiled": True, "count": len(top)}

    async def _topic_top_vendors(self) -> Dict[str, Any]:
        """I5+ phase 1：高頻廠商 Top 10（依 expense_invoice 累計金額）。

        承接 docs/architecture/WIKI_TOPICS_BACKLOG.md #10。
        """
        from app.extended.models.invoice import ExpenseInvoice
        from sqlalchemy import select as _select, func as _func
        try:
            rows = (await self.db.execute(
                _select(
                    ExpenseInvoice.vendor_id,
                    _func.count().label("invoice_count"),
                    _func.sum(ExpenseInvoice.amount).label("total_amount"),
                )
                .where(ExpenseInvoice.vendor_id.isnot(None))
                .group_by(ExpenseInvoice.vendor_id)
                .order_by(_func.sum(ExpenseInvoice.amount).desc())
                .limit(10)
            )).all()
        except Exception as e:
            return {"compiled": False, "error": f"query failed: {e}"}

        if not rows:
            return {"compiled": False, "reason": "no expense_invoice with vendor_id"}

        # 取 vendor name
        from app.extended.models.core import PartnerVendor
        vendor_ids = [r.vendor_id for r in rows]
        vendor_map: Dict[int, str] = {}
        try:
            v_rows = (await self.db.execute(
                _select(PartnerVendor.id, PartnerVendor.name)
                .where(PartnerVendor.id.in_(vendor_ids))
            )).all()
            vendor_map = {v.id: v.name for v in v_rows}
        except Exception:
            pass

        lines = [
            f"**統計來源**: expense_invoices.amount 累計（含稅）",
            f"**編譯時間**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "| 排名 | 廠商 | 發票筆數 | 累計金額（含稅）|",
            "|------|------|---------:|----------------:|",
        ]
        for i, r in enumerate(rows, 1):
            name = vendor_map.get(r.vendor_id, f"vendor#{r.vendor_id}")
            amount = float(r.total_amount or 0)
            lines.append(
                f"| {i} | [[entities/{_slugify(name)}|{name[:40]}]] "
                f"| {r.invoice_count} | NT$ {amount:,.0f} |"
            )

        slug = "高頻廠商 Top 10"
        page_path = self.wiki.root / "topics" / f"{slug}.md"
        content = (
            f"---\ntitle: {slug}\ntype: topic\n"
            f"created: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"sources: [expense_invoices, partner_vendors]\n"
            f"tags: [統計, 廠商, erp, auto-compiled]\n"
            f"confidence: high\n---\n\n# {slug}\n\n" + "\n".join(lines) + "\n"
        )
        page_path.write_text(content, encoding="utf-8")
        self.wiki._append_log("compile", f"topic | {slug} ({len(rows)} vendors)")
        return {"compiled": True, "count": len(rows)}

    async def _topic_weekly_work_heatmap(self) -> Dict[str, Any]:
        """I5+ phase 2：每週工作流量熱圖（過去 4 週 work_records by week × category）。

        承接 docs/architecture/WIKI_TOPICS_BACKLOG.md #13。
        """
        from app.extended.models.taoyuan import TaoyuanWorkRecord
        from sqlalchemy import select as _select, func as _func
        from datetime import date as _date, timedelta as _td

        cutoff = _date.today() - _td(days=28)
        try:
            rows = (await self.db.execute(
                _select(
                    TaoyuanWorkRecord.work_category,
                    _func.date_trunc("week", TaoyuanWorkRecord.created_at).label("week"),
                    _func.count().label("c"),
                )
                .where(TaoyuanWorkRecord.created_at >= cutoff)
                .where(TaoyuanWorkRecord.work_category.isnot(None))
                .group_by(TaoyuanWorkRecord.work_category, "week")
                .order_by("week")
            )).all()
        except Exception as e:
            return {"compiled": False, "error": f"query failed: {e}"}

        if not rows:
            return {"compiled": False, "reason": "no work_records last 28d"}

        # 重組成 week × category 矩陣
        weeks: Dict[str, Dict[str, int]] = {}
        all_cats: set = set()
        for cat, week, count in rows:
            wk = week.strftime("%m/%d") if week else "?"
            weeks.setdefault(wk, {})[cat] = count
            all_cats.add(cat)

        sorted_weeks = sorted(weeks.keys())
        sorted_cats = sorted(all_cats)

        # markdown table
        header = "| 週起始 | " + " | ".join(sorted_cats) + " | 週合計 |"
        sep = "|" + "---|" * (len(sorted_cats) + 2)
        lines = [
            f"**統計來源**: taoyuan_work_records 過去 28 天 by category",
            f"**編譯時間**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            header,
            sep,
        ]
        for wk in sorted_weeks:
            row_data = weeks[wk]
            counts = [str(row_data.get(c, 0)) for c in sorted_cats]
            total = sum(row_data.values())
            lines.append(f"| {wk} | " + " | ".join(counts) + f" | **{total}** |")

        # category totals
        cat_totals = {c: sum(w.get(c, 0) for w in weeks.values()) for c in sorted_cats}
        totals_row = "| **總計** | " + " | ".join(
            f"**{cat_totals[c]}**" for c in sorted_cats
        ) + f" | **{sum(cat_totals.values())}** |"
        lines.append(totals_row)

        slug = "每週工作流量熱圖"
        page_path = self.wiki.root / "topics" / f"{slug}.md"
        content = (
            f"---\ntitle: {slug}\ntype: topic\n"
            f"created: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"sources: [taoyuan_work_records]\n"
            f"tags: [統計, 派工, 工作流量, auto-compiled]\n"
            f"confidence: high\n---\n\n# {slug}\n\n" + "\n".join(lines) + "\n"
        )
        page_path.write_text(content, encoding="utf-8")
        self.wiki._append_log(
            "compile", f"topic | {slug} ({len(sorted_weeks)}w × {len(sorted_cats)}cat)",
        )
        return {"compiled": True, "weeks": len(sorted_weeks), "categories": len(sorted_cats)}

    async def _topic_adr_active_index(self) -> Dict[str, Any]:
        """I5+ phase 3：ADR active 索引（掃 docs/adr/ 取 status=accepted）。

        承接 docs/architecture/WIKI_TOPICS_BACKLOG.md #15。
        純檔案系統掃描，無需 DB；wiki cron 跑一次即更新。
        """
        import re
        from pathlib import Path
        adr_dir = Path(__file__).resolve().parents[4] / "docs" / "adr"
        if not adr_dir.exists():
            return {"compiled": False, "reason": "docs/adr/ not found"}

        adrs: List[tuple] = []  # (number, title, status)
        for f in sorted(adr_dir.glob("*.md")):
            try:
                text = f.read_text(encoding="utf-8")
            except Exception:
                continue
            # 提 ADR number from filename (e.g., 0028-error-contract-...)
            m_num = re.match(r"^(\d{4})-(.+)\.md$", f.name)
            if not m_num:
                continue
            num = m_num.group(1)
            slug_from_name = m_num.group(2)
            # 從 frontmatter 或 H1 取 title
            m_title = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
            title = m_title.group(1).strip() if m_title else slug_from_name
            # 從 status 區塊取狀態
            m_status = re.search(
                r"(?:Status|狀態)[:：]\s*([A-Za-z一-鿿]+)",
                text, re.IGNORECASE,
            )
            status = m_status.group(1).strip() if m_status else "?"
            adrs.append((num, title[:60], status))

        if not adrs:
            return {"compiled": False, "reason": "no ADR files"}

        # 分類 active / archived / proposal
        active = [a for a in adrs if a[2].lower() in ("accepted", "active")]
        proposed = [a for a in adrs if a[2].lower() in ("proposed", "proposal")]
        other = [a for a in adrs if a not in active and a not in proposed]

        lines = [
            f"**統計來源**: docs/adr/ 全 {len(adrs)} 篇 frontmatter 解析",
            f"**編譯時間**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            f"## Active ({len(active)})",
            "",
            "| # | Title | Status |",
            "|---|---|---|",
        ]
        for num, title, status in active:
            lines.append(f"| {num} | {title} | {status} |")

        if proposed:
            lines.extend([
                "",
                f"## Proposed ({len(proposed)})",
                "",
                "| # | Title | Status |",
                "|---|---|---|",
            ])
            for num, title, status in proposed:
                lines.append(f"| {num} | {title} | {status} |")

        if other:
            lines.extend([
                "",
                f"## Other ({len(other)})",
                "",
                "| # | Title | Status |",
                "|---|---|---|",
            ])
            for num, title, status in other:
                lines.append(f"| {num} | {title} | {status} |")

        slug = "ADR 索引"
        page_path = self.wiki.root / "topics" / f"{slug}.md"
        content = (
            f"---\ntitle: {slug}\ntype: topic\n"
            f"created: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"sources: [docs/adr]\n"
            f"tags: [架構, ADR, 治理, auto-compiled]\n"
            f"confidence: high\n---\n\n# {slug}\n\n" + "\n".join(lines) + "\n"
        )
        page_path.write_text(content, encoding="utf-8")
        self.wiki._append_log(
            "compile", f"topic | {slug} ({len(active)} active / {len(adrs)} total)",
        )
        return {
            "compiled": True,
            "active": len(active),
            "proposed": len(proposed),
            "total": len(adrs),
        }

    async def _topic_erp_monthly_trend(self) -> Dict[str, Any]:
        """I5+ phase 4：ERP 月度趨勢（報價+開票+請款 過去 6 個月）。

        承接 docs/architecture/WIKI_TOPICS_BACKLOG.md #11。
        """
        from app.extended.models.invoice import ExpenseInvoice
        from sqlalchemy import select as _select, func as _func
        from datetime import date as _date, timedelta as _td

        cutoff = _date.today() - _td(days=180)
        # 簡化：以 expense_invoice.created_at 月份分組（後續可加 quotation/billing
        # 等其他 ERP 表，本 lite 版只覆蓋 invoice）
        try:
            rows = (await self.db.execute(
                _select(
                    _func.date_trunc("month", ExpenseInvoice.created_at).label("month"),
                    _func.count().label("invoice_count"),
                    _func.sum(ExpenseInvoice.amount).label("total_amount"),
                )
                .where(ExpenseInvoice.created_at >= cutoff)
                .group_by("month")
                .order_by("month")
            )).all()
        except Exception as e:
            return {"compiled": False, "error": f"query failed: {e}"}

        if not rows:
            return {"compiled": False, "reason": "no expense_invoice last 6 months"}

        lines = [
            f"**統計來源**: expense_invoices 過去 6 個月 by month",
            f"**編譯時間**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "| 月份 | 發票筆數 | 累計金額（含稅）|",
            "|------|---------:|----------------:|",
        ]
        total_count = 0
        total_amount = 0.0
        for r in rows:
            month_str = r.month.strftime("%Y-%m") if r.month else "?"
            cnt = int(r.invoice_count or 0)
            amt = float(r.total_amount or 0)
            total_count += cnt
            total_amount += amt
            lines.append(f"| {month_str} | {cnt} | NT$ {amt:,.0f} |")
        lines.append(f"| **6個月總計** | **{total_count}** | **NT$ {total_amount:,.0f}** |")

        slug = "ERP 月度趨勢"
        page_path = self.wiki.root / "topics" / f"{slug}.md"
        content = (
            f"---\ntitle: {slug}\ntype: topic\n"
            f"created: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"sources: [expense_invoices]\n"
            f"tags: [統計, ERP, 財務, 趨勢, auto-compiled]\n"
            f"confidence: high\n---\n\n# {slug}\n\n" + "\n".join(lines) + "\n"
        )
        page_path.write_text(content, encoding="utf-8")
        self.wiki._append_log(
            "compile", f"topic | {slug} ({len(rows)} months / NT$ {total_amount:,.0f})",
        )
        return {"compiled": True, "months": len(rows), "total_amount": total_amount}

    async def _topic_lessons_registry(self) -> Dict[str, Any]:
        """I5+ phase 5：LESSONS_REGISTRY 索引（22+ lessons L01~ 速查）。

        承接 docs/architecture/WIKI_TOPICS_BACKLOG.md #14。
        """
        import re
        from pathlib import Path
        registry_path = (
            Path(__file__).resolve().parents[4]
            / "docs" / "architecture" / "LESSONS_REGISTRY.md"
        )
        if not registry_path.exists():
            return {"compiled": False, "reason": "LESSONS_REGISTRY.md not found"}

        try:
            text = registry_path.read_text(encoding="utf-8")
        except Exception as e:
            return {"compiled": False, "error": f"read failed: {e}"}

        # 抓 ## L## — title 行
        lessons: List[tuple] = []
        for m in re.finditer(r"^##\s+(L\d+)\s+[—-]\s+(.+)$", text, re.MULTILINE):
            lid = m.group(1)
            title = m.group(2).strip()
            lessons.append((lid, title))

        if not lessons:
            return {"compiled": False, "reason": "no L## headers found"}

        lines = [
            f"**統計來源**: docs/architecture/LESSONS_REGISTRY.md",
            f"**編譯時間**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Lessons 總數**: {len(lessons)}",
            "",
            "| ID | Lesson Title |",
            "|----|--------------|",
        ]
        for lid, title in lessons:
            # 標題長度限制 + 移除 markdown 強調
            clean_title = re.sub(r"[*`]", "", title)[:80]
            lines.append(f"| {lid} | {clean_title} |")

        slug = "Lessons Registry 索引"
        page_path = self.wiki.root / "topics" / f"{slug}.md"
        content = (
            f"---\ntitle: {slug}\ntype: topic\n"
            f"created: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"sources: [docs/architecture/LESSONS_REGISTRY.md]\n"
            f"tags: [架構, lessons, 治理, auto-compiled]\n"
            f"confidence: high\n---\n\n# {slug}\n\n" + "\n".join(lines) + "\n"
            f"\n\n## 完整內容\n\n見 [LESSONS_REGISTRY.md](../../docs/architecture/LESSONS_REGISTRY.md)\n"
        )
        page_path.write_text(content, encoding="utf-8")
        self.wiki._append_log("compile", f"topic | {slug} ({len(lessons)} lessons)")
        return {"compiled": True, "count": len(lessons)}

    async def _topic_overdue_docs(self) -> Dict[str, Any]:
        """逾期公文 Top 20（依 calendar_event.end_date < today 且 status != completed）。"""
        from app.extended.models import OfficialDocument
        from app.extended.models.calendar import DocumentCalendarEvent
        from datetime import date as _date
        today = _date.today()

        rows = (await self.db.execute(
            select(
                OfficialDocument.doc_number,
                OfficialDocument.subject,
                OfficialDocument.sender,
                DocumentCalendarEvent.end_date,
            )
            .join(DocumentCalendarEvent,
                  OfficialDocument.id == DocumentCalendarEvent.document_id)
            .where(DocumentCalendarEvent.end_date < today)
            .where(DocumentCalendarEvent.status != 'completed')
            .order_by(DocumentCalendarEvent.end_date)
            .limit(20)
        )).all()

        if not rows:
            return {"compiled": False, "reason": "no overdue docs"}

        lines = [
            f"**統計時間**: {today.isoformat()}",
            f"**編譯時間**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "| 文號 | 主旨 | 發文者 | 截止日 | 逾期天數 |",
            "|------|------|--------|--------|----------|",
        ]
        for doc_no, subj, sender, end_date in rows:
            overdue = (today - end_date).days if end_date else 0
            subj_short = (subj or "")[:40]
            lines.append(
                f"| {doc_no or '-'} | {subj_short} | {(sender or '-')[:20]} | "
                f"{end_date} | {overdue} |"
            )

        slug = "逾期公文 Top 20"
        page_path = self.wiki.root / "topics" / f"{slug}.md"
        content = (
            f"---\ntitle: {slug}\ntype: topic\n"
            f"created: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"sources: [official_documents, document_calendar_events]\n"
            f"tags: [統計, 逾期, auto-compiled]\nconfidence: high\n---\n\n"
            f"# {slug}\n\n" + "\n".join(lines) + "\n"
        )
        page_path.write_text(content, encoding="utf-8")
        self.wiki._append_log("compile", f"topic | {slug} ({len(rows)} overdue)")
        return {"compiled": True, "count": len(rows)}

    async def _topic_monthly_dispatch_volume(self) -> Dict[str, Any]:
        """月派工量趨勢（過去 12 月，依 created_at 統計）。"""
        from app.extended.models.taoyuan import TaoyuanDispatchOrder
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=400)

        rows = (await self.db.execute(
            select(
                func.to_char(TaoyuanDispatchOrder.created_at, 'YYYY-MM').label("month"),
                func.count().label("c"),
            )
            .where(TaoyuanDispatchOrder.created_at >= cutoff)
            .group_by("month")
            .order_by("month")
        )).all()

        if not rows:
            return {"compiled": False, "reason": "no dispatch data"}

        lines = [
            f"**統計範圍**: 過去 12 個月（≥ {cutoff.strftime('%Y-%m-%d')}）",
            f"**編譯時間**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "| 月份 | 派工量 |",
            "|------|--------|",
        ]
        for month, c in rows:
            lines.append(f"| {month} | {c} |")

        slug = "月派工量趨勢"
        page_path = self.wiki.root / "topics" / f"{slug}.md"
        content = (
            f"---\ntitle: {slug}\ntype: topic\n"
            f"created: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"sources: [dispatch_orders]\ntags: [統計, 派工, auto-compiled]\n"
            f"confidence: high\n---\n\n# {slug}\n\n" + "\n".join(lines) + "\n"
        )
        page_path.write_text(content, encoding="utf-8")
        self.wiki._append_log("compile", f"topic | {slug} ({len(rows)} months)")
        return {"compiled": True, "count": len(rows)}

    async def _topic_kg_top_degree(self) -> Dict[str, Any]:
        """KG 高 degree entities Top 10（連線最多的 entity）。"""
        rows = (await self.db.execute(
            text(
                """
                SELECT ce.canonical_name, ce.entity_type, COUNT(ee.id) AS deg
                FROM canonical_entities ce
                LEFT JOIN entity_edges ee
                  ON ce.id = ee.source_id OR ce.id = ee.target_id
                GROUP BY ce.id, ce.canonical_name, ce.entity_type
                HAVING COUNT(ee.id) > 0
                ORDER BY deg DESC
                LIMIT 10
                """
            )
        )).all()

        if not rows:
            return {"compiled": False, "reason": "no KG edges"}

        lines = [
            f"**編譯時間**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**KG 來源**: canonical_entities + entity_edges",
            "",
            "| 排名 | 實體 | 類型 | 連線數 |",
            "|------|------|------|--------|",
        ]
        for i, (name, etype, deg) in enumerate(rows, 1):
            lines.append(f"| {i} | {(name or '-')[:40]} | {etype or '-'} | {deg} |")

        slug = "KG 高連線 Top 10"
        page_path = self.wiki.root / "topics" / f"{slug}.md"
        content = (
            f"---\ntitle: {slug}\ntype: topic\n"
            f"created: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"sources: [canonical_entities, entity_edges]\n"
            f"tags: [統計, 圖譜, auto-compiled]\nconfidence: high\n---\n\n"
            f"# {slug}\n\n" + "\n".join(lines) + "\n"
        )
        page_path.write_text(content, encoding="utf-8")
        self.wiki._append_log("compile", f"topic | {slug} ({len(rows)} entities)")
        return {"compiled": True, "count": len(rows)}

    async def _topic_data_quality_snapshot(self) -> Dict[str, Any]:
        """資料品質快照（無 KG 連結的 wiki entity / 缺 agency_code 的機關等）。"""
        # Wiki entities 未連 KG
        import re
        no_kg = 0
        with_kg = 0
        wiki_entities_dir = self.wiki.root / "entities"
        if wiki_entities_dir.exists():
            for f in wiki_entities_dir.glob("*.md"):
                try:
                    head = f.read_text(encoding="utf-8")[:400]
                    if re.search(r"^kg_entity_id:\s*\d+", head, re.MULTILINE):
                        with_kg += 1
                    else:
                        no_kg += 1
                except Exception:
                    pass
        total_wiki = with_kg + no_kg
        link_rate = with_kg / total_wiki if total_wiki else 0

        # 缺 agency_code 的機關
        from app.extended.models import GovernmentAgency
        no_code_count = await self.db.scalar(
            select(func.count()).where(
                GovernmentAgency.agency_code.is_(None)
            )
        ) or 0
        total_agency = await self.db.scalar(
            select(func.count(GovernmentAgency.id))
        ) or 0

        # 派工 KG canonical_entity 覆蓋（dispatch type 的 entity 數）
        dispatch_kg_count = (await self.db.execute(
            text(
                "SELECT COUNT(*) FROM canonical_entities "
                "WHERE entity_type = 'dispatch'"
            )
        )).scalar() or 0

        lines = [
            f"**編譯時間**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Wiki ↔ KG 連結率",
            "",
            f"- 總 wiki entities：**{total_wiki}**",
            f"- 已連 KG：**{with_kg}**（{link_rate:.1%}）",
            f"- 未連 KG：**{no_kg}**",
            "",
            "## 機關資料完整度",
            "",
            f"- 總機關數：**{total_agency}**",
            f"- 缺 agency_code：**{no_code_count}**",
            "",
            "## KG 派工 entity 覆蓋",
            "",
            f"- canonical_entities 中 type=dispatch：**{dispatch_kg_count}**",
        ]

        slug = "資料品質快照"
        page_path = self.wiki.root / "topics" / f"{slug}.md"
        content = (
            f"---\ntitle: {slug}\ntype: topic\n"
            f"created: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"sources: [wiki/entities, government_agencies, canonical_entities]\n"
            f"tags: [統計, 品質, auto-compiled]\nconfidence: high\n---\n\n"
            f"# {slug}\n\n" + "\n".join(lines) + "\n"
        )
        page_path.write_text(content, encoding="utf-8")
        self.wiki._append_log(
            "compile", f"topic | {slug} (link={link_rate:.1%})"
        )
        return {
            "compiled": True,
            "wiki_total": total_wiki,
            "kg_link_rate": round(link_rate, 4),
        }

    # =========================================================================
    # Interest Signal — 從 Agent 查詢提取近期關注焦點
    # =========================================================================

    async def compile_interest_signals(self, days: int = 7) -> Dict[str, Any]:
        """從 AgentTrace 提取近期高頻查詢主題，寫入 wiki topics 頁面。

        Karpathy insight: 「每次提問都成為知識的一部分」。
        將使用者關注焦點寫回 wiki，Agent 下次能優先命中。
        """
        from app.extended.models.agent_trace import AgentTrace as AgentTraceModel
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)

        stmt = (
            select(AgentTraceModel.question)
            .where(AgentTraceModel.created_at > cutoff)
            .order_by(desc(AgentTraceModel.created_at))
            .limit(100)
        )
        result = await self.db.execute(stmt)
        questions = [r.question for r in result.all() if r.question]

        if not questions:
            return {"compiled": False, "reason": "no recent queries"}

        # 簡易詞頻 (中文 bigram + 英文 word)
        import re as _re
        word_freq: Dict[str, int] = {}
        stop_words = {"的", "是", "在", "有", "和", "了", "我", "你", "他", "她",
                      "請", "嗎", "吧", "呢", "啊", "幫", "什麼", "怎麼", "哪些",
                      "幫我", "查詢", "搜尋", "列出", "整理"}
        for q in questions:
            clean = _re.sub(r'[^\u4e00-\u9fff\w]', ' ', q)
            chars = [c for c in clean if '\u4e00' <= c <= '\u9fff']
            for i in range(len(chars) - 1):
                bigram = chars[i] + chars[i + 1]
                if bigram not in stop_words:
                    word_freq[bigram] = word_freq.get(bigram, 0) + 1
            for word in _re.findall(r'[a-zA-Z]{3,}', q):
                word_freq[word.lower()] = word_freq.get(word.lower(), 0) + 1

        top_terms = sorted(word_freq.items(), key=lambda x: -x[1])[:20]
        if not top_terms:
            return {"compiled": False, "reason": "no meaningful terms"}

        lines = [
            f"**統計期間**: 最近 {days} 天",
            f"**查詢總數**: {len(questions)} 筆",
            f"**提取時間**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 高頻關注詞",
            "",
            "| 關鍵詞 | 出現次數 |",
            "|--------|---------|",
        ]
        for term, count in top_terms:
            lines.append(f"| {term} | {count} |")
        lines.extend(["", "## 最近 10 筆查詢", ""])
        for q in questions[:10]:
            lines.append(f"- {q[:80]}")

        slug = "近期關注焦點"
        page_path = self.wiki.root / "topics" / f"{slug}.md"
        content = f"""---
title: {slug}
type: topic
created: {datetime.now().strftime('%Y-%m-%d')}
sources: [agent_traces, last {days} days]
tags: [interest, auto-compiled]
confidence: medium
---

# {slug}

{chr(10).join(lines)}
"""
        page_path.write_text(content, encoding="utf-8")
        self.wiki._append_log("compile", f"topic | {slug} ({len(questions)} queries)")

        return {
            "compiled": True,
            "queries_analyzed": len(questions),
            "top_terms": top_terms[:10],
        }
