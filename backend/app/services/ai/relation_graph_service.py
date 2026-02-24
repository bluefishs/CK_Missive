"""
關聯圖譜 & 語意相似推薦 Service

將 relation_graph.py 端點的業務邏輯與 DB 操作集中到 Service 層。

Version: 1.0.0
Created: 2026-02-24
"""

import hashlib
import logging
import os
from collections import Counter
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    OfficialDocument,
    ContractProject,
    DocumentEntity,
    EntityRelation,
    TaoyuanDispatchOrder,
    TaoyuanDispatchDocumentLink,
    TaoyuanDispatchProjectLink,
    TaoyuanProject,
)
from app.schemas.ai import (
    GraphNode,
    GraphEdge,
    SemanticSimilarItem,
)

logger = logging.getLogger(__name__)


class RelationGraphService:
    """關聯圖譜 & 語意相似推薦 Service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 關聯圖譜
    # ------------------------------------------------------------------

    async def build_relation_graph(
        self, doc_ids: List[int]
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """
        建構完整關聯圖譜。

        回傳 (nodes, edges)。如果 doc_ids 為空，自動載入最近公文。
        """
        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []
        seen_nodes: Set[str] = set()
        seen_edges: Set[str] = set()

        def add_node(node: GraphNode):
            if node.id not in seen_nodes:
                seen_nodes.add(node.id)
                nodes.append(node)

        def add_edge(edge: GraphEdge):
            key = f"{edge.source}->{edge.target}:{edge.type}"
            if key not in seen_edges:
                seen_edges.add(key)
                edges.append(edge)

        # Phase 0: 自動載入
        if not doc_ids:
            doc_ids = await self._load_default_doc_ids()
            if not doc_ids:
                return [], []

        # Phase 1: 公文節點 + 機關節點
        documents = await self._fetch_documents(doc_ids)
        if not documents:
            return [], []

        project_ids: Set[int] = set()
        for doc in documents:
            node_id = f"doc_{doc.id}"
            add_node(GraphNode(
                id=node_id,
                type="document",
                label=doc.subject[:30] if doc.subject else doc.doc_number or f"公文#{doc.id}",
                category=doc.doc_type or doc.category,
                doc_number=doc.doc_number,
                status=doc.status,
            ))
            if doc.contract_project_id:
                project_ids.add(doc.contract_project_id)

            self._add_agency_nodes(doc, node_id, add_node, add_edge)

        # Phase 2: 承攬案件
        if project_ids:
            await self._add_project_nodes(
                project_ids, documents, add_node, add_edge
            )

        # Phase 3: 同專案其他公文
        if project_ids:
            await self._add_related_docs(
                project_ids, doc_ids, add_node, add_edge
            )

        # Phase 4: 收發配對
        self._add_reply_edges(documents, add_edge)

        # Phase 5: NER 實體 & 關係
        entity_count, relation_count = await self._add_ner_entities(
            doc_ids, add_node, add_edge
        )

        # Phase 6 & 7: 派工單 & 桃園工程
        dispatch_link_count = await self._add_dispatch_nodes(
            doc_ids, seen_nodes, add_node, add_edge
        )

        logger.info(
            f"關聯圖譜: {len(doc_ids)} 筆公文 → {len(nodes)} 節點, {len(edges)} 邊"
            f" (含 {entity_count} 提取實體, {relation_count} 提取關係,"
            f" {dispatch_link_count} 派工關聯)"
        )

        return nodes, edges

    # ------------------------------------------------------------------
    # 語意相似推薦
    # ------------------------------------------------------------------

    async def get_semantic_similar(
        self, doc_id: int, limit: int = 10
    ) -> Optional[List[SemanticSimilarItem]]:
        """
        取得語意相似公文推薦。

        回傳 None 表示 pgvector 未啟用；回傳空列表表示無 embedding。
        HTTPException (404) 由呼叫方處理。
        """
        pgvector_enabled = os.environ.get("PGVECTOR_ENABLED", "false").lower() == "true"
        if not pgvector_enabled:
            return None

        # 取得來源 embedding
        source_result = await self.db.execute(
            select(
                OfficialDocument.id,
                OfficialDocument.embedding,
            ).where(OfficialDocument.id == doc_id)
        )
        source_row = source_result.first()
        if not source_row:
            return None  # 呼叫方判斷 404

        source_embedding = source_row.embedding
        if source_embedding is None:
            return []

        if not isinstance(source_embedding, list):
            source_embedding = list(source_embedding)

        # cosine_distance 查詢
        distance_expr = OfficialDocument.embedding.cosine_distance(source_embedding)
        similarity_expr = (1 - distance_expr).label("similarity")

        similar_result = await self.db.execute(
            select(
                OfficialDocument.id,
                OfficialDocument.doc_number,
                OfficialDocument.subject,
                OfficialDocument.category,
                OfficialDocument.sender,
                OfficialDocument.doc_date,
                similarity_expr,
            )
            .where(OfficialDocument.id != doc_id)
            .where(OfficialDocument.embedding.isnot(None))
            .order_by(distance_expr)
            .limit(limit)
        )

        return [
            SemanticSimilarItem(
                id=row.id,
                doc_number=row.doc_number,
                subject=row.subject,
                category=row.category,
                sender=row.sender,
                doc_date=str(row.doc_date) if row.doc_date else None,
                similarity=round(float(row.similarity), 4),
            )
            for row in similar_result.all()
            if row.similarity >= 0.3
        ]

    # ==================================================================
    # Private helpers
    # ==================================================================

    async def _load_default_doc_ids(self) -> List[int]:
        """載入預設公文 ID（最近公文 + 有派工關聯的公文）"""
        recent_result = await self.db.execute(
            select(OfficialDocument.id)
            .order_by(OfficialDocument.created_at.desc().nullslast())
            .limit(10)
        )
        recent_ids = [row[0] for row in recent_result.all()]

        dispatch_doc_result = await self.db.execute(
            select(TaoyuanDispatchDocumentLink.document_id)
            .distinct()
            .order_by(TaoyuanDispatchDocumentLink.document_id.desc())
            .limit(5)
        )
        dispatch_doc_ids = [row[0] for row in dispatch_doc_result.all()]

        fk_agency_result = await self.db.execute(
            select(TaoyuanDispatchOrder.agency_doc_id)
            .where(TaoyuanDispatchOrder.agency_doc_id.isnot(None))
            .order_by(TaoyuanDispatchOrder.id.desc())
            .limit(5)
        )
        fk_company_result = await self.db.execute(
            select(TaoyuanDispatchOrder.company_doc_id)
            .where(TaoyuanDispatchOrder.company_doc_id.isnot(None))
            .order_by(TaoyuanDispatchOrder.id.desc())
            .limit(5)
        )
        fk_doc_ids = (
            [row[0] for row in fk_agency_result.all()]
            + [row[0] for row in fk_company_result.all()]
        )
        dispatch_doc_ids = list(dict.fromkeys(dispatch_doc_ids + fk_doc_ids))
        return list(dict.fromkeys(recent_ids + dispatch_doc_ids))

    async def _fetch_documents(self, doc_ids: List[int]) -> list:
        result = await self.db.execute(
            select(OfficialDocument).where(OfficialDocument.id.in_(doc_ids))
        )
        return list(result.scalars().all())

    @staticmethod
    def _add_agency_nodes(doc, node_id, add_node, add_edge):
        """為公文的發文/受文機關建立節點和邊"""
        for field, label, edge_type in [
            ("sender", "發文", "sends"),
            ("receiver", "受文", "receives"),
        ]:
            name = getattr(doc, field)
            if not name:
                continue
            name = name.strip()
            if not name:
                continue
            ag_id = f"agency_{hashlib.md5(name.encode()).hexdigest()[:8]}"
            add_node(GraphNode(id=ag_id, type="agency", label=name))
            if field == "sender":
                add_edge(GraphEdge(source=ag_id, target=node_id, label=label, type=edge_type))
            else:
                add_edge(GraphEdge(source=node_id, target=ag_id, label=label, type=edge_type))

    async def _add_project_nodes(self, project_ids, documents, add_node, add_edge):
        proj_result = await self.db.execute(
            select(ContractProject).where(ContractProject.id.in_(list(project_ids)))
        )
        for proj in proj_result.scalars().all():
            proj_node_id = f"project_{proj.id}"
            add_node(GraphNode(
                id=proj_node_id,
                type="project",
                label=proj.project_name[:25] if proj.project_name else f"專案#{proj.id}",
            ))
            for doc in documents:
                if doc.contract_project_id == proj.id:
                    add_edge(GraphEdge(
                        source=f"doc_{doc.id}",
                        target=proj_node_id,
                        label="所屬專案",
                        type="belongs_to",
                    ))

    async def _add_related_docs(self, project_ids, doc_ids, add_node, add_edge):
        related_result = await self.db.execute(
            select(OfficialDocument)
            .where(OfficialDocument.contract_project_id.in_(list(project_ids)))
            .where(OfficialDocument.id.notin_(doc_ids))
            .order_by(OfficialDocument.doc_date.desc().nullslast())
            .limit(20)
        )
        for rdoc in related_result.scalars().all():
            rdoc_node_id = f"doc_{rdoc.id}"
            add_node(GraphNode(
                id=rdoc_node_id,
                type="document",
                label=rdoc.subject[:30] if rdoc.subject else rdoc.doc_number or f"公文#{rdoc.id}",
                category=rdoc.doc_type or rdoc.category,
                doc_number=rdoc.doc_number,
                status=rdoc.status,
            ))
            if rdoc.contract_project_id:
                add_edge(GraphEdge(
                    source=rdoc_node_id,
                    target=f"project_{rdoc.contract_project_id}",
                    label="同專案",
                    type="belongs_to",
                ))

    @staticmethod
    def _add_reply_edges(documents, add_edge):
        for i, d1 in enumerate(documents):
            for d2 in documents[i + 1:]:
                if d1.doc_number and d2.doc_number:
                    if d1.sender and d2.receiver and d1.sender.strip() == d2.receiver.strip():
                        add_edge(GraphEdge(
                            source=f"doc_{d1.id}",
                            target=f"doc_{d2.id}",
                            label="收發配對",
                            type="reply",
                        ))

    async def _add_ner_entities(self, doc_ids, add_node, add_edge) -> Tuple[int, int]:
        """加入 NER 提取的實體和關係，回傳 (entity_count, relation_count)"""
        entity_result = await self.db.execute(
            select(DocumentEntity)
            .where(DocumentEntity.document_id.in_(doc_ids))
            .where(DocumentEntity.confidence >= 0.7)
        )
        extracted_entities = entity_result.scalars().all()

        entity_mention_counts: Counter = Counter()
        for ent in extracted_entities:
            entity_mention_counts[f"{ent.entity_type}:{ent.entity_name}"] += 1

        entity_node_map: Dict[str, str] = {}
        for ent in extracted_entities:
            entity_key = f"{ent.entity_type}:{ent.entity_name}"
            if entity_key not in entity_node_map:
                ent_node_id = f"ent_{hashlib.md5(entity_key.encode()).hexdigest()[:8]}"
                entity_node_map[entity_key] = ent_node_id
                add_node(GraphNode(
                    id=ent_node_id,
                    type=ent.entity_type,
                    label=ent.entity_name[:30],
                    mention_count=entity_mention_counts.get(entity_key, 1),
                ))
            add_edge(GraphEdge(
                source=f"doc_{ent.document_id}",
                target=entity_node_map[entity_key],
                label="提及",
                type="mentions",
            ))

        relation_result = await self.db.execute(
            select(EntityRelation)
            .where(EntityRelation.document_id.in_(doc_ids))
            .where(EntityRelation.confidence >= 0.7)
        )
        extracted_relations = relation_result.scalars().all()

        for rel in extracted_relations:
            src_id = entity_node_map.get(f"{rel.source_entity_type}:{rel.source_entity_name}")
            tgt_id = entity_node_map.get(f"{rel.target_entity_type}:{rel.target_entity_name}")
            if src_id and tgt_id:
                add_edge(GraphEdge(
                    source=src_id,
                    target=tgt_id,
                    label=rel.relation_label or rel.relation_type,
                    type=rel.relation_type,
                    weight=rel.confidence,
                ))

        return len(extracted_entities), len(extracted_relations)

    async def _add_dispatch_nodes(
        self, doc_ids, seen_nodes, add_node, add_edge
    ) -> int:
        """加入派工單和桃園工程節點，回傳 dispatch link 數量"""
        # 路徑 1: dispatch_document_link
        dispatch_link_result = await self.db.execute(
            select(TaoyuanDispatchDocumentLink)
            .where(TaoyuanDispatchDocumentLink.document_id.in_(doc_ids))
        )
        dispatch_links = dispatch_link_result.scalars().all()
        dispatch_ids: Set[int] = set(dl.dispatch_order_id for dl in dispatch_links)

        # 路徑 2: FK 反向查詢
        fk_dispatch_result = await self.db.execute(
            select(TaoyuanDispatchOrder)
            .where(or_(
                TaoyuanDispatchOrder.agency_doc_id.in_(doc_ids),
                TaoyuanDispatchOrder.company_doc_id.in_(doc_ids),
            ))
        )
        for fk_disp in fk_dispatch_result.scalars().all():
            dispatch_ids.add(fk_disp.id)

        if not dispatch_ids:
            return len(dispatch_links)

        dispatch_result = await self.db.execute(
            select(TaoyuanDispatchOrder)
            .where(TaoyuanDispatchOrder.id.in_(list(dispatch_ids)))
        )
        for disp in dispatch_result.scalars().all():
            disp_node_id = f"dispatch_{disp.id}"
            add_node(GraphNode(
                id=disp_node_id,
                type="dispatch",
                label=f"派工 {disp.dispatch_no or disp.id}",
                status=disp.project_name[:20] if disp.project_name else None,
            ))
            if disp.agency_doc_id and f"doc_{disp.agency_doc_id}" in seen_nodes:
                add_edge(GraphEdge(
                    source=disp_node_id,
                    target=f"doc_{disp.agency_doc_id}",
                    label="機關公文",
                    type="agency_doc",
                ))
            if disp.company_doc_id and f"doc_{disp.company_doc_id}" in seen_nodes:
                add_edge(GraphEdge(
                    source=disp_node_id,
                    target=f"doc_{disp.company_doc_id}",
                    label="乾坤公文",
                    type="company_doc",
                ))

        for dl in dispatch_links:
            add_edge(GraphEdge(
                source=f"doc_{dl.document_id}",
                target=f"dispatch_{dl.dispatch_order_id}",
                label=dl.link_type or "派工關聯",
                type="dispatch_link",
            ))

        # Phase 7: 桃園工程
        dispatch_proj_result = await self.db.execute(
            select(TaoyuanDispatchProjectLink)
            .where(TaoyuanDispatchProjectLink.dispatch_order_id.in_(list(dispatch_ids)))
        )
        ty_project_ids: Set[int] = set()
        dispatch_proj_links = dispatch_proj_result.scalars().all()
        for dpl in dispatch_proj_links:
            ty_project_ids.add(dpl.taoyuan_project_id)

        if ty_project_ids:
            ty_proj_result = await self.db.execute(
                select(TaoyuanProject)
                .where(TaoyuanProject.id.in_(list(ty_project_ids)))
            )
            for tp in ty_proj_result.scalars().all():
                tp_node_id = f"typroject_{tp.id}"
                add_node(GraphNode(
                    id=tp_node_id,
                    type="project",
                    label=tp.project_name[:25] if tp.project_name else f"工程#{tp.id}",
                    category=tp.district,
                ))

            for dpl in dispatch_proj_links:
                add_edge(GraphEdge(
                    source=f"dispatch_{dpl.dispatch_order_id}",
                    target=f"typroject_{dpl.taoyuan_project_id}",
                    label="關聯工程",
                    type="dispatch_project",
                ))

        return len(dispatch_links)
