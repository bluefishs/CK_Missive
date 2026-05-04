"""
Agent 合成模組 — 答案合成、thinking 過濾、context 建構

職責：
- synthesize_answer: 根據工具結果串流生成最終回答
- strip_thinking: 從 LLM 回答中提取真正答案（5 階段策略，適用 Gemma 4 / Qwen3 等）
- build_synthesis_context: 將工具結果建構為 LLM 上下文
- summarize_tool_result: 生成工具結果的簡短摘要
- fallback_rag: 無工具直接回答時回退到 RAG

Extracted from agent_orchestrator.py v1.8.0
"""

import asyncio
import logging
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.services.ai.agent.agent_roles import get_role_profile
from app.services.ai.core.agent_utils import sanitize_history
from app.services.ai.core.citation_validator import validate_citations  # noqa: F401
from app.services.ai.core.thinking_filter import strip_thinking_from_synthesis  # noqa: F401
from app.services.ai.tools.tool_result_formatter import (  # noqa: F401
    format_tool_context,
    summarize_tool_result,
    self_reflect,
)

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
        context: Optional[str] = None,
        cross_session_hints: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[str, None]:
        """根據所有工具結果，串流生成最終回答。

        v6.3 體感型輸出：cross_session_hints 為同 user 過去 30 天最近 5 次 query。
        若提供且與本問題相關，synthesis 會在回應第一句明確 acknowledge
        「上次（日期）你問過 X」— 解決「沒有延續性」體感斷鏈。
        """
        from app.services.ai.core.ai_prompt_manager import AIPromptManager

        synthesis_context = self.build_synthesis_context(tool_results)

        # Graph-RAG: 注入 2-hop KG context (增強答案品質)
        kg_context = await self._inject_kg_context(tool_results)
        if kg_context:
            synthesis_context = f"## 知識圖譜關聯\n{kg_context}\n\n{synthesis_context}"

        # Wiki-RAG: 注入 LLM Wiki narrative (2026-04-19 KG+Wiki 雙源融合)
        wiki_context = await self._inject_wiki_context(question)
        if wiki_context:
            synthesis_context = f"## Wiki 相關頁面\n{wiki_context}\n\n{synthesis_context}"

        await AIPromptManager.ensure_db_prompts_loaded()

        role = get_role_profile(context)

        # 2026-04-19 Memory Wiki Phase 0: SOUL.md 動態載入 > DB prompt > 靜態 role
        # 優先序：SOUL（身份層 SSOT）→ DB-stored rag_system → 硬編碼 fallback
        try:
            from app.services.ai.agent.agent_roles import build_system_prompt_with_soul
            soul_prompt = await build_system_prompt_with_soul(role_context=context)
        except Exception:
            soul_prompt = None

        if soul_prompt and len(soul_prompt) > 100:
            base_prompt = soul_prompt
        else:
            # 舊路徑 fallback
            db_prompt = AIPromptManager.get_system_prompt("rag_system") if context != "dev" else None
            if db_prompt:
                base_prompt = db_prompt
            else:
                base_prompt = (
                    f"你是{role.identity}。根據檢索到的資料回答使用者問題。"
                    f"引用來源時使用 {role.citation_format} 格式。使用繁體中文回答。"
                    f"{(' ' + role.style_hints) if role.style_hints else ''}"
                )

        system_prompt = (
            f"{base_prompt}\n\n"
            "根據以下查詢結果回答使用者的問題。\n\n"
            "## 回覆原則\n"
            "1. **先分析再回答** — 不要只列資料，要給出你的判斷和建議\n"
            "2. **整合多來源** — 如果有多個工具結果，要交叉分析，找出關聯和趨勢\n"
            "3. **主動提醒** — 發現異常要主動說明（逾期、超預算、進度落後）\n"
            "4. **量化表達** — 用百分比、比較、趨勢描述，不要只說「有幾筆」\n"
            "5. **可行動建議** — 回答結尾給 1-2 個具體的下一步建議\n"
            "6. **層次結構** — 用標題、列點、粗體組織回答，重點在前\n\n"
            "## 統計/分析回覆模板\n"
            "- 總覽：一句話結論\n"
            "- 關鍵數字：最重要的 2-3 個指標\n"
            "- 趨勢/比較：和上期比、和預算比\n"
            "- 異常/風險：需要注意的問題\n"
            "- 建議：具體的行動項目\n\n"
            "## 一般回覆風格\n"
            "- 如果結果中有 summary 欄位，優先引用它的內容\n"
            "- 公文列表附文號和日期\n"
            "- 多個工具的結果要整合成一份，不要按工具分開\n"
            "- 結尾可以簡短問一句「需要更多細節嗎？」之類的\n\n"
            "## 語言規範（嚴格遵守）\n"
            "- 必須全程使用**繁體中文**，嚴禁簡體字\n"
            "- 金額加千分位和幣別（NT$）\n"
            "- 日期用 YYYY/MM/DD 格式\n"
            "- 語氣像資深同事在做簡報，專業但不生硬\n"
            "- 常見錯誤：数据→資料、关系→關係、实体→實體、统计→統計、"
            "查询→查詢、文档→文件、系统→系統、节点→節點、信息→資訊\n"
        )

        # v6.3 體感型：cross-session 連續性 acknowledgment（解「沒有延續性」斷鏈）
        if cross_session_hints:
            try:
                from datetime import datetime as _dt
                lines = []
                for h in cross_session_hints[:5]:
                    try:
                        d = _dt.fromtimestamp(h.get("ts", 0)).strftime("%m/%d")
                    except Exception:
                        d = "?"
                    q_text = (h.get("q") or "")[:80]
                    if q_text:
                        lines.append(f"- ({d}) {q_text}")
                if lines:
                    system_prompt += (
                        "\n## 連續性原則（v6.3 體感型輸出）\n"
                        "以下是同位使用者過去 30 天的相關提問：\n"
                        + "\n".join(lines) + "\n\n"
                        "**若上述任一項與本次問題相關（同主題 / 同人物 / 同案件），"
                        "回應的第一句必須明確 acknowledge**，例如：\n"
                        "  「上次（M/D）你問過 X，今天的 Y 是延續/相關，差別是…」\n"
                        "若無相關，可忽略本區塊。不要硬塞無關 acknowledge。\n"
                    )
            except Exception as e:
                logger.debug("cross_session_hints inject failed: %s", e)

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]

        messages.extend(sanitize_history(history, self.config.rag_max_history_turns))

        user_prompt = f"查詢結果：\n\n{synthesis_context}\n\n問題：{question}\n\n請根據上述資料回答問題。"
        messages.append({"role": "user", "content": user_prompt})

        # 非串流呼叫 + 後處理：本地模型可能在回覆中穿插推理段落
        # 超時保護：避免 LLM 無回應時永久阻塞整個 SSE 串流
        # Q3 (5/04 v3.0 覆盤): 改用 TIMEOUTS.synthesis SSOT（cloud_llm + 5 = 35s）
        # ADR-0028 contract enforced，避免 dead config 兩處不同值
        from app.core.timeouts import TIMEOUTS
        synthesis_timeout = TIMEOUTS.synthesis
        # 2026-04-24: model env-based，支援 qwen/qwen3-32b 切換（零成本整合評估）
        # 預設保留 llama-3.3-70b（與現狀一致，backward compat）
        synthesis_model = os.getenv("SYNTHESIS_MODEL", "llama-3.3-70b-versatile")
        # D2-A: synthesis start/end 觀測性 — 防止 silent gap
        logger.info(
            "synthesis_start timeout=%ds messages=%d model=%s",
            synthesis_timeout, len(messages), synthesis_model,
        )
        _t0 = time.monotonic()
        try:
            # 合成優先用 Groq Cloud（llama-3.3-70B，~1.5s）或 Qwen3-32B（~0.6s）
            # 指定 model 跳過 vLLM P0，直接走 Groq→NVIDIA→Ollama fallback
            raw = await asyncio.wait_for(
                self.ai.chat_completion(
                    messages=messages,
                    temperature=self.config.rag_temperature,
                    max_tokens=self.config.rag_max_tokens,
                    model=synthesis_model,
                    task_type="synthesis",
                ),
                timeout=synthesis_timeout,
            )
            logger.info(
                "synthesis_end elapsed=%.2fs raw_len=%d",
                time.monotonic() - _t0, len(raw or ""),
            )
            cleaned = strip_thinking_from_synthesis(raw)
            # 簡體→繁體後處理（OpenCC s2twp，防 LLM 簡體輸出）
            from app.services.ai.agent.agent_post_processing import _sc2tc
            cleaned = _sc2tc(cleaned)
            # 品質審查：檢查回答是否充分利用資料，必要時請 LLM 改善
            cleaned = await self._quality_review(question, cleaned, tool_results)
            # F19 (5/04 v3.0 覆盤): fact_check — 偵測 LLM hallucinated 數字
            self._fact_check_numbers(cleaned, tool_results)
            yield cleaned
        except asyncio.TimeoutError:
            logger.warning("Synthesis timed out after %ds", synthesis_timeout)
            yield "AI 回答生成超時，請參考上方查詢結果與來源文件。"
        except Exception as e:
            logger.warning("Synthesis chat_completion failed, trying stream: %s", e)
            try:
                async for token in self.ai.stream_completion(
                    messages=messages,
                    temperature=self.config.rag_temperature,
                    max_tokens=self.config.rag_max_tokens,
                ):
                    yield token
            except asyncio.TimeoutError:
                logger.warning("Synthesis stream fallback also timed out")
                yield "AI 回答生成超時，請參考上方查詢結果與來源文件。"

    async def _quality_review(
        self,
        question: str,
        answer: str,
        tool_results: List[Dict[str, Any]],
    ) -> str:
        """Review and improve answer quality before sending.

        Checks:
        1. Does the answer actually address the question?
        2. Are statistics properly contextualized (not just raw numbers)?
        3. Are there actionable suggestions?
        4. Is the format readable?

        If quality is low, ask LLM to improve it.
        """
        # Quick heuristic checks
        needs_improvement = False
        reasons: List[str] = []

        # Check 1: Answer is too short for a data-heavy query
        has_data = any(
            tr.get("result", {}).get("count", 0) > 0
            or tr.get("result", {}).get("document_total", 0) > 0
            or tr.get("result", {}).get("documents")
            for tr in tool_results
        )
        if has_data and len(answer) < 100:
            needs_improvement = True
            reasons.append("回答過短，未充分利用查詢結果")

        # Check 2: No analysis — just listing data without insight
        analysis_keywords = [
            "建議", "趨勢", "注意", "風險", "比較", "異常",
            "應", "需要", "可以", "佔比", "偏高", "偏低",
            "成長", "下降", "優先", "重點",
        ]
        if has_data and not any(kw in answer for kw in analysis_keywords):
            needs_improvement = True
            reasons.append("缺乏分析和建議，僅列出原始資料")

        # Check 3: Statistics without context
        has_stats = any(
            tr["tool"] in ("get_statistics", "get_financial_summary")
            for tr in tool_results
        )
        if has_stats and "建議" not in answer and "趨勢" not in answer:
            needs_improvement = True
            reasons.append("統計數字缺乏脈絡和行動建議")

        if not needs_improvement:
            return answer

        # Ask LLM to improve
        try:
            logger.info(
                "Quality review triggered: %s",
                "; ".join(reasons),
            )
            improve_prompt = (
                f"以下回答品質不足，請改善：\n\n"
                f"問題：{question[:200]}\n"
                f"原始回答：{answer[:800]}\n"
                f"問題：{'; '.join(reasons)}\n\n"
                "請重新撰寫，要求：\n"
                "1. 加入分析觀點（不只列資料）\n"
                "2. 標出異常或需注意的地方\n"
                "3. 結尾給 1-2 個具體建議\n"
                "4. 保持繁體中文\n"
                "5. 保留原始回答中的所有數據和事實，不要遺漏"
            )
            # P0-1：quality review 降至 10s（原 15s），非關鍵路徑避免拖慢整體
            improved = await asyncio.wait_for(
                self.ai.chat_completion(
                    messages=[{"role": "user", "content": improve_prompt}],
                    temperature=0.4,
                    max_tokens=800,
                    task_type="synthesis",
                ),
                timeout=10,
            )
            if improved and len(improved.strip()) > len(answer) * 0.5:
                from app.services.ai.agent.agent_post_processing import _sc2tc
                improved = _sc2tc(strip_thinking_from_synthesis(improved))
                logger.info(
                    "Quality review improved answer: %d -> %d chars",
                    len(answer), len(improved),
                )
                return improved
        except Exception as e:
            logger.debug("Quality review LLM call failed: %s", e)
        return answer

    def _fact_check_numbers(
        self,
        answer: str,
        tool_results: List[Dict[str, Any]],
    ) -> None:
        """F19 (5/04 v3.0 覆盤洞察 12)：偵測 LLM 編造數字。

        策略：
        1. 從 answer 提 ≥3 位數字（小數字過多 false positive）
        2. 從 tool_results 提所有出現過的數字（含 dict values）
        3. 標記 answer 中數字不在 source 集合的（potential hallucination）
        4. 僅 log warning（不改 answer，避免 over-correction）

        對應事故：5/03 14:00:40 LLM 回「知識圖譜共 3 個實體」但 tool 回 12118。
        現在 Q2 (commit dd0ce4db) 已加 summary 引導；此 fact_check 是雙保險。
        """
        try:
            import json
            import re

            # 1. 從 answer 抓 ≥3 位數字（避免 1-2 位高 false positive）
            answer_nums = set(re.findall(r"\b\d{3,}\b", answer))
            if not answer_nums:
                return

            # 2. 把整個 tool_results 序列化後抓所有數字
            try:
                tools_json = json.dumps(tool_results, ensure_ascii=False, default=str)
            except Exception:
                return
            source_nums = set(re.findall(r"\b\d{3,}\b", tools_json))

            # 3. 找 answer 中沒 source 的數字
            unsourced = answer_nums - source_nums
            if unsourced:
                logger.warning(
                    "[fact_check] potential hallucinated numbers in answer: %s "
                    "(source had: %d distinct ≥3-digit numbers)",
                    sorted(unsourced)[:5],  # log 最多 5 個
                    len(source_nums),
                )
                # F19 v2 (5/04 修): 改用 memory_wiki_metrics 集中管理的 Counter
                # 啟動就註冊，/metrics 永遠暴露（即使 0），owner 可看到差異。
                try:
                    from app.core.memory_wiki_metrics import get_memory_wiki_metrics
                    get_memory_wiki_metrics().synthesis_unsourced_numbers.inc(len(unsourced))
                except Exception:
                    pass
        except Exception as e:
            logger.debug("fact_check failed: %s", e)

    async def _inject_kg_context(self, tool_results: List[Dict[str, Any]]) -> str:
        """
        Graph-RAG: 從工具結果中提取實體 ID，查詢 2-hop 鄰居注入合成上下文。
        提升答案品質 — 讓 LLM 看到實體間的關聯。
        """
        try:
            # 收集工具結果中的實體 ID
            entity_ids = set()
            for tr in tool_results:
                result = tr.get("result", {})
                # 多種格式支援
                for key in ("entity_ids", "entities", "canonical_entity_ids"):
                    ids = result.get(key, [])
                    if isinstance(ids, list):
                        entity_ids.update(int(i) for i in ids if i)
                # 從 records 中提取
                for rec in result.get("records", [])[:5]:
                    eid = rec.get("canonical_entity_id") or rec.get("entity_id")
                    if eid:
                        entity_ids.add(int(eid))

            if not entity_ids or len(entity_ids) > 10:
                return ""  # 太多則跳過（避免過重查詢）

            from app.services.ai.graph.graph_traversal_service import GraphTraversalService
            from app.db.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                traversal = GraphTraversalService(db)
                context_parts = []
                for eid in list(entity_ids)[:5]:
                    neighbors = await traversal.get_neighbors(
                        entity_id=eid, max_hops=2, limit=10,
                    )
                    nodes = neighbors.get("nodes", [])
                    if len(nodes) > 1:  # Skip if only root node
                        names = [f"{n['name']}({n['type']})" for n in nodes[1:6]]
                        root = nodes[0]["name"] if nodes else str(eid)
                        context_parts.append(f"- {root} 相關: {', '.join(names)}")

                return "\n".join(context_parts) if context_parts else ""
        except Exception as e:
            logger.debug("KG context injection skipped: %s", e)
            return ""

    async def _inject_wiki_context(self, question: str) -> str:
        """Wiki-RAG: 從 LLM Wiki 檢索相關 narrative，注入合成上下文。

        2026-04-19 新增：補 KG + Wiki 雙源融合缺口。
        - 原本 Wiki 只在 rag_retrieval 路徑被使用，agent 走 tool 路徑時 wiki 完全不被讀
        - 此函數讓 synthesis 階段**無條件**查 wiki（若命中 top 3）
        - 每筆限 300 字，避免 prompt 過長
        """
        try:
            from app.services.wiki.service import get_wiki_service
            svc = get_wiki_service()
            stats = svc.get_stats()
            if not stats or stats.get("total", 0) == 0:
                return ""

            # 取 query 前 60 字作為 wiki 搜尋關鍵字（避免傳整句含標點）
            wiki_query = question.replace("？", " ").replace("?", " ").strip()[:60]
            if not wiki_query:
                return ""

            results = await svc.search_wiki(wiki_query, limit=3)
            if not results:
                return ""

            parts: List[str] = []
            for wr in results:
                try:
                    content = await svc.read_page(wr["path"])
                    if not content:
                        continue
                    # 去除 frontmatter + 只取前 300 字
                    body = content.split("---", 2)[-1].strip()[:300]
                    parts.append(f"- **{wr.get('title', wr['path'])}** (score={wr.get('score', 0)})\n  {body}")
                except Exception:
                    continue

            return "\n\n".join(parts) if parts else ""
        except Exception as e:
            logger.debug("Wiki context injection skipped: %s", e)
            return ""

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

            # Tool Result Guard: 標記合成回退結果
            if result.get("guarded"):
                reason = result.get("guard_reason", "工具暫時無法回應")
                parts.append(f"[{tool}] (回退) {reason}\n")
                total_chars += 30
                continue

            part = format_tool_context(tool, result, max_chars - total_chars)
            if part:
                parts.append(part)
                total_chars += len(part)

        # 跨工具分析指示：多來源時引導 LLM 整合分析
        if len(parts) >= 2:
            successful_tools = [
                tr["tool"] for tr in tool_results
                if not tr.get("result", {}).get("error")
                and not tr.get("result", {}).get("guarded")
            ]
            if len(successful_tools) >= 2:
                cross_hint = (
                    "\n[跨工具分析指示]\n"
                    f"以上來自 {len(successful_tools)} 個工具的結果"
                    f"（{', '.join(successful_tools)}），請整合分析：\n"
                    "- 找出資料間的關聯（例：派工進度 vs 公文時間線）\n"
                    "- 標出不一致或異常的地方\n"
                    "- 給出綜合判斷\n"
                )
                parts.append(cross_hint)

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
