"""Diff 影響分析服務 — 分析 git diff 受影響的 service/endpoint/schema

Inspired by Understand-Anything's diff impact analysis concept.

Version: 1.0.0
Created: 2026-03-30
"""
import logging
import subprocess
from pathlib import Path
from typing import List, Dict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.extended.models.knowledge_graph import CanonicalEntity, EntityRelationship

logger = logging.getLogger(__name__)


class DiffImpactAnalyzer:
    """分析程式碼變更的影響範圍"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_diff(self, base_ref: str = "HEAD~1") -> dict:
        """分析 git diff 受影響的元件"""
        # 1. Get changed files from git
        project_root = str(Path(__file__).resolve().parents[5])
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", base_ref, "HEAD"],
                capture_output=True, text=True, cwd=project_root,
                timeout=10,
            )
            changed_files = [
                f.strip() for f in result.stdout.strip().split("\n") if f.strip()
            ]
        except Exception as e:
            logger.error(f"Git diff failed: {e}")
            return {"error": str(e)}

        if not changed_files:
            return {"changed_files": [], "affected": {}, "summary": "No changes"}

        # 2. Map changed files to code entities
        affected_entities: List[Dict] = []
        for f in changed_files:
            module_name = (
                f.replace("/", ".")
                .replace("\\", ".")
                .replace(".py", "")
                .replace(".ts", "")
                .replace(".tsx", "")
            )
            # Extract short module name for matching (last 2 segments)
            parts = module_name.split(".")
            short_name = ".".join(parts[-2:]) if len(parts) >= 2 else module_name

            # Find entities that belong to this module
            entities = (
                await self.db.execute(
                    select(CanonicalEntity)
                    .where(CanonicalEntity.canonical_name.ilike(f"%{short_name}%"))
                    .limit(20)
                )
            ).scalars().all()
            for e in entities:
                if e.id not in [ae["id"] for ae in affected_entities]:
                    affected_entities.append({
                        "id": e.id,
                        "name": e.canonical_name,
                        "type": e.entity_type,
                    })

        # 3. Find downstream dependents (who uses these entities)
        entity_ids = [e["id"] for e in affected_entities]
        downstream: List[Dict] = []
        if entity_ids:
            rels = (
                await self.db.execute(
                    select(EntityRelationship, CanonicalEntity)
                    .join(
                        CanonicalEntity,
                        EntityRelationship.source_entity_id == CanonicalEntity.id,
                    )
                    .where(
                        EntityRelationship.target_entity_id.in_(entity_ids),
                        EntityRelationship.relation_type.in_([
                            "uses_service", "uses_repository", "depends_on",
                            "validates_with", "imports", "calls",
                        ]),
                    )
                    .limit(50)
                )
            ).all()
            for rel, src_entity in rels:
                downstream.append({
                    "entity": src_entity.canonical_name,
                    "type": src_entity.entity_type,
                    "relation": rel.relation_type,
                    "depends_on": next(
                        (
                            e["name"]
                            for e in affected_entities
                            if e["id"] == rel.target_entity_id
                        ),
                        "unknown",
                    ),
                })

        # 4. Categorize
        by_type: Dict[str, List[str]] = {}
        for e in affected_entities:
            t = e["type"]
            by_type.setdefault(t, []).append(e["name"])

        return {
            "changed_files": changed_files[:20],
            "affected_entities": len(affected_entities),
            "affected_by_type": {k: len(v) for k, v in by_type.items()},
            "downstream_dependents": len(downstream),
            "downstream": downstream[:20],
            "summary": (
                f"{len(changed_files)} files changed, "
                f"{len(affected_entities)} entities affected, "
                f"{len(downstream)} downstream dependents"
            ),
        }
