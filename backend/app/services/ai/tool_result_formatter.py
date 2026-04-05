"""
工具結果格式化模組 — 工具上下文建構、結果摘要、品質自省

職責：
- format_tool_context: 格式化單一工具結果為上下文字串
- summarize_tool_result: 生成工具結果的簡短摘要
- self_reflect: 答案品質自省（輕量 LLM 評估）

Extracted from agent_synthesis.py v1.8.0
"""

import asyncio
import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def format_tool_context(tool: str, result: Dict[str, Any], remaining_chars: int) -> str:
    """格式化單一工具結果為上下文字串"""
    parts: list[str] = []

    if tool == "search_documents":
        for i, doc in enumerate(result.get("documents", []), 1):
            part = (
                f"[公文{i}] 字號: {doc.get('doc_number', '')}\n"
                f"  主旨: {doc.get('subject', '')}\n"
                f"  類型: {doc.get('doc_type', '')} | 類別: {doc.get('category', '')}\n"
                f"  發文: {doc.get('sender', '')} → 受文: {doc.get('receiver', '')}\n"
                f"  日期: {doc.get('doc_date', '')}\n"
            )
            if sum(len(p) for p in parts) + len(part) > remaining_chars:
                break
            parts.append(part)

    elif tool == "search_dispatch_orders":
        linked_docs = result.get("linked_documents", [])
        for i, d in enumerate(result.get("dispatch_orders", []), 1):
            d_linked = [
                ld for ld in linked_docs
                if ld.get("dispatch_order_id") == d.get("id")
            ]
            linked_str = ""
            if d_linked:
                linked_str = "  關聯公文:\n"
                for ld in d_linked[:3]:
                    linked_str += (
                        f"    - {ld.get('doc_number', '')} "
                        f"{ld.get('subject', '')[:60]}\n"
                    )
            part = (
                f"[派工單{i}] 單號: {d.get('dispatch_no', '')}\n"
                f"  工程名稱: {d.get('project_name', '')}\n"
                f"  作業類別: {d.get('work_type', '')}\n"
                f"  子案名稱: {d.get('sub_case_name', '')}\n"
                f"  承辦人: {d.get('case_handler', '')} | 測量單位: {d.get('survey_unit', '')}\n"
                f"  契約期限: {d.get('deadline', '')}\n"
                f"{linked_str}"
            )
            if sum(len(p) for p in parts) + len(part) > remaining_chars:
                break
            parts.append(part)

    elif tool == "search_entities":
        for e in result.get("entities", []):
            part = (
                f"[實體] {e.get('canonical_name', '')} "
                f"({e.get('entity_type', '')}, "
                f"提及 {e.get('mention_count', 0)} 次)\n"
            )
            if sum(len(p) for p in parts) + len(part) > remaining_chars:
                break
            parts.append(part)

    elif tool == "get_entity_detail":
        entity = result.get("entity", {})
        part = (
            f"[實體詳情] {entity.get('canonical_name', '')} "
            f"({entity.get('entity_type', '')})\n"
            f"  別名: {', '.join(entity.get('aliases', [])[:5])}\n"
        )
        for doc in entity.get("documents", [])[:5]:
            part += f"  關聯公文: {doc.get('doc_number', '')} - {doc.get('subject', '')}\n"
        for rel in entity.get("relationships", [])[:5]:
            target = rel.get("target_name") or rel.get("source_name", "")
            part += f"  關係: {rel.get('relation_label', '')} → {target}\n"
        if len(part) <= remaining_chars:
            parts.append(part)

    elif tool == "find_similar":
        for doc in result.get("documents", []):
            part = (
                f"[相似公文] {doc.get('doc_number', '')} "
                f"(相似度 {doc.get('similarity', 0):.0%})\n"
                f"  主旨: {doc.get('subject', '')}\n"
            )
            if sum(len(p) for p in parts) + len(part) > remaining_chars:
                break
            parts.append(part)

    elif tool == "get_statistics":
        # 公文統計（優先使用預合成摘要）
        summary_text = result.get("summary", "")
        if summary_text:
            part = f"[統計] {summary_text}\n"
        else:
            doc_total = result.get("document_total", 0)
            doc_by_cat = result.get("document_by_category", {})
            cat_detail = "、".join(f"{k} {v}" for k, v in doc_by_cat.items()) if doc_by_cat else ""
            part = f"[統計] 系統共有 {doc_total} 筆公文"
            if cat_detail:
                part += f"（{cat_detail}）"
            part += "\n"
        # 知識圖譜統計
        graph_stats = result.get("graph_stats", {})
        if graph_stats:
            part += (
                f"  知識圖譜: {graph_stats.get('total_entities', 0)} 實體, "
                f"{graph_stats.get('total_relationships', 0)} 關係\n"
            )
        top = result.get("top_entities", [])
        if top:
            names = [f"{e.get('canonical_name', '')}({e.get('mention_count', 0)})" for e in top[:5]]
            part += f"  高頻實體: {', '.join(names)}\n"
        if len(part) <= remaining_chars:
            parts.append(part)

    elif tool == "navigate_graph":
        center = result.get("center_entity", {})
        cluster = result.get("cluster_nodes", [])
        part = (
            f"[導航] 已定位至「{center.get('name', '')}」叢集\n"
            f"  相關節點 {len(cluster)} 個:\n"
        )
        for node in cluster[:8]:
            part += f"    - {node.get('name', '')} ({node.get('type', '')})\n"
        if len(part) <= remaining_chars:
            parts.append(part)

    elif tool == "summarize_entity":
        entity = result.get("entity", {})
        summary_text = result.get("summary", "")
        part = (
            f"[實體摘要] {entity.get('name', '')} ({entity.get('type', '')})\n"
            f"  {summary_text[:200]}\n"
        )
        for u in result.get("upstream", [])[:3]:
            part += f"  上游: {u.get('entity_name', '')} ({u.get('relation', '')})\n"
        for d in result.get("downstream", [])[:3]:
            part += f"  下游: {d.get('entity_name', '')} ({d.get('relation', '')})\n"
        timeline = result.get("timeline", [])
        if timeline:
            part += f"  時間軸: {len(timeline)} 個事件\n"
            for evt in timeline[:3]:
                part += f"    - {evt.get('date', '')} {evt.get('subject', '')[:40]}\n"
        docs = result.get("documents", [])
        if docs:
            part += f"  關聯公文 {len(docs)} 篇:\n"
            for doc in docs[:3]:
                part += f"    - {doc.get('doc_number', '')} {doc.get('subject', '')[:40]}\n"
        if len(part) <= remaining_chars:
            parts.append(part)

    elif tool == "draw_diagram":
        dtype = result.get("diagram_type", "er")
        mermaid = result.get("mermaid", "")
        related = result.get("related_entities", [])
        part = f"[圖表] 類型: {dtype}\n"
        if related:
            part += f"  涵蓋實體: {', '.join(str(e) for e in related[:10])}\n"
        if mermaid:
            part += f"  Mermaid 程式碼已產生 ({len(mermaid)} 字元)\n"
        if len(part) <= remaining_chars:
            parts.append(part)

    elif tool == "find_correspondence":
        pairs = result.get("pairs", [])
        part = f"[公文配對] 共找到 {len(pairs)} 組收發對應\n"
        for p in pairs[:5]:
            conf = p.get("confidence", "")
            part += (
                f"  - {p.get('incoming_doc', '')} ↔ {p.get('outgoing_doc', '')} "
                f"({conf})\n"
            )
        shared = result.get("shared_entities", [])
        if shared:
            part += f"  共同實體: {', '.join(str(e) for e in shared[:8])}\n"
        if len(part) <= remaining_chars:
            parts.append(part)

    elif tool == "explore_entity_path":
        path_nodes = result.get("path", [])
        part = f"[路徑探索] {len(path_nodes)} 個節點\n"
        if path_nodes:
            names = [n.get("name", "") for n in path_nodes]
            part += f"  路徑: {' → '.join(names)}\n"
        relations = result.get("relations", [])
        for rel in relations[:5]:
            part += (
                f"  {rel.get('source', '')} —[{rel.get('label', '')}]→ "
                f"{rel.get('target', '')}\n"
            )
        if len(part) <= remaining_chars:
            parts.append(part)

    elif tool == "get_system_health":
        summary = result.get("summary", {})
        db_info = summary.get("database", {})
        res_info = summary.get("resources", {})
        dq_info = summary.get("data_quality", {})
        backup_info = summary.get("backup", {})
        part = (
            f"[系統健康]\n"
            f"  資料庫: {db_info.get('status', 'unknown')}\n"
            f"  CPU: {res_info.get('cpu_percent', 'N/A')}% | "
            f"記憶體: {res_info.get('memory_percent', 'N/A')}%\n"
        )
        if dq_info:
            part += (
                f"  資料品質: FK覆蓋率 {dq_info.get('fk_coverage', 'N/A')} | "
                f"NER覆蓋率 {dq_info.get('ner_coverage', 'N/A')}\n"
            )
        if backup_info:
            part += f"  備份: {backup_info.get('status', 'N/A')}\n"
        benchmarks = summary.get("benchmarks", {})
        if benchmarks and not benchmarks.get("error"):
            part += f"  效能基準: 查詢延遲 {benchmarks.get('query_latency_ms', 'N/A')}ms\n"
        recommendations = summary.get("recommendations", [])
        if recommendations:
            part += "  建議:\n"
            for rec in recommendations[:5]:
                part += f"    - {rec}\n"
        if len(part) <= remaining_chars:
            parts.append(part)

    return "".join(parts)


def summarize_tool_result(tool_name: str, result: Dict[str, Any]) -> str:
    """生成工具結果的簡短摘要"""
    if result.get("error"):
        return f"錯誤: {result['error']}"

    if tool_name == "search_documents":
        count = result.get("count", 0)
        total = result.get("total", 0)
        if count == 0:
            return "未找到匹配公文"
        docs = result.get("documents", [])
        first_subjects = [d.get("subject", "")[:30] for d in docs[:3]]
        return f"找到 {total} 篇公文（顯示 {count} 篇）: {'; '.join(first_subjects)}"

    if tool_name == "search_dispatch_orders":
        count = result.get("count", 0)
        total = result.get("total", 0)
        if count == 0:
            return "未找到匹配派工單"
        orders = result.get("dispatch_orders", [])
        linked_docs = result.get("linked_documents", [])
        first_items = [
            f"{d.get('dispatch_no', '')}({d.get('project_name', '')[:20]})"
            for d in orders[:3]
        ]
        summary = f"找到 {total} 筆派工單（顯示 {count} 筆）: {'; '.join(first_items)}"
        # 完整列出關聯公文讓 LLM 能看到全部內容
        if linked_docs:
            summary += f"（含 {len(linked_docs)} 筆關聯公文）"
            for doc in linked_docs:
                dn = doc.get("doc_number", "?")
                subj = (doc.get("subject") or "")[:50]
                dt = doc.get("doc_date", "")
                summary += f"\n  - [{dn}] {subj} ({dt})"
        return summary

    if tool_name == "search_entities":
        count = result.get("count", 0)
        if count == 0:
            return "未找到匹配實體"
        entities = result.get("entities", [])
        names = [e.get("canonical_name", "") for e in entities[:5]]
        return f"找到 {count} 個實體: {', '.join(names)}"

    if tool_name == "get_entity_detail":
        entity = result.get("entity", {})
        name = entity.get("canonical_name", "")
        doc_count = len(entity.get("documents", []))
        rel_count = len(entity.get("relationships", []))
        return f"實體「{name}」: {doc_count} 篇關聯公文, {rel_count} 條關係"

    if tool_name == "find_similar":
        count = result.get("count", 0)
        return f"找到 {count} 篇相似公文" if count > 0 else "未找到相似公文"

    if tool_name == "get_statistics":
        stats = result.get("stats", {})
        return (
            f"實體 {stats.get('total_entities', 0)} 個, "
            f"關係 {stats.get('total_relationships', 0)} 條"
        )

    if tool_name == "navigate_graph":
        count = result.get("count", 0)
        center = result.get("center_entity", {})
        center_name = center.get("name", "") if center else ""
        return json.dumps({
            "action": "navigate",
            "center_entity": center,
            "highlight_ids": result.get("highlight_ids", []),
            "cluster_nodes": result.get("cluster_nodes", [])[:20],
            "count": count,
            "summary": f"已導航至「{center_name}」叢集，共 {count} 個相關節點",
        }, ensure_ascii=False)

    if tool_name == "summarize_entity":
        entity = result.get("entity", {})
        name = entity.get("name", "")
        summary_text = result.get("summary", "")
        upstream_count = len(result.get("upstream", []))
        downstream_count = len(result.get("downstream", []))
        doc_count = len(result.get("documents", []))
        return json.dumps({
            "entity": entity,
            "upstream": result.get("upstream", [])[:10],
            "downstream": result.get("downstream", [])[:10],
            "doc_count": doc_count,
            "summary": (
                f"「{name}」摘要: {summary_text[:100]}... "
                f"(上游 {upstream_count}, 下游 {downstream_count}, 關聯公文 {doc_count})"
                if summary_text else
                f"「{name}」: 上游 {upstream_count}, 下游 {downstream_count}, 關聯公文 {doc_count}"
            ),
        }, ensure_ascii=False)

    return f"完成 (count={result.get('count', 0)})"


# ============================================================================
# 品質自省 — 對標 OpenClaw Thinking/Reflection (Phase 2C)
# ============================================================================

async def self_reflect(
    ai_connector,
    question: str,
    answer: str,
    tool_results: List[Dict[str, Any]],
    config,
) -> Dict[str, Any]:
    """
    答案品質自省 — 輕量 LLM 評估。

    Returns:
        {"score": 0-10, "issues": [...], "suggested_tools": [...]}
        失敗時回傳 {"score": 10, "issues": []}（安全預設，不觸發重試）
    """
    try:
        total_count = sum(
            tr.get("result", {}).get("count", 0) for tr in tool_results
        )
        prompt = (
            f"評估以下回答的品質（0-10 分，10=完美）：\n\n"
            f"問題：{question[:200]}\n"
            f"回答：{answer[:500]}\n"
            f"可用資料量：{total_count} 筆\n\n"
            f"評估標準：完整性、相關性、引用準確性。\n"
            f"回傳 JSON：{{\"score\": N, \"issues\": [\"問題描述\"], "
            f"\"suggested_tools\": [\"tool_name\"]}}"
        )

        response = await asyncio.wait_for(
            ai_connector.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=128,
                task_type="chat",
                response_format={"type": "json_object"},
            ),
            timeout=config.self_reflect_timeout,
        )

        from app.services.ai.agent_utils import parse_json_safe
        result = parse_json_safe(response)
        if result and "score" in result:
            return result
        return {"score": 10, "issues": []}

    except Exception as e:
        logger.debug("self_reflect failed: %s", e)
        return {"score": 10, "issues": []}
