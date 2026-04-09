"""Code Wiki Auto-Generator — AST + Gemma 4 → zero-maintenance code documentation.

Reads code graph entities (modules, classes, functions) and generates
human-readable wiki pages with Gemma 4 semantic understanding.

Version: 1.0.0
Created: 2026-04-05
"""

import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.knowledge_graph import CanonicalEntity, EntityRelationship
from app.services.ai.graph.graph_helpers import _graph_cache

logger = logging.getLogger(__name__)

# Cache TTL for wiki pages (10 minutes)
_WIKI_CACHE_TTL = 600


def _parse_description(raw: Any) -> dict:
    """Safely parse entity description (may be JSON str or dict)."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    return {}


class CodeWikiGenerator:
    """Generate code wiki from code graph entities + Gemma 4."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_module_wiki(self, module_name: str) -> dict:
        """Generate wiki page for a single module.

        Returns: {"module": str, "description": str, "classes": [...],
                  "functions": [...], "dependencies": [...], "wiki_markdown": str}
        """
        if not module_name or not module_name.strip():
            return {"module": module_name, "error": "Module name is required"}

        # Check cache first
        cache_key = f"code_wiki:module:{module_name}"
        cached = await _graph_cache.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except (json.JSONDecodeError, TypeError):
                pass

        # 1. Fetch module entity
        result = await self.db.execute(
            select(CanonicalEntity)
            .where(CanonicalEntity.canonical_name == module_name)
            .where(
                CanonicalEntity.entity_type.in_(
                    ["py_module", "ts_module", "service", "repository"]
                )
            )
        )
        module_entity = result.scalar_one_or_none()
        if not module_entity:
            return {"module": module_name, "error": "Module not found in code graph"}

        # 2. Fetch child entities (classes, functions)
        children_result = await self.db.execute(
            select(CanonicalEntity)
            .join(
                EntityRelationship,
                EntityRelationship.target_entity_id == CanonicalEntity.id,
            )
            .where(EntityRelationship.source_entity_id == module_entity.id)
            .where(
                EntityRelationship.relation_type.in_(
                    ["defines_class", "defines_function", "has_method"]
                )
            )
            .where(EntityRelationship.invalidated_at.is_(None))
        )
        children = children_result.scalars().all()

        classes = [c for c in children if c.entity_type == "py_class"]
        functions = [f for f in children if f.entity_type in ("py_function", "ts_hook")]

        # 3. Fetch dependencies (imports)
        deps_result = await self.db.execute(
            select(CanonicalEntity.canonical_name)
            .join(
                EntityRelationship,
                EntityRelationship.target_entity_id == CanonicalEntity.id,
            )
            .where(EntityRelationship.source_entity_id == module_entity.id)
            .where(EntityRelationship.relation_type == "imports")
            .where(EntityRelationship.invalidated_at.is_(None))
        )
        dependencies = [r[0] for r in deps_result.all()]

        # 4. Generate wiki with Gemma 4
        desc = _parse_description(module_entity.description)
        class_names = [c.canonical_name.split("::")[-1] for c in classes]
        func_names = [
            f.canonical_name.split("::")[-1]
            for f in functions
            if not f.canonical_name.split("::")[-1].startswith("_")
        ]

        wiki_md = await self._generate_wiki_markdown(
            module_name=module_name,
            desc=desc,
            class_names=class_names,
            func_names=func_names,
            dependencies=dependencies,
        )

        result_data = {
            "module": module_name,
            "file_path": desc.get("file_path"),
            "lines": desc.get("lines"),
            "classes": class_names,
            "functions": func_names,
            "dependencies": dependencies[:20],
            "wiki_markdown": wiki_md,
        }

        # Cache the result
        try:
            await _graph_cache.set(
                cache_key,
                json.dumps(result_data, ensure_ascii=False),
                _WIKI_CACHE_TTL,
            )
        except Exception:
            logger.debug("Failed to cache wiki for %s", module_name)

        return result_data

    async def _generate_wiki_markdown(
        self,
        module_name: str,
        desc: dict,
        class_names: List[str],
        func_names: List[str],
        dependencies: List[str],
    ) -> str:
        """Call Gemma 4 to generate wiki markdown for a module."""
        from app.core.ai_connector import get_ai_connector

        ai = get_ai_connector()

        prompt = (
            f"為以下 Python 模組生成 Markdown 文檔：\n\n"
            f"模組: {module_name}\n"
            f"路徑: {desc.get('file_path', 'unknown')}\n"
            f"行數: {desc.get('lines', '?')}\n"
            f"類別: {', '.join(class_names) if class_names else '無'}\n"
            f"函數: {', '.join(func_names[:10]) if func_names else '無'}\n"
            f"依賴: {', '.join(dependencies[:10]) if dependencies else '無'}\n"
            f"文檔字串: {(desc.get('docstring') or '')[:300]}\n\n"
            "生成格式:\n"
            "# {模組名}\n\n## 概述\n2-3句描述\n\n"
            "## 主要類別\n列點\n\n## 公開函數\n列點\n\n## 依賴關係\n列點"
        )

        try:
            wiki_md = await ai.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=512,
                task_type="summary",
            )
            return wiki_md
        except Exception as e:
            logger.warning("Wiki generation failed for %s: %s", module_name, e)
            return f"# {module_name}\n\n*Wiki 自動生成失敗*"

    async def generate_overview(self, limit: int = 50) -> dict:
        """Generate overview wiki of the top modules by size/relations."""
        # Check cache
        cache_key = f"code_wiki:overview:{limit}"
        cached = await _graph_cache.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except (json.JSONDecodeError, TypeError):
                pass

        # Top modules by relation count
        result = await self.db.execute(
            select(
                CanonicalEntity.canonical_name,
                CanonicalEntity.entity_type,
                CanonicalEntity.description,
                func.count(EntityRelationship.id).label("rel_count"),
            )
            .outerjoin(
                EntityRelationship,
                EntityRelationship.source_entity_id == CanonicalEntity.id,
            )
            .where(
                CanonicalEntity.entity_type.in_(
                    ["py_module", "ts_module", "service", "repository"]
                )
            )
            .group_by(
                CanonicalEntity.id,
                CanonicalEntity.canonical_name,
                CanonicalEntity.entity_type,
                CanonicalEntity.description,
            )
            .order_by(func.count(EntityRelationship.id).desc())
            .limit(limit)
        )

        modules = []
        for row in result.all():
            desc = _parse_description(row[2])
            modules.append(
                {
                    "name": row[0],
                    "type": row[1],
                    "file_path": desc.get("file_path"),
                    "lines": desc.get("lines", 0),
                    "relations": row[3],
                    "docstring": (desc.get("docstring") or "")[:100],
                }
            )

        overview = {"modules": modules, "total": len(modules)}

        # Cache
        try:
            await _graph_cache.set(
                cache_key,
                json.dumps(overview, ensure_ascii=False),
                _WIKI_CACHE_TTL,
            )
        except Exception:
            logger.debug("Failed to cache wiki overview")

        return overview
