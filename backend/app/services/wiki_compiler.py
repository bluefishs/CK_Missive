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

from app.services.wiki_service import get_wiki_service, WikiService, WIKI_ROOT, _slugify

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
        """建構案件 wiki 描述 (v2 完整版 — 工程 + 公文 + 派工 + 機關 + 財務)"""
        amount_str = (
            f"${row.contract_amount:,.0f}" if row.contract_amount else "(未登錄)"
        )
        lines = [
            f"**案號**: {row.project_code or '(未指派)'}",
            f"**狀態**: {row.status or '(未設定)'}",
            f"**年度**: {row.year or '(未設定)'}",
            f"**合約金額**: {amount_str}",
            f"**地點**: {row.location or '(未登錄)'}",
            f"**關聯公文**: {len(all_docs)} 件",
            f"**派工單**: {len(dispatches)} 筆" if dispatches else "",
            "",
        ]

        # 工程名稱
        if engineering:
            lines.append(f"## 工程名稱 ({len(engineering)} 筆)")
            lines.append("")
            lines.append("| 工程 | 區域 | 起點 | 終點 |")
            lines.append("|------|------|------|------|")
            for eng in engineering:
                lines.append(
                    f"| {eng['name'][:40]} | {eng['district']} | {eng['start_point']} | {eng['end_point']} |"
                )
            lines.append("")

        # 往來機關
        if agencies:
            lines.append("## 往來機關")
            lines.append("")
            lines.append("| 機關 | 公文數 |")
            lines.append("|------|--------|")
            for a in agencies:
                lines.append(f"| [[entities/{a['name']}|{a['name']}]] | {a['doc_count']} |")
            lines.append("")

        # 財務
        if financial:
            lines.append("## 財務摘要")
            lines.append(
                f"- 報價紀錄 {financial['quote_count']} 筆, "
                f"合計 ${financial['total_quoted']:,.0f}"
            )
            lines.append("")

        # 派工單
        if dispatches:
            lines.append(f"## 派工單 ({len(dispatches)} 筆)")
            lines.append("")
            lines.append("| 派工單號 | 工程名稱 | 作業類別 | 承辦 | 履約期限 |")
            lines.append("|----------|----------|----------|------|----------|")
            for d in dispatches:
                dno = d['dispatch_no']
                lines.append(
                    f"| [[entities/{dno}|{dno}]] | {d.get('project_name','')[:25]} | {d['work_type'][:15]} | {d.get('handler','')} | {d.get('deadline','')[:15]} |"
                )
            lines.append("")

        # 公文 — 按月份分組 (完整列表)
        if all_docs:
            lines.append(f"## 公文清單 ({len(all_docs)} 件)")
            lines.append("")

            # 按月份分組
            by_month: Dict[str, List] = {}
            for d in all_docs:
                month = d['date'][:7] if d['date'] else 'unknown'
                by_month.setdefault(month, []).append(d)

            for month in sorted(by_month.keys(), reverse=True):
                docs = by_month[month]
                lines.append(f"### {month} ({len(docs)} 件)")
                lines.append("")
                for d in docs:
                    lines.append(
                        f"- [{d['category']}] {d['date']} `{d['doc_number'][:20]}` {d['subject'][:50]}"
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

        # 自動建立索引頁 — 所有 entity 頁面至少有一個入站連結 (解決 orphan)
        await self._build_index_pages()

        return {
            "documents": doc_count,
            "projects": project_count,
            "agencies": agency_count,
        }

    async def _build_index_pages(self):
        """建立機關/案件/派工索引 topic 頁，為所有 entity 建立入站連結 (消除 orphan)"""
        from app.services.wiki_service import _slugify as _slug

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
