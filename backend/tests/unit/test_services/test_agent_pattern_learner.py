"""
QueryPatternLearner 單元測試

測試查詢模式學習邏輯（不依賴 Redis）:
- 問題正規化
- Pattern key 生成
- 衰減評分計算
- Few-shot 格式化
"""

import time
from unittest.mock import AsyncMock, patch

import pytest
from app.services.ai.agent_pattern_learner import QueryPattern, QueryPatternLearner
from app.services.ai.pattern_semantic_matcher import _cosine_similarity, _jaccard_match


class TestNormalizeQuestion:
    """問題正規化測試"""

    def test_org_replacement_from_hints(self):
        result = QueryPatternLearner.normalize_question(
            "工務局的函有幾件",
            {"sender": "工務局"},
        )
        assert "{ORG}" in result
        assert "工務局" not in result

    def test_date_replacement_yyyy_mm_dd(self):
        result = QueryPatternLearner.normalize_question("2026-03-14的公文")
        assert "{DATE}" in result
        assert "2026-03-14" not in result

    def test_date_replacement_yyyy_mm(self):
        result = QueryPatternLearner.normalize_question("2026年3月的統計")
        assert "{DATE}" in result

    def test_date_range_replacement(self):
        result = QueryPatternLearner.normalize_question("最近30天的公文")
        assert "{DATE_RANGE}" in result

    def test_minguo_date_replacement(self):
        result = QueryPatternLearner.normalize_question("民國115年的案件")
        assert "{DATE}" in result

    def test_doc_number_replacement(self):
        result = QueryPatternLearner.normalize_question("桃工養字第12345號的內容")
        assert "{DOC_NO}" in result

    def test_dispatch_number_replacement(self):
        result = QueryPatternLearner.normalize_question("派工單 123 的進度")
        assert "{DISPATCH_NO}" in result

    def test_count_replacement(self):
        result = QueryPatternLearner.normalize_question("最近5件公文")
        assert "{N}" in result

    def test_doc_type_replacement(self):
        result = QueryPatternLearner.normalize_question("工務局的函有多少")
        assert "{DOC_TYPE}" in result

    def test_multiple_replacements(self):
        result = QueryPatternLearner.normalize_question(
            "工務局在2026年3月發的函",
            {"sender": "工務局"},
        )
        assert "{ORG}" in result
        assert "{DATE}" in result

    def test_no_replacement_needed(self):
        result = QueryPatternLearner.normalize_question("什麼是知識圖譜")
        assert result == "什麼是知識圖譜"

    def test_empty_hints(self):
        result = QueryPatternLearner.normalize_question("查詢公文", {})
        assert "查詢公文" in result

    def test_receiver_replacement(self):
        result = QueryPatternLearner.normalize_question(
            "發給養工處的公文",
            {"receiver": "養工處"},
        )
        assert "{ORG}" in result

    def test_short_org_name_not_replaced(self):
        """單字機關名不應被替換（避免誤替換）"""
        result = QueryPatternLearner.normalize_question(
            "局長的函",
            {"sender": "局"},
        )
        # 單字 "局" 長度 < 2，不應替換
        assert "局" in result


class TestMakeKey:
    """Pattern key 生成"""

    def test_deterministic(self):
        key1 = QueryPatternLearner._make_key("{ORG}的{DOC_TYPE}")
        key2 = QueryPatternLearner._make_key("{ORG}的{DOC_TYPE}")
        assert key1 == key2

    def test_different_templates_different_keys(self):
        key1 = QueryPatternLearner._make_key("{ORG}的{DOC_TYPE}")
        key2 = QueryPatternLearner._make_key("{DATE}的統計")
        assert key1 != key2

    def test_key_length(self):
        key = QueryPatternLearner._make_key("test template")
        assert len(key) == 12


class TestCalcScore:
    """衰減評分計算"""

    def test_recent_high_hit(self):
        learner = QueryPatternLearner(decay_half_life=604800)
        score = learner._calc_score(10, 1.0, time.time())
        assert score > 9.0  # 近似 10 * 1.0 * ~1.0

    def test_old_pattern_decays(self):
        learner = QueryPatternLearner(decay_half_life=604800)
        old_time = time.time() - 604800  # 7 天前
        score = learner._calc_score(10, 1.0, old_time)
        assert 4.0 < score < 6.0  # 半衰期，約 5.0

    def test_low_success_rate_penalized(self):
        learner = QueryPatternLearner(decay_half_life=604800)
        score = learner._calc_score(10, 0.5, time.time())
        assert score < 6.0

    def test_zero_hits(self):
        learner = QueryPatternLearner(decay_half_life=604800)
        score = learner._calc_score(0, 1.0, time.time())
        assert score == 0.0


class TestFormatFewShot:
    """Few-shot 格式化"""

    def test_format_patterns(self):
        learner = QueryPatternLearner()
        patterns = [
            QueryPattern(
                pattern_key="abc",
                template="{ORG}的{DOC_TYPE}",
                tool_sequence=["search_documents"],
                params_template={},
                hit_count=5,
                avg_latency_ms=200,
            ),
        ]
        result = learner.format_as_few_shot(patterns)
        assert "歷史成功模式" in result
        assert "{ORG}的{DOC_TYPE}" in result
        assert "search_documents" in result

    def test_format_empty(self):
        learner = QueryPatternLearner()
        result = learner.format_as_few_shot([])
        assert result == ""

    def test_format_max_3(self):
        learner = QueryPatternLearner()
        patterns = [
            QueryPattern(
                pattern_key=f"k{i}",
                template=f"template_{i}",
                tool_sequence=["tool"],
                params_template={},
                hit_count=i,
            )
            for i in range(5)
        ]
        result = learner.format_as_few_shot(patterns)
        # Should only include 3 patterns
        assert result.count("命中") == 3


class TestCosineSimilarity:
    """餘弦相似度計算"""

    def test_identical_vectors(self):
        score = _cosine_similarity([1, 0, 0], [1, 0, 0])
        assert abs(score - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        score = _cosine_similarity([1, 0, 0], [0, 1, 0])
        assert abs(score) < 1e-6

    def test_similar_vectors(self):
        score = _cosine_similarity([1, 1, 0], [1, 0.9, 0])
        assert score > 0.99

    def test_zero_vector(self):
        score = _cosine_similarity([0, 0, 0], [1, 1, 0])
        assert score == 0.0

    def test_negative_correlation(self):
        score = _cosine_similarity([1, 0], [-1, 0])
        assert score < 0


class TestJaccardMatch:
    """Jaccard 字元相似度降級方案"""

    def test_identical_templates(self):
        candidates = [
            QueryPattern(
                pattern_key="a", template="{ORG}的{DOC_TYPE}有幾件",
                tool_sequence=["search_documents"], params_template={},
                hit_count=3,
            ),
        ]
        best, score = _jaccard_match(
            "{ORG}的{DOC_TYPE}有幾件", candidates
        )
        assert best is not None
        assert score == 1.0

    def test_similar_templates(self):
        candidates = [
            QueryPattern(
                pattern_key="a", template="{ORG}的{DOC_TYPE}有多少",
                tool_sequence=["search_documents"], params_template={},
                hit_count=3,
            ),
            QueryPattern(
                pattern_key="b", template="派工單{DISPATCH_NO}的進度",
                tool_sequence=["query_dispatch"], params_template={},
                hit_count=3,
            ),
        ]
        best, score = _jaccard_match(
            "{ORG}的{DOC_TYPE}有幾件", candidates
        )
        # Should match closer to template "a"
        assert best is not None
        assert best.pattern_key == "a"
        assert score > 0.5

    def test_no_candidates(self):
        best, score = _jaccard_match("test", [])
        assert best is None
        assert score == 0.0


class TestPatternLearnerNoRedis:
    """無 Redis 時的安全降級"""

    @pytest.mark.asyncio
    async def test_learn_no_redis_does_not_raise(self):
        learner = QueryPatternLearner()
        learner._get_redis = AsyncMock(return_value=None)
        await learner.learn(
            "工務局的函",
            {"sender": "工務局"},
            [{"name": "search_documents", "params": {}}],
            success=True,
        )

    @pytest.mark.asyncio
    async def test_match_no_redis_returns_empty(self):
        learner = QueryPatternLearner()
        learner._get_redis = AsyncMock(return_value=None)
        result = await learner.match("工務局的函")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_top_patterns_no_redis_returns_empty(self):
        learner = QueryPatternLearner()
        learner._get_redis = AsyncMock(return_value=None)
        result = await learner.get_top_patterns()
        assert result == []
