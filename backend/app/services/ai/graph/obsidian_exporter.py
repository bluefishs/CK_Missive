"""
Obsidian Vault Export Service

Exports the knowledge graph (CanonicalEntity + EntityRelationship + EntityAlias)
into an Obsidian-compatible Markdown vault with [[wiki links]] for auto-connection.

Version: 1.0.0
Created: 2026-04-08
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.knowledge_graph import (
    CanonicalEntity,
    EntityAlias,
    EntityRelationship,
)

logger = logging.getLogger(__name__)


def _sanitize_filename(name: str) -> str:
    """Remove/replace characters not valid in file names."""
    # Replace path separators and other problematic chars
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    # Collapse multiple underscores
    sanitized = re.sub(r"_{2,}", "_", sanitized)
    # Trim to reasonable length
    return sanitized[:200].strip("_. ")


async def export_vault(
    db: AsyncSession,
    output_dir: str,
    entity_types: Optional[List[str]] = None,
) -> Dict:
    """
    Export knowledge graph entities to Obsidian Markdown vault.

    Args:
        db: Async database session
        output_dir: Directory to write Markdown files
        entity_types: Optional filter for entity types (None = all)

    Returns:
        {"entities_exported": int, "files_created": int, "output_dir": str}
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Load entities
    entity_query = select(CanonicalEntity)
    if entity_types:
        entity_query = entity_query.where(
            CanonicalEntity.entity_type.in_(entity_types)
        )
    result = await db.execute(entity_query)
    entities = result.scalars().all()

    if not entities:
        return {"entities_exported": 0, "files_created": 0, "output_dir": output_dir}

    entity_ids = [e.id for e in entities]
    entity_map: Dict[int, CanonicalEntity] = {e.id: e for e in entities}

    # 2. Load aliases (batch)
    alias_result = await db.execute(
        select(EntityAlias).where(
            EntityAlias.canonical_entity_id.in_(entity_ids)
        )
    )
    aliases_by_entity: Dict[int, List[str]] = {}
    for alias in alias_result.scalars().all():
        aliases_by_entity.setdefault(alias.canonical_entity_id, []).append(
            alias.alias_name
        )

    # 3. Load relationships (batch) — outgoing from these entities
    rel_result = await db.execute(
        select(EntityRelationship).where(
            EntityRelationship.source_entity_id.in_(entity_ids),
            EntityRelationship.invalidated_at.is_(None),
        )
    )
    rels_by_source: Dict[int, List[EntityRelationship]] = {}
    for rel in rel_result.scalars().all():
        rels_by_source.setdefault(rel.source_entity_id, []).append(rel)

    # 4. Also load incoming relationships
    incoming_result = await db.execute(
        select(EntityRelationship).where(
            EntityRelationship.target_entity_id.in_(entity_ids),
            EntityRelationship.invalidated_at.is_(None),
        )
    )
    incoming_by_target: Dict[int, List[EntityRelationship]] = {}
    for rel in incoming_result.scalars().all():
        incoming_by_target.setdefault(rel.target_entity_id, []).append(rel)

    # 5. Generate Markdown files
    files_created = 0
    for entity in entities:
        entity_type_dir = out_path / _sanitize_filename(entity.entity_type)
        entity_type_dir.mkdir(parents=True, exist_ok=True)

        filename = _sanitize_filename(entity.canonical_name) + ".md"
        filepath = entity_type_dir / filename

        lines = [
            f"# {entity.canonical_name}",
            "",
            f"Type: {entity.entity_type}",
        ]

        if entity.first_seen_at:
            lines.append(f"First seen: {entity.first_seen_at}")
        lines.append(f"Mentions: {entity.mention_count or 0}")
        lines.append("")

        # Relationships (outgoing)
        outgoing = rels_by_source.get(entity.id, [])
        incoming = incoming_by_target.get(entity.id, [])
        if outgoing or incoming:
            lines.append("## Relationships")
            lines.append("")
            for rel in outgoing:
                target = entity_map.get(rel.target_entity_id)
                target_name = target.canonical_name if target else f"Entity#{rel.target_entity_id}"
                weight_str = f" (weight: {rel.weight})" if rel.weight else ""
                lines.append(
                    f"- [[{target_name}]] --- {rel.relation_type}{weight_str}"
                )
            for rel in incoming:
                source = entity_map.get(rel.source_entity_id)
                source_name = source.canonical_name if source else f"Entity#{rel.source_entity_id}"
                weight_str = f" (weight: {rel.weight})" if rel.weight else ""
                lines.append(
                    f"- [[{source_name}]] --- {rel.relation_type} (incoming){weight_str}"
                )
            lines.append("")

        # Aliases
        entity_aliases = aliases_by_entity.get(entity.id, [])
        if entity_aliases:
            lines.append("## Aliases")
            lines.append("")
            lines.append(f"- {', '.join(entity_aliases)}")
            lines.append("")

        filepath.write_text("\n".join(lines), encoding="utf-8")
        files_created += 1

    logger.info(
        "Obsidian vault exported: %d entities, %d files to %s",
        len(entities),
        files_created,
        output_dir,
    )

    return {
        "entities_exported": len(entities),
        "files_created": files_created,
        "output_dir": output_dir,
    }
