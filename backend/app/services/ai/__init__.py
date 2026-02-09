"""
AI 服務模組

Version: 2.1.0
Created: 2026-02-04
Updated: 2026-02-09 - 新增意圖規則引擎 (Layer 1)

此模組提供公文管理系統的 AI 智慧功能：
- 公文摘要生成
- 分類建議
- 關鍵字提取
- 機關匹配強化
- Redis 快取與統計持久化 (v2.0.0)
- 意圖規則引擎 (v2.1.0)
"""

from .ai_config import AIConfig, get_ai_config
from .base_ai_service import (
    BaseAIService,
    RedisCache,
    AIStatsManager,
    get_stats_manager,
)
from .document_ai_service import DocumentAIService
from .rule_engine import IntentRuleEngine, get_rule_engine

__all__ = [
    "AIConfig",
    "get_ai_config",
    "BaseAIService",
    "RedisCache",
    "AIStatsManager",
    "get_stats_manager",
    "DocumentAIService",
    "IntentRuleEngine",
    "get_rule_engine",
]
