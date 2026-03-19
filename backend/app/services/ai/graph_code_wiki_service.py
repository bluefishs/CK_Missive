"""
Code Wiki 圖譜服務

從 graph_query_service.py 提取的程式碼圖譜相關方法：
- get_code_wiki_graph / _get_code_wiki_graph_uncached
- get_module_overview

Version: 1.0.0
Created: 2026-03-15
"""

import json
import logging
from typing import Optional

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    CanonicalEntity,
    EntityRelationship,
)
from .graph_helpers import _graph_cache

logger = logging.getLogger(__name__)


class GraphCodeWikiService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_code_wiki_graph(
        self,
        entity_types: Optional[list] = None,
        module_prefix: Optional[str] = None,
        limit: int = 500,
    ) -> dict:
        """取得 Code Wiki 代碼圖譜（nodes + edges），帶 Redis 快取"""
        try:
            types_key = ",".join(sorted(entity_types or ["py_module"]))
            cache_key = f"code_wiki:{types_key}:{module_prefix or ''}:{limit}"
            cached = await _graph_cache.get(cache_key)
            if cached:
                return json.loads(cached)

            result = await self._get_code_wiki_graph_uncached(entity_types, module_prefix, limit)
            await _graph_cache.set(cache_key, json.dumps(result, ensure_ascii=False), 600)
            return result
        except Exception as e:
            logger.error(f"get_code_wiki_graph failed: {e}")
            return {"nodes": [], "edges": []}

    async def get_module_overview(self) -> dict:
        """取得模組架構概覽：按 layer 分組統計 + DB ERD 資訊。

        回傳:
            layers: 各架構層模組清單與統計
            db_tables: 資料表 ERD 摘要
            summary: 總計數
        """
        from app.services.ai.code_graph_service import CODE_GRAPH_LABEL

        # 1. 載入所有模組實體
        mod_result = await self.db.execute(
            select(
                CanonicalEntity.id,
                CanonicalEntity.canonical_name,
                CanonicalEntity.entity_type,
                CanonicalEntity.description,
            ).where(CanonicalEntity.entity_type.in_(["py_module", "ts_module"]))
        )
        mod_rows = mod_result.all()

        # 2. 按 layer 分組
        layers: dict[str, dict] = {}
        for eid, ename, etype, desc_raw in mod_rows:
            desc = desc_raw
            if isinstance(desc, str):
                try:
                    desc = json.loads(desc)
                except (json.JSONDecodeError, TypeError):
                    desc = {}
            if not isinstance(desc, dict):
                desc = {}

            layer = desc.get("layer", "other")
            if layer not in layers:
                layers[layer] = {"modules": [], "total_lines": 0, "total_functions": 0}

            lines = desc.get("lines", 0) or 0
            func_count = (desc.get("function_count", 0) or 0) + (desc.get("method_count", 0) or 0)

            layers[layer]["modules"].append({
                "name": ename,
                "type": etype,
                "lines": lines,
                "functions": func_count,
                "outgoing_deps": desc.get("outgoing_deps", 0),
                "incoming_deps": desc.get("incoming_deps", 0),
            })
            layers[layer]["total_lines"] += lines
            layers[layer]["total_functions"] += func_count

        # 3. 載入 DB 表實體
        table_result = await self.db.execute(
            select(
                CanonicalEntity.canonical_name,
                CanonicalEntity.description,
            ).where(CanonicalEntity.entity_type == "db_table")
        )
        table_rows = table_result.all()

        db_tables = []
        for tname, desc_raw in table_rows:
            desc = desc_raw
            if isinstance(desc, str):
                try:
                    desc = json.loads(desc)
                except (json.JSONDecodeError, TypeError):
                    desc = {}
            if not isinstance(desc, dict):
                desc = {}

            columns = desc.get("columns", [])
            fks = desc.get("foreign_key_targets", [])
            db_tables.append({
                "name": tname,
                "columns": len(columns),
                "foreign_keys": fks,
                "indexes": desc.get("index_count", 0),
                "has_primary_key": desc.get("has_primary_key", False),
                "unique_constraints": desc.get("unique_constraints_count", 0),
            })

        # 4. 總關聯數
        rel_count_result = await self.db.execute(
            select(sa_func.count())
            .select_from(EntityRelationship)
            .where(EntityRelationship.relation_label == CODE_GRAPH_LABEL)
        )
        total_relations = rel_count_result.scalar() or 0

        return {
            "layers": layers,
            "db_tables": db_tables,
            "summary": {
                "total_modules": len(mod_rows),
                "total_tables": len(table_rows),
                "total_relations": total_relations,
            },
        }

    async def _get_code_wiki_graph_uncached(
        self,
        entity_types: Optional[list],
        module_prefix: Optional[str],
        limit: int,
    ) -> dict:
        """取得 Code Wiki 代碼圖譜（無快取）"""
        from app.services.ai.code_graph_service import CODE_ENTITY_TYPES, CODE_GRAPH_LABEL

        types = entity_types or ["py_module"]
        valid_types = [t for t in types if t in CODE_ENTITY_TYPES]
        if not valid_types:
            return {"nodes": [], "edges": []}

        # 查詢 code entities
        query = (
            select(CanonicalEntity)
            .where(CanonicalEntity.entity_type.in_(valid_types))
        )
        if module_prefix:
            import re
            safe_prefix = re.sub(r'([%_\\])', r'\\\1', module_prefix)
            query = query.where(CanonicalEntity.canonical_name.like(f"{safe_prefix}%"))
        query = query.order_by(CanonicalEntity.canonical_name).limit(limit)

        entities_result = await self.db.execute(query)
        entities = entities_result.scalars().all()
        node_ids = {e.id for e in entities}

        if not node_ids:
            return {"nodes": [], "edges": []}

        # 查詢 code graph 關聯（source 和 target 都在 node_ids 中）
        edges_result = await self.db.execute(
            select(EntityRelationship)
            .where(
                EntityRelationship.relation_label == CODE_GRAPH_LABEL,
                EntityRelationship.source_entity_id.in_(node_ids),
                EntityRelationship.target_entity_id.in_(node_ids),
                EntityRelationship.invalidated_at.is_(None),
            )
        )

        nodes = [
            {
                "id": str(e.id),
                "type": e.entity_type,
                "label": e.canonical_name.split("::")[-1] if "::" in e.canonical_name else e.canonical_name.split(".")[-1],
                "category": e.canonical_name,
                "mention_count": e.mention_count,
            }
            for e in entities
        ]

        edges = [
            {
                "source": str(rel.source_entity_id),
                "target": str(rel.target_entity_id),
                "label": rel.relation_type,
                "type": rel.relation_type,
                "weight": rel.weight,
            }
            for rel in edges_result.scalars().all()
        ]

        return {"nodes": nodes, "edges": edges}
