"""
跨專案實體自動連結服務 (Cross-Domain Entity Linker)

在聯邦貢獻完成後，自動偵測不同來源專案間可連結的實體，
建立跨域關係 (contracted_by, located_at, part_of_project, commissioned_by)。

連結規則：
1. Contractor bridging: Tunnel contractor ↔ Missive org (fuzzy ≥ 0.85)
2. Location bridging: Missive location ↔ LvrLand land_parcel (section name)
3. Project bridging: Missive project ↔ Tunnel tunnel (name similarity ≥ 0.80)
4. Agency bridging: Missive org (with linked_agency_id) ↔ Tunnel inspection commissioned_by

Version: 1.1.0
Created: 2026-03-22
Updated: 2026-03-23 — 整合 CanonicalEntityMatcher + link_after_contribution + agency meta
"""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    CanonicalEntity,
    EntityRelationship,
)
from app.services.ai.canonical_entity_matcher import CanonicalEntityMatcher

logger = logging.getLogger(__name__)

# 模糊匹配閾值
CONTRACTOR_THRESHOLD = 0.85
PROJECT_THRESHOLD = 0.80
LOCATION_THRESHOLD = 0.75
AGENCY_THRESHOLD = 0.85
# 每次連結批次上限
BATCH_LIMIT = 200


@dataclass
class LinkResult:
    """單筆連結結果"""
    source_id: int
    target_id: int
    relation_type: str
    source_name: str
    target_name: str
    similarity: float
    bridge_type: str


@dataclass
class LinkingReport:
    """連結批次報告"""
    links_created: int = 0
    links_skipped: int = 0
    processing_ms: int = 0
    details: List[LinkResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class CrossDomainLinker:
    """跨專案實體自動連結服務

    在 CrossDomainContributionService 完成實體貢獻後呼叫，
    掃描新貢獻的實體並與其他專案的實體建立橋接關係。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def link_after_contribution(
        self, source_project: str,
    ) -> LinkingReport:
        """
        對指定來源專案的實體執行對應的橋接規則。

        Args:
            source_project: 剛完成貢獻的來源專案 (e.g. 'ck-tunnel', 'ck-lvrland')

        Returns:
            LinkingReport 包含建立的連結數與詳細結果
        """
        start = time.monotonic()
        report = LinkingReport()

        try:
            if source_project == "ck-tunnel":
                await self._rule_contractor_bridging(report)
                await self._rule_project_bridging(report)
                await self._rule_agency_bridging(report)
            elif source_project == "ck-lvrland":
                await self._rule_location_bridging(report)

            if report.links_created > 0:
                await self.db.flush()
        except Exception as e:
            report.errors.append(f"Linking failed: {str(e)[:200]}")
            logger.error("CrossDomainLinker error: %s", e, exc_info=True)

        report.processing_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "CrossDomainLinker for %s: %d created, %d skipped, %dms",
            source_project, report.links_created,
            report.links_skipped, report.processing_ms,
        )
        return report

    async def run_all_rules(self) -> LinkingReport:
        """
        執行所有跨域連結規則（全量掃描）。

        Returns:
            LinkingReport 包含所有規則的連結結果
        """
        start = time.monotonic()
        report = LinkingReport()

        try:
            await self._rule_contractor_bridging(report)
            await self._rule_location_bridging(report)
            await self._rule_project_bridging(report)
            await self._rule_agency_bridging(report)

            if report.links_created > 0:
                await self.db.commit()
        except Exception as e:
            report.errors.append(f"Linking failed: {str(e)[:200]}")
            logger.error("CrossDomainLinker error: %s", e, exc_info=True)

        report.processing_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "CrossDomainLinker all rules: %d created, %d skipped, %dms",
            report.links_created, report.links_skipped, report.processing_ms,
        )
        return report

    # -----------------------------------------------------------------------
    # Rule 1: Contractor bridging
    # Tunnel 'contractor' entity ↔ Missive 'org' entity
    # -----------------------------------------------------------------------

    async def _rule_contractor_bridging(self, report: LinkingReport) -> None:
        """Tunnel 承包商 ↔ Missive 機關/公司 模糊匹配 → contracted_by"""
        tunnel_contractors = await self._get_entities(
            "contractor", "ck-tunnel",
        )
        if not tunnel_contractors:
            return

        missive_orgs = await self._get_entities("org", "ck-missive")
        if not missive_orgs:
            return

        for contractor in tunnel_contractors:
            best_match, best_score = self._find_best_match(
                contractor.canonical_name, missive_orgs,
                threshold=CONTRACTOR_THRESHOLD,
            )
            if best_match is not None:
                created = await self._create_relation_if_absent(
                    contractor.id, best_match.id,
                    "contracted_by", "ck-tunnel",
                )
                report.details.append(LinkResult(
                    source_id=contractor.id,
                    target_id=best_match.id,
                    relation_type="contracted_by",
                    source_name=contractor.canonical_name,
                    target_name=best_match.canonical_name,
                    similarity=best_score,
                    bridge_type="contractor",
                ))
                if created:
                    report.links_created += 1
                    logger.info(
                        "Contractor bridge: %s ↔ %s (%.2f)",
                        contractor.canonical_name,
                        best_match.canonical_name, best_score,
                    )
                else:
                    report.links_skipped += 1

    # -----------------------------------------------------------------------
    # Rule 2: Location bridging
    # Missive 'location' entity ↔ LvrLand 'land_parcel' entity
    # -----------------------------------------------------------------------

    async def _rule_location_bridging(self, report: LinkingReport) -> None:
        """Missive 地點 ↔ LvrLand 地段 名稱匹配 → located_at"""
        missive_locations = await self._get_entities("location", "ck-missive")
        if not missive_locations:
            return

        lvrland_parcels = await self._get_entities("land_parcel", "ck-lvrland")
        if not lvrland_parcels:
            return

        # 建立段名索引: "桃園市桃園區大興段" → [parcel1, parcel2, ...]
        section_index: Dict[str, List[CanonicalEntity]] = {}
        for parcel in lvrland_parcels:
            section = self._extract_section_name(parcel.canonical_name)
            if section:
                section_index.setdefault(section, []).append(parcel)

        for location in missive_locations:
            loc_name = location.canonical_name
            matched = False

            # 嘗試匹配段名
            for section, parcels in section_index.items():
                if section in loc_name or loc_name in section:
                    parcel = parcels[0]  # 取第一筆代表
                    created = await self._create_relation_if_absent(
                        location.id, parcel.id,
                        "located_at", "ck-lvrland",
                    )
                    report.details.append(LinkResult(
                        source_id=location.id,
                        target_id=parcel.id,
                        relation_type="located_at",
                        source_name=loc_name,
                        target_name=parcel.canonical_name,
                        similarity=0.90,
                        bridge_type="location",
                    ))
                    if created:
                        report.links_created += 1
                        logger.info(
                            "Location bridge: %s → %s",
                            loc_name, parcel.canonical_name,
                        )
                    else:
                        report.links_skipped += 1
                    matched = True
                    break

            # 段名未命中 → trigram 降級
            if not matched:
                best_match, best_score = self._find_best_match(
                    loc_name, lvrland_parcels,
                    threshold=LOCATION_THRESHOLD,
                    use_false_match_check=False,
                )
                if best_match is not None:
                    created = await self._create_relation_if_absent(
                        location.id, best_match.id,
                        "located_at", "ck-lvrland",
                    )
                    report.details.append(LinkResult(
                        source_id=location.id,
                        target_id=best_match.id,
                        relation_type="located_at",
                        source_name=loc_name,
                        target_name=best_match.canonical_name,
                        similarity=best_score,
                        bridge_type="location",
                    ))
                    if created:
                        report.links_created += 1
                    else:
                        report.links_skipped += 1

    # -----------------------------------------------------------------------
    # Rule 3: Project bridging
    # Missive 'project' entity ↔ Tunnel 'tunnel' entity
    # -----------------------------------------------------------------------

    async def _rule_project_bridging(self, report: LinkingReport) -> None:
        """Missive 專案 ↔ Tunnel 隧道 名稱相似度匹配 → part_of_project"""
        missive_projects = await self._get_entities("project", "ck-missive")
        if not missive_projects:
            return

        tunnel_tunnels = await self._get_entities("tunnel", "ck-tunnel")
        if not tunnel_tunnels:
            return

        for tunnel in tunnel_tunnels:
            best_match, best_score = self._find_best_match(
                tunnel.canonical_name, missive_projects,
                threshold=PROJECT_THRESHOLD,
            )
            if best_match is not None:
                created = await self._create_relation_if_absent(
                    tunnel.id, best_match.id,
                    "part_of_project", "ck-tunnel",
                )
                report.details.append(LinkResult(
                    source_id=tunnel.id,
                    target_id=best_match.id,
                    relation_type="part_of_project",
                    source_name=tunnel.canonical_name,
                    target_name=best_match.canonical_name,
                    similarity=best_score,
                    bridge_type="project",
                ))
                if created:
                    report.links_created += 1
                    logger.info(
                        "Project bridge: %s → %s (%.2f)",
                        tunnel.canonical_name,
                        best_match.canonical_name, best_score,
                    )
                else:
                    report.links_skipped += 1

    # -----------------------------------------------------------------------
    # Rule 4: Agency bridging
    # Missive 'org' (with linked_agency_id) ↔ Tunnel 'inspection' commissioned_by
    # -----------------------------------------------------------------------

    async def _rule_agency_bridging(self, report: LinkingReport) -> None:
        """Missive 機關 (linked_agency_id) ↔ Tunnel inspection 的委辦機關 → commissioned_by

        從 Tunnel inspection 的 external_meta.commissioning_agency 取得委辦機關名稱，
        與 Missive 中已連結 agency 的 org 實體進行模糊匹配。
        """
        # 取得有 linked_agency_id 的 Missive org 實體
        result = await self.db.execute(
            select(CanonicalEntity).where(
                and_(
                    CanonicalEntity.entity_type == "org",
                    CanonicalEntity.source_project == "ck-missive",
                    CanonicalEntity.linked_agency_id.isnot(None),
                )
            ).limit(BATCH_LIMIT)
        )
        linked_orgs = list(result.scalars().all())
        if not linked_orgs:
            return

        tunnel_inspections = await self._get_entities("inspection", "ck-tunnel")
        if not tunnel_inspections:
            return

        for inspection in tunnel_inspections:
            # 從 external_meta 取得委辦機關名稱
            meta = inspection.external_meta or {}
            commissioning = meta.get("commissioning_agency", "")
            if not commissioning:
                # 無委辦機關 meta — 回退到 inspection 名稱匹配
                commissioning = inspection.canonical_name

            best_match, best_score = self._find_best_match(
                commissioning, linked_orgs,
                threshold=AGENCY_THRESHOLD,
            )
            if best_match is not None:
                created = await self._create_relation_if_absent(
                    inspection.id, best_match.id,
                    "commissioned_by", "ck-tunnel",
                )
                report.details.append(LinkResult(
                    source_id=inspection.id,
                    target_id=best_match.id,
                    relation_type="commissioned_by",
                    source_name=inspection.canonical_name,
                    target_name=best_match.canonical_name,
                    similarity=best_score,
                    bridge_type="agency",
                ))
                if created:
                    report.links_created += 1
                    logger.info(
                        "Agency bridge: %s → %s (%.2f)",
                        inspection.canonical_name,
                        best_match.canonical_name, best_score,
                    )
                else:
                    report.links_skipped += 1

    # -----------------------------------------------------------------------
    # Utility methods
    # -----------------------------------------------------------------------

    async def _get_entities(
        self, entity_type: str, source_project: str,
    ) -> List[CanonicalEntity]:
        """取得指定類型 + 來源的實體清單"""
        result = await self.db.execute(
            select(CanonicalEntity).where(
                and_(
                    CanonicalEntity.entity_type == entity_type,
                    CanonicalEntity.source_project == source_project,
                )
            ).limit(BATCH_LIMIT)
        )
        return list(result.scalars().all())

    @staticmethod
    def _find_best_match(
        name: str,
        candidates: List[CanonicalEntity],
        threshold: float = CONTRACTOR_THRESHOLD,
        use_false_match_check: bool = True,
    ) -> tuple[Optional[CanonicalEntity], float]:
        """
        在候選清單中尋找最佳 trigram 模糊匹配。
        使用 CanonicalEntityMatcher.compute_similarity (Python 端 trigram)。

        Returns:
            (best_entity, best_score) — 無匹配時回傳 (None, 0.0)
        """
        if not candidates or not name:
            return None, 0.0

        best_entity: Optional[CanonicalEntity] = None
        best_score = 0.0

        for candidate in candidates:
            score = CanonicalEntityMatcher.compute_similarity(
                name, candidate.canonical_name,
            )
            if score >= threshold and score > best_score:
                if use_false_match_check and CanonicalEntityMatcher.is_false_fuzzy_match(
                    name, candidate.canonical_name,
                ):
                    continue
                best_entity = candidate
                best_score = score

        return best_entity, best_score

    async def _create_relation_if_absent(
        self,
        source_id: int,
        target_id: int,
        relation_type: str,
        source_project: str,
    ) -> bool:
        """建立關係（若不存在）。回傳 True 表示新建。"""
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
            weight=0.8,  # 自動連結權重略低於手動/公文佐證
            source_project=source_project,
            document_count=0,
        ))
        return True

    @staticmethod
    def _extract_section_name(parcel_name: str) -> Optional[str]:
        """從地段名稱擷取段名 (去掉地號)

        典型格式: "桃園市桃園區大興段0001-0000"
        擷取: "桃園市桃園區大興段"
        """
        match = re.match(r'^(.+?段)', parcel_name)
        return match.group(1) if match else None
