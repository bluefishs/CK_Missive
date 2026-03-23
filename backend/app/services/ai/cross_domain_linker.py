"""
跨專案實體自動連結服務 (Cross-Domain Entity Linker)

在聯邦貢獻完成後，自動偵測不同來源專案間可連結的實體，
建立跨域關係 (contracted_by, located_at, part_of_project, commissioned_by)。

連結規則：
1. Contractor bridging: Tunnel contractor ↔ Missive org (fuzzy ≥ 0.85)
2. Location bridging: Missive location ↔ LvrLand land_parcel (section name)
3. Project bridging: Missive project ↔ Tunnel tunnel (name similarity)
4. Agency bridging: Missive org (with linked_agency_id) ↔ Tunnel commissioned_by

Version: 1.0.0
Created: 2026-03-22
"""

import logging
import time
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select, and_, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import CROSS_PROJECT_RELATION_TYPES
from app.extended.models import (
    CanonicalEntity,
    EntityAlias,
    EntityRelationship,
)

logger = logging.getLogger(__name__)

# 模糊匹配閾值
FUZZY_THRESHOLD = 0.85
# 每次連結批次上限
BATCH_LIMIT = 200


class CrossDomainLinker:
    """跨專案實體自動連結服務"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_all_rules(self) -> Dict[str, int]:
        """
        執行所有跨域連結規則。

        Returns:
            Dict 記錄每條規則建立的關係數量
        """
        start = time.monotonic()
        results: Dict[str, int] = {}

        results["contractor_bridging"] = await self._rule_contractor_bridging()
        results["location_bridging"] = await self._rule_location_bridging()
        results["project_bridging"] = await self._rule_project_bridging()
        results["agency_bridging"] = await self._rule_agency_bridging()

        total = sum(results.values())
        elapsed_ms = int((time.monotonic() - start) * 1000)

        if total > 0:
            await self.db.commit()

        logger.info(
            "CrossDomainLinker completed: %d relations created (%s), %dms",
            total, results, elapsed_ms,
        )
        return results

    # -----------------------------------------------------------------------
    # Rule 1: Contractor bridging
    # Tunnel 'contractor' entity ↔ Missive 'org' entity
    # -----------------------------------------------------------------------

    async def _rule_contractor_bridging(self) -> int:
        """
        Tunnel 承包商 ↔ Missive 機關/公司 模糊匹配。
        建立 contracted_by 關係。
        """
        # 取得 Tunnel contractor 實體
        tunnel_contractors = await self._get_entities_by_type_and_project(
            "contractor", "ck-tunnel",
        )
        if not tunnel_contractors:
            return 0

        # 取得 Missive org 實體
        missive_orgs = await self._get_entities_by_type_and_project(
            "org", "ck-missive",
        )
        if not missive_orgs:
            return 0

        created = 0
        for contractor in tunnel_contractors:
            best_match = await self._find_best_fuzzy_match(
                contractor.canonical_name, missive_orgs,
            )
            if best_match is not None:
                if await self._create_relation_if_absent(
                    contractor.id, best_match.id,
                    "contracted_by", "ck-tunnel",
                ):
                    created += 1
                    logger.info(
                        "Contractor bridge: %s ↔ %s",
                        contractor.canonical_name, best_match.canonical_name,
                    )

        return created

    # -----------------------------------------------------------------------
    # Rule 2: Location bridging
    # Missive 'location' entity ↔ LvrLand 'land_parcel' entity
    # -----------------------------------------------------------------------

    async def _rule_location_bridging(self) -> int:
        """
        Missive 地點 ↔ LvrLand 地段 名稱匹配。
        建立 located_at 關係。
        """
        missive_locations = await self._get_entities_by_type_and_project(
            "location", "ck-missive",
        )
        if not missive_locations:
            return 0

        lvrland_parcels = await self._get_entities_by_type_and_project(
            "land_parcel", "ck-lvrland",
        )
        if not lvrland_parcels:
            return 0

        created = 0
        # 建立 section name 索引 (取地段名稱前綴)
        parcel_index: Dict[str, CanonicalEntity] = {}
        for parcel in lvrland_parcels:
            # land_parcel canonical_name 格式: "{city}{district}{section}{land_no14}"
            # 取前面的區段名稱作為 key
            name = parcel.canonical_name
            if len(name) >= 6:
                section_key = name[:6]  # 前6字 (市+區+段)
                parcel_index[section_key] = parcel

        for location in missive_locations:
            loc_name = location.canonical_name
            # 嘗試匹配地段前綴
            for section_key, parcel in parcel_index.items():
                if section_key in loc_name:
                    if await self._create_relation_if_absent(
                        location.id, parcel.id,
                        "located_at", "cross-domain",
                    ):
                        created += 1
                        logger.info(
                            "Location bridge: %s → %s",
                            loc_name, parcel.canonical_name,
                        )
                    break

        return created

    # -----------------------------------------------------------------------
    # Rule 3: Project bridging
    # Missive 'project' entity ↔ Tunnel 'tunnel' entity
    # -----------------------------------------------------------------------

    async def _rule_project_bridging(self) -> int:
        """
        Missive 專案 ↔ Tunnel 隧道 名稱相似度匹配。
        建立 part_of_project 關係。
        """
        missive_projects = await self._get_entities_by_type_and_project(
            "project", "ck-missive",
        )
        if not missive_projects:
            return 0

        tunnel_tunnels = await self._get_entities_by_type_and_project(
            "tunnel", "ck-tunnel",
        )
        if not tunnel_tunnels:
            return 0

        created = 0
        for tunnel in tunnel_tunnels:
            best_match = await self._find_best_fuzzy_match(
                tunnel.canonical_name, missive_projects,
            )
            if best_match is not None:
                if await self._create_relation_if_absent(
                    tunnel.id, best_match.id,
                    "part_of_project", "cross-domain",
                ):
                    created += 1
                    logger.info(
                        "Project bridge: %s → %s",
                        tunnel.canonical_name, best_match.canonical_name,
                    )

        return created

    # -----------------------------------------------------------------------
    # Rule 4: Agency bridging
    # Missive 'org' (with linked_agency_id) ↔ Tunnel 'inspection' commissioned_by
    # -----------------------------------------------------------------------

    async def _rule_agency_bridging(self) -> int:
        """
        Missive 機關 (有 linked_agency_id) ↔ Tunnel 檢查紀錄 的委辦機關。
        建立 commissioned_by 關係。
        """
        # 取得有 linked_agency_id 的 Missive org 實體
        result = await self.db.execute(
            select(CanonicalEntity)
            .where(
                and_(
                    CanonicalEntity.entity_type == "org",
                    CanonicalEntity.source_project == "ck-missive",
                    CanonicalEntity.linked_agency_id.isnot(None),
                )
            )
            .limit(BATCH_LIMIT)
        )
        missive_agencies = list(result.scalars().all())
        if not missive_agencies:
            return 0

        tunnel_inspections = await self._get_entities_by_type_and_project(
            "inspection", "ck-tunnel",
        )
        if not tunnel_inspections:
            return 0

        created = 0
        for inspection in tunnel_inspections:
            best_match = await self._find_best_fuzzy_match(
                inspection.canonical_name, missive_agencies,
            )
            if best_match is not None:
                if await self._create_relation_if_absent(
                    inspection.id, best_match.id,
                    "commissioned_by", "cross-domain",
                ):
                    created += 1
                    logger.info(
                        "Agency bridge: %s → %s",
                        inspection.canonical_name, best_match.canonical_name,
                    )

        return created

    # -----------------------------------------------------------------------
    # Utility methods
    # -----------------------------------------------------------------------

    async def _get_entities_by_type_and_project(
        self, entity_type: str, source_project: str,
    ) -> List[CanonicalEntity]:
        """取得指定類型 + 來源的實體清單"""
        result = await self.db.execute(
            select(CanonicalEntity)
            .where(
                and_(
                    CanonicalEntity.entity_type == entity_type,
                    CanonicalEntity.source_project == source_project,
                )
            )
            .limit(BATCH_LIMIT)
        )
        return list(result.scalars().all())

    async def _find_best_fuzzy_match(
        self,
        name: str,
        candidates: List[CanonicalEntity],
    ) -> Optional[CanonicalEntity]:
        """
        在候選清單中尋找最佳模糊匹配。
        使用 pg_trgm similarity 若可用，否則降級為 Python difflib。
        """
        if not candidates:
            return None

        try:
            # 嘗試使用 pg_trgm (需要 pg_trgm extension)
            candidate_ids = [c.id for c in candidates]
            result = await self.db.execute(
                select(
                    CanonicalEntity,
                    func.similarity(CanonicalEntity.canonical_name, name).label("sim"),
                )
                .where(CanonicalEntity.id.in_(candidate_ids))
                .order_by(text("sim DESC"))
                .limit(1)
            )
            row = result.first()
            if row and row.sim >= FUZZY_THRESHOLD:
                return row[0]
        except Exception:
            # pg_trgm 不可用 — 降級為 Python
            return self._python_fuzzy_match(name, candidates)

        return None

    @staticmethod
    def _python_fuzzy_match(
        name: str,
        candidates: List[CanonicalEntity],
    ) -> Optional[CanonicalEntity]:
        """Python fallback 模糊匹配 (SequenceMatcher)"""
        from difflib import SequenceMatcher

        best_score = 0.0
        best_entity = None

        for candidate in candidates:
            score = SequenceMatcher(
                None, name, candidate.canonical_name,
            ).ratio()
            if score > best_score and score >= FUZZY_THRESHOLD:
                best_score = score
                best_entity = candidate

        return best_entity

    async def _create_relation_if_absent(
        self,
        source_id: int,
        target_id: int,
        relation_type: str,
        source_project: str,
    ) -> bool:
        """建立關係（若不存在）"""
        existing = await self.db.execute(
            select(EntityRelationship.id).where(
                and_(
                    EntityRelationship.source_entity_id == source_id,
                    EntityRelationship.target_entity_id == target_id,
                    EntityRelationship.relation_type == relation_type,
                    EntityRelationship.invalidated_at.is_(None),
                )
            )
        )
        if existing.scalar_one_or_none() is not None:
            return False

        self.db.add(EntityRelationship(
            source_entity_id=source_id,
            target_entity_id=target_id,
            relation_type=relation_type,
            relation_label=relation_type.replace("_", " "),
            weight=1.0,
            source_project=source_project,
            document_count=0,
        ))
        return True
