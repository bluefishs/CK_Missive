"""
Agent 合成模組 — 答案合成、thinking 過濾、context 建構

職責：
- synthesize_answer: 根據工具結果串流生成最終回答
- strip_thinking: 從 qwen3:4b 回答中提取真正答案（5 階段策略）
- build_synthesis_context: 將工具結果建構為 LLM 上下文
- summarize_tool_result: 生成工具結果的簡短摘要
- fallback_rag: 無工具直接回答時回退到 RAG

Extracted from agent_orchestrator.py v1.8.0
"""

import re
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentSynthesizer:
    """Agent 答案合成器 — 負責將工具結果轉換為自然語言回答"""

    def __init__(self, ai_connector, config):
        self.ai = ai_connector
        self.config = config

    async def synthesize_answer(
        self,
        question: str,
        tool_results: List[Dict[str, Any]],
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        """根據所有工具結果，串流生成最終回答"""
        from app.services.ai.ai_prompt_manager import AIPromptManager

        context = self.build_synthesis_context(tool_results)

        await AIPromptManager.ensure_db_prompts_loaded()
        base_prompt = AIPromptManager.get_system_prompt("rag_system")
        if not base_prompt:
            base_prompt = (
                "你是公文管理系統的 AI 助理。根據檢索到的資料回答使用者問題。"
                "引用來源時使用 [公文N] 格式。使用繁體中文回答。"
            )

        system_prompt = (
            f"{base_prompt}\n\n"
            "以下是透過多個工具查詢到的資料。請綜合所有資訊回答。\n\n"
            "嚴格規則（違反任一條都是錯誤）：\n"
            "- 禁止輸出推理、分析、思考過程\n"
            "- 禁止寫「首先」「我需要」「讓我」「問題是」「從資料看」「規則要求」\n"
            "- 禁止重複這些規則\n"
            "- 禁止解釋你為什麼這樣回答\n"
            "- 直接輸出答案，格式為要點列表\n\n"
            "正確輸出範例：\n"
            "工務局近期函件如下：\n"
            "- [公文1] 桃工用字第XXX號：主旨內容（2026-02-25）\n"
            "- [公文2] 桃工用字第XXX號：主旨內容（2026-02-25）\n"
        )

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]

        if history:
            for turn in history[-(self.config.rag_max_history_turns * 2):]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        user_prompt = f"查詢結果：\n\n{context}\n\n問題：{question}\n\n請根據上述資料回答問題。"
        messages.append({"role": "user", "content": user_prompt})

        # 非串流呼叫 + 後處理：qwen3:4b 會在回覆中大量穿插推理段落
        try:
            raw = await self.ai.chat_completion(
                messages=messages,
                temperature=self.config.rag_temperature,
                max_tokens=self.config.rag_max_tokens,
                task_type="chat",
            )
            cleaned = strip_thinking_from_synthesis(raw)
            yield cleaned
        except Exception as e:
            logger.warning("Synthesis chat_completion failed, trying stream: %s", e)
            async for token in self.ai.stream_completion(
                messages=messages,
                temperature=self.config.rag_temperature,
                max_tokens=self.config.rag_max_tokens,
            ):
                yield token

    def build_synthesis_context(self, tool_results: List[Dict[str, Any]]) -> str:
        """將所有工具結果建構為 LLM 合成上下文"""
        max_chars = self.config.rag_max_context_chars
        parts = []
        total_chars = 0

        for tr in tool_results:
            tool = tr["tool"]
            result = tr["result"]

            if result.get("error"):
                continue

            if tool == "search_documents":
                for i, doc in enumerate(result.get("documents", []), 1):
                    part = (
                        f"[公文{i}] 字號: {doc.get('doc_number', '')}\n"
                        f"  主旨: {doc.get('subject', '')}\n"
                        f"  類型: {doc.get('doc_type', '')} | 類別: {doc.get('category', '')}\n"
                        f"  發文: {doc.get('sender', '')} → 受文: {doc.get('receiver', '')}\n"
                        f"  日期: {doc.get('doc_date', '')}\n"
                    )
                    if total_chars + len(part) > max_chars:
                        break
                    parts.append(part)
                    total_chars += len(part)

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
                    if total_chars + len(part) > max_chars:
                        break
                    parts.append(part)
                    total_chars += len(part)

            elif tool == "search_entities":
                for e in result.get("entities", []):
                    part = (
                        f"[實體] {e.get('canonical_name', '')} "
                        f"({e.get('entity_type', '')}, "
                        f"提及 {e.get('mention_count', 0)} 次)\n"
                    )
                    if total_chars + len(part) > max_chars:
                        break
                    parts.append(part)
                    total_chars += len(part)

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
                if total_chars + len(part) <= max_chars:
                    parts.append(part)
                    total_chars += len(part)

            elif tool == "find_similar":
                for doc in result.get("documents", []):
                    part = (
                        f"[相似公文] {doc.get('doc_number', '')} "
                        f"(相似度 {doc.get('similarity', 0):.0%})\n"
                        f"  主旨: {doc.get('subject', '')}\n"
                    )
                    if total_chars + len(part) > max_chars:
                        break
                    parts.append(part)
                    total_chars += len(part)

            elif tool == "get_statistics":
                stats = result.get("stats", {})
                part = (
                    f"[統計] 知識圖譜: {stats.get('total_entities', 0)} 實體, "
                    f"{stats.get('total_relationships', 0)} 關係\n"
                )
                top = result.get("top_entities", [])
                if top:
                    names = [f"{e.get('canonical_name', '')}({e.get('mention_count', 0)})" for e in top[:5]]
                    part += f"  高頻實體: {', '.join(names)}\n"
                if total_chars + len(part) <= max_chars:
                    parts.append(part)
                    total_chars += len(part)

        return "\n".join(parts) if parts else "(查詢未取得有效資料)"

    @staticmethod
    def build_results_summary(tool_results: List[Dict[str, Any]]) -> str:
        """建構工具結果摘要供 LLM 評估"""
        parts = []
        for tr in tool_results:
            tool = tr["tool"]
            result = tr["result"]
            summary = summarize_tool_result(tool, result)
            parts.append(f"- [{tool}] {summary}")
        return "\n".join(parts) if parts else "(無結果)"


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
        linked_count = len(result.get("linked_documents", []))
        first_items = [
            f"{d.get('dispatch_no', '')}({d.get('project_name', '')[:20]})"
            for d in orders[:3]
        ]
        summary = f"找到 {total} 筆派工單（顯示 {count} 筆）: {'; '.join(first_items)}"
        if linked_count:
            summary += f"（含 {linked_count} 筆關聯公文）"
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

    return f"完成 (count={result.get('count', 0)})"


def strip_thinking_from_synthesis(raw: str) -> str:
    """
    從合成回答中提取真正的答案，丟棄 qwen3:4b 洩漏的推理段落。

    策略：「答案提取」而非「推理過濾」
    - Phase 1: 移除 <think> 標記
    - Phase 2: 短回答快速通過
    - Phase 3: 尋找答案邊界標記（「如下：」「以下是」等），取後半段
    - Phase 4: 從末尾向前掃描，找最後一段含 [公文N]/[派工單N] 的區塊
    - Phase 5: 逐行過濾（最後手段）
    """
    if not raw:
        return raw

    # Phase 1: 移除 <think> 標記
    cleaned = re.sub(r"<think>.*?</think>\s*", "", raw, flags=re.DOTALL).strip()

    # Phase 2: 短回答快速通過
    _OBVIOUS_THINKING = ("首先", "我需要", "問題是", "規則要求", "讓我分析", "从资料")
    ref_pattern = re.compile(r"\[(公文|派工單)\d+\]")
    has_refs = bool(ref_pattern.search(cleaned))

    if len(cleaned) < 300 and not has_refs and not any(m in cleaned for m in _OBVIOUS_THINKING):
        return cleaned

    lines = cleaned.split("\n")

    # Phase 3: 尋找答案邊界
    _ANSWER_BOUNDARIES = (
        "如下：", "如下:", "重點如下", "資訊如下", "相關資訊如下",
        "可能的回應", "回答：", "回答:", "回覆：", "回覆:",
        "綜合以上", "以下是", "以下為",
    )

    boundary_idx = None
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if any(marker in stripped for marker in _ANSWER_BOUNDARIES):
            boundary_idx = i
            break

    if boundary_idx is not None:
        answer_lines = lines[boundary_idx:]
        result = "\n".join(answer_lines).strip()
        if result and len(result) > 20:
            return result

    # Phase 3.5: 找末尾的 intro + 結構化區塊
    for i in range(len(lines) - 2, -1, -1):
        stripped = lines[i].strip()
        if stripped and (stripped.endswith("：") or stripped.endswith(":")):
            next_stripped = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if ref_pattern.search(next_stripped) or next_stripped.startswith("-") or next_stripped.startswith("*"):
                answer_lines = lines[i:]
                result = "\n".join(answer_lines).strip()
                if result and len(result) > 20:
                    return result

    # Phase 4: 無明確邊界 → 找最後一段含 [公文N]/[派工單N] 的連續區塊
    ref_blocks: list[tuple[int, int]] = []
    block_start = -1
    block_end = -1

    for i, line in enumerate(lines):
        stripped = line.strip()
        has_ref = bool(ref_pattern.search(stripped))
        is_continuation = line.startswith("  ") or stripped.startswith("*") or not stripped

        if has_ref:
            if block_start == -1:
                block_start = i
            block_end = i
        elif block_start != -1:
            if is_continuation:
                block_end = i
            else:
                ref_blocks.append((block_start, block_end))
                block_start = -1

    if block_start != -1:
        ref_blocks.append((block_start, block_end))

    if ref_blocks:
        start, end = ref_blocks[-1]

        for back in range(1, 3):
            idx = start - back
            if idx >= 0:
                prev = lines[idx].strip()
                if prev and len(prev) < 100 and not any(
                    prev.startswith(m) for m in _OBVIOUS_THINKING
                ):
                    start = idx
                    break
                elif not prev:
                    break

        answer_lines = lines[start:end + 1]
        result = "\n".join(answer_lines).strip()
        if result and len(result) > 20:
            return result

    # Phase 5: 逐行過濾（最後手段）
    _THINK_PREFIXES = (
        "首先", "我需要", "問題是", "讓我", "让我",
        "用户", "用戶", "規則要求", "規則說", "回答結構",
        "回答要", "日期格式", "我假設", "我将", "我將",
        "在公文資料中", "由於問題", "可能用戶",
        "但規則", "但問題", "回覆結構", "結構建議",
        "從資料看", "從檢索結果", "所以重點", "所以我",
        "列出每", "所有公文",
        "- 只根據", "- 引用來源", "- 如果資料不足",
        "- 使用繁體", "- 回答簡潔", "- 若問題涉及",
        "- 日期格式使用", "- 簡潔扼要", "- 用繁體",
        "在中文公文術語中", "這有點", "為了遵守",
        "我應該", "先提取", "現在，",
    )

    kept: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if kept and kept[-1] != "":
                kept.append("")
            continue
        if any(stripped.startswith(m) for m in _THINK_PREFIXES):
            continue
        meta_count = sum(1 for m in ("分析", "假設", "應該", "需要",
                                      "結構", "格式", "簡潔") if m in stripped)
        if meta_count >= 3:
            continue
        kept.append(line)

    result = "\n".join(kept).strip()

    if not result or len(result) < 20:
        doc_lines = [ln for ln in lines if ref_pattern.search(ln)]
        if doc_lines:
            return "\n".join(doc_lines).strip()
        return cleaned

    return result
