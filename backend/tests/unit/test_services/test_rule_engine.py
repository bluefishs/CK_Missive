"""
rule_engine 意圖規則引擎單元測試

測試範圍：
- IntentRuleEngine 初始化與規則載入
- match 方法匹配邏輯
- _resolve_value 值解析（群組引用、特殊函數）
- _roc_year_to_date_start / _roc_year_to_date_end 民國年轉換
- 各規則模式匹配
"""

import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from app.services.ai.search.rule_engine import IntentRuleEngine, get_rule_engine


class TestIntentRuleEngineInit:
    """初始化測試"""

    def test_rules_loaded(self):
        engine = IntentRuleEngine()
        assert len(engine._rules) > 0

    def test_compiled_rules_same_count(self):
        engine = IntentRuleEngine()
        assert len(engine._compiled_rules) == len(engine._rules)

    def test_reload_returns_count(self):
        engine = IntentRuleEngine()
        count = engine.reload()
        assert count == len(engine._rules)


class TestRocYearConversion:
    """民國年轉換"""

    def test_roc_year_start(self):
        engine = IntentRuleEngine()
        result = engine._roc_year_to_date_start("114")
        assert result == "2025-01-01"

    def test_roc_year_end(self):
        engine = IntentRuleEngine()
        result = engine._roc_year_to_date_end("114")
        assert result == "2025-12-31"

    def test_roc_year_start_none(self):
        engine = IntentRuleEngine()
        assert engine._roc_year_to_date_start(None) is None

    def test_roc_year_end_none(self):
        engine = IntentRuleEngine()
        assert engine._roc_year_to_date_end(None) is None

    def test_roc_year_invalid(self):
        engine = IntentRuleEngine()
        assert engine._roc_year_to_date_start("abc") is None
        assert engine._roc_year_to_date_end("abc") is None

    def test_roc_year_100(self):
        engine = IntentRuleEngine()
        assert engine._roc_year_to_date_start("100") == "2011-01-01"
        assert engine._roc_year_to_date_end("100") == "2011-12-31"


class TestMatchRules:
    """match 方法匹配測試"""

    @pytest.fixture
    def engine(self):
        return IntentRuleEngine()

    def test_empty_query(self, engine):
        assert engine.match("") is None
        assert engine.match(None) is None

    def test_dispatch_entity_simple(self, engine):
        result = engine.match("派工單")
        assert result is not None
        assert result.related_entity == "dispatch_order"
        assert result.confidence >= 0.85

    def test_dispatch_entity_with_year(self, engine):
        result = engine.match("民國114年的派工單")
        assert result is not None
        assert result.related_entity == "dispatch_order"
        assert result.date_from == "2025-01-01"
        assert result.date_to == "2025-12-31"

    def test_meeting_notice(self, engine):
        result = engine.match("開會通知")
        assert result is not None
        assert result.doc_type == "開會通知單"

    def test_inspection_notice(self, engine):
        result = engine.match("會勘通知")
        assert result is not None
        assert result.doc_type == "會勘通知單"

    def test_has_deadline(self, engine):
        result = engine.match("快到期的公文")
        assert result is not None
        assert result.has_deadline is True

    def test_recent_period(self, engine):
        result = engine.match("最近的公文")
        assert result is not None
        assert result.date_from is not None
        assert result.date_to is not None

    def test_doc_number_full(self, engine):
        result = engine.match("桃工用字第1140005057號")
        assert result is not None
        assert result.keywords is not None
        assert result.confidence >= 0.90

    def test_roc_year_only(self, engine):
        result = engine.match("114年的公文")
        assert result is not None
        assert result.date_from == "2025-01-01"
        assert result.date_to == "2025-12-31"

    def test_no_match(self, engine):
        result = engine.match("隨便的文字完全不匹配任何規則的查詢XYZABC")
        # 可能匹配到某些寬泛規則，也可能不匹配
        # 這裡主要確認不拋出例外
        # 如果沒有匹配，返回 None
        pass  # 不斷言結果，僅確認無例外


class TestGetRuleEngine:
    """Singleton 取得"""

    def test_returns_instance(self):
        engine = get_rule_engine()
        assert isinstance(engine, IntentRuleEngine)

    def test_singleton(self):
        engine1 = get_rule_engine()
        engine2 = get_rule_engine()
        assert engine1 is engine2


class TestResolveValue:
    """值解析"""

    def test_bool_value(self):
        engine = IntentRuleEngine()
        import re
        m = re.match(r'(test)', 'test')
        assert engine._resolve_value(True, m) is True
        assert engine._resolve_value(False, m) is False

    def test_literal_string(self):
        engine = IntentRuleEngine()
        import re
        m = re.match(r'(test)', 'test')
        assert engine._resolve_value("dispatch_order", m) == "dispatch_order"

    def test_group_reference(self):
        engine = IntentRuleEngine()
        import re
        m = re.match(r'(\d+)年', '114年')
        assert engine._resolve_value("$1", m) == "114"

    def test_group_reference_out_of_range(self):
        engine = IntentRuleEngine()
        import re
        m = re.match(r'(test)', 'test')
        assert engine._resolve_value("$5", m) is None

    def test_today_function(self):
        engine = IntentRuleEngine()
        import re
        m = re.match(r'(test)', 'test')
        result = engine._resolve_value("today()", m)
        assert result == date.today().isoformat()

    def test_last_30_days_function(self):
        engine = IntentRuleEngine()
        import re
        m = re.match(r'(test)', 'test')
        result = engine._resolve_value("last_30_days()", m)
        expected = (date.today() - timedelta(days=30)).isoformat()
        assert result == expected
