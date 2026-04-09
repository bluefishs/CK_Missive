"""
AI 意圖解析規則引擎

Version: 2.1.0
Created: 2026-02-09
Updated: 2026-03-06 - 狀態/機關映射改委託 SynonymExpander (DB SSOT)

Layer 1 規則引擎 -- 處理常見、明確的查詢模式。
高信心度 (>=0.85) 才直接返回，否則返回部分匹配結果供 Layer 2 (LLM) 合併。
"""
import logging
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from app.schemas.ai.search import ParsedSearchIntent

logger = logging.getLogger(__name__)


class IntentRuleEngine:
    """意圖規則引擎 -- 正則/關鍵字匹配"""

    # 高信心度閾值（直接返回）
    HIGH_CONFIDENCE_THRESHOLD = 0.85

    def __init__(self) -> None:
        self._rules: List[Dict[str, Any]] = []
        self._compiled_rules: List[Tuple[re.Pattern[str], Dict[str, Any]]] = []
        self._load_rules()

    def _load_rules(self) -> None:
        """從 YAML 載入規則"""
        yaml_path = Path(__file__).parent.parent / "intent_rules.yaml"
        try:
            if yaml_path.exists():
                with open(yaml_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                self._rules = data.get("rules", [])
                self._compile_rules()
                logger.info(f"規則引擎載入 {len(self._rules)} 條規則")
            else:
                logger.warning(f"規則引擎配置檔不存在: {yaml_path}")
        except Exception as e:
            logger.error(f"規則引擎載入失敗: {e}")

    def _compile_rules(self) -> None:
        """預編譯正則表達式"""
        self._compiled_rules = []
        for rule in self._rules:
            try:
                pattern = re.compile(rule["pattern"], re.IGNORECASE)
                self._compiled_rules.append((pattern, rule))
            except re.error as e:
                logger.error(f"規則 '{rule.get('name')}' 正則編譯失敗: {e}")

    def reload(self) -> int:
        """重新載入規則（Hot Reload）"""
        self._load_rules()
        return len(self._rules)

    def match(self, query: str) -> Optional[ParsedSearchIntent]:
        """
        嘗試規則匹配

        Returns:
            ParsedSearchIntent 或 None（無匹配）
        """
        if not query or not self._compiled_rules:
            return None

        query = query.strip()
        best_match: Optional[ParsedSearchIntent] = None
        best_confidence = 0.0

        for pattern, rule in self._compiled_rules:
            m = pattern.search(query)
            if m:
                try:
                    intent = self._extract_intent(m, rule)
                    if intent and intent.confidence > best_confidence:
                        best_match = intent
                        best_confidence = intent.confidence
                except Exception as e:
                    logger.warning(f"規則 '{rule.get('name')}' 提取失敗: {e}")

        if best_match:
            logger.info(
                f"規則引擎匹配: query='{query}', "
                f"confidence={best_match.confidence:.2f}"
            )

        return best_match

    def _extract_intent(
        self, match: re.Match[str], rule: Dict[str, Any]
    ) -> Optional[ParsedSearchIntent]:
        """從正則匹配結果提取意圖"""
        extract = rule.get("extract", {})
        confidence = rule.get("confidence", 0.85)
        intent_data: Dict[str, Any] = {"confidence": confidence}

        for field, value_spec in extract.items():
            resolved = self._resolve_value(value_spec, match)
            if resolved is not None:
                # keywords 欄位需要是 List[str]
                if field == "keywords" and isinstance(resolved, str):
                    resolved = [resolved]
                intent_data[field] = resolved

        # 至少有一個有效欄位才返回
        valid_fields = {
            k for k in intent_data
            if k != "confidence" and intent_data[k] is not None
        }
        if not valid_fields:
            return None

        return ParsedSearchIntent(**intent_data)

    def _resolve_value(self, spec: Any, match: re.Match[str]) -> Any:
        """解析值規格"""
        if isinstance(spec, bool):
            return spec

        if not isinstance(spec, str):
            return spec

        # 正則群組引用: "$1", "$2"
        if spec.startswith("$"):
            group_idx = int(spec[1:])
            return match.group(group_idx) if group_idx <= len(match.groups()) else None

        # 特殊函數
        if spec.startswith("roc_year_start("):
            roc_str = self._resolve_value(spec[15:-1], match)
            return self._roc_year_to_date_start(roc_str)

        if spec.startswith("roc_year_end("):
            roc_str = self._resolve_value(spec[13:-1], match)
            return self._roc_year_to_date_end(roc_str)

        if spec == "today()":
            return date.today().isoformat()

        if spec == "last_30_days()":
            return (date.today() - timedelta(days=30)).isoformat()

        if spec == "month_start()":
            today = date.today()
            return today.replace(day=1).isoformat()

        if spec == "last_month_start()":
            today = date.today()
            first = today.replace(day=1)
            last_month = first - timedelta(days=1)
            return last_month.replace(day=1).isoformat()

        if spec == "last_month_end()":
            today = date.today()
            first = today.replace(day=1)
            return (first - timedelta(days=1)).isoformat()

        if spec == "quarter_start()":
            today = date.today()
            q = (today.month - 1) // 3
            return today.replace(month=q * 3 + 1, day=1).isoformat()

        if spec == "last_quarter_start()":
            today = date.today()
            q = (today.month - 1) // 3
            if q == 0:
                return f"{today.year - 1}-10-01"
            return today.replace(month=(q - 1) * 3 + 1, day=1).isoformat()

        if spec == "last_quarter_end()":
            today = date.today()
            q = (today.month - 1) // 3
            if q == 0:
                return f"{today.year - 1}-12-31"
            end_month = q * 3
            if end_month == 12:
                return f"{today.year}-12-31"
            return (today.replace(month=end_month + 1, day=1) - timedelta(days=1)).isoformat()

        if spec.startswith("normalize_status("):
            raw = self._resolve_value(spec[17:-1], match)
            if not raw:
                return None
            from app.services.ai.synonym_expander import SynonymExpander
            status_map = SynonymExpander.get_status_normalize()
            return status_map.get(raw, raw)

        if spec.startswith("expand_agency("):
            raw = self._resolve_value(spec[14:-1], match)
            return self._expand_agency(raw) if raw else None

        # 字面值
        return spec

    def _roc_year_to_date_start(self, roc_str: Optional[str]) -> Optional[str]:
        """民國年 -> 西元年起始日"""
        if not roc_str:
            return None
        try:
            roc_year = int(roc_str)
            western_year = roc_year + 1911
            return f"{western_year}-01-01"
        except ValueError:
            return None

    def _roc_year_to_date_end(self, roc_str: Optional[str]) -> Optional[str]:
        """民國年 -> 西元年結束日"""
        if not roc_str:
            return None
        try:
            roc_year = int(roc_str)
            western_year = roc_year + 1911
            return f"{western_year}-12-31"
        except ValueError:
            return None

    def _expand_agency(self, name: str) -> str:
        """機關縮寫轉全稱（委託 SynonymExpander，走 DB 統一資料源）"""
        from app.services.ai.synonym_expander import SynonymExpander
        return SynonymExpander.expand_agency(name)


# 全域規則引擎實例 (Singleton)
_rule_engine: Optional[IntentRuleEngine] = None


def get_rule_engine() -> IntentRuleEngine:
    """獲取規則引擎實例"""
    global _rule_engine
    if _rule_engine is None:
        _rule_engine = IntentRuleEngine()
    return _rule_engine
