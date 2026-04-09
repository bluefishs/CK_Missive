"""
Tests for UserQueryTracker (Phase 9.1-9.2).

Tests:
- Name extraction from tool results
- Interest classification (agency/project/doc_type/entity/topic)
- Redis tracking (mocked)
- Interest retrieval and summary formatting
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.ai.misc.user_query_tracker import (
    UserQueryTracker,
    classify_interest,
    _extract_names_from_tool_results,
    get_query_tracker,
    INTEREST_REDIS_PREFIX,
    INTEREST_TTL,
)


# ── Phase 9.2: Classification tests ──


class TestClassifyInterest:
    def test_agency_keywords(self):
        assert classify_interest("桃園市政府工務局") == "agency"
        assert classify_interest("養護工程處") == "agency"
        assert classify_interest("交通部公路總局") == "agency"
        assert classify_interest("桃園區公所") == "agency"

    def test_project_keywords(self):
        assert classify_interest("道路改善工程") == "project"
        assert classify_interest("XX標案") == "project"
        assert classify_interest("都市更新計畫") == "project"

    def test_document_type_keywords(self):
        assert classify_interest("函") == "document_type"
        assert classify_interest("開會通知") == "document_type"
        assert classify_interest("會議紀錄") == "document_type"

    def test_topic_keywords(self):
        assert classify_interest("預算") == "topic"
        assert classify_interest("施工品質") == "topic"
        assert classify_interest("驗收") == "topic"

    def test_fallback_to_entity(self):
        assert classify_interest("張三") == "entity"
        assert classify_interest("ABC") == "entity"


# ── Phase 9.1: Extraction tests ──


class TestExtractNames:
    def test_extract_from_documents(self):
        tool_results = [
            {
                "tool": "search_documents",
                "result": {
                    "documents": [
                        {"sender": "桃園市政府工務局", "receiver": "養護工程處", "subject": "道路維護"},
                        {"sender": "交通部", "receiver": "桃園市政府", "subject": "路權申請"},
                    ],
                    "count": 2,
                },
            }
        ]
        names = _extract_names_from_tool_results(tool_results)
        assert "桃園市政府工務局" in names
        assert "養護工程處" in names
        assert "交通部" in names
        assert "道路維護" in names

    def test_extract_from_entities(self):
        tool_results = [
            {
                "tool": "search_entities",
                "result": {
                    "entities": [
                        {"entity_name": "桃園市政府", "canonical_name": "桃園市政府"},
                        {"entity_name": "工務局", "canonical_name": "桃園市政府工務局"},
                    ],
                },
            }
        ]
        names = _extract_names_from_tool_results(tool_results)
        assert "桃園市政府" in names
        assert "工務局" in names
        assert "桃園市政府工務局" in names

    def test_extract_dedup(self):
        tool_results = [
            {
                "tool": "search_documents",
                "result": {
                    "documents": [
                        {"sender": "工務局", "receiver": "工務局"},
                    ],
                },
            }
        ]
        names = _extract_names_from_tool_results(tool_results)
        assert names.count("工務局") == 1

    def test_skip_short_names(self):
        tool_results = [
            {
                "tool": "search_documents",
                "result": {
                    "documents": [{"sender": "A", "receiver": ""}],
                },
            }
        ]
        names = _extract_names_from_tool_results(tool_results)
        assert len(names) == 0

    def test_skip_long_subjects(self):
        tool_results = [
            {
                "tool": "search_documents",
                "result": {
                    "documents": [
                        {"subject": "x" * 50, "sender": "工務局"},
                    ],
                },
            }
        ]
        names = _extract_names_from_tool_results(tool_results)
        assert "工務局" in names
        assert ("x" * 50) not in names

    def test_empty_results(self):
        assert _extract_names_from_tool_results([]) == []
        assert _extract_names_from_tool_results([{"tool": "x", "result": {}}]) == []

    def test_non_dict_result(self):
        assert _extract_names_from_tool_results([{"tool": "x", "result": "error"}]) == []

    def test_direct_fields(self):
        tool_results = [
            {
                "tool": "get_entity_detail",
                "result": {
                    "entity_name": "桃園市政府",
                    "agency_name": "工務局",
                },
            }
        ]
        names = _extract_names_from_tool_results(tool_results)
        assert "桃園市政府" in names
        assert "工務局" in names

    def test_dispatch_orders(self):
        tool_results = [
            {
                "tool": "search_dispatch_orders",
                "result": {
                    "dispatch_orders": [
                        {"name": "道路修補工程", "project_name": "XX改善計畫"},
                    ],
                },
            }
        ]
        names = _extract_names_from_tool_results(tool_results)
        assert "道路修補工程" in names
        assert "XX改善計畫" in names


# ── Phase 9.1: Tracker Redis tests ──


class TestUserQueryTracker:
    def _make_tracker(self, redis_mock):
        tracker = UserQueryTracker(redis=redis_mock)
        return tracker

    @pytest.mark.asyncio
    async def test_track_query_increments_redis(self):
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe

        tracker = self._make_tracker(mock_redis)
        tool_results = [
            {
                "tool": "search_documents",
                "result": {
                    "documents": [
                        {"sender": "桃園市政府工務局"},
                    ],
                },
            }
        ]

        count = await tracker.track_query("user123", "查工務局的公文", tool_results)

        assert count == 1
        mock_redis.pipeline.assert_called_once_with(transaction=False)
        mock_pipe.hincrby.assert_called_once_with(
            f"{INTEREST_REDIS_PREFIX}user123",
            "agency:桃園市政府工務局",
            1,
        )
        mock_pipe.expire.assert_called_once_with(
            f"{INTEREST_REDIS_PREFIX}user123",
            INTEREST_TTL,
        )
        mock_pipe.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_query_no_user_id(self):
        tracker = self._make_tracker(MagicMock())
        count = await tracker.track_query("", "test", [{"tool": "x", "result": {}}])
        assert count == 0

    @pytest.mark.asyncio
    async def test_track_query_no_results(self):
        tracker = self._make_tracker(MagicMock())
        count = await tracker.track_query("user1", "test", [])
        assert count == 0

    @pytest.mark.asyncio
    async def test_track_query_redis_error(self):
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.execute.side_effect = Exception("Redis down")
        mock_redis.pipeline.return_value = mock_pipe

        tracker = self._make_tracker(mock_redis)
        tool_results = [
            {"tool": "x", "result": {"entities": [{"entity_name": "test_entity"}]}},
        ]
        count = await tracker.track_query("user1", "q", tool_results)
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_interests_sorted(self):
        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {
            "agency:工務局": "5",
            "project:道路工程": "3",
            "entity:張三": "1",
        }

        tracker = self._make_tracker(mock_redis)
        interests = await tracker.get_interests("user1", top_n=2)

        assert len(interests) == 2
        assert interests[0]["name"] == "工務局"
        assert interests[0]["count"] == 5
        assert interests[0]["category"] == "agency"
        assert interests[1]["name"] == "道路工程"
        assert interests[1]["count"] == 3

    @pytest.mark.asyncio
    async def test_get_interests_empty(self):
        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {}

        tracker = self._make_tracker(mock_redis)
        interests = await tracker.get_interests("user1")
        assert interests == []

    @pytest.mark.asyncio
    async def test_get_interests_no_user(self):
        tracker = self._make_tracker(MagicMock())
        interests = await tracker.get_interests("")
        assert interests == []

    @pytest.mark.asyncio
    async def test_get_interest_summary(self):
        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {
            "agency:工務局": "5",
            "agency:養護處": "3",
            "project:道路工程": "2",
        }

        tracker = self._make_tracker(mock_redis)
        summary = await tracker.get_interest_summary("user1")

        assert "使用者關注領域" in summary
        assert "機關" in summary
        assert "工務局(5)" in summary
        assert "專案" in summary
        assert "道路工程(2)" in summary

    @pytest.mark.asyncio
    async def test_get_interest_summary_empty(self):
        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {}

        tracker = self._make_tracker(mock_redis)
        summary = await tracker.get_interest_summary("user1")
        assert summary == ""

    @pytest.mark.asyncio
    async def test_get_interests_malformed_field(self):
        """Fields without colon separator should fallback to entity category."""
        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {
            "legacy_name": "2",
        }

        tracker = self._make_tracker(mock_redis)
        interests = await tracker.get_interests("user1")
        assert len(interests) == 1
        assert interests[0]["category"] == "entity"
        assert interests[0]["name"] == "legacy_name"


# ── Singleton test ──


class TestGetQueryTracker:
    def test_singleton(self):
        # Reset singleton
        import app.services.ai.misc.user_query_tracker as mod
        mod._tracker_instance = None

        t1 = get_query_tracker()
        t2 = get_query_tracker()
        assert t1 is t2

        # Cleanup
        mod._tracker_instance = None


# ── Tracker without Redis (lazy init failure) ──


class TestTrackerNoRedis:
    @pytest.mark.asyncio
    async def test_track_query_no_redis(self):
        tracker = UserQueryTracker(redis=None)
        # Patch the lazy init to fail
        with patch("app.services.ai.misc.user_query_tracker.UserQueryTracker._get_redis", return_value=None):
            count = await tracker.track_query("user1", "test", [
                {"tool": "x", "result": {"entities": [{"entity_name": "ABC工務局"}]}},
            ])
            assert count == 0

    @pytest.mark.asyncio
    async def test_get_interests_no_redis(self):
        tracker = UserQueryTracker(redis=None)
        with patch("app.services.ai.misc.user_query_tracker.UserQueryTracker._get_redis", return_value=None):
            interests = await tracker.get_interests("user1")
            assert interests == []
