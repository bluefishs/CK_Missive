"""
跨專案實體自動連結服務 (Cross-Domain Entity Linker)

在聯邦貢獻完成後，自動偵測不同來源專案間可連結的實體，
建立跨域關係 (contracted_by, located_at, part_of_project, commissioned_by)。

連結規則：
1. Contractor bridging: Tunnel contractor ↔ Missive org (fuzzy ≥ 0.85)
2. Location bridging: Missive location ↔ LvrLand land_parcel (section name)
3. Project bridging: Missive project ↔ Tunnel tunnel (name similarity ≥ 0.80)
4. Agency bridging: Missive org (with linked_agency_id) ↔ Tunnel inspection

匹配引擎已拆分至 cross_domain_matcher.py (trigram + 語意向量回退)。

Version: 2.0.0 — refactored from 554L monolith
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import CanonicalEntity
from app.services.ai.domain.cross_domain_matcher import CrossDomainMatchEngine

logger = logging.getLogger(__name__)

# 模糊匹配閾值
CONTRACTOR_THRESHOLD = 0.85
PROJECT_THRESHOLD = 0.80
LOCATION_THRESHOLD = 0.75
AGENCY_THRESHOLD = 0.85
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

    v2.1.0: 新增 Gemma 4 語意匹配 — 模糊分數落在 0.4-0.7 模糊區間時
    透過 LLM 判斷兩實體是否為同一事物。
    """

    # Ambiguous fuzzy score range — triggers Gemma 4 semantic judgment
    AMBIGUOUS_LOW = 0.4
    AMBIGUOUS_HIGH = 0.7

    def __init__(self, db: AsyncSession):
        self.db = db
        self.matcher = CrossDomainMatchEngine(db)

    async def _semantic_match_score(
        self, entity_a: dict, entity_b: dict,
    ) -> float:
        """Gemma 4 semantic matching for cross-domain entity pairs.

        Used when fuzzy string matching is inconclusive (0.4-0.7 range).
        Returns confidence score 0.0-1.0 if entities are the same, else 0.0.
        """
        try:
            from app.core.ai_connector import get_ai_connector
            ai = get_ai_connector()
            prompt = (
                "判斷以下兩個實體是否指同一事物：\n"
                f"A: {entity_a.get('name', '')} (類型: {entity_a.get('type', '')}, "
                f"來源: {entity_a.get('source', '')})\n"
                f"B: {entity_b.get('name', '')} (類型: {entity_b.get('type', '')}, "
                f"來源: {entity_b.get('source', '')})\n\n"
                '回覆 JSON: {"is_same": true/false, "confidence": 0.0-1.0, "reason": "..."}'
            )
            result = await ai.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0, max_tokens=80, task_type="classify",
            )
            from app.services.ai.core.agent_utils import parse_json_safe
            parsed = parse_json_safe(result)
            if parsed and parsed.get("is_same"):
                return float(parsed.get("confidence", 0.0))
            return 0.0
        except Exception:
            return 0.0

    async def enhanced_find_best_match(
        self,
        name: str,
        candidates: List[CanonicalEntity],
        threshold: float,
        source_project: str = "",
    ) -> tuple:
        """Enhanced matching: trigram first, then Gemma 4 for ambiguous cases.

        When the best fuzzy score falls in the ambiguous range (0.4-0.7),
        Gemma 4 is used to make a semantic judgment.

        Returns: (best_entity, best_score) or (None, 0.0)
        """
        from app.services.ai.graph.canonical_entity_matcher import CanonicalEntityMatcher

        if not candidates or not name:
            return None, 0.0

        # Collect all scores
        scored: list[tuple[CanonicalEntity, float]] = []
        for candidate in candidates:
            score = CanonicalEntityMatcher.compute_similarity(
                name, candidate.canonical_name,
            )
            scored.append((candidate, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        if not scored:
            return None, 0.0

        best_candidate, best_score = scored[0]

        # Clear match above threshold — use directly
        if best_score >= threshold:
            if not CanonicalEntityMatcher.is_false_fuzzy_match(
                name, best_candidate.canonical_name,
            ):
                return best_candidate, best_score

        # Ambiguous range — ask Gemma 4
        if self.AMBIGUOUS_LOW <= best_score <= self.AMBIGUOUS_HIGH:
            entity_a = {"name": name, "type": "unknown", "source": source_project}
            entity_b = {
                "name": best_candidate.canonical_name,
                "type": best_candidate.entity_type or "",
                "source": best_candidate.source_project or "",
            }
            llm_score = await self._semantic_match_score(entity_a, entity_b)
            if llm_score >= 0.7:
                logger.info(
                    "Gemma 4 semantic match: '%s' ↔ '%s' (fuzzy=%.2f, llm=%.2f)",
                    name, best_candidate.canonical_name, best_score, llm_score,
                )
                return best_candidate, llm_score

        # Fall through to matcher's original pipeline (includes semantic vector fallback)
        return await self.matcher.find_best_match(
            name, candidates, threshold=threshold,
        )

    async def link_after_contribution(
        self, source_project: str,
    ) -> LinkingReport:
        """對指定來源專案的實體執行對應的橋接規則。"""
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
        """執行所有跨域連結規則（全量掃描）。"""
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
    # -----------------------------------------------------------------------

    async def _rule_contractor_bridging(self, report: LinkingReport) -> None:
        """Tunnel 承包商 ↔ Missive 機關/公司 模糊匹配 → contracted_by"""
        tunnel_contractors = await self.matcher.get_entities("contractor", "ck-tunnel")
        if not tunnel_contractors:
            return

        missive_orgs = await self.matcher.get_entities("org", "ck-missive")
        if not missive_orgs:
            return

        for contractor in tunnel_contractors:
            best_match, best_score = await self.enhanced_find_best_match(
                contractor.canonical_name, missive_orgs,
                threshold=CONTRACTOR_THRESHOLD,
                source_project="ck-tunnel",
            )
            if best_match is not None:
                created = await self.matcher.create_relation_if_absent(
                    contractor.id, best_match.id, "contracted_by", "ck-tunnel",
                )
                report.details.append(LinkResult(
                    source_id=contractor.id, target_id=best_match.id,
                    relation_type="contracted_by",
                    source_name=contractor.canonical_name,
                    target_name=best_match.canonical_name,
                    similarity=best_score, bridge_type="contractor",
                ))
                if created:
                    report.links_created += 1
                    logger.info("Contractor bridge: %s ↔ %s (%.2f)",
                                contractor.canonical_name, best_match.canonical_name, best_score)
                else:
                    report.links_skipped += 1

    # -----------------------------------------------------------------------
    # Rule 2: Location bridging
    # -----------------------------------------------------------------------

    async def _rule_location_bridging(self, report: LinkingReport) -> None:
        """Missive 地點 ↔ LvrLand 地段 名稱匹配 → located_at"""
        missive_locations = await self.matcher.get_entities("location", "ck-missive")
        if not missive_locations:
            return

        lvrland_parcels = await self.matcher.get_entities("land_parcel", "ck-lvrland")
        if not lvrland_parcels:
            return

        # 建立段名索引
        section_index: Dict[str, List[CanonicalEntity]] = {}
        for parcel in lvrland_parcels:
            section = self.matcher.extract_section_name(parcel.canonical_name)
            if section:
                section_index.setdefault(section, []).append(parcel)

        for location in missive_locations:
            loc_name = location.canonical_name
            matched = False

            for section, parcels in section_index.items():
                if section in loc_name or loc_name in section:
                    parcel = parcels[0]
                    created = await self.matcher.create_relation_if_absent(
                        location.id, parcel.id, "located_at", "ck-lvrland",
                    )
                    report.details.append(LinkResult(
                        source_id=location.id, target_id=parcel.id,
                        relation_type="located_at",
                        source_name=loc_name, target_name=parcel.canonical_name,
                        similarity=0.90, bridge_type="location",
                    ))
                    if created:
                        report.links_created += 1
                        logger.info("Location bridge: %s → %s", loc_name, parcel.canonical_name)
                    else:
                        report.links_skipped += 1
                    matched = True
                    break

            if not matched:
                best_match, best_score = await self.enhanced_find_best_match(
                    loc_name, lvrland_parcels,
                    threshold=LOCATION_THRESHOLD,
                    source_project="ck-lvrland",
                )
                if best_match is not None:
                    created = await self.matcher.create_relation_if_absent(
                        location.id, best_match.id, "located_at", "ck-lvrland",
                    )
                    report.details.append(LinkResult(
                        source_id=location.id, target_id=best_match.id,
                        relation_type="located_at",
                        source_name=loc_name, target_name=best_match.canonical_name,
                        similarity=best_score, bridge_type="location",
                    ))
                    if created:
                        report.links_created += 1
                    else:
                        report.links_skipped += 1

    # -----------------------------------------------------------------------
    # Rule 3: Project bridging
    # -----------------------------------------------------------------------

    async def _rule_project_bridging(self, report: LinkingReport) -> None:
        """Missive 專案 ↔ Tunnel 隧道 名稱相似度匹配 → part_of_project"""
        missive_projects = await self.matcher.get_entities("project", "ck-missive")
        if not missive_projects:
            return

        tunnel_tunnels = await self.matcher.get_entities("tunnel", "ck-tunnel")
        if not tunnel_tunnels:
            return

        for tunnel in tunnel_tunnels:
            best_match, best_score = await self.enhanced_find_best_match(
                tunnel.canonical_name, missive_projects,
                threshold=PROJECT_THRESHOLD,
                source_project="ck-tunnel",
            )
            if best_match is not None:
                created = await self.matcher.create_relation_if_absent(
                    tunnel.id, best_match.id, "part_of_project", "ck-tunnel",
                )
                report.details.append(LinkResult(
                    source_id=tunnel.id, target_id=best_match.id,
                    relation_type="part_of_project",
                    source_name=tunnel.canonical_name,
                    target_name=best_match.canonical_name,
                    similarity=best_score, bridge_type="project",
                ))
                if created:
                    report.links_created += 1
                    logger.info("Project bridge: %s → %s (%.2f)",
                                tunnel.canonical_name, best_match.canonical_name, best_score)
                else:
                    report.links_skipped += 1

    # -----------------------------------------------------------------------
    # Rule 4: Agency bridging
    # -----------------------------------------------------------------------

    async def _rule_agency_bridging(self, report: LinkingReport) -> None:
        """Missive 機關 (linked_agency_id) ↔ Tunnel inspection → commissioned_by"""
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

        tunnel_inspections = await self.matcher.get_entities("inspection", "ck-tunnel")
        if not tunnel_inspections:
            return

        for inspection in tunnel_inspections:
            meta = inspection.external_meta or {}
            commissioning = meta.get("commissioning_agency", "") or inspection.canonical_name

            best_match, best_score = await self.enhanced_find_best_match(
                commissioning, linked_orgs,
                threshold=AGENCY_THRESHOLD,
                source_project="ck-tunnel",
            )
            if best_match is not None:
                created = await self.matcher.create_relation_if_absent(
                    inspection.id, best_match.id, "commissioned_by", "ck-tunnel",
                )
                report.details.append(LinkResult(
                    source_id=inspection.id, target_id=best_match.id,
                    relation_type="commissioned_by",
                    source_name=inspection.canonical_name,
                    target_name=best_match.canonical_name,
                    similarity=best_score, bridge_type="agency",
                ))
                if created:
                    report.links_created += 1
                    logger.info("Agency bridge: %s → %s (%.2f)",
                                inspection.canonical_name, best_match.canonical_name, best_score)
                else:
                    report.links_skipped += 1
