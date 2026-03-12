"""
Agent 工具模組 — 9 個工具定義與實作

工具清單：
- search_documents: 向量+SQL 混合公文搜尋 + Hybrid Reranking + 圖增強鄰域擴展
- search_dispatch_orders: 派工單搜尋 (桃園工務局)
- search_entities: 知識圖譜實體搜尋
- get_entity_detail: 實體詳情 (關係+關聯公文)
- find_similar: 語意相似公文
- get_statistics: 圖譜 / 公文統計
- navigate_graph: 3D 知識圖譜導航
- summarize_entity: 實體摘要簡報
- draw_diagram: Mermaid 圖表生成

Version: 1.2.0 - Tool #9 draw_diagram
Extracted from agent_orchestrator.py v1.8.0
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ============================================================================
# Tool 定義 — 由 ToolRegistry 統一管理（SSOT）
# tool_registry.py 不匯入本模組，無循環匯入風險
# ============================================================================

from app.services.ai.tool_registry import get_tool_registry as _get_tool_registry

_registry = _get_tool_registry()

TOOL_DEFINITIONS = _registry.get_definitions()
TOOL_DEFINITIONS_STR = _registry.get_definitions_json()
VALID_TOOL_NAMES = _registry.valid_tool_names

# dispatch_map 鍵集合（模組載入時一次性定義，供一致性檢查）
_DISPATCH_KEYS = {
    "search_documents",
    "search_dispatch_orders",
    "search_entities",
    "get_entity_detail",
    "find_similar",
    "get_statistics",
    "navigate_graph",
    "summarize_entity",
    "draw_diagram",
}
if _DISPATCH_KEYS != VALID_TOOL_NAMES:
    raise RuntimeError(
        f"dispatch_map keys {_DISPATCH_KEYS} != registry tools {VALID_TOOL_NAMES}"
    )

# LLM 自然語言 entity_type → DB 欄位值對照
ENTITY_TYPE_MAP = {
    "organization": "org", "organisation": "org", "機關": "org",
    "人員": "person", "人": "person",
    "專案": "project", "案件": "project",
    "地點": "location", "地址": "location",
    "主題": "topic", "議題": "topic",
    "日期": "date", "時間": "date",
    # Code Graph (v1.80.0)
    "模組": "py_module", "module": "py_module",
    "類別": "py_class", "class": "py_class",
    "函數": "py_function", "function": "py_function", "方法": "py_function",
    "資料表": "db_table", "table": "db_table",
}


class AgentToolExecutor:
    """Agent 工具執行器 — 封裝 9 個工具的實作邏輯"""

    # D1: 模組層級快取 er-model.json（避免每次工具呼叫重讀磁碟）
    _er_model_cache: Dict[str, Any] | None = None
    _er_model_loaded: bool = False

    def __init__(self, db: AsyncSession, ai_connector, embedding_mgr, config):
        self.db = db
        self.ai = ai_connector
        self.embedding_mgr = embedding_mgr
        self.config = config
        # 首次實例化時載入 er-model.json
        if not AgentToolExecutor._er_model_loaded:
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

    async def execute_parallel(
        self, calls: List[Dict[str, Any]], tool_timeout: float,
    ) -> List[Dict[str, Any]]:
        """
        並行執行多個工具（每個工具獨立 db session + 超時保護）。

        用於 LLM 規劃回傳 2+ 個無相依工具呼叫時，省去串行等待。
        每個工具建立獨立 AsyncSession，避免 SQLAlchemy 並發存取限制。
        """
        from app.db.database import AsyncSessionLocal

        async def _run_one(call: Dict[str, Any]) -> Dict[str, Any]:
            tool_name = call.get("name", "")
            params = call.get("params", {})
            try:
                async with AsyncSessionLocal() as session:
                    executor = AgentToolExecutor(
                        session, self.ai, self.embedding_mgr, self.config,
                    )
                    return await asyncio.wait_for(
                        executor.execute(tool_name, params),
                        timeout=tool_timeout,
                    )
            except asyncio.TimeoutError:
                logger.warning("Tool %s timed out (%ds) in parallel", tool_name, tool_timeout)
                return {"error": f"工具執行超時 ({tool_timeout}s)", "count": 0}
            except Exception as e:
                logger.error("Tool %s failed in parallel: %s", tool_name, e)
                return {"error": "工具執行失敗", "count": 0}

        results = await asyncio.gather(*[_run_one(c) for c in calls])
        return list(results)

    async def execute(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """路由工具呼叫至對應實作"""
        dispatch_map = {
            "search_documents": self._search_documents,
            "search_dispatch_orders": self._search_dispatch_orders,
            "search_entities": self._search_entities,
            "get_entity_detail": self._get_entity_detail,
            "find_similar": self._find_similar,
            "get_statistics": self._get_statistics,
            "navigate_graph": self._navigate_graph,
            "summarize_entity": self._summarize_entity,
            "draw_diagram": self._draw_diagram,
        }

        handler = dispatch_map.get(tool_name)
        if not handler:
            return {"error": f"未知工具: {tool_name}", "count": 0}

        return await handler(params)

    async def _search_documents(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜尋公文 — 向量+SQL搜尋 + Hybrid Reranking"""
        from app.services.ai.search_entity_expander import expand_search_terms, flatten_expansions
        from app.services.ai.reranker import rerank_documents
        from app.repositories.query_builders.document_query_builder import DocumentQueryBuilder

        keywords = params.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [keywords]
        original_keywords = list(keywords)

        # 統一詞彙擴展管道（SynonymExpander + 知識圖譜）
        if keywords:
            try:
                expansions = await expand_search_terms(self.db, keywords)
                keywords = flatten_expansions(expansions)
            except Exception as e:
                logger.debug("Search term expansion failed, using original keywords: %s", e)

        qb = DocumentQueryBuilder(self.db)

        if keywords:
            qb = qb.with_keywords_full(keywords)
        if params.get("sender"):
            from app.services.ai.synonym_expander import SynonymExpander
            sender = SynonymExpander.expand_agency(params["sender"])
            qb = qb.with_sender_like(sender)
        if params.get("receiver"):
            from app.services.ai.synonym_expander import SynonymExpander
            receiver = SynonymExpander.expand_agency(params["receiver"])
            qb = qb.with_receiver_like(receiver)
        if params.get("doc_type"):
            qb = qb.with_doc_type(params["doc_type"])

        date_from, date_to = None, None
        if params.get("date_from"):
            try:
                date_from = datetime.strptime(params["date_from"], "%Y-%m-%d").date()
            except ValueError:
                pass
        if params.get("date_to"):
            try:
                date_to = datetime.strptime(params["date_to"], "%Y-%m-%d").date()
            except ValueError:
                pass
        if date_from or date_to:
            qb = qb.with_date_range(date_from, date_to)

        if keywords:
            relevance_text = " ".join(keywords)
            try:
                query_embedding = await self.embedding_mgr.get_embedding(
                    relevance_text, self.ai
                )
                if query_embedding:
                    qb = qb.with_relevance_order(relevance_text)
                    qb = qb.with_semantic_search(
                        query_embedding,
                        weight=self.config.hybrid_semantic_weight,
                    )
                else:
                    qb = qb.with_relevance_order(relevance_text)
            except Exception:
                qb = qb.with_relevance_order(relevance_text)
        else:
            qb = qb.order_by("updated_at", descending=True)

        limit = min(int(params.get("limit", 5)), 10)
        fetch_limit = min(limit * 2, 20)
        qb = qb.limit(fetch_limit)

        documents, total = await qb.execute_with_count()

        docs = []
        for doc in documents:
            docs.append({
                "id": doc.id,
                "doc_number": doc.doc_number or "",
                "subject": doc.subject or "",
                "doc_type": doc.doc_type or "",
                "category": doc.category or "",
                "sender": doc.sender or "",
                "receiver": doc.receiver or "",
                "doc_date": str(doc.doc_date) if doc.doc_date else "",
                "status": doc.status or "",
                "similarity": 0,
            })

        # Hybrid Reranking (向量+關鍵字覆蓋度)
        if docs and original_keywords:
            docs = rerank_documents(docs, original_keywords)
            docs = docs[:limit]
        else:
            docs = docs[:limit]

        # GraphRAG Phase 1: 圖增強鄰域擴展
        # 從搜尋結果的文件 → 知識圖譜實體 → 1-hop 鄰域文件 → 合併擴展
        if docs and len(docs) < limit:
            try:
                expanded = await self._expand_via_knowledge_graph(
                    [d["id"] for d in docs],
                    max_extra=limit - len(docs),
                )
                if expanded:
                    existing_ids = {d["id"] for d in docs}
                    for doc in expanded:
                        if doc["id"] not in existing_ids:
                            docs.append(doc)
                            existing_ids.add(doc["id"])
                        if len(docs) >= limit:
                            break
            except Exception as e:
                logger.debug("Graph expansion skipped: %s", e)

        return {"documents": docs, "total": total, "count": len(docs)}

    async def _search_dispatch_orders(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜尋派工單紀錄"""
        from app.repositories.taoyuan.dispatch_order_repository import DispatchOrderRepository

        dispatch_no = params.get("dispatch_no", "")
        search = params.get("search", "")
        work_type = params.get("work_type")
        limit = min(int(params.get("limit", 10)), 20)

        repo = DispatchOrderRepository(self.db)

        if dispatch_no:
            search_term = dispatch_no.strip()
            items, total = await repo.filter_dispatch_orders(
                search=search_term,
                work_type=work_type,
                limit=limit,
                sort_by="id",
                sort_order="desc",
            )
        elif search:
            items, total = await repo.filter_dispatch_orders(
                search=search.strip(),
                work_type=work_type,
                limit=limit,
                sort_by="id",
                sort_order="desc",
            )
        else:
            items, total = await repo.filter_dispatch_orders(
                work_type=work_type,
                limit=limit,
                sort_by="id",
                sort_order="desc",
            )

        dispatch_orders = []
        dispatch_ids = []
        for item in items:
            dispatch_orders.append({
                "id": item.id,
                "dispatch_no": item.dispatch_no or "",
                "project_name": item.project_name or "",
                "work_type": item.work_type or "",
                "sub_case_name": item.sub_case_name or "",
                "case_handler": item.case_handler or "",
                "survey_unit": item.survey_unit or "",
                "deadline": item.deadline or "",
                "created_at": str(item.created_at) if item.created_at else "",
            })
            dispatch_ids.append(item.id)

        # 查詢關聯公文（透過 taoyuan_dispatch_document_link）
        linked_docs: List[Dict[str, Any]] = []
        if dispatch_ids:
            try:
                from sqlalchemy import select
                from app.extended.models import (
                    OfficialDocument,
                    TaoyuanDispatchDocumentLink,
                )

                stmt = (
                    select(
                        TaoyuanDispatchDocumentLink.dispatch_order_id,
                        OfficialDocument.id,
                        OfficialDocument.doc_number,
                        OfficialDocument.subject,
                        OfficialDocument.doc_type,
                        OfficialDocument.doc_date,
                    )
                    .join(
                        OfficialDocument,
                        OfficialDocument.id == TaoyuanDispatchDocumentLink.document_id,
                    )
                    .where(
                        TaoyuanDispatchDocumentLink.dispatch_order_id.in_(dispatch_ids)
                    )
                )
                result = await self.db.execute(stmt)
                for row in result.fetchall():
                    linked_docs.append({
                        "dispatch_order_id": row[0],
                        "document_id": row[1],
                        "doc_number": row[2] or "",
                        "subject": row[3] or "",
                        "doc_type": row[4] or "",
                        "doc_date": str(row[5]) if row[5] else "",
                    })
            except Exception as e:
                logger.debug("Failed to fetch linked documents for dispatch orders: %s", e)

        return {
            "dispatch_orders": dispatch_orders,
            "linked_documents": linked_docs,
            "total": total,
            "count": len(dispatch_orders),
        }

    async def _search_entities(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜尋知識圖譜實體"""
        from app.services.ai.graph_query_service import GraphQueryService

        svc = GraphQueryService(self.db)
        query = params.get("query", "")
        entity_type = params.get("entity_type")
        # 正規化 entity_type：LLM 可能產生 "organization" 等自然語言名稱
        if entity_type:
            entity_type = ENTITY_TYPE_MAP.get(entity_type.lower(), entity_type)
        limit = min(int(params.get("limit", 10)), 20)

        entities = await svc.search_entities(query, entity_type=entity_type, limit=limit)
        return {"entities": entities, "count": len(entities)}

    async def _get_entity_detail(self, params: Dict[str, Any]) -> Dict[str, Any]:
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

    async def _find_similar(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """查找語意相似公文"""
        from app.extended.models import OfficialDocument
        from sqlalchemy import select

        doc_id = params.get("document_id")
        if not doc_id:
            return {"error": "缺少 document_id 參數", "count": 0}

        result = await self.db.execute(
            select(OfficialDocument).where(OfficialDocument.id == int(doc_id))
        )
        source_doc = result.scalar_one_or_none()
        if not source_doc or source_doc.embedding is None:
            return {"error": f"公文 ID={doc_id} 不存在或無向量", "count": 0}

        embedding_col = OfficialDocument.embedding
        distance_expr = embedding_col.cosine_distance(source_doc.embedding)
        similarity_expr = (1 - distance_expr).label("similarity")

        limit = min(int(params.get("limit", 5)), 10)

        stmt = (
            select(
                OfficialDocument.id,
                OfficialDocument.doc_number,
                OfficialDocument.subject,
                OfficialDocument.doc_type,
                OfficialDocument.sender,
                OfficialDocument.doc_date,
                similarity_expr,
            )
            .where(embedding_col.isnot(None))
            .where(OfficialDocument.id != int(doc_id))
            .where(distance_expr <= self.config.agent_find_similar_threshold)
            .order_by(distance_expr)
            .limit(limit)
        )

        rows = (await self.db.execute(stmt)).all()
        docs = [
            {
                "id": row.id,
                "doc_number": row.doc_number or "",
                "subject": row.subject or "",
                "doc_type": row.doc_type or "",
                "sender": row.sender or "",
                "doc_date": str(row.doc_date) if row.doc_date else "",
                "similarity": round(float(row.similarity), 4),
            }
            for row in rows
        ]

        return {"documents": docs, "count": len(docs)}

    async def _get_statistics(self, _params: Dict[str, Any]) -> Dict[str, Any]:
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

    async def _navigate_graph(self, params: Dict[str, Any]) -> Dict[str, Any]:
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

    async def _summarize_entity(self, params: Dict[str, Any]) -> Dict[str, Any]:
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

    # ========================================================================
    # Tool #9: draw_diagram — Mermaid 圖表生成
    # ========================================================================

    async def _draw_diagram(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool #9: Generate Mermaid diagram based on query context."""
        diagram_type = params.get("diagram_type", "auto")
        scope = params.get("scope", "")
        detail_level = params.get("detail_level", "normal")

        # D1: 使用類別層級快取，避免每次讀磁碟
        er_data = AgentToolExecutor._er_model_cache

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

        if diagram_type == "erDiagram" and er_data:
            title, description, lines = self._build_er_diagram(er_data, scope, detail_level)
        elif diagram_type == "graph":
            title, description, lines = await self._build_dependency_graph(scope, detail_level)
        elif diagram_type == "flowchart":
            title, description, lines = await self._build_flowchart(scope)
        elif diagram_type == "classDiagram":
            title, description, lines = await self._build_class_diagram(scope, detail_level)
        else:
            # Fallback ER
            if er_data:
                title, description, lines = self._build_er_diagram(er_data, scope, detail_level)
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

    def _build_er_diagram(
        self, er_data: Dict[str, Any], scope: str, detail_level: str
    ) -> tuple:
        """Build Mermaid ER diagram from er-model.json."""
        tables = er_data.get("tables", {})
        scope_lower = scope.lower() if scope else ""

        # Filter tables by scope
        if scope_lower:
            filtered = {
                k: v for k, v in tables.items()
                if scope_lower in k.lower()
                or any(scope_lower in fk.get("ref_table", "").lower() for fk in v.get("foreign_keys", []))
            }
            # Also include referenced tables
            ref_tables: set = set()
            for t_info in filtered.values():
                for fk in t_info.get("foreign_keys", []):
                    ref = fk.get("ref_table", "")
                    if ref in tables:
                        ref_tables.add(ref)
            for ref in ref_tables:
                if ref not in filtered:
                    filtered[ref] = tables[ref]
            tables = filtered

        if not tables:
            return ("無匹配的表", f"範圍 '{scope}' 沒有匹配的資料表", ["erDiagram"])

        type_map = {
            "INTEGER": "int", "BIGINT": "bigint", "SMALLINT": "smallint",
            "BOOLEAN": "bool", "CHARACTER VARYING": "varchar", "TEXT": "text",
            "TIMESTAMP WITHOUT TIME ZONE": "timestamp",
            "TIMESTAMP WITH TIME ZONE": "timestamptz",
            "DATE": "date", "UUID": "uuid", "JSONB": "jsonb",
            "DOUBLE PRECISION": "float8", "NUMERIC": "numeric",
            "VECTOR": "vector",
        }

        lines: List[str] = ["erDiagram"]

        # Relationships
        seen_rels: set = set()
        for tbl_name, tbl_info in tables.items():
            for fk in tbl_info.get("foreign_keys", []):
                ref = fk.get("ref_table", "")
                if ref in tables:
                    rel_key = f"{ref}-{tbl_name}-{fk.get('column', '')}"
                    if rel_key not in seen_rels:
                        seen_rels.add(rel_key)
                        lines.append(f'    {ref} ||--o{{ {tbl_name} : "{fk.get("column", "")}"')

        lines.append("")

        # Table definitions
        for tbl_name in sorted(tables.keys()):
            tbl_info = tables[tbl_name]
            pk_set = set(tbl_info.get("primary_key", []))
            fk_cols = {fk["column"] for fk in tbl_info.get("foreign_keys", [])}
            cols = tbl_info.get("columns", [])

            if detail_level == "brief":
                cols = [c for c in cols if c["name"] in pk_set or c["name"] in fk_cols]

            lines.append(f"    {tbl_name} {{")
            for col in cols:
                mtype = type_map.get(col.get("type", ""), col.get("type", "").lower())
                markers: List[str] = []
                if col["name"] in pk_set:
                    markers.append("PK")
                if col["name"] in fk_cols:
                    markers.append("FK")
                marker_str = f' "{",".join(markers)}"' if markers else ""
                lines.append(f'        {mtype} {col["name"]}{marker_str}')
            lines.append("    }")

        table_count = len(tables)
        title = f"ER Diagram — {scope or '全部'} ({table_count} 表)"
        description = f"包含 {table_count} 個資料表及其外鍵關聯"
        return (title, description, lines)

    async def _build_dependency_graph(
        self, scope: str, detail_level: str
    ) -> tuple:
        """Build module dependency graph from canonical_entities."""
        from sqlalchemy import select
        from app.extended.models import CanonicalEntity, EntityRelationship

        scope_lower = scope.lower() if scope else ""

        # Query modules
        stmt = select(
            CanonicalEntity.id,
            CanonicalEntity.canonical_name,
            CanonicalEntity.entity_type,
        ).where(
            CanonicalEntity.entity_type.in_(["py_module", "ts_module"])
        )
        if scope_lower:
            stmt = stmt.where(CanonicalEntity.canonical_name.ilike(f"%{scope_lower}%"))

        mod_rows = (await self.db.execute(stmt)).all()
        if not mod_rows:
            return ("無匹配模組", f"範圍 '{scope}' 沒有匹配的模組", ["graph LR"])

        mod_ids = {r[0] for r in mod_rows}
        id_to_name = {r[0]: r[1] for r in mod_rows}

        # Get imports relations
        rel_stmt = select(
            EntityRelationship.source_entity_id,
            EntityRelationship.target_entity_id,
        ).where(
            EntityRelationship.relation_type == "imports",
            EntityRelationship.source_entity_id.in_(mod_ids),
            EntityRelationship.target_entity_id.in_(mod_ids),
        )
        rel_rows = (await self.db.execute(rel_stmt)).all()

        lines: List[str] = ["graph LR"]
        # Limit to manageable size
        max_nodes = 30 if detail_level != "full" else 60
        shown_ids: set = set()
        shown_rels: List[str] = []

        for src_id, tgt_id in rel_rows:
            if len(shown_ids) >= max_nodes:
                break
            shown_ids.add(src_id)
            shown_ids.add(tgt_id)
            src_name = id_to_name.get(src_id, str(src_id)).split(".")[-1].split("/")[-1]
            tgt_name = id_to_name.get(tgt_id, str(tgt_id)).split(".")[-1].split("/")[-1]
            shown_rels.append(f"    {src_name} --> {tgt_name}")

        lines.extend(shown_rels[:50])

        title = f"模組依賴圖 — {scope or '全部'} ({len(shown_ids)} 模組)"
        description = f"{len(shown_rels)} 條 import 關聯"
        return (title, description, lines)

    async def _build_flowchart(self, scope: str) -> tuple:
        """Build flowchart via LLM generation or known system flows."""
        # Known system flow templates
        known_flows: Dict[str, list] = {
            "document": [
                "flowchart TD",
                "    A[收文登錄] --> B[分文指派]",
                "    B --> C{需核稿?}",
                "    C -->|是| D[擬稿]",
                "    C -->|否| E[歸檔]",
                "    D --> F[核稿審查]",
                "    F -->|退回| D",
                "    F -->|通過| G[發文]",
                "    G --> H[送達追蹤]",
                "    H --> E",
            ],
            "dispatch": [
                "flowchart TD",
                "    A[接收派工單] --> B[建立工程紀錄]",
                "    B --> C[派工單匯入]",
                "    C --> D[公文配對]",
                "    D --> E{配對成功?}",
                "    E -->|是| F[建立作業歷程]",
                "    E -->|否| G[手動關聯]",
                "    G --> F",
                "    F --> H[進度追蹤]",
                "    H --> I{結案?}",
                "    I -->|否| H",
                "    I -->|是| J[結案歸檔]",
            ],
            "ai": [
                "flowchart TD",
                "    A[使用者提問] --> B[意圖解析]",
                "    B --> C[Agent Planner]",
                "    C --> D[工具選擇 1-3 個]",
                "    D --> E[平行執行工具]",
                "    E --> F[GraphRAG 鄰域擴展]",
                "    F --> G[答案合成]",
                "    G --> H[SSE 串流回覆]",
                "    H --> I[回饋收集]",
            ],
        }

        scope_lower = scope.lower() if scope else ""

        # Match known flows
        for key, flow_lines in known_flows.items():
            if key in scope_lower:
                title = f"流程圖 — {scope}"
                description = f"{scope} 處理流程"
                return (title, description, flow_lines)

        # LLM generation fallback
        if self.ai:
            try:
                prompt = (
                    f"請根據以下主題生成 Mermaid flowchart（flowchart TD 格式）：{scope}\n"
                    "要求：\n"
                    "- 節點數 5-12 個\n"
                    "- 包含決策節點（菱形 {{}}）\n"
                    "- 使用中文標籤\n"
                    "- 只輸出 Mermaid 語法，不要任何解釋\n"
                )
                response = await self.ai.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=500,
                )
                content = response.get("content", "") if isinstance(response, dict) else str(response)
                # Extract mermaid block if wrapped
                if "```mermaid" in content:
                    content = content.split("```mermaid")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                lines = content.strip().split("\n")
                if lines and lines[0].strip().startswith("flowchart"):
                    title = f"流程圖 — {scope}"
                    description = f"AI 生成的 {scope} 流程圖"
                    return (title, description, lines)
            except Exception as e:
                logger.warning("Flowchart LLM generation failed: %s", e)

        # Ultimate fallback
        lines = [
            "flowchart TD",
            f"    A[{scope or '開始'}] --> B{{判斷條件}}",
            "    B -->|是| C[處理步驟]",
            "    B -->|否| D[替代路徑]",
            "    C --> E[結束]",
            "    D --> E",
        ]
        title = f"流程圖 — {scope or '通用'}"
        description = "基本流程圖模板"
        return (title, description, lines)

    async def _build_class_diagram(
        self, scope: str, detail_level: str
    ) -> tuple:
        """Build class diagram from py_class entities."""
        from sqlalchemy import select
        from app.extended.models import CanonicalEntity, EntityRelationship

        scope_lower = scope.lower() if scope else ""

        stmt = select(
            CanonicalEntity.id,
            CanonicalEntity.canonical_name,
            CanonicalEntity.description,
        ).where(CanonicalEntity.entity_type == "py_class")
        if scope_lower:
            stmt = stmt.where(CanonicalEntity.canonical_name.ilike(f"%{scope_lower}%"))
        stmt = stmt.limit(20)

        class_rows = (await self.db.execute(stmt)).all()
        if not class_rows:
            return ("無匹配類別", f"範圍 '{scope}' 沒有匹配的類別", ["classDiagram"])

        class_ids = {r[0] for r in class_rows}
        lines: List[str] = ["classDiagram"]

        for row in class_rows:
            name = row[1].split(".")[-1]
            desc = row[2]
            if isinstance(desc, str):
                try:
                    desc = json.loads(desc)
                except Exception:
                    desc = {}
            if not isinstance(desc, dict):
                desc = {}

            lines.append(f"    class {name} {{")
            methods = desc.get("methods", [])
            if detail_level == "brief":
                methods = methods[:3]
            for m in methods[:10]:
                lines.append(f"        +{m}()")
            lines.append("    }")

        # Inheritance relations
        rel_stmt = select(
            EntityRelationship.source_entity_id,
            EntityRelationship.target_entity_id,
            EntityRelationship.relation_type,
        ).where(
            EntityRelationship.source_entity_id.in_(class_ids),
            EntityRelationship.relation_type.in_(["inherits", "defines_class"]),
        )
        rel_rows = (await self.db.execute(rel_stmt)).all()
        id_to_name = {r[0]: r[1].split(".")[-1] for r in class_rows}

        for src_id, tgt_id, rtype in rel_rows:
            src_name = id_to_name.get(src_id, "")
            if src_name:
                if rtype == "inherits":
                    lines.append(f"    {src_name} --|> Parent")

        title = f"類別圖 — {scope or '全部'} ({len(class_rows)} 類別)"
        description = f"包含 {len(class_rows)} 個類別的結構"
        return (title, description, lines)

    # ========================================================================
    # GraphRAG Phase 1: 圖增強鄰域擴展
    # ========================================================================

    async def _expand_via_knowledge_graph(
        self, doc_ids: List[int], max_extra: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        從已知文件出發，透過知識圖譜鄰域擴展找出相關文件。

        流程：
        1. doc_ids → document_entity_mentions → canonical_entity_ids
        2. canonical_entity_ids → 1-hop 鄰居實體
        3. 鄰居實體 → document_entity_mentions → 新文件
        4. 回傳未在原始結果中的文件
        """
        from sqlalchemy import select, and_, func as sa_func
        from app.extended.models import (
            OfficialDocument,
            DocumentEntityMention,
            EntityRelationship,
        )

        if not doc_ids:
            return []

        # Step 1: 找出原始文件中提及的正規化實體 (取平均信心度最高的前 10 個)
        mention_stmt = (
            select(DocumentEntityMention.canonical_entity_id)
            .where(DocumentEntityMention.document_id.in_(doc_ids))
            .group_by(DocumentEntityMention.canonical_entity_id)
            .order_by(
                sa_func.avg(DocumentEntityMention.confidence).desc()
            )
            .limit(10)
        )
        mention_result = await self.db.execute(mention_stmt)
        entity_ids = [row[0] for row in mention_result.all()]

        if not entity_ids:
            return []

        # Step 2: 1-hop 鄰居實體 (透過 entity_relationships, 雙向)
        neighbor_stmt = (
            select(EntityRelationship.target_entity_id)
            .where(
                EntityRelationship.source_entity_id.in_(entity_ids),
                EntityRelationship.invalidated_at.is_(None),
            )
            .union_all(
                select(EntityRelationship.source_entity_id)
                .where(
                    EntityRelationship.target_entity_id.in_(entity_ids),
                    EntityRelationship.invalidated_at.is_(None),
                )
            )
            .limit(20)
        )
        neighbor_result = await self.db.execute(neighbor_stmt)
        all_entity_ids = set(entity_ids)
        for row in neighbor_result.all():
            all_entity_ids.add(row[0])

        # Step 3: 鄰居實體 → 關聯文件 (排除原始文件)
        expanded_doc_stmt = (
            select(
                OfficialDocument.id,
                OfficialDocument.doc_number,
                OfficialDocument.subject,
                OfficialDocument.doc_type,
                OfficialDocument.category,
                OfficialDocument.sender,
                OfficialDocument.receiver,
                OfficialDocument.doc_date,
                OfficialDocument.status,
            )
            .join(
                DocumentEntityMention,
                DocumentEntityMention.document_id == OfficialDocument.id,
            )
            .where(
                and_(
                    DocumentEntityMention.canonical_entity_id.in_(all_entity_ids),
                    OfficialDocument.id.notin_(doc_ids),
                )
            )
            .group_by(OfficialDocument.id)
            .order_by(OfficialDocument.doc_date.desc().nullslast())
            .limit(max_extra)
        )
        expanded_result = await self.db.execute(expanded_doc_stmt)

        return [
            {
                "id": row.id,
                "doc_number": row.doc_number or "",
                "subject": row.subject or "",
                "doc_type": row.doc_type or "",
                "category": row.category or "",
                "sender": row.sender or "",
                "receiver": row.receiver or "",
                "doc_date": str(row.doc_date) if row.doc_date else "",
                "status": row.status or "",
                "similarity": 0,
                "_source": "graph_expansion",
            }
            for row in expanded_result.all()
        ]
