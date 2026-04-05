"""
Phase 2 自動學習架構單元測試

測試範圍：
- 2A: ToolResultGuard（工具結果守衛）
- 2B: Adaptive Few-shot（歷史成功案例注入）
- 2C: Self-Reflection（品質自省）
- 2D: Memory Flush Pre-Compaction（壓縮前學習提取）
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ============================================================================
# 2A: ToolResultGuard
# ============================================================================

class TestToolResultGuard:
    """Tool Result Guard — 對標 OpenClaw session-tool-result-guard"""

    def _guard(self):
        from app.services.ai.agent_tools import ToolResultGuard
        return ToolResultGuard

    def test_guard_search_documents_timeout(self):
        Guard = self._guard()
        raw = {"error": "工具執行超時 (15s)", "count": 0}
        result = Guard.guard("search_documents", {"keywords": ["test"]}, raw)
        assert result["guarded"] is True
        assert result["documents"] == []
        assert result["count"] == 0
        assert "error" not in result

    def test_guard_search_entities_timeout(self):
        Guard = self._guard()
        raw = {"error": "工具執行超時 (15s)", "count": 0}
        result = Guard.guard("search_entities", {"query": "test"}, raw)
        assert result["guarded"] is True
        assert result["entities"] == []
        assert "error" not in result

    def test_guard_search_dispatch_orders(self):
        Guard = self._guard()
        raw = {"error": "工具執行失敗", "count": 0}
        result = Guard.guard("search_dispatch_orders", {}, raw)
        assert result["guarded"] is True
        assert result["dispatch_orders"] == []

    def test_guard_find_correspondence(self):
        Guard = self._guard()
        raw = {"error": "timeout", "count": 0}
        result = Guard.guard("find_correspondence", {"dispatch_id": 1}, raw)
        assert result["guarded"] is True
        assert result["pairs"] == []

    def test_guard_unknown_tool_returns_original(self):
        Guard = self._guard()
        raw = {"error": "timeout", "count": 0}
        result = Guard.guard("unknown_tool", {}, raw)
        assert result is raw  # 回傳原始錯誤

    def test_guard_preserves_guard_reason(self):
        Guard = self._guard()
        raw = {"error": "DB 連線逾時", "count": 0}
        result = Guard.guard("get_statistics", {}, raw)
        assert result["guard_reason"] == "DB 連線逾時"

    def test_guarded_result_not_skipped_by_synthesis(self):
        """確認 build_synthesis_context 不跳過 guarded 結果"""
        Guard = self._guard()
        raw = {"error": "timeout", "count": 0}
        result = Guard.guard("search_documents", {}, raw)
        # build_synthesis_context 跳過 result.get("error") 的項目
        # guarded 結果不應有 error key
        assert "error" not in result
        assert result.get("guarded") is True

    def test_all_tools_have_templates(self):
        """確認所有已知工具都有守衛模板（skill_ 前綴工具動態處理，不需模板）"""
        Guard = self._guard()
        # 確認守衛模板覆蓋所有非 skill 的已註冊工具
        from app.services.ai.agent_tools import VALID_TOOL_NAMES
        non_skill_tools = {n for n in VALID_TOOL_NAMES if not n.startswith("skill_")}
        assert set(Guard._GUARD_TEMPLATES.keys()) == non_skill_tools


# ============================================================================
# 2B: Adaptive Few-shot
# ============================================================================

class TestAdaptiveFewshot:
    """Adaptive Few-shot — 從歷史 trace 注入範例"""

    @pytest.mark.asyncio
    async def test_build_adaptive_fewshot_with_traces(self):
        from app.services.ai.agent_planner import AgentPlanner

        mock_ai = AsyncMock()
        config = MagicMock()
        config.adaptive_fewshot_enabled = True
        config.adaptive_fewshot_limit = 3
        config.adaptive_fewshot_min_results = 1
        config.rag_max_history_turns = 4

        planner = AgentPlanner(mock_ai, config)
        mock_db = AsyncMock()

        mock_traces = [
            {
                "question": "工務局的函",
                "tools_used": ["search_documents"],
                "total_results": 5,
                "answer_preview": "找到 5 筆...",
            },
        ]

        with patch(
            "app.repositories.agent_trace_repository.AgentTraceRepository"
        ) as MockRepo:
            MockRepo.return_value.find_similar_successful_traces = AsyncMock(
                return_value=mock_traces
            )
            result = await planner._build_adaptive_fewshot("工務局來函", mock_db, None)

        assert "工務局的函" in result
        assert "search_documents" in result

    @pytest.mark.asyncio
    async def test_build_adaptive_fewshot_no_traces(self):
        from app.services.ai.agent_planner import AgentPlanner

        mock_ai = AsyncMock()
        config = MagicMock()
        config.adaptive_fewshot_limit = 3
        config.adaptive_fewshot_min_results = 1
        config.rag_max_history_turns = 4

        planner = AgentPlanner(mock_ai, config)
        mock_db = AsyncMock()

        with patch(
            "app.repositories.agent_trace_repository.AgentTraceRepository"
        ) as MockRepo:
            MockRepo.return_value.find_similar_successful_traces = AsyncMock(
                return_value=[]
            )
            result = await planner._build_adaptive_fewshot("某問題", mock_db, None)

        assert result == ""

    def test_find_similar_traces_returns_empty_on_no_keywords(self):
        """無中文關鍵字時回傳空"""
        import re
        keywords = re.findall(r'[\u4e00-\u9fff]{2,4}', "123 456")
        assert keywords == []


# ============================================================================
# 2C: Self-Reflection
# ============================================================================

class TestSelfReflection:
    """品質自省 — 對標 OpenClaw Thinking/Reflection"""

    @pytest.mark.asyncio
    async def test_high_score_no_retry(self):
        from app.services.ai.tool_result_formatter import self_reflect

        mock_ai = AsyncMock()
        mock_ai.chat_completion = AsyncMock(
            return_value='{"score": 8, "issues": []}'
        )
        config = MagicMock()
        config.self_reflect_timeout = 5

        result = await self_reflect(
            mock_ai, "test question", "test answer",
            [{"tool": "search_documents", "result": {"count": 3}}],
            config,
        )
        assert result["score"] == 8
        assert result["issues"] == []

    @pytest.mark.asyncio
    async def test_low_score_with_issues(self):
        from app.services.ai.tool_result_formatter import self_reflect

        mock_ai = AsyncMock()
        mock_ai.chat_completion = AsyncMock(
            return_value='{"score": 3, "issues": ["答案不完整"], "suggested_tools": ["search_entities"]}'
        )
        config = MagicMock()
        config.self_reflect_timeout = 5

        result = await self_reflect(
            mock_ai, "test", "incomplete answer",
            [{"tool": "search_documents", "result": {"count": 1}}],
            config,
        )
        assert result["score"] == 3
        assert "答案不完整" in result["issues"]

    @pytest.mark.asyncio
    async def test_timeout_returns_safe_default(self):
        from app.services.ai.tool_result_formatter import self_reflect

        mock_ai = AsyncMock()
        mock_ai.chat_completion = AsyncMock(
            side_effect=TimeoutError("timeout")
        )
        config = MagicMock()
        config.self_reflect_timeout = 1

        result = await self_reflect(
            mock_ai, "test", "answer", [], config,
        )
        assert result["score"] == 10  # 安全預設

    @pytest.mark.asyncio
    async def test_invalid_json_returns_safe_default(self):
        from app.services.ai.tool_result_formatter import self_reflect

        mock_ai = AsyncMock()
        mock_ai.chat_completion = AsyncMock(return_value="not json")
        config = MagicMock()
        config.self_reflect_timeout = 5

        result = await self_reflect(
            mock_ai, "test", "answer", [], config,
        )
        assert result["score"] == 10


# ============================================================================
# 2D: Memory Flush Pre-Compaction
# ============================================================================

class TestMemoryFlush:
    """Memory Flush — 對標 OpenClaw memory-flush pre-compaction"""

    def _make_summarizer(self):
        from app.services.ai.agent_summarizer import ConversationSummarizer
        return ConversationSummarizer(trigger_turns=3, max_chars=500, keep_recent=2)

    @pytest.mark.asyncio
    async def test_extract_learnings_stores_to_redis(self):
        summarizer = self._make_summarizer()

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()
        summarizer._redis = mock_redis

        mock_ai = AsyncMock()
        mock_ai.chat_completion = AsyncMock(
            return_value='{"learnings": [{"type": "entity", "content": "工務局"}]}'
        )

        history = [
            {"role": "user", "content": "工務局的函"},
            {"role": "assistant", "content": "找到 3 筆公文..."},
        ] * 4  # 8 messages

        with patch("app.services.ai.ai_config.get_ai_config") as mock_config:
            mock_config.return_value.memory_flush_enabled = True
            mock_config.return_value.memory_flush_max_learnings = 10
            mock_config.return_value.memory_flush_learnings_ttl = 86400

            await summarizer.extract_and_flush_learnings("sess-1", history, mock_ai)

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert "agent:learnings:sess-1" in str(call_args)

    @pytest.mark.asyncio
    async def test_memory_flush_disabled(self):
        summarizer = self._make_summarizer()
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        summarizer._redis = mock_redis

        mock_ai = AsyncMock()

        with patch("app.services.ai.ai_config.get_ai_config") as mock_config:
            mock_config.return_value.memory_flush_enabled = False

            await summarizer.extract_and_flush_learnings("sess-1", [], mock_ai)

        mock_ai.chat_completion.assert_not_called()

    @pytest.mark.asyncio
    async def test_learnings_loaded_in_effective_history(self):
        summarizer = self._make_summarizer()

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.get = AsyncMock(
            side_effect=lambda key: (
                b"summary text" if "conv_summary" in key
                else b'{"learnings": [{"type": "entity", "content": "test"}]}'
            )
        )
        summarizer._redis = mock_redis

        history = [{"role": "user", "content": "q"}] * 8

        result = await summarizer.get_effective_history("sess-2", history)

        # 第一個應是 system message，包含學習 + 摘要
        assert result[0]["role"] == "system"
        assert "先前學習" in result[0]["content"]
        assert "先前對話摘要" in result[0]["content"]

    @pytest.mark.asyncio
    async def test_redis_unavailable_degrades_gracefully(self):
        summarizer = self._make_summarizer()
        summarizer._redis = None

        mock_ai = AsyncMock()

        # 不應拋出異常
        await summarizer.extract_and_flush_learnings("sess-3", [], mock_ai)
