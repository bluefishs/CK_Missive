"""
DispatchLinkService - 派工單關聯同步與自動匹配邏輯

從 dispatch_order_service.py 拆分：
- 公文關聯同步 (_sync_document_links, _sync_document_project_links)
- 自動匹配公文 (_auto_match_documents, _score_document_relevance)
- 實體連結同步 (_sync_dispatch_entity_links)
- 作業類別同步 (_sync_work_type_links)
- 欄位同步到工程 (_sync_fields_to_linked_projects)

@version 2.0.0
@date 2026-03-18
@update 移除直接 DB 查詢，改用 Repository 層
"""

import logging
import re
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.taoyuan import (
    DispatchOrderRepository,
    DispatchLinkRepository,
    TaoyuanProjectRepository,
)
from app.utils.doc_helpers import is_outgoing_doc_number

logger = logging.getLogger(__name__)

# 通用合約級公文關鍵字（不屬於特定子工程，所有派工單都應關聯）
GENERIC_DOC_PATTERNS = [
    r'契約書', r'教育訓練', r'系統建置', r'開口契約',
    r'履約保證', r'保險', r'印鑑', r'投標', r'決標',
    r'簽約', r'工作計畫書', r'採購案',
]

# 剝離通用合約名稱前綴的正則（移除後剩餘的文字用來判斷地名歸屬）
_CONTRACT_PREFIX_RE = re.compile(
    r'(?:檢送|請領|有關|為)?(?:本公司|貴公司|本局)?'
    r'(?:辦理|承攬|所提|提送|檢送)?'
    r'[「『]?'
    r'115年度桃園市[^\u3000-\u303F」』）)]*?(?:開口契約)[」』）)]*'
    r'[」』）)]*'
    r'[案之的一]*[，,\-\s]*'
)


class DispatchLinkService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DispatchOrderRepository(db)
        self.link_repo = DispatchLinkRepository(db)
        self.project_repo = TaoyuanProjectRepository(db)

    async def sync_fields_to_linked_projects(
        self,
        dispatch_id: int,
        fields: Dict[str, Any]
    ) -> None:
        project_ids = await self.link_repo.get_project_ids_for_dispatch(
            dispatch_id
        )
        if not project_ids:
            return

        projects = await self.project_repo.get_by_ids(project_ids)

        updated_count = 0
        for project in projects:
            changed = False
            for field, value in fields.items():
                current = getattr(project, field, None)
                if current != value:
                    setattr(project, field, value)
                    changed = True
            if changed:
                updated_count += 1

        if updated_count > 0:
            logger.info(
                "[sync_fields] 派工單 %d 同步 %s 到 %d 個工程",
                dispatch_id, list(fields.keys()), updated_count
            )

    async def sync_work_type_links(
        self,
        dispatch_id: int,
        work_type_str: Optional[str],
    ) -> None:
        types = (
            [t.strip() for t in work_type_str.split(',') if t.strip()]
            if work_type_str
            else []
        )
        count = await self.repository.replace_work_types(dispatch_id, types)

        if count:
            logger.info(
                "[sync_work_type_links] 派工單 %d 同步 %d 個作業類別",
                dispatch_id, count
            )

    async def sync_document_links(
        self,
        dispatch_id: int,
        agency_doc_id: Optional[int],
        company_doc_id: Optional[int]
    ) -> None:
        if agency_doc_id:
            await self.link_repo.link_dispatch_to_document(
                dispatch_id, agency_doc_id,
                link_type='agency_incoming',
                auto_commit=False,
            )

        if company_doc_id:
            await self.link_repo.link_dispatch_to_document(
                dispatch_id, company_doc_id,
                link_type='company_outgoing',
                auto_commit=False,
            )

        await self.sync_document_project_links(dispatch_id)

    async def auto_match_documents(
        self,
        dispatch_id: int,
        project_name: str,
        contract_project_id: Optional[int] = None,
        work_type: Optional[str] = None,
    ) -> int:
        matched_docs = await self.repository.get_document_history(
            project_name=project_name,
            contract_project_id=contract_project_id,
            work_type=work_type,
            allow_fallback=False,
        )

        if not matched_docs:
            return 0

        core_ids = extract_core_identifiers(project_name, work_type)

        other_ids: List[str] = []
        if contract_project_id and core_ids:
            other_ids = await self._collect_sibling_identifiers(
                contract_project_id, exclude_dispatch_id=dispatch_id
            )

        if core_ids:
            before = len(matched_docs)
            matched_docs = [
                doc for doc in matched_docs
                if score_document_relevance(
                    doc, core_ids, other_ids=other_ids
                ) >= 0.15
            ]
            after = len(matched_docs)
            if before != after:
                logger.info(
                    "[auto_match] 派工單 %s 相關性過濾: %d -> %d 筆",
                    dispatch_id, before, after,
                )

        linked_count = 0
        for doc in matched_docs:
            doc_id = doc.get('id')
            doc_number = doc.get('doc_number', '')
            if not doc_id:
                continue

            link_type = (
                'company_outgoing'
                if is_outgoing_doc_number(doc_number)
                else 'agency_incoming'
            )

            link = await self.link_repo.link_dispatch_to_document(
                dispatch_id, doc_id,
                link_type=link_type,
                auto_commit=False,
            )
            if link is not None:
                linked_count += 1

        if linked_count > 0:
            logger.info(
                "[auto_match] 派工單 %d 自動匹配 %d 筆公文",
                dispatch_id, linked_count,
            )

        return linked_count

    async def _collect_sibling_identifiers(
        self,
        contract_project_id: int,
        exclude_dispatch_id: int,
    ) -> List[str]:
        siblings = await self.repository.get_siblings_by_contract(
            contract_project_id, exclude_dispatch_id
        )
        ids: List[str] = []
        for _dispatch_id, project_name in siblings:
            for ident in extract_core_identifiers(project_name):
                if any(ident.endswith(s) for s in ('路', '街', '公園', '廣場', '用地')):
                    if ident not in ids:
                        ids.append(ident)
                elif ident.startswith('派工單'):
                    if ident not in ids:
                        ids.append(ident)
        return ids

    async def sync_dispatch_entity_links(
        self, dispatch_id: int, project_name: str
    ) -> int:
        if not project_name:
            return 0

        core_ids = extract_core_identifiers(project_name)
        if not core_ids:
            return 0

        matched_entity_ids = await self.link_repo.find_matching_entity_ids(
            core_ids
        )

        if not matched_entity_ids:
            return 0

        linked = await self.link_repo.replace_auto_entity_links(
            dispatch_id, matched_entity_ids
        )

        if linked:
            logger.info(
                "[entity_link] 派工單 %d 自動關聯 %d 個正規化實體 (關鍵詞: %s)",
                dispatch_id, linked, core_ids,
            )
        return linked

    async def sync_document_project_links(self, dispatch_id: int) -> int:
        dispatch = await self.repository.get_by_id(dispatch_id)
        if not dispatch or not dispatch.dispatch_no:
            return 0

        project_ids = await self.link_repo.get_project_ids_for_dispatch(
            dispatch_id
        )
        if not project_ids:
            return 0

        doc_links = await self.link_repo.get_doc_id_and_types_for_dispatch(
            dispatch_id
        )
        if not doc_links:
            return 0

        linked_count = 0
        notes_tag = f"自動同步自派工單 {dispatch.dispatch_no}"
        for doc_id, link_type in doc_links:
            for project_id in project_ids:
                result = await self.link_repo.link_document_to_project(
                    document_id=doc_id,
                    project_id=project_id,
                    link_type=link_type,
                    notes=notes_tag,
                    auto_commit=False,
                )
                if result is not None:
                    linked_count += 1

        if linked_count > 0:
            logger.info(
                "[sync_doc_project] 派工單 %s "
                "自動傳遞 %d 筆公文-工程關聯",
                dispatch.dispatch_no, linked_count,
            )

        return linked_count


def extract_core_identifiers(
    project_name: str, work_type: Optional[str] = None
) -> List[str]:
    ids: List[str] = []

    if not project_name:
        return ids

    m = re.search(r'派工單[號]?\s*(\d{2,4})', project_name)
    if m:
        ids.append(f"派工單{m.group(1)}")

    for m in re.finditer(r'([\u4e00-\u9fff]{2,6}(?:路|街))', project_name):
        name = m.group(1)
        if name not in ids and len(name) >= 3:
            ids.append(name)

    for m in re.finditer(r'([\u4e00-\u9fff]{2,6}(?:公園|廣場|用地))', project_name):
        if m.group(1) not in ids:
            ids.append(m.group(1))

    m = re.search(r'([\u4e00-\u9fff]{1,3}[區鄉鎮市])', project_name)
    if m and m.group(1) not in ids:
        ids.append(m.group(1))

    return ids


def score_document_relevance(
    doc: Dict[str, Any],
    core_ids: List[str],
    other_ids: Optional[List[str]] = None,
) -> float:
    subject = doc.get('subject', '') or ''

    for cid in core_ids:
        if cid.startswith('派工單') and cid in subject:
            return 1.0

    stripped = _CONTRACT_PREFIX_RE.sub('', subject).strip()

    if other_ids:
        for oid in other_ids:
            if oid in subject:
                if any(cid in subject for cid in core_ids
                       if not cid.endswith('區')):
                    break
                return 0.0

    is_generic = any(re.search(p, subject) for p in GENERIC_DOC_PATTERNS)
    if is_generic:
        remaining_locations = re.findall(
            r'[\u4e00-\u9fff]{2,6}(?:路|街|公園|廣場)', stripped
        )
        if not remaining_locations:
            return 0.5
        if not any(cid in subject for cid in core_ids if not cid.endswith('區')):
            return 0.0
        return 0.5

    if not core_ids:
        return 0.0

    matched = sum(1 for cid in core_ids if cid in subject)
    return matched / len(core_ids)
