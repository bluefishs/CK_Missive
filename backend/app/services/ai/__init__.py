"""
AI 服務模組

Version: 1.0.0
Created: 2026-02-04

此模組提供公文管理系統的 AI 智慧功能：
- 公文摘要生成
- 分類建議
- 關鍵字提取
- 機關匹配強化
"""

from .ai_config import AIConfig, get_ai_config
from .base_ai_service import BaseAIService
from .document_ai_service import DocumentAIService

__all__ = [
    "AIConfig",
    "get_ai_config",
    "BaseAIService",
    "DocumentAIService",
]
