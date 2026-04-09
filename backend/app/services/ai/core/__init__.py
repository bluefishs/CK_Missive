"""
AI 核心基礎模組

提供 AI 服務的基礎設施：配置、快取、限流、統計、嵌入向量、工具函數等。
"""

from .ai_config import AIConfig, get_ai_config
from .ai_cache import SimpleCache, RedisCache
from .ai_rate_limiter import RateLimiter
from .ai_stats_manager import AIStatsManager
from .base_ai_service import BaseAIService, get_rate_limiter, get_stats_manager
from .ai_prompt_manager import AIPromptManager
from .embedding_manager import EmbeddingManager
from .utils import (
    parse_json_safe,
    sse,
    sanitize_history,
    compute_adaptive_timeout,
    collect_sources,
)
from .name_utils import normalize_for_match, clean_agency_name, PRONOUN_ENTITY_BLACKLIST
from .thinking_filter import strip_thinking_from_synthesis
from .domain_prompts import (  # noqa: F401 — constants, re-exported for discoverability
    DISPATCH_STATUS_PROMPT,
    FINANCE_SUMMARY_PROMPT,
    DOCUMENT_ANALYSIS_PROMPT,
    DOCUMENT_STATS_PROMPT,
    PROJECT_PROGRESS_PROMPT,
    EXPENSE_REVIEW_PROMPT,
    ASSET_SUMMARY_PROMPT,
    TENDER_ANALYSIS_PROMPT,
    CROSS_TOOL_SYNTHESIS_PROMPT,
    CHITCHAT_RESPONSE_PROMPT,
)
from .token_usage_tracker import TokenUsageTracker, get_token_tracker
from .citation_validator import validate_citations
from .response_enricher import (
    enrich_dispatch_results,
    enrich_financial_results,
    enrich_document_results,
    enrich_project_results,
    enrich_expense_results,
    enrich_asset_results,
)

__all__ = [
    # config
    "AIConfig",
    "get_ai_config",
    # cache
    "SimpleCache",
    "RedisCache",
    # rate limiter
    "RateLimiter",
    # stats
    "AIStatsManager",
    "get_stats_manager",
    # base service
    "BaseAIService",
    "get_rate_limiter",
    # prompt
    "AIPromptManager",
    # embedding
    "EmbeddingManager",
    # utils
    "parse_json_safe",
    "sse",
    "sanitize_history",
    "compute_adaptive_timeout",
    "collect_sources",
    "normalize_for_match",
    "clean_agency_name",
    # thinking filter
    "strip_thinking_from_synthesis",
    # domain prompts
    "DISPATCH_STATUS_PROMPT",
    "FINANCE_SUMMARY_PROMPT",
    "DOCUMENT_ANALYSIS_PROMPT",
    "DOCUMENT_STATS_PROMPT",
    "PROJECT_PROGRESS_PROMPT",
    "EXPENSE_REVIEW_PROMPT",
    "ASSET_SUMMARY_PROMPT",
    "TENDER_ANALYSIS_PROMPT",
    "CROSS_TOOL_SYNTHESIS_PROMPT",
    "CHITCHAT_RESPONSE_PROMPT",
    # token tracker
    "TokenUsageTracker",
    "get_token_tracker",
    # citation
    "validate_citations",
    # response enricher
    "enrich_dispatch_results",
    "enrich_financial_results",
    "enrich_document_results",
    "enrich_project_results",
    "enrich_expense_results",
    "enrich_asset_results",
]
