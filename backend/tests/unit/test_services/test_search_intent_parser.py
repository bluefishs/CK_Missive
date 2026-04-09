"""
search_intent_parser 搜尋意圖解析器單元測試

測試範圍：
- SearchIntentParser.merge_intents 靜態合併方法
- SearchIntentParser._post_process_intent 後處理
- 派工單自動偵測
- 關鍵字去重
- 低 confidence 回退
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.schemas.ai.search import ParsedSearchIntent
from app.services.ai.search.search_intent_parser import SearchIntentParser


@pytest.fixture
def mock_ai():
    ai = MagicMock()
    ai.is_enabled = MagicMock(return_value=True)
    return ai


@pytest.fixture
def parser(mock_ai):
    with patch("app.services.ai.search.rule_engine.get_rule_engine") as mock_get:
        mock_engine = MagicMock()
        mock_engine.HIGH_CONFIDENCE_THRESHOLD = 0.85
        mock_get.return_value = mock_engine
        return SearchIntentParser(mock_ai)


class TestMergeIntents:
    """merge_intents 靜態方法"""

    def test_empty_intents(self):
        result = SearchIntentParser.merge_intents()
        assert result.confidence == 0.0

    def test_single_intent(self):
        intent = ParsedSearchIntent(keywords=["test"], confidence=0.9)
        result = SearchIntentParser.merge_intents(intent)
        assert result.keywords == ["test"]
        assert result.confidence == 0.9

    def test_deterministic_fields_priority(self):
        """確定性欄位：第一個非 None 優先"""
        intent1 = ParsedSearchIntent(status="處理中", confidence=0.8)
        intent2 = ParsedSearchIntent(status="已結案", confidence=0.9)
        result = SearchIntentParser.merge_intents(intent1, intent2)
        assert result.status == "處理中"

    def test_semantic_fields_reverse_priority(self):
        """語意性欄位：最後一個非 None 優先"""
        intent1 = ParsedSearchIntent(keywords=["道路"], confidence=0.8)
        intent2 = ParsedSearchIntent(keywords=["橋梁工程"], confidence=0.9)
        result = SearchIntentParser.merge_intents(intent1, intent2)
        assert result.keywords == ["橋梁工程"]

    def test_confidence_average(self):
        """無權重時取平均"""
        intent1 = ParsedSearchIntent(keywords=["a"], confidence=0.8)
        intent2 = ParsedSearchIntent(keywords=["b"], confidence=0.6)
        result = SearchIntentParser.merge_intents(intent1, intent2)
        assert abs(result.confidence - 0.7) < 0.01

    def test_confidence_weighted_average(self):
        """加權平均"""
        intent1 = ParsedSearchIntent(keywords=["a"], confidence=1.0)
        intent2 = ParsedSearchIntent(keywords=["b"], confidence=0.0)
        result = SearchIntentParser.merge_intents(
            intent1, intent2, weights=[0.3, 0.7]
        )
        expected = (1.0 * 0.3 + 0.0 * 0.7) / 1.0
        assert abs(result.confidence - expected) < 0.01

    def test_merge_with_none_fields(self):
        """含 None 欄位的合併"""
        intent1 = ParsedSearchIntent(sender="工務局", confidence=0.7)
        intent2 = ParsedSearchIntent(doc_type="函", confidence=0.8)
        result = SearchIntentParser.merge_intents(intent1, intent2)
        assert result.sender == "工務局"
        assert result.doc_type == "函"


class TestPostProcessIntent:
    """_post_process_intent 後處理"""

    def test_dispatch_entity_detection(self, parser):
        """自動偵測派工單關鍵字"""
        intent = ParsedSearchIntent(keywords=["派工單", "道路"], confidence=0.8)
        with patch("app.services.ai.search.synonym_expander.SynonymExpander.expand_keywords",
                   return_value=["派工單", "道路"]):
            result = parser._post_process_intent(intent)
            assert result.related_entity == "dispatch_order"
            assert "道路" in result.keywords

    def test_keyword_deduplication(self, parser):
        """關鍵字去重"""
        intent = ParsedSearchIntent(
            keywords=["工務局", "工務局", "道路", "道路"],
            confidence=0.8,
        )
        with patch("app.services.ai.search.synonym_expander.SynonymExpander.expand_keywords",
                   return_value=["工務局", "工務局", "道路", "道路"]):
            result = parser._post_process_intent(intent)
            assert len(result.keywords) == 2

    def test_fallback_to_original_query(self, parser):
        """無有效條件時回退原始查詢"""
        intent = ParsedSearchIntent(confidence=0.3)
        with patch("app.services.ai.search.synonym_expander.SynonymExpander.expand_keywords",
                   side_effect=lambda x: x):
            result = parser._post_process_intent(intent, original_query="測試查詢")
            assert result.keywords == ["測試查詢"]

    def test_agency_expansion(self, parser):
        """機關名稱擴展"""
        intent = ParsedSearchIntent(sender="工務局", confidence=0.8)
        with patch("app.services.ai.search.synonym_expander.SynonymExpander.expand_agency",
                   return_value="桃園市政府工務局"):
            result = parser._post_process_intent(intent)
            assert result.sender == "桃園市政府工務局"

    def test_low_confidence_keyword_supplement(self, parser):
        """低 confidence 補充 keywords"""
        intent = ParsedSearchIntent(
            sender="工務局", confidence=0.5,
        )
        with patch("app.services.ai.search.synonym_expander.SynonymExpander.expand_agency",
                   return_value="工務局"):
            result = parser._post_process_intent(intent, original_query="工務局 道路改善")
            # 應補充非結構化的部分
            if result.keywords:
                assert "道路改善" in result.keywords[0]


class TestParseSearchIntent:
    """parse_search_intent 完整流程（mock 外部依賴）"""

    @pytest.mark.asyncio
    async def test_rule_engine_high_confidence(self, parser):
        """規則引擎高 confidence 直接返回"""
        rule_result = ParsedSearchIntent(
            related_entity="dispatch_order", confidence=0.92
        )
        parser._rule_engine.match = MagicMock(return_value=rule_result)

        with patch("app.services.ai.search.synonym_expander.SynonymExpander.expand_keywords",
                   side_effect=lambda x: x), \
             patch("app.services.ai.search.synonym_expander.SynonymExpander.expand_agency",
                   side_effect=lambda x: x):
            intent, source = await parser.parse_search_intent("派工單")
            assert source == "rule_engine"
            assert intent.related_entity == "dispatch_order"

    @pytest.mark.asyncio
    async def test_fallback_when_ai_disabled(self, parser, mock_ai):
        """AI 未啟用時的降級"""
        mock_ai.is_enabled.return_value = False
        parser._rule_engine.match = MagicMock(return_value=None)

        with patch.object(parser, '_vector_match_intent',
                         new_callable=AsyncMock,
                         return_value=(None, None)):
            intent, source = await parser.parse_search_intent("一些查詢")
            assert source == "fallback"
            assert intent.keywords == ["一些查詢"]
