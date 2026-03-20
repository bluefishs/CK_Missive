"""
Agent 意圖前處理模組 — 從 agent_planner.py 提取

負責在 LLM 規劃前，透過 SearchIntentParser 4 層架構
提取結構化線索 (hints)，提高工具選擇與參數品質。

Extracted from agent_planner.py v2.9.0
Version: 1.0.0
"""

import logging
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)

# 文號正則 (e.g. 1130006974, 桃工用字第1130006974號)
_DOC_NUMBER_RE = re.compile(r'(\d{10})')


async def preprocess_question(question: str, db) -> Dict[str, Any]:
    """
    意圖預處理 — 共用 SearchIntentParser 完整 4 層架構

    Layer 1: 規則引擎（<5ms）
    Layer 2: 向量歷史意圖匹配（10-50ms）
    Layer 3: LLM 意圖解析（~500ms，已有快取）
    Merge:  多層合併

    在 LLM 規劃前先提取結構化線索，提高工具選擇與參數品質。
    """
    hints: Dict[str, Any] = {}

    # 文號偵測 — 精確匹配優先
    doc_num_match = _DOC_NUMBER_RE.search(question)
    if doc_num_match:
        hints["keywords"] = [doc_num_match.group(1)]
        hints["_doc_number_detected"] = True
        logger.info("文號偵測: %s", doc_num_match.group(1))

    try:
        from app.services.ai.base_ai_service import BaseAIService
        from app.services.ai.search_intent_parser import SearchIntentParser

        ai_service = BaseAIService()
        parser = SearchIntentParser(ai_service)
        intent, source = await parser.parse_search_intent(question, db)

        if intent.confidence >= 0.3:
            for field in ("sender", "receiver", "doc_type", "status",
                          "date_from", "date_to", "keywords",
                          "related_entity", "category"):
                val = getattr(intent, field, None)
                if val is not None:
                    hints[field] = val

            logger.info(
                "Agent preprocessing: %s extracted %d hints (conf=%.2f)",
                source, len(hints), intent.confidence,
            )
    except Exception as e:
        logger.warning("Agent preprocessing SearchIntentParser failed: %s", e)
        # Fallback: 僅用規則引擎
        try:
            from app.services.ai.rule_engine import get_rule_engine
            rule_engine = get_rule_engine()
            rule_result = rule_engine.match(question)
            if rule_result and rule_result.confidence >= 0.5:
                for field in ("sender", "receiver", "doc_type", "status",
                              "date_from", "date_to", "keywords", "related_entity"):
                    val = getattr(rule_result, field, None)
                    if val is not None:
                        hints[field] = val
                logger.info(
                    "Agent preprocessing fallback: rule engine %d hints (conf=%.2f)",
                    len(hints), rule_result.confidence,
                )
        except Exception as e2:
            logger.debug("Agent preprocessing rule engine fallback failed: %s", e2)

    return hints
