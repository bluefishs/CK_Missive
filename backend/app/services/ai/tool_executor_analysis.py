"""
分析/查詢類工具執行器

包含工具：
- get_entity_detail: 實體詳情
- get_statistics: 圖譜統計
- get_system_health: 系統健康報告
- navigate_graph: 3D 知識圖譜導航
- summarize_entity: 實體摘要簡報
- draw_diagram: Mermaid 圖表生成
- explore_entity_path: 圖譜路徑探索

Extracted from agent_tools.py v1.3.0
"""

import logging
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# LLM 自然語言 entity_type → DB 欄位值對照（與 search executor 共用）
ENTITY_TYPE_MAP = {
    "organization": "org", "organisation": "org", "機關": "org",
    "人員": "person", "人": "person",
    "專案": "project", "案件": "project",
    "地點": "location", "地址": "location",
    "日期": "date", "時間": "date",
    # Code Graph (v1.80.0)
    "模組": "py_module", "module": "py_module",
    "類別": "py_class", "class": "py_class",
    "函數": "py_function", "function": "py_function", "方法": "py_function",
    "資料表": "db_table", "table": "db_table",
}


class AnalysisToolExecutor:
    """分析/查詢類工具執行器"""

    # D1: 模組層級快取 er-model.json（避免每次工具呼叫重讀磁碟）
    _er_model_cache: Dict[str, Any] | None = None
    _er_model_loaded: bool = False

    def __init__(self, db: AsyncSession, ai_connector, embedding_mgr, config):
        self.db = db
        self.ai = ai_connector
        self.embedding_mgr = embedding_mgr
        self.config = config
        if not AnalysisToolExecutor._er_model_loaded:
            self._load_er_model_cache()

    @classmethod
    def _load_er_model_cache(cls) -> None:
        """載入 er-model.json 到類別層級快取"""
        import json as json_mod
        from pathlib import Path
        er_path = Path(__file__).resolve().parents[3] / "docs" / "er-model.json"
        if er_path.exists():
            try:
                cls._er_model_cache = json_mod.loads(er_path.read_text(encoding="utf-8"))
            except Exception:
                cls._er_model_cache = None
        cls._er_model_loaded = True

    async def get_entity_detail(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """取得實體詳情"""
        from app.services.ai.graph_query_service import GraphQueryService

        entity_id = params.get("entity_id")
        if not entity_id:
            return {"error": "缺少 entity_id 參數", "count": 0}

        svc = GraphQueryService(self.db)
        detail = await svc.get_entity_detail(int(entity_id))

        if not detail:
            return {"error": f"找不到實體 ID={entity_id}", "count": 0}

        return {
            "entity": detail,
            "count": 1,
            "documents": detail.get("documents", []),
            "relationships": detail.get("relationships", []),
        }

    async def get_statistics(self, _params: Dict[str, Any]) -> Dict[str, Any]:
        """取得圖譜統計 + 高頻實體"""
        from app.services.ai.graph_query_service import GraphQueryService

        svc = GraphQueryService(self.db)
        stats = await svc.get_graph_stats()
        top_entities = await svc.get_top_entities(limit=10)

        return {
            "stats": stats,
            "top_entities": top_entities,
            "count": 1,
        }

    async def get_system_health_report(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """取得系統健康報告（乾坤智能體專用）"""
        from app.services.system_health_service import SystemHealthService

        svc = SystemHealthService(self.db)
        summary = await svc.build_summary()

        # 可選：效能基準測試
        if params.get("include_benchmarks"):
            try:
                benchmarks = await svc.run_performance_benchmarks()
                summary["benchmarks"] = benchmarks
                recommendations = svc.get_performance_recommendations(benchmarks)
                summary["recommendations"] = recommendations
            except Exception as e:
                summary["benchmarks"] = {"error": str(e)}

        return {"summary": summary, "count": 1}

    async def navigate_graph(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """導航 Agent — 搜尋實體並回傳叢集資訊供前端 fly-to"""
        from app.services.ai.graph_query_service import GraphQueryService

        svc = GraphQueryService(self.db)
        query = params.get("query", "")
        entity_type = params.get("entity_type")
        expand = params.get("expand_neighbors", True)

        if entity_type:
            entity_type = ENTITY_TYPE_MAP.get(entity_type.lower(), entity_type)

        # 搜尋實體
        entities = await svc.search_entities(query, entity_type=entity_type, limit=10)
        if not entities:
            return {"error": f"找不到與「{query}」相關的實體", "count": 0}

        # 取得每個實體的鄰居（展開叢集）
        cluster_nodes = []
        for entity in entities:
            node = {
                "id": entity.get("id"),
                "name": entity.get("name", ""),
                "type": entity.get("entity_type", ""),
                "mention_count": entity.get("mention_count", 0),
            }
            cluster_nodes.append(node)

            if expand and entity.get("id"):
                neighbors = await svc.get_neighbors(int(entity["id"]), max_hops=1, limit=5)
                for n in neighbors.get("neighbors", []):
                    cluster_nodes.append({
                        "id": n.get("id"),
                        "name": n.get("name", ""),
                        "type": n.get("entity_type", ""),
                        "mention_count": n.get("mention_count", 0),
                        "relation": n.get("relation_type", ""),
                    })

        # 去重
        seen_ids = set()
        unique_nodes = []
        for node in cluster_nodes:
            nid = node.get("id")
            if nid and nid not in seen_ids:
                seen_ids.add(nid)
                unique_nodes.append(node)

        return {
            "cluster_nodes": unique_nodes,
            "center_entity": entities[0] if entities else None,
            "count": len(unique_nodes),
            "action": "navigate",
            "highlight_ids": [str(e.get("id")) for e in entities],
        }

    async def summarize_entity(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """摘要 Agent — 生成實體簡報（上下游關係 + 時間軸 + LLM 摘要）"""
        from app.services.ai.graph_query_service import GraphQueryService

        entity_id = params.get("entity_id")
        if not entity_id:
            return {"error": "缺少 entity_id 參數", "count": 0}

        svc = GraphQueryService(self.db)
        entity_id = int(entity_id)

        # 取得實體詳情
        detail = await svc.get_entity_detail(entity_id)
        if not detail:
            return {"error": f"找不到實體 ID={entity_id}", "count": 0}

        include_timeline = params.get("include_timeline", True)
        include_upstream = params.get("include_upstream_downstream", True)

        result: Dict[str, Any] = {
            "entity": {
                "id": entity_id,
                "name": detail.get("name", ""),
                "type": detail.get("entity_type", ""),
                "aliases": detail.get("aliases", []),
                "mention_count": detail.get("mention_count", 0),
            },
            "count": 1,
        }

        # 時間軸
        if include_timeline:
            timeline = await svc.get_entity_timeline(entity_id)
            result["timeline"] = timeline

        # 上下游關係分析
        if include_upstream:
            relationships = detail.get("relationships", [])
            upstream = []   # 指向此實體的（誰 → 它）
            downstream = []  # 此實體指向的（它 → 誰）
            for rel in relationships:
                if rel.get("direction") == "outgoing":
                    downstream.append({
                        "entity_name": rel.get("target_name", ""),
                        "entity_type": rel.get("target_type", ""),
                        "relation": rel.get("relation_type", ""),
                        "weight": rel.get("weight", 1),
                    })
                else:
                    upstream.append({
                        "entity_name": rel.get("source_name", ""),
                        "entity_type": rel.get("source_type", ""),
                        "relation": rel.get("relation_type", ""),
                        "weight": rel.get("weight", 1),
                    })
            result["upstream"] = upstream
            result["downstream"] = downstream

        # 關聯公文
        result["documents"] = detail.get("documents", [])[:10]

        # LLM 摘要生成
        try:
            summary_text = self._build_entity_summary_prompt(detail, result)
            summary = await self.ai.chat_completion(
                messages=[
                    {"role": "system", "content": "你是公文管理系統的智能助理。請根據提供的實體資訊生成一段簡潔的中文摘要簡報（200字以內），重點包含：該實體的角色定位、主要關聯、關鍵事件時間軸。"},
                    {"role": "user", "content": summary_text},
                ],
                temperature=0.3,
                max_tokens=500,
                task_type="summary",
            )
            result["summary"] = summary
        except Exception as e:
            logger.warning("Entity summary LLM call failed: %s", e)
            result["summary"] = f"{detail.get('name', '')} 為 {detail.get('entity_type', '')} 類型實體，共被 {detail.get('mention_count', 0)} 篇公文提及。"

        return result

    @staticmethod
    def _build_entity_summary_prompt(detail: Dict, result: Dict) -> str:
        """組合實體摘要 prompt"""
        parts = [
            f"實體名稱：{detail.get('name', '')}",
            f"類型：{detail.get('entity_type', '')}",
            f"別名：{', '.join(detail.get('aliases', [])[:5])}",
            f"提及次數：{detail.get('mention_count', 0)}",
        ]
        if result.get("upstream"):
            parts.append(f"上游關聯：{', '.join(u['entity_name'] for u in result['upstream'][:5])}")
        if result.get("downstream"):
            parts.append(f"下游關聯：{', '.join(d['entity_name'] for d in result['downstream'][:5])}")
        if result.get("documents"):
            parts.append("關聯公文：")
            for doc in result["documents"][:5]:
                parts.append(f"  - {doc.get('doc_number', '')} {doc.get('subject', '')}")
        if result.get("timeline"):
            parts.append(f"時間軸：共 {len(result['timeline'])} 個事件")
        return "\n".join(parts)

    async def draw_diagram(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool #9: Generate Mermaid diagram based on query context."""
        diagram_type = params.get("diagram_type", "auto")
        scope = params.get("scope", "")
        detail_level = params.get("detail_level", "normal")

        # D1: 使用類別層級快取，避免每次讀磁碟
        er_data = AnalysisToolExecutor._er_model_cache

        # Auto-detect diagram type
        if diagram_type == "auto":
            scope_lower = scope.lower()
            if any(kw in scope_lower for kw in ["table", "db", "資料", "er", "schema"]):
                diagram_type = "erDiagram"
            elif any(kw in scope_lower for kw in ["flow", "流程", "步驟", "pipeline"]):
                diagram_type = "flowchart"
            elif any(kw in scope_lower for kw in ["module", "模組", "import", "依賴", "架構"]):
                diagram_type = "graph"
            elif any(kw in scope_lower for kw in ["class", "類別", "繼承"]):
                diagram_type = "classDiagram"
            else:
                diagram_type = "erDiagram"  # default to ER

        lines: List[str] = []
        title = ""
        description = ""

        from app.services.ai.agent_diagram_builder import (
            build_er_diagram, build_dependency_graph, build_flowchart, build_class_diagram,
        )

        if diagram_type == "erDiagram" and er_data:
            title, description, lines = build_er_diagram(er_data, scope, detail_level)
        elif diagram_type == "graph":
            title, description, lines = await build_dependency_graph(self.db, scope, detail_level)
        elif diagram_type == "flowchart":
            title, description, lines = await build_flowchart(scope, ai_connector=self.ai)
        elif diagram_type == "classDiagram":
            title, description, lines = await build_class_diagram(self.db, scope, detail_level)
        else:
            # Fallback ER
            if er_data:
                title, description, lines = build_er_diagram(er_data, scope, detail_level)
            else:
                return {"mermaid": "", "title": "無法生成圖表", "description": "找不到 ER 模型資料"}

        mermaid_str = "\n".join(lines)

        # B8: 提取圖中涉及的實體名稱供前端圖譜高亮
        related_entities: List[str] = []
        for line in lines:
            stripped = line.strip()
            # ER: "    table_name {" → extract table_name
            if stripped.endswith("{") and not stripped.startswith("erDiagram"):
                related_entities.append(stripped.rstrip(" {").strip())
            # Dependency graph: "    module_name[" or quoted labels
            elif "[" in stripped and "-->" not in stripped and "graph" not in stripped:
                name = stripped.split("[")[0].strip()
                if name:
                    related_entities.append(name)

        return {
            "mermaid": mermaid_str,
            "title": title,
            "description": description,
            "diagram_type": diagram_type,
            "related_entities": related_entities,
        }

    async def explore_entity_path(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """探索兩實體間的知識圖譜最短路徑"""
        from app.services.ai.graph_query_service import GraphQueryService
        from app.extended.models import CanonicalEntity
        from sqlalchemy import select, func

        entity_a = params.get("entity_a", "")
        entity_b = params.get("entity_b", "")
        max_hops = min(int(params.get("max_hops", 3)), 6)

        if not entity_a or not entity_b:
            return {"error": "需要提供 entity_a 和 entity_b 參數", "count": 0}

        try:
            # 解析實體：支援 ID 或名稱
            async def resolve_entity(value: str) -> int | None:
                if value.isdigit():
                    return int(value)
                # 模糊名稱搜尋
                result = await self.db.execute(
                    select(CanonicalEntity.id)
                    .where(
                        func.lower(CanonicalEntity.canonical_name)
                        .contains(value.lower())
                    )
                    .limit(1)
                )
                row = result.scalar_one_or_none()
                return row

            source_id = await resolve_entity(str(entity_a))
            target_id = await resolve_entity(str(entity_b))

            if not source_id:
                return {"error": f"找不到實體: {entity_a}", "count": 0}
            if not target_id:
                return {"error": f"找不到實體: {entity_b}", "count": 0}
            if source_id == target_id:
                return {"error": "起始和目標實體相同", "count": 0}

            svc = GraphQueryService(self.db)
            path_result = await svc.find_shortest_path(source_id, target_id, max_hops)

            if not path_result:
                return {
                    "found": False,
                    "message": f"在 {max_hops} 步內找不到 {entity_a} → {entity_b} 的路徑",
                    "count": 0,
                }

            return {
                "found": True,
                "depth": path_result["depth"],
                "path": path_result["path"],
                "relations": path_result["relations"],
                "count": 1,
            }
        except Exception as e:
            logger.error("explore_entity_path failed: %s", e)
            return {"error": "圖譜路徑探索失敗", "count": 0}

    async def execute_skill_query(self, params: Dict[str, Any], skill_name: str) -> Dict[str, Any]:
        """執行 skill-based 查詢 — 從 KB 搜尋相關知識"""
        query = params.get("query", "")
        # Delegate to search_knowledge_base with skill name as context
        return await self.search_knowledge_base(
            {"query": f"{skill_name} {query}".strip(), "limit": 3}
        )

    async def search_knowledge_base(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜尋知識庫文件（API 規格、架構、ADR、開發規範）"""
        import re as re_mod
        from pathlib import Path

        query = params.get("query", "")
        limit = min(params.get("limit", 5), 10)

        if not query:
            return {"error": "缺少 query 參數", "count": 0}

        docs_dir = Path(__file__).resolve().parents[3] / "docs"
        search_dirs = ["knowledge-map", "adr", "diagrams", "reports", "specifications"]
        query_lower = query.lower()
        results: List[Dict[str, Any]] = []

        # 先嘗試 vector search（如果 kb_chunks 表有資料）
        try:
            from app.services.kb_embedding_service import KBEmbeddingService
            kb_svc = KBEmbeddingService(self.db)
            vector_results = await kb_svc.search(query, limit=limit)
            if vector_results:
                return {
                    "results": vector_results,
                    "count": len(vector_results),
                    "search_type": "vector",
                }
        except Exception:
            pass  # 降級為文字搜尋

        # 文字搜尋降級
        for subdir_name in search_dirs:
            subdir = docs_dir / subdir_name
            if not subdir.is_dir():
                continue
            for md_file in subdir.rglob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                except Exception:
                    continue
                lines = content.splitlines()
                for i, line in enumerate(lines):
                    if query_lower in line.lower():
                        start = max(0, i - 1)
                        end = min(len(lines), i + 2)
                        excerpt = "\n".join(lines[start:end])
                        results.append({
                            "file": md_file.relative_to(docs_dir).as_posix(),
                            "line": i + 1,
                            "excerpt": excerpt[:300],
                            "score": 2.0 if query in line else 1.0,
                        })
                        break  # 每個檔案只取第一個匹配

        results.sort(key=lambda r: -r["score"])
        limited = results[:limit]
        return {
            "results": limited,
            "count": len(limited),
            "search_type": "text",
        }
