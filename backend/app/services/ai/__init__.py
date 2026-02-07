"""
AI 服務模組

Version: 2.0.0
Created: 2026-02-04
Updated: 2026-02-07 - Redis 快取與統計持久化

此模組提供公文管理系統的 AI 智慧功能：
- 公文摘要生成
- 分類建議
- 關鍵字提取
- 機關匹配強化
- Redis 快取與統計持久化 (v2.0.0)
"""

from .ai_config import AIConfig, get_ai_config
from .base_ai_service import (
    BaseAIService,
    RedisCache,
    AIStatsManager,
    get_stats_manager,
)
from .document_ai_service import DocumentAIService

__all__ = [
    "AIConfig",
    "get_ai_config",
    "BaseAIService",
    "RedisCache",
    "AIStatsManager",
    "get_stats_manager",
    "DocumentAIService",
]
