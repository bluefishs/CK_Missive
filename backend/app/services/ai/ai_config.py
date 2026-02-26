"""
AI 配置管理

Version: 2.1.0
Created: 2026-02-04
Updated: 2026-02-26 - v2.1.0 新增 agency_match / hybrid_semantic / graph_cache 閾值
"""

import os
from dataclasses import dataclass
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
    ollama_model: str = "qwen3:4b"

    # 超時設定 (秒)
    cloud_timeout: int = 30
    local_timeout: int = 60

    # 生成設定
    default_temperature: float = 0.7
    summary_max_tokens: int = 256
    classify_max_tokens: int = 128
    keywords_max_tokens: int = 64

    # 速率限制
    rate_limit_requests: int = 30  # Groq 免費方案: 30 req/min
    rate_limit_window: int = 60  # 時間窗口 (秒)

    # 快取設定
    cache_enabled: bool = True
    cache_ttl_summary: int = 3600
    cache_ttl_classify: int = 3600
    cache_ttl_keywords: int = 3600

    # RAG 問答 (v2.0.0 新增)
    rag_top_k: int = 5                         # 預設檢索文件數
    rag_similarity_threshold: float = 0.3      # 最低相似度門檻
    rag_max_context_chars: int = 6000          # LLM 上下文最大字數
    rag_max_history_turns: int = 4             # 多輪對話保留輪數
    rag_temperature: float = 0.3              # RAG 生成溫度
    rag_max_tokens: int = 1024                 # RAG 生成最大 tokens

    # NER 實體提取 (v2.0.0 新增)
    ner_min_confidence: float = 0.6            # 實體最低信心度
    ner_max_input_chars: int = 2000            # 提取輸入最大字數
    ner_batch_size: int = 10                   # 批次提取每批數量

    # Embedding (v2.0.0 新增)
    embedding_dimension: int = 768             # 向量維度 (nomic-embed-text)
    embedding_cache_max_size: int = 500        # LRU 快取大小
    embedding_cache_ttl: int = 1800            # 快取 TTL (秒)
    embedding_max_text_chars: int = 8000       # 文字截斷長度

    # 知識圖譜 (v2.0.0 新增)
    kg_fuzzy_threshold: float = 0.75           # 模糊匹配相似度閾值
    kg_semantic_distance: float = 0.15         # 語意匹配距離閾值
    kg_max_neighbors_depth: int = 3            # 鄰居查詢最大深度

    # 語意搜尋 (v2.0.0 新增)
    search_vector_threshold: float = 0.88      # 向量語意匹配閾值
    search_intent_timeout: int = 10            # 意圖解析超時 (秒)
    search_query_timeout: int = 20             # 查詢執行超時 (秒)

    # 機關匹配 + 混合搜尋 (v2.1.0 新增)
    agency_match_threshold: float = 0.7        # 機關名稱匹配最低信心度
    hybrid_semantic_weight: float = 0.4        # 混合搜尋中語意權重 (0-1)

    # 圖譜查詢快取 (v2.1.0 新增)
    graph_cache_ttl_detail: int = 300          # 實體詳情快取 TTL (秒)
    graph_cache_ttl_neighbors: int = 300       # 鄰居查詢快取 TTL (秒)
    graph_cache_ttl_search: int = 120          # 搜尋快取 TTL (秒)
    graph_cache_ttl_stats: int = 1800          # 統計快取 TTL (秒)

    @classmethod
    def from_env(cls) -> "AIConfig":
        """從環境變數建立配置"""
        return cls(
            enabled=os.getenv("AI_ENABLED", "true").lower() == "true",
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            groq_model=os.getenv("AI_DEFAULT_MODEL", "llama-3.3-70b-versatile"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen3:4b"),
            cloud_timeout=int(os.getenv("AI_CLOUD_TIMEOUT", "30")),
            local_timeout=int(os.getenv("AI_LOCAL_TIMEOUT", "60")),
            rate_limit_requests=int(os.getenv("AI_RATE_LIMIT_REQUESTS", "30")),
            rate_limit_window=int(os.getenv("AI_RATE_LIMIT_WINDOW", "60")),
            cache_enabled=os.getenv("AI_CACHE_ENABLED", "true").lower() == "true",
            cache_ttl_summary=int(os.getenv("AI_CACHE_TTL_SUMMARY", "3600")),
            cache_ttl_classify=int(os.getenv("AI_CACHE_TTL_CLASSIFY", "3600")),
            cache_ttl_keywords=int(os.getenv("AI_CACHE_TTL_KEYWORDS", "3600")),
            # RAG
            rag_top_k=int(os.getenv("RAG_TOP_K", "5")),
            rag_similarity_threshold=float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.3")),
            rag_max_context_chars=int(os.getenv("RAG_MAX_CONTEXT_CHARS", "6000")),
            rag_max_history_turns=int(os.getenv("RAG_MAX_HISTORY_TURNS", "4")),
            rag_temperature=float(os.getenv("RAG_TEMPERATURE", "0.3")),
            rag_max_tokens=int(os.getenv("RAG_MAX_TOKENS", "1024")),
            # NER
            ner_min_confidence=float(os.getenv("NER_MIN_CONFIDENCE", "0.6")),
            ner_max_input_chars=int(os.getenv("NER_MAX_INPUT_CHARS", "2000")),
            ner_batch_size=int(os.getenv("NER_BATCH_SIZE", "10")),
            # Embedding
            embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "768")),
            embedding_cache_max_size=int(os.getenv("EMBEDDING_CACHE_MAX_SIZE", "500")),
            embedding_cache_ttl=int(os.getenv("EMBEDDING_CACHE_TTL", "1800")),
            embedding_max_text_chars=int(os.getenv("EMBEDDING_MAX_TEXT_CHARS", "8000")),
            # 知識圖譜
            kg_fuzzy_threshold=float(os.getenv("KG_FUZZY_THRESHOLD", "0.75")),
            kg_semantic_distance=float(os.getenv("KG_SEMANTIC_DISTANCE", "0.15")),
            kg_max_neighbors_depth=int(os.getenv("KG_MAX_NEIGHBORS_DEPTH", "3")),
            # 語意搜尋
            search_vector_threshold=float(os.getenv("SEARCH_VECTOR_THRESHOLD", "0.88")),
            search_intent_timeout=int(os.getenv("SEARCH_INTENT_TIMEOUT", "10")),
            search_query_timeout=int(os.getenv("SEARCH_QUERY_TIMEOUT", "20")),
            # 機關匹配 + 混合搜尋
            agency_match_threshold=float(os.getenv("AGENCY_MATCH_THRESHOLD", "0.7")),
            hybrid_semantic_weight=float(os.getenv("HYBRID_SEMANTIC_WEIGHT", "0.4")),
            # 圖譜查詢快取
            graph_cache_ttl_detail=int(os.getenv("GRAPH_CACHE_TTL_DETAIL", "300")),
            graph_cache_ttl_neighbors=int(os.getenv("GRAPH_CACHE_TTL_NEIGHBORS", "300")),
            graph_cache_ttl_search=int(os.getenv("GRAPH_CACHE_TTL_SEARCH", "120")),
            graph_cache_ttl_stats=int(os.getenv("GRAPH_CACHE_TTL_STATS", "1800")),
        )


# 全域配置實例
_ai_config: Optional[AIConfig] = None


def get_ai_config() -> AIConfig:
    """獲取 AI 配置實例 (Singleton)"""
    global _ai_config
    if _ai_config is None:
        _ai_config = AIConfig.from_env()
    return _ai_config
