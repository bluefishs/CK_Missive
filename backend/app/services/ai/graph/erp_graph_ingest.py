# -*- coding: utf-8 -*-
"""
ERP Graph 入圖服務

將 ERP 資料 (quotation/invoice/billing/expense/asset/vendor) 入圖到
canonical_entities + entity_relationships，與 Code Graph 同模式。

以 case_code 為樞紐建立跨圖橋接 (KG-5 標案 / KG-2 公文 / KG-4 業務)。

Version: 1.0.0
Created: 2026-04-08
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Set

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from .erp_graph_types import (
    ERP_ENTITY_TYPES,
    ERP_RELATION_TYPES,
    ErpEntity,
    ErpRelation,
)

logger = logging.getLogger(__name__)


class ErpGraphIngestService:
    """ERP 圖譜入圖：從 ERP 表提取實體+關係 → canonical_entities"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest_all(self) -> Dict[str, Any]:
        """全量入圖：掃描 ERP 表 → 提取 → upsert"""
        t0 = datetime.now()

        entities: List[ErpEntity] = []
        relations: List[ErpRelation] = []

        # 提取各 ERP 模組
        await self._extract_quotations(entities, relations)
        await self._extract_expenses(entities, relations)
        await self._extract_assets(entities, relations)

        if not entities:
            return {"entities": 0, "relations": 0, "duration_ms": 0}

        # Upsert 到 canonical_entities
        from app.extended.models.knowledge_graph import CanonicalEntity, EntityRelationship
        entity_map = await self._upsert_entities(entities, CanonicalEntity)
        rel_count = await self._upsert_relations(relations, entity_map, EntityRelationship)

        # Phase 1.2: case_code 跨圖橋接
        bridge_count = await self._bridge_case_codes(entity_map, CanonicalEntity, EntityRelationship)

        await self.db.commit()
        duration = int((datetime.now() - t0).total_seconds() * 1000)

        logger.info(
            "ERP graph ingest: %d entities, %d relations, %d bridges, %dms",
            len(entity_map), rel_count, bridge_count, duration,
        )
        return {
            "entities": len(entity_map),
            "relations": rel_count,
            "cross_graph_bridges": bridge_count,
            "duration_ms": duration,
        }

    # ── 提取器 ──

    async def _extract_quotations(
        self, entities: List[ErpEntity], relations: List[ErpRelation],
    ) -> None:
        """從 ERPQuotation 提取案件 + 廠商實體"""
        from app.extended.models.erp import ERPQuotation, ERPVendorPayable

        rows = (await self.db.execute(
            select(ERPQuotation).where(ERPQuotation.deleted_at.is_(None))
        )).scalars().all()

        for q in rows:
            if not q.case_name:
                continue
            entities.append(ErpEntity(
                canonical_name=q.case_name,
                entity_type="erp_quotation",
                description={
                    "case_code": q.case_code,
                    "year": q.year,
                    "total_price": float(q.total_price) if q.total_price else 0,
                    "status": q.status,
                },
                external_id=q.case_code or "",
            ))

        # 廠商 (從 vendor_payables)
        vp_rows = (await self.db.execute(select(ERPVendorPayable))).scalars().all()
        seen_vendors: Set[str] = set()
        for vp in vp_rows:
            if not vp.vendor_name or vp.vendor_name in seen_vendors:
                continue
            seen_vendors.add(vp.vendor_name)
            entities.append(ErpEntity(
                canonical_name=vp.vendor_name,
                entity_type="erp_vendor",
                description={"vendor_type": "subcontractor"},
                external_id=str(vp.vendor_id) if hasattr(vp, "vendor_id") else "",
            ))

            # 關係：vendor → quotation
            if vp.erp_quotation_id:
                # 找對應 quotation 的 case_name
                for q in rows:
                    if q.id == vp.erp_quotation_id and q.case_name:
                        relations.append(ErpRelation(
                            source_name=vp.vendor_name,
                            source_type="erp_vendor",
                            target_name=q.case_name,
                            target_type="erp_quotation",
                            relation_type="supplies_to",
                            metadata={"amount": float(vp.payable_amount) if vp.payable_amount else 0},
                        ))
                        break

    async def _extract_expenses(
        self, entities: List[ErpEntity], relations: List[ErpRelation],
    ) -> None:
        """從 ExpenseInvoice 提取費用實體"""
        from app.extended.models.invoice import ExpenseInvoice

        rows = (await self.db.execute(
            select(ExpenseInvoice).limit(500)
        )).scalars().all()

        for e in rows:
            name = e.inv_num or f"expense_{e.id}"
            entities.append(ErpEntity(
                canonical_name=name,
                entity_type="erp_expense",
                description={
                    "amount": float(e.amount) if e.amount else 0,
                    "tax_amount": float(e.tax_amount) if e.tax_amount else 0,
                    "category": e.category or "",
                    "status": e.status or "",
                },
                external_id=e.case_code or "",
            ))

            # 關係：expense → project (via case_code)
            if e.case_code:
                relations.append(ErpRelation(
                    source_name=name,
                    source_type="erp_expense",
                    target_name=e.case_code,
                    target_type="erp_quotation",
                    relation_type="expensed_for",
                ))

    async def _extract_assets(
        self, entities: List[ErpEntity], relations: List[ErpRelation],
    ) -> None:
        """從 Asset 提取資產實體"""
        from app.extended.models.asset import Asset

        rows = (await self.db.execute(select(Asset).limit(500))).scalars().all()

        for a in rows:
            asset_name = a.name or a.asset_code or f"asset_{a.id}"
            entities.append(ErpEntity(
                canonical_name=asset_name,
                entity_type="erp_asset",
                description={
                    "asset_code": a.asset_code or "",
                    "purchase_amount": float(a.purchase_amount) if a.purchase_amount else 0,
                },
                external_id=a.asset_code or "",
            ))

    # ── Upsert ──

    async def _upsert_entities(
        self, entities: List[ErpEntity], CanonicalEntity: Any,
    ) -> Dict[str, int]:
        """Batch upsert ERP entities. Returns {key: id}."""
        seen: Set[str] = set()
        unique: List[Dict[str, Any]] = []
        for ent in entities:
            key = f"{ent.entity_type}:{ent.canonical_name}"
            if key in seen:
                continue
            seen.add(key)
            unique.append({
                "canonical_name": ent.canonical_name,
                "entity_type": ent.entity_type,
                "description": json.dumps(ent.description, ensure_ascii=False),
                "external_id": ent.external_id or None,
                "alias_count": 0,
                "mention_count": 1,
            })

        BATCH_SIZE = 500
        for i in range(0, len(unique), BATCH_SIZE):
            batch = unique[i:i + BATCH_SIZE]
            stmt = pg_insert(CanonicalEntity).values(batch)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_canonical_name_type",
                set_={
                    "description": stmt.excluded.description,
                    "external_id": stmt.excluded.external_id,
                    "last_seen_at": func.now(),
                    "mention_count": CanonicalEntity.mention_count + 1,
                },
            )
            await self.db.execute(stmt)

        await self.db.flush()

        rows = (await self.db.execute(
            select(
                CanonicalEntity.id,
                CanonicalEntity.canonical_name,
                CanonicalEntity.entity_type,
            ).where(CanonicalEntity.entity_type.in_(ERP_ENTITY_TYPES))
        )).all()

        return {f"{r[2]}:{r[1]}": r[0] for r in rows}

    async def _upsert_relations(
        self,
        relations: List[ErpRelation],
        entity_map: Dict[str, int],
        EntityRelationship: Any,
    ) -> int:
        """Batch upsert ERP relations."""
        values = []
        for rel in relations:
            src_id = entity_map.get(f"{rel.source_type}:{rel.source_name}")
            tgt_id = entity_map.get(f"{rel.target_type}:{rel.target_name}")
            if not src_id or not tgt_id:
                continue
            values.append({
                "source_entity_id": src_id,
                "target_entity_id": tgt_id,
                "relation_type": rel.relation_type,
                "relation_label": "erp_ingest",
                "weight": 1.0,
                "confidence_level": "extracted",
                "source_project": "ck-missive",
            })

        if not values:
            return 0

        # 先查已存在的關係，避免重複插入
        existing = set()
        for v in values:
            row = (await self.db.execute(
                select(EntityRelationship.id)
                .where(EntityRelationship.source_entity_id == v["source_entity_id"])
                .where(EntityRelationship.target_entity_id == v["target_entity_id"])
                .where(EntityRelationship.relation_type == v["relation_type"])
                .limit(1)
            )).scalar()
            if row:
                existing.add((v["source_entity_id"], v["target_entity_id"], v["relation_type"]))

        new_values = [
            v for v in values
            if (v["source_entity_id"], v["target_entity_id"], v["relation_type"]) not in existing
        ]

        count = 0
        BATCH_SIZE = 500
        for i in range(0, len(new_values), BATCH_SIZE):
            batch = new_values[i:i + BATCH_SIZE]
            await self.db.execute(EntityRelationship.__table__.insert(), batch)
            count += len(batch)

        await self.db.flush()
        return count

    # ── 跨圖橋接 (case_code 樞紐) ──

    async def _bridge_case_codes(
        self,
        erp_entity_map: Dict[str, int],
        CanonicalEntity: Any,
        EntityRelationship: Any,
    ) -> int:
        """
        以 case_code 為樞紐，建立 ERP ↔ 其他圖譜的橋接關係。

        橋接路徑：
        - erp_quotation ↔ project (KG-1, entity_type='project')
        - erp_quotation ↔ org (KG-1, entity_type='org', 機關/委託單位)
        - erp_quotation ↔ tender (KG-5, via case_code 在 tender_records)
        """
        bridges = []

        # 找所有有 external_id (=case_code) 的 ERP quotation entities
        erp_quotations = {
            k: v for k, v in erp_entity_map.items()
            if k.startswith("erp_quotation:")
        }

        if not erp_quotations:
            return 0

        # 取得所有 KG-1 project 實體 (external_id = case_code 或 project_code)
        kg1_projects = (await self.db.execute(
            select(CanonicalEntity.id, CanonicalEntity.canonical_name, CanonicalEntity.external_id)
            .where(CanonicalEntity.entity_type == "project")
            .where(CanonicalEntity.external_id.isnot(None))
        )).all()
        kg1_by_ext_id = {r[2]: r[0] for r in kg1_projects if r[2]}

        # 取得 ERP quotation 的 case_code → entity_id 映射
        erp_q_rows = (await self.db.execute(
            select(CanonicalEntity.id, CanonicalEntity.external_id)
            .where(CanonicalEntity.entity_type == "erp_quotation")
            .where(CanonicalEntity.external_id.isnot(None))
        )).all()

        for erp_id, case_code in erp_q_rows:
            if not case_code:
                continue
            # 橋接到 KG-1 project
            kg1_id = kg1_by_ext_id.get(case_code)
            if kg1_id:
                bridges.append({
                    "source_entity_id": erp_id,
                    "target_entity_id": kg1_id,
                    "relation_type": "case_link",
                    "relation_label": "erp_bridge",
                    "weight": 2.0,
                    "confidence_level": "extracted",
                    "source_project": "ck-missive",
                })

        if not bridges:
            return 0

        # 過濾已存在的橋接
        new_bridges = []
        for b in bridges:
            exists = (await self.db.execute(
                select(EntityRelationship.id)
                .where(EntityRelationship.source_entity_id == b["source_entity_id"])
                .where(EntityRelationship.target_entity_id == b["target_entity_id"])
                .where(EntityRelationship.relation_type == b["relation_type"])
                .limit(1)
            )).scalar()
            if not exists:
                new_bridges.append(b)

        if new_bridges:
            await self.db.execute(EntityRelationship.__table__.insert(), new_bridges)
            await self.db.flush()

        logger.info("ERP cross-graph bridges: %d created", len(new_bridges))
        return len(new_bridges)
