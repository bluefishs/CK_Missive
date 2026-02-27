"""
AI 服務模組

Version: 3.1.0
Created: 2026-02-04
Updated: 2026-02-27 - Agent Orchestrator 模組化重構 (v2.0.0)

此模組提供公文管理系統的 AI 智慧功能：
- 公文摘要生成、分類建議、關鍵字提取、機關匹配
- AI Prompt 模板管理 (AIPromptManager)
- 四組件搜尋意圖解析 (SearchIntentParser)
- Agentic 文件檢索引擎 (AgentOrchestrator)
- Redis 快取與統計持久化
- 意圖規則引擎
"""

from .ai_config import AIConfig, get_ai_config
from .ai_prompt_manager import AIPromptManager
from .base_ai_service import (
    BaseAIService,
    RedisCache,
    AIStatsManager,
    get_stats_manager,
)
from .document_ai_service import DocumentAIService
from .rule_engine import IntentRuleEngine, get_rule_engine
from .search_intent_parser import SearchIntentParser
from .agent_orchestrator import AgentOrchestrator

__all__ = [
    "AIConfig",
    "get_ai_config",
    "AIPromptManager",
    "BaseAIService",
    "RedisCache",
    "AIStatsManager",
    "get_stats_manager",
    "DocumentAIService",
    "IntentRuleEngine",
    "get_rule_engine",
    "SearchIntentParser",
    "AgentOrchestrator",
]
