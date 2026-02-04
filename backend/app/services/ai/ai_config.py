"""
AI 配置管理

Version: 1.1.0
Created: 2026-02-04
Updated: 2026-02-05 - 新增速率限制與快取配置
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AIConfig:
    """AI 服務配置"""

    # 功能開關
    enabled: bool = True

    # Groq API
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # 超時設定 (秒)
    cloud_timeout: int = 30
    local_timeout: int = 60

    # 生成設定
    default_temperature: float = 0.7
    summary_max_tokens: int = 256
    classify_max_tokens: int = 128
    keywords_max_tokens: int = 64

    # 速率限制 (v1.1.0 新增)
    rate_limit_requests: int = 30  # Groq 免費方案: 30 req/min
    rate_limit_window: int = 60  # 時間窗口 (秒)

    # 快取設定 (v1.1.0 新增)
    cache_enabled: bool = True
    cache_ttl_summary: int = 3600  # 摘要快取 1 小時
    cache_ttl_classify: int = 3600  # 分類快取 1 小時
    cache_ttl_keywords: int = 3600  # 關鍵字快取 1 小時

    @classmethod
    def from_env(cls) -> "AIConfig":
        """從環境變數建立配置"""
        return cls(
            enabled=os.getenv("AI_ENABLED", "true").lower() == "true",
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            groq_model=os.getenv("AI_DEFAULT_MODEL", "llama-3.3-70b-versatile"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            cloud_timeout=int(os.getenv("AI_CLOUD_TIMEOUT", "30")),
            local_timeout=int(os.getenv("AI_LOCAL_TIMEOUT", "60")),
            rate_limit_requests=int(os.getenv("AI_RATE_LIMIT_REQUESTS", "30")),
            rate_limit_window=int(os.getenv("AI_RATE_LIMIT_WINDOW", "60")),
            cache_enabled=os.getenv("AI_CACHE_ENABLED", "true").lower() == "true",
            cache_ttl_summary=int(os.getenv("AI_CACHE_TTL_SUMMARY", "3600")),
            cache_ttl_classify=int(os.getenv("AI_CACHE_TTL_CLASSIFY", "3600")),
            cache_ttl_keywords=int(os.getenv("AI_CACHE_TTL_KEYWORDS", "3600")),
        )


# 全域配置實例
_ai_config: Optional[AIConfig] = None


def get_ai_config() -> AIConfig:
    """獲取 AI 配置實例 (Singleton)"""
    global _ai_config
    if _ai_config is None:
        _ai_config = AIConfig.from_env()
    return _ai_config
