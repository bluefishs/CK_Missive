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
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.services.ai.agent_roles import get_role_profile
from app.services.ai.agent_utils import sanitize_history
from app.services.ai.citation_validator import validate_citations  # noqa: F401
from app.services.ai.thinking_filter import strip_thinking_from_synthesis  # noqa: F401
from app.services.ai.tool_result_formatter import (  # noqa: F401
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
    ) -> AsyncGenerator[str, None]:
        """根據所有工具結果，串流生成最終回答"""
        from app.services.ai.ai_prompt_manager import AIPromptManager

        synthesis_context = self.build_synthesis_context(tool_results)

        await AIPromptManager.ensure_db_prompts_loaded()

        role = get_role_profile(context)

        # 嘗試從 DB Prompt 模板載入，回退到角色定義
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
            "## 回覆風格\n"
            "- 像一個有經驗的同事在跟你說明，不是在寫報告\n"
            "- 直接給答案，不要廢話或解釋推理過程\n"
            "- 如果結果中有 summary 欄位，優先引用它的內容\n"
            "- 統計問題直接回答數字（如「共 1643 筆公文」）\n"
            "- 資料多時用列點整理，但語氣要自然\n"
            "- 公文列表附文號和日期\n"
            "- 多個工具的結果要整合成一份，不要按工具分開\n"
            "- 結尾可以簡短問一句「需要更多細節嗎？」之類的\n"
            "\n## 語言規範（嚴格遵守）\n"
            "- 必須全程使用**繁體中文**，嚴禁簡體字\n"
            "- 常見錯誤：数据→資料、关系→關係、实体→實體、统计→統計、"
            "查询→查詢、文档→文件、系统→系統、节点→節點、信息→資訊\n"
        )

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]

        messages.extend(sanitize_history(history, self.config.rag_max_history_turns))

        user_prompt = f"查詢結果：\n\n{synthesis_context}\n\n問題：{question}\n\n請根據上述資料回答問題。"
        messages.append({"role": "user", "content": user_prompt})

        # 非串流呼叫 + 後處理：本地模型可能在回覆中穿插推理段落
        # 超時保護：避免 LLM 無回應時永久阻塞整個 SSE 串流
        synthesis_timeout = max(self.config.cloud_timeout, self.config.local_timeout)
        try:
            # 合成優先用 Groq Cloud（llama-3.3-70B，~1.5s），vLLM 7B 合成 ~7s
            # 指定 model 跳過 vLLM P0，直接走 Groq→NVIDIA→Ollama fallback
            raw = await asyncio.wait_for(
                self.ai.chat_completion(
                    messages=messages,
                    temperature=self.config.rag_temperature,
                    max_tokens=self.config.rag_max_tokens,
                    model="llama-3.3-70b-versatile",  # Groq Cloud
                    task_type="synthesis",
                ),
                timeout=synthesis_timeout,
            )
            cleaned = strip_thinking_from_synthesis(raw)
            # 簡體→繁體後處理（OpenCC s2twp，防 LLM 簡體輸出）
            from app.services.ai.agent_post_processing import _sc2tc
            yield _sc2tc(cleaned)
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
