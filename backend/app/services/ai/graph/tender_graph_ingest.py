# -*- coding: utf-8 -*-
"""
Tender Graph Ingest — 將 tender_records 橋接到 canonical_entities（graph_domain='tender'）

2026-04-19 新建：彌補 unified-search 統一面（原 tender 6351 records 獨立於 KG）。

Entity types:
  - tender_record: 單筆標案
  - tender_agency: 委託機關（unit_name，與 KG knowledge domain 的 agency 可橋接）

設計：
  - mention_count = award_amount > 0 ? 10 : 1（決標案權重高）
  - external_id = f"{unit_id}:{job_number}"（PCC 唯一識別）
  - description 含預算/決標/公告日期/狀態

批次 upsert，idempotent：重複執行不會爆量。
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.knowledge_graph import CanonicalEntity

logger = logging.getLogger(__name__)

TENDER_DOMAIN = "tender"
BATCH_SIZE = 200


class TenderGraphIngestService:
    """掃 tender_records → canonical_entities (domain=tender)。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest_all(self) -> Dict[str, Any]:
        t0 = time.time()

        # 以原始 SQL 讀 tender_records（避免 model dependency）
        rows = (
            await self.db.execute(
                text(
                    "SELECT id, unit_id, job_number, title, unit_name, "
                    "category, budget, award_amount, announce_date, status "
                    "FROM tender_records"
                )
            )
        ).all()

        tender_batch: List[Dict[str, Any]] = []
        agency_batch: Dict[str, Dict[str, Any]] = {}

        for r in rows:
            (tid, unit_id, job_number, title, unit_name,
             category, budget, award, announce_date, status) = r

            # 單筆標案
            ext_id = f"{unit_id}:{job_number}" if job_number else f"{unit_id}:t{tid}"
            desc_parts = []
            if category: desc_parts.append(f"類別: {category}")
            if budget: desc_parts.append(f"預算: {budget}")
            if award: desc_parts.append(f"決標: {award}")
            if announce_date: desc_parts.append(f"公告: {announce_date}")
            if status: desc_parts.append(f"狀態: {status}")

            tender_batch.append({
                "canonical_name": (title or "")[:500],
                "entity_type": "tender_record",
                "graph_domain": TENDER_DOMAIN,
                "description": " | ".join(desc_parts)[:1000],
                "external_id": ext_id[:100],
                "mention_count": 10 if award else 1,
            })

            # 機關（合併同名）
            if unit_name:
                key = unit_name[:200]
                # 確保 external_id 唯一（用 unit_id 或 fallback 到 canonical_name）
                agency_ext_id = unit_id if unit_id else f"agency:{key}"
                if key not in agency_batch:
                    agency_batch[key] = {
                        "canonical_name": key,
                        "entity_type": "tender_agency",
                        "graph_domain": TENDER_DOMAIN,
                        "description": f"標案委託機關（unit_id: {unit_id or 'N/A'}）",
                        "external_id": agency_ext_id[:100],
                        "mention_count": 1,
                    }
                else:
                    agency_batch[key]["mention_count"] += 1

        # 合併批次 + 去重（同 (canonical_name, entity_type) 避免 ON CONFLICT 衝突自己）
        all_entities = tender_batch + list(agency_batch.values())
        dedup_map: Dict[tuple, Dict[str, Any]] = {}
        for ent in all_entities:
            key = (ent["canonical_name"], ent["entity_type"])
            if key in dedup_map:
                # 保留 mention_count 較高的（或相加）
                dedup_map[key]["mention_count"] = max(
                    dedup_map[key]["mention_count"], ent["mention_count"],
                )
            else:
                dedup_map[key] = ent
        all_entities = list(dedup_map.values())
        logger.info("Tender dedup: %d → %d unique entities", len(tender_batch) + len(agency_batch), len(all_entities))

        # 批次 upsert（ON CONFLICT 更新 mention_count + description）
        inserted = 0
        for i in range(0, len(all_entities), BATCH_SIZE):
            chunk = all_entities[i:i + BATCH_SIZE]
            if not chunk:
                continue
            stmt = pg_insert(CanonicalEntity).values(chunk)
            # 既有 constraint: uq_canonical_name_type (canonical_name, entity_type)
            stmt = stmt.on_conflict_do_update(
                index_elements=["canonical_name", "entity_type"],
                set_={
                    "description": stmt.excluded.description,
                    "mention_count": stmt.excluded.mention_count,
                    "external_id": stmt.excluded.external_id,
                    "graph_domain": stmt.excluded.graph_domain,
                },
            )
            await self.db.execute(stmt)
            inserted += len(chunk)

        await self.db.commit()

        duration_ms = int((time.time() - t0) * 1000)
        logger.info(
            "Tender graph ingest 完成: records=%d, agencies=%d, upserted=%d, %dms",
            len(tender_batch), len(agency_batch), inserted, duration_ms,
        )
        return {
            "records": len(tender_batch),
            "agencies": len(agency_batch),
            "upserted": inserted,
            "duration_ms": duration_ms,
        }
