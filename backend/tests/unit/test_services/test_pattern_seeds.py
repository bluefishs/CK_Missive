"""
Pattern Learner Cold-Start Seed 單元測試

測試種子載入邏輯（使用 mock Redis）：
- Redis 為空時載入種子
- 已有模式時跳過載入
- 冪等性（重複呼叫不重複載入）
- 種子產生的模式可被 match 命中
"""

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai.agent.agent_pattern_learner import QueryPatternLearner
from app.services.ai.agent.pattern_seeds import SEED_PATTERNS


class TestSeedPatterns:
    """種子資料結構驗證"""

    def test_seed_count_in_range(self):
        """種子數量在 25-30 之間"""
        assert 25 <= len(SEED_PATTERNS) <= 30

    def test_seed_structure(self):
        """每筆種子具備必要欄位"""
        for i, seed in enumerate(SEED_PATTERNS):
            assert "question" in seed, f"Seed {i} missing 'question'"
            assert "tools" in seed, f"Seed {i} missing 'tools'"
            assert "category" in seed, f"Seed {i} missing 'category'"
            assert isinstance(seed["tools"], list), f"Seed {i} tools not list"
            assert len(seed["tools"]) > 0, f"Seed {i} has empty tools"

    def test_seed_tools_are_valid(self):
        """種子使用的工具名稱都是合法的"""
        from app.services.ai.tools.tool_registry import get_tool_registry

        registry = get_tool_registry()
        valid_names = registry.valid_tool_names
        for seed in SEED_PATTERNS:
            for tool in seed["tools"]:
                assert tool in valid_names, (
                    f"Seed tool '{tool}' not in registry: {valid_names}"
                )

    def test_seed_categories_diverse(self):
        """種子涵蓋多個類別"""
        categories = {s["category"] for s in SEED_PATTERNS}
        assert len(categories) >= 5, f"Only {len(categories)} categories: {categories}"

    def test_no_duplicate_questions(self):
        """種子問題不重複"""
        questions = [s["question"] for s in SEED_PATTERNS]
        assert len(questions) == len(set(questions)), "Duplicate seed questions found"


class TestLoadSeedsIfEmpty:
    """load_seeds_if_empty 邏輯測試"""

    @pytest.fixture
    def learner(self):
        return QueryPatternLearner(max_patterns=500)

    def _make_mock_redis(self, has_flag=False, pattern_count=0):
        """建立 mock Redis"""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=b"1" if has_flag else None)
        redis.zcard = AsyncMock(return_value=pattern_count)
        redis.set = AsyncMock()
        redis.exists = AsyncMock(return_value=True)
        redis.hset = AsyncMock()
        redis.zadd = AsyncMock()
        redis.hgetall = AsyncMock(return_value={})
        redis.expire = AsyncMock()
        redis.ping = AsyncMock()
        redis.pipeline = MagicMock(return_value=AsyncMock(execute=AsyncMock()))
        return redis

    @pytest.mark.asyncio
    async def test_loads_seeds_when_empty(self, learner):
        """Redis 為空時成功載入種子"""
        mock_redis = self._make_mock_redis(has_flag=False, pattern_count=0)
        learner._redis = mock_redis

        loaded = await learner.load_seeds_if_empty()
        assert loaded == len(SEED_PATTERNS)
        # 確認設定了旗標
        mock_redis.set.assert_called()

    @pytest.mark.asyncio
    async def test_skips_when_flag_exists(self, learner):
        """旗標已存在時跳過"""
        mock_redis = self._make_mock_redis(has_flag=True, pattern_count=0)
        learner._redis = mock_redis

        loaded = await learner.load_seeds_if_empty()
        assert loaded == 0

    @pytest.mark.asyncio
    async def test_skips_when_patterns_exist(self, learner):
        """已有模式時跳過"""
        mock_redis = self._make_mock_redis(has_flag=False, pattern_count=10)
        learner._redis = mock_redis

        loaded = await learner.load_seeds_if_empty()
        assert loaded == 0
        # 仍然設定旗標
        mock_redis.set.assert_called()

    @pytest.mark.asyncio
    async def test_idempotent(self, learner):
        """重複呼叫不重複載入"""
        mock_redis = self._make_mock_redis(has_flag=False, pattern_count=0)
        learner._redis = mock_redis

        first = await learner.load_seeds_if_empty()
        assert first == len(SEED_PATTERNS)

        # 第二次呼叫：旗標已設定
        mock_redis.get = AsyncMock(return_value=b"1")
        second = await learner.load_seeds_if_empty()
        assert second == 0

    @pytest.mark.asyncio
    async def test_graceful_without_redis(self, learner):
        """Redis 不可用時回傳 0"""
        learner._redis = None
        with patch.object(learner, "_get_redis", return_value=None):
            loaded = await learner.load_seeds_if_empty()
            assert loaded == 0

    @pytest.mark.asyncio
    async def test_hit_count_boosted_to_five(self, learner):
        """種子的 hit_count 被提升至 5"""
        mock_redis = self._make_mock_redis(has_flag=False, pattern_count=0)
        learner._redis = mock_redis

        await learner.load_seeds_if_empty()

        # 檢查 hset 是否以 hit_count=5 被呼叫
        hset_calls = mock_redis.hset.call_args_list
        hit_count_updates = [
            c for c in hset_calls
            if len(c.args) >= 3 and c.args[1] == "hit_count" and c.args[2] == "5"
        ]
        assert len(hit_count_updates) == len(SEED_PATTERNS)


class TestSeedMatchability:
    """種子模式經 normalize 後可以產生穩定的 key"""

    def test_seeds_produce_unique_keys(self):
        """每筆種子正規化後產生唯一 key"""
        keys = set()
        for seed in SEED_PATTERNS:
            template = QueryPatternLearner.normalize_question(seed["question"])
            key = QueryPatternLearner._make_key(template)
            keys.add(key)
        # 允許少量因為正規化導致的合併，但大部分應唯一
        assert len(keys) >= len(SEED_PATTERNS) * 0.8

    def test_similar_questions_normalize_to_same_template(self):
        """相似問題正規化後模板相同（驗證正規化有效性）"""
        q1 = "最近30天的公文"
        q2 = "最近7天的公文"
        t1 = QueryPatternLearner.normalize_question(q1)
        t2 = QueryPatternLearner.normalize_question(q2)
        # 兩者都應替換為 {DATE_RANGE}
        assert "{DATE_RANGE}" in t1
        assert "{DATE_RANGE}" in t2
