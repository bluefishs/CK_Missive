"""
AI 搜尋模組

意圖解析、RAG 問答、重排序、同義詞擴展、規則引擎。
"""

__all__ = [
    "RAGQueryService",
    "IntentRuleEngine",
    "get_rule_engine",
    "SearchIntentParser",
    "SynonymExpander",
]


def __getattr__(name: str):
    if name == "RAGQueryService":
        from .rag_query_service import RAGQueryService
        return RAGQueryService
    if name in ("IntentRuleEngine", "get_rule_engine"):
        from . import rule_engine
        return getattr(rule_engine, name)
    if name == "SearchIntentParser":
        from .search_intent_parser import SearchIntentParser
        return SearchIntentParser
    if name == "SynonymExpander":
        from .synonym_expander import SynonymExpander
        return SynonymExpander
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
