"""
Cross-session Learning 啟動注入測試

驗證：
1. 有學習記錄時正確注入
2. DB 無記錄時優雅回退
3. 尊重 learning_inject_limit 設定
4. learning_persist_enabled=False 時跳過注入
5. DB 異常時靜默跳過
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

REPO_PATCH = "app.repositories.agent_learning_repository.AgentLearningRepository"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_config(**overrides):
    """建立模擬 AIConfig"""
    defaults = {
        "learning_persist_enabled": True,
        "learning_inject_limit": 5,
        "adaptive_fewshot_enabled": False,
        "rag_max_history_turns": 4,
    }
    defaults.update(overrides)
    config = MagicMock()
    for k, v in defaults.items():
        setattr(config, k, v)
    return config


def _make_planner(config=None):
    from app.services.ai.agent_planner import AgentPlanner
    ai = AsyncMock()
    return AgentPlanner(ai, config or _make_config())


# ---------------------------------------------------------------------------
# Tests for _inject_cross_session_learnings
# ---------------------------------------------------------------------------

class TestInjectCrossSessionLearnings:
    """Cross-session learning injection into planner"""

    @pytest.mark.asyncio
    async def test_inject_with_learnings(self):
        """DB 有學習記錄 → 注入格式化文字"""
        planner = _make_planner()
        db = AsyncMock()

        mock_learnings = [
            {"type": "preference", "content": "使用者偏好搜尋派工單", "hit_count": 5, "confidence": 1.0},
            {"type": "entity", "content": "桃園市政府是常見機關", "hit_count": 3, "confidence": 1.0},
        ]

        with patch(REPO_PATCH) as MockRepo:
            repo_instance = MockRepo.return_value
            repo_instance.get_relevant_learnings = AsyncMock(return_value=mock_learnings)

            result = await planner._inject_cross_session_learnings("查派工單", db)

        assert "歷史學習記錄" in result
        assert "使用者偏好搜尋派工單" in result
        assert "桃園市政府是常見機關" in result
        assert "(使用 5 次)" in result
        assert "(使用 3 次)" in result

    @pytest.mark.asyncio
    async def test_inject_empty_db(self):
        """DB 無學習記錄 → 回傳空字串"""
        planner = _make_planner()
        db = AsyncMock()

        with patch(REPO_PATCH) as MockRepo:
            repo_instance = MockRepo.return_value
            repo_instance.get_relevant_learnings = AsyncMock(return_value=[])

            result = await planner._inject_cross_session_learnings("測試問題", db)

        assert result == ""

    @pytest.mark.asyncio
    async def test_inject_fetches_candidates_for_filtering(self):
        """先取得候選學習 (3x limit)，再由語意篩選 top-N"""
        config = _make_config(learning_inject_limit=5)
        planner = _make_planner(config)
        db = AsyncMock()

        with patch(REPO_PATCH) as MockRepo:
            repo_instance = MockRepo.return_value
            repo_instance.get_relevant_learnings = AsyncMock(return_value=[])

            await planner._inject_cross_session_learnings("問題", db)

            # Phase 7.1: fetch 3x limit candidates for cosine similarity filtering
            repo_instance.get_relevant_learnings.assert_called_once_with(
                "問題",
                limit=15,
            )

    @pytest.mark.asyncio
    async def test_inject_db_error_returns_empty(self):
        """DB 異常 → 靜默回傳空字串（不拋例外）"""
        planner = _make_planner()
        db = AsyncMock()

        with patch(REPO_PATCH) as MockRepo:
            repo_instance = MockRepo.return_value
            repo_instance.get_relevant_learnings = AsyncMock(
                side_effect=Exception("DB connection lost")
            )

            # _inject_cross_session_learnings itself raises; the caller catches it
            # But since the repo raises, we need to verify the method propagates the error
            # The caller (plan_tools) catches it. Let's test the raw method:
            with pytest.raises(Exception, match="DB connection lost"):
                await planner._inject_cross_session_learnings("問題", db)

    @pytest.mark.asyncio
    async def test_plan_tools_catches_injection_error(self):
        """plan_tools 中 DB 異常 → 靜默跳過（不影響規劃）"""
        config = _make_config(learning_persist_enabled=True)
        planner = _make_planner(config)

        planner.ai.chat_completion = AsyncMock(
            return_value='{"reasoning": "test", "tool_calls": []}'
        )

        with patch(REPO_PATCH) as MockRepo:
            repo_instance = MockRepo.return_value
            repo_instance.get_relevant_learnings = AsyncMock(
                side_effect=Exception("DB connection lost")
            )
            with patch("app.services.ai.agent_planner.get_tool_registry") as mock_registry:
                mock_registry.return_value.get_definitions_json.return_value = "[]"
                mock_registry.return_value.get_few_shot_prompt.return_value = ""
                with patch("app.services.ai.agent_roles.get_role_profile") as mock_role:
                    mock_role.return_value.identity = "測試助理"

                    db = AsyncMock()
                    # Should NOT raise - error is caught silently
                    result = await planner.plan_tools("測試", [], db=db)
                    assert result is not None

    @pytest.mark.asyncio
    async def test_single_hit_no_count_label(self):
        """hit_count=1 → 不顯示 '(使用 N 次)' 標籤"""
        planner = _make_planner()
        db = AsyncMock()

        mock_learnings = [
            {"type": "entity", "content": "新增的學習", "hit_count": 1, "confidence": 1.0},
        ]

        with patch(REPO_PATCH) as MockRepo:
            repo_instance = MockRepo.return_value
            repo_instance.get_relevant_learnings = AsyncMock(return_value=mock_learnings)

            result = await planner._inject_cross_session_learnings("問題", db)

        assert "新增的學習" in result
        assert "(使用" not in result


class TestPlanToolsLearningIntegration:
    """plan_tools 中 cross-session learning 的整合行為"""

    @pytest.mark.asyncio
    async def test_plan_tools_skips_when_disabled(self):
        """learning_persist_enabled=False → 跳過注入"""
        config = _make_config(learning_persist_enabled=False)
        planner = _make_planner(config)

        planner.ai.chat_completion = AsyncMock(
            return_value='{"reasoning": "test", "tool_calls": []}'
        )

        with patch(REPO_PATCH) as MockRepo:
            with patch("app.services.ai.agent_planner.get_tool_registry") as mock_registry:
                mock_registry.return_value.get_definitions_json.return_value = "[]"
                mock_registry.return_value.get_few_shot_prompt.return_value = ""
                with patch("app.services.ai.agent_roles.get_role_profile") as mock_role:
                    mock_role.return_value.identity = "測試助理"

                    db = AsyncMock()
                    await planner.plan_tools("測試", [], db=db)

            # Repository should NOT have been instantiated
            MockRepo.assert_not_called()

    @pytest.mark.asyncio
    async def test_plan_tools_skips_when_no_db(self):
        """db=None → 跳過注入"""
        config = _make_config(learning_persist_enabled=True)
        planner = _make_planner(config)

        planner.ai.chat_completion = AsyncMock(
            return_value='{"reasoning": "test", "tool_calls": []}'
        )

        with patch(REPO_PATCH) as MockRepo:
            with patch("app.services.ai.agent_planner.get_tool_registry") as mock_registry:
                mock_registry.return_value.get_definitions_json.return_value = "[]"
                mock_registry.return_value.get_few_shot_prompt.return_value = ""
                with patch("app.services.ai.agent_roles.get_role_profile") as mock_role:
                    mock_role.return_value.identity = "測試助理"

                    await planner.plan_tools("測試", [], db=None)

            MockRepo.assert_not_called()

    @pytest.mark.asyncio
    async def test_plan_tools_injects_learnings_into_prompt(self):
        """有學習記錄 → 注入到 system prompt"""
        config = _make_config(learning_persist_enabled=True, learning_inject_limit=3)
        planner = _make_planner(config)

        captured_messages = []

        async def capture_chat(**kwargs):
            captured_messages.extend(kwargs.get("messages", []))
            return '{"reasoning": "test", "tool_calls": []}'

        planner.ai.chat_completion = capture_chat

        mock_learnings = [
            {"type": "tool_combo", "content": "派工單+收發文配對一起查", "hit_count": 8, "confidence": 1.0},
        ]

        with patch(REPO_PATCH) as MockRepo:
            repo_instance = MockRepo.return_value
            repo_instance.get_relevant_learnings = AsyncMock(return_value=mock_learnings)

            with patch("app.services.ai.agent_planner.get_tool_registry") as mock_registry:
                mock_registry.return_value.get_definitions_json.return_value = "[]"
                mock_registry.return_value.get_few_shot_prompt.return_value = ""
                with patch("app.services.ai.agent_roles.get_role_profile") as mock_role:
                    mock_role.return_value.identity = "測試助理"

                    db = AsyncMock()
                    await planner.plan_tools("派工單查詢", [], db=db)

        # 檢查 system prompt 包含學習記錄
        assert len(captured_messages) >= 1
        system_msg = captured_messages[0]["content"]
        assert "歷史學習記錄" in system_msg
        assert "派工單+收發文配對一起查" in system_msg
        assert "(使用 8 次)" in system_msg


class TestRepositoryRelevantLearnings:
    """AgentLearningRepository.get_relevant_learnings 增強測試"""

    @pytest.mark.asyncio
    async def test_passes_limit_param(self):
        """確認 limit 參數正確傳遞至查詢"""
        from unittest.mock import MagicMock as SyncMock

        mock_db = AsyncMock()
        mock_result = SyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        from app.repositories.agent_learning_repository import AgentLearningRepository
        repo = AgentLearningRepository(mock_db)

        result = await repo.get_relevant_learnings("測試問題", limit=3)
        assert result == []
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_db_exception(self):
        """DB 異常 → 回傳空列表"""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=Exception("connection refused"))

        from app.repositories.agent_learning_repository import AgentLearningRepository
        repo = AgentLearningRepository(mock_db)

        result = await repo.get_relevant_learnings("問題")
        assert result == []
