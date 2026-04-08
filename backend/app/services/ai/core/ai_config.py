"""
AI 配置管理

Version: 3.1.0
Created: 2026-02-04
Updated: 2026-03-18 - v3.1.0 NemoClaw-inspired: YAML policy + inference profiles
"""

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Resolve config directory relative to backend/config/
_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "config"


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
    ollama_model: str = "gemma4"

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
    embedding_cache_max_size: int = 2000       # LRU 快取大小（覆蓋 728 文件 + 查詢快取）
    embedding_cache_ttl: int = 3600            # 快取 TTL (秒)，Embedding 穩定可延長
    embedding_max_text_chars: int = 8000       # 文字截斷長度

    # 知識圖譜 (v2.0.0 新增)
    kg_fuzzy_threshold: float = 0.85           # 模糊匹配相似度閾值
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
    graph_cache_ttl_path: int = 300            # 最短路徑快取 TTL (秒)

    # Agent 編排引擎 (v2.2.0 新增)
    agent_max_iterations: int = 3              # 工具迴圈最大輪次
    agent_tool_timeout: int = 15               # 單個工具執行超時 (秒)
    agent_stream_timeout: int = 60             # 整體串流超時 (秒)
    agent_sync_query_timeout: int = 90         # 同步問答超時 (秒, MCP/LINE)
    agent_find_similar_threshold: float = 0.7  # find_similar 向量距離閾值

    # Tool Monitor (v2.6.0 新增)
    tool_monitor_window_size: int = 100        # 滑動窗口大小
    tool_monitor_degraded_threshold: float = 0.3   # 成功率 < 30% → 降級
    tool_monitor_recovery_threshold: float = 0.7   # 成功率 > 70% → 解除降級
    tool_monitor_probe_interval: int = 600     # 降級探測間隔 (秒)

    # Pattern Learner (v2.6.0 新增)
    pattern_max_count: int = 500               # 最多保存模式數
    pattern_decay_half_life: int = 604800      # 7 天半衰期
    pattern_match_threshold: float = 0.8       # 模式匹配信心門檻

    # Conversation Summarizer (v2.6.0 新增)
    conv_summary_trigger_turns: int = 6        # 超過 N 輪觸發摘要
    conv_summary_max_chars: int = 500          # 摘要最大字數
    conv_summary_keep_recent: int = 2          # 摘要後保留最近 N 輪

    # Agent Router (v2.6.0 新增)
    router_pattern_threshold: float = 0.8      # Pattern 路由信心門檻
    router_rule_threshold: float = 0.9         # Rule 路由信心門檻

    # Tool Result Guard (v2.7.0 — Phase 2A, 對標 OpenClaw session-tool-result-guard)
    tool_guard_enabled: bool = True            # 工具失敗時合成回退結果

    # Adaptive Few-shot (v2.7.0 — Phase 2B, 對標 OpenClaw Adaptive Few-shot)
    adaptive_fewshot_enabled: bool = True      # 從 trace 注入歷史成功案例
    adaptive_fewshot_limit: int = 3            # 最多注入 N 條
    adaptive_fewshot_min_results: int = 1      # 歷史查詢最低結果數

    # Self-Reflection (v2.7.0 — Phase 2C, 對標 OpenClaw Thinking/Reflection)
    self_reflect_enabled: bool = True          # 答案品質自省
    self_reflect_threshold: int = 5            # score < N 觸發重試
    self_reflect_timeout: int = 5              # 自省超時 (秒)

    # Memory Flush (v2.7.0 — Phase 2D, 對標 OpenClaw memory-flush pre-compaction)
    memory_flush_enabled: bool = True          # 壓縮前提取學習
    memory_flush_learnings_ttl: int = 86400    # 學習 TTL 24 小時
    memory_flush_max_learnings: int = 10       # 最多 N 條學習項

    # Persistent Learning Store (v3.0.0 — Phase 3A, 對標 OpenClaw agent-reflect)
    learning_persist_enabled: bool = True      # 學習寫入 DB 永久保存
    learning_max_per_session: int = 10         # 每次 session 最多學習數
    learning_inject_limit: int = 5             # 注入 planner prompt 的最大學習數

    # 3-Tier Adaptive Compaction (v3.0.0 — Phase 3A, 對標 OpenClaw compaction.ts)
    compaction_tier1_timeout: int = 10         # Tier 1 完整摘要超時 (秒)
    compaction_tier2_max_msg_chars: int = 500  # Tier 2 跳過超長訊息的閾值
    compaction_tier3_topic_limit: int = 10     # Tier 3 元數據最大主題數

    # Semantic Pattern Matching (v3.0.0 — Phase 3A, PatternLearner 語意增強)
    pattern_semantic_enabled: bool = True      # 精確匹配失敗時嘗試語意匹配
    pattern_semantic_threshold: float = 0.85   # 語意匹配最低餘弦相似度
    pattern_semantic_top_k: int = 5            # 語意匹配候選池大小

    # Evolution (EVO-4: 閾值外部化至 agent-policy.yaml)
    evolution_trigger_every_n_queries: int = 50
    evolution_trigger_interval_hours: int = 24
    evolution_promote_min_hits: int = 15
    evolution_promote_min_success: float = 0.90
    evolution_demote_max_success: float = 0.30
    evolution_signal_batch_size: int = 100

    # Capability (EVO-4)
    capability_strong_threshold: float = 0.70
    capability_weak_threshold: float = 0.50
    capability_cache_ttl_seconds: int = 300

    # Adaptive Context Window (v4.1.0 — 依查詢複雜度動態調整歷史窗口)
    adaptive_context_enabled: bool = True      # 是否啟用自適應上下文窗口
    adaptive_context_simple: int = 2           # simple 查詢保留輪數
    adaptive_context_medium: int = 4           # medium 查詢保留輪數
    adaptive_context_complex: int = 6          # complex 查詢保留輪數
    adaptive_context_query_short: int = 20     # 短查詢閾值（字元數）
    adaptive_context_query_long: int = 100     # 長查詢閾值（字元數）
    adaptive_context_tool_complex: int = 3     # 多工具複雜度閾值

    # Vision settings (v5.4.1 — Gemma 4 multimodal)
    vision_max_image_size: int = 1024              # 圖片最大維度 (pixels)
    vision_max_tokens: int = 1024                  # Vision 回應最大 tokens
    vision_temperature: float = 0.3                # Vision 生成溫度

    # --- Inference profiles & provider routing (loaded from YAML, read-only) ---
    _inference_profiles: dict = field(default_factory=dict, repr=False)
    _provider_routing: dict = field(default_factory=dict, repr=False)

    @staticmethod
    def _resolve_env_vars(value: str) -> str:
        """Resolve ${VAR} placeholders in a string using os.environ."""
        def _replacer(m: re.Match) -> str:
            return os.environ.get(m.group(1), m.group(0))
        return re.sub(r"\$\{([^}]+)\}", _replacer, value)

    @staticmethod
    def _load_yaml(filename: str) -> dict:
        """Load a YAML file from the config directory. Returns {} on any failure."""
        try:
            import yaml  # noqa: delayed import – graceful if PyYAML absent
        except ImportError:
            logger.debug("PyYAML not installed; skipping %s", filename)
            return {}
        filepath = _CONFIG_DIR / filename
        if not filepath.exists():
            logger.debug("Config file not found: %s", filepath)
            return {}
        try:
            with open(filepath, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            logger.info("Loaded config: %s (%d top-level keys)", filename, len(data))
            return data
        except Exception as exc:
            logger.warning("Failed to load %s: %s", filename, exc)
            return {}

    @staticmethod
    def _yaml_get(data: dict, *keys: str, default: Any = None) -> Any:
        """Safely traverse nested dict keys."""
        node = data
        for k in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(k)
            if node is None:
                return default
        return node

    @classmethod
    def from_env(cls) -> "AIConfig":
        """從環境變數建立配置 (YAML defaults → env overrides)"""

        # --- Load YAML policy defaults ---
        policy = cls._load_yaml("agent-policy.yaml")
        profiles_data = cls._load_yaml("inference-profiles.yaml")

        # Helper: get from env first, then YAML, then hardcoded default
        def _env_or_yaml(
            env_key: str,
            yaml_keys: tuple,
            default: Any,
            cast: type = str,
        ) -> Any:
            env_val = os.getenv(env_key)
            if env_val is not None:
                if cast is bool:
                    return env_val.lower() == "true"
                return cast(env_val)
            yaml_val = cls._yaml_get(policy, *yaml_keys)
            if yaml_val is not None:
                return cast(yaml_val) if cast is not bool else bool(yaml_val)
            if cast is bool:
                return bool(default)
            return cast(default)

        # Resolve inference profiles env vars
        resolved_profiles: dict = {}
        raw_profiles = (profiles_data.get("profiles") or {}) if profiles_data else {}
        for name, prof in raw_profiles.items():
            resolved: dict = {}
            for k, v in (prof or {}).items():
                if isinstance(v, str):
                    resolved[k] = cls._resolve_env_vars(v)
                else:
                    resolved[k] = v
            resolved_profiles[name] = resolved

        instance = cls(
            enabled=os.getenv("AI_ENABLED", "true").lower() == "true",
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            groq_model=os.getenv("AI_DEFAULT_MODEL", "llama-3.3-70b-versatile"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "gemma4"),
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
            embedding_cache_max_size=int(os.getenv("EMBEDDING_CACHE_MAX_SIZE", "2000")),
            embedding_cache_ttl=int(os.getenv("EMBEDDING_CACHE_TTL", "3600")),
            embedding_max_text_chars=int(os.getenv("EMBEDDING_MAX_TEXT_CHARS", "8000")),
            # 知識圖譜
            kg_fuzzy_threshold=float(os.getenv("KG_FUZZY_THRESHOLD", "0.85")),
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
            graph_cache_ttl_path=int(os.getenv("GRAPH_CACHE_TTL_PATH", "300")),
            # Agent 編排引擎 (YAML: agent.*)
            agent_max_iterations=_env_or_yaml(
                "AGENT_MAX_ITERATIONS", ("agent", "max_iterations"), 3, int),
            agent_tool_timeout=_env_or_yaml(
                "AGENT_TOOL_TIMEOUT", ("agent", "tool_timeout_seconds"), 15, int),
            agent_stream_timeout=_env_or_yaml(
                "AGENT_STREAM_TIMEOUT", ("agent", "stream_timeout_seconds"), 60, int),
            agent_sync_query_timeout=_env_or_yaml(
                "AGENT_SYNC_QUERY_TIMEOUT", ("agent", "sync_query_timeout_seconds"), 90, int),
            agent_find_similar_threshold=_env_or_yaml(
                "AGENT_FIND_SIMILAR_THRESHOLD", ("agent", "find_similar_threshold"), 0.7, float),
            # Tool Monitor (YAML: tool_monitor.*)
            tool_monitor_window_size=_env_or_yaml(
                "TOOL_MONITOR_WINDOW_SIZE", ("tool_monitor", "window_size"), 100, int),
            tool_monitor_degraded_threshold=_env_or_yaml(
                "TOOL_MONITOR_DEGRADED_THRESHOLD", ("tool_monitor", "degrade_threshold"), 0.3, float),
            tool_monitor_recovery_threshold=_env_or_yaml(
                "TOOL_MONITOR_RECOVERY_THRESHOLD", ("tool_monitor", "recovery_threshold"), 0.7, float),
            tool_monitor_probe_interval=_env_or_yaml(
                "TOOL_MONITOR_PROBE_INTERVAL", ("tool_monitor", "probe_interval_seconds"), 600, int),
            # Pattern Learner (YAML: pattern_learner.*)
            pattern_max_count=_env_or_yaml(
                "PATTERN_MAX_COUNT", ("pattern_learner", "max_patterns"), 500, int),
            pattern_decay_half_life=_env_or_yaml(
                "PATTERN_DECAY_HALF_LIFE", ("pattern_learner", "decay_half_life_seconds"), 604800, int),
            pattern_match_threshold=_env_or_yaml(
                "PATTERN_MATCH_THRESHOLD", ("pattern_learner", "match_threshold"), 0.8, float),
            # Conversation Summarizer (YAML: summarizer.*)
            conv_summary_trigger_turns=_env_or_yaml(
                "CONV_SUMMARY_TRIGGER_TURNS", ("summarizer", "trigger_turns"), 6, int),
            conv_summary_max_chars=_env_or_yaml(
                "CONV_SUMMARY_MAX_CHARS", ("summarizer", "max_chars"), 500, int),
            conv_summary_keep_recent=_env_or_yaml(
                "CONV_SUMMARY_KEEP_RECENT", ("summarizer", "keep_recent"), 2, int),
            # Agent Router (YAML: router.*)
            router_pattern_threshold=_env_or_yaml(
                "ROUTER_PATTERN_THRESHOLD", ("router", "pattern_threshold"), 0.8, float),
            router_rule_threshold=_env_or_yaml(
                "ROUTER_RULE_THRESHOLD", ("router", "rule_threshold"), 0.9, float),
            # Tool Result Guard (YAML: tool_guard.*)
            tool_guard_enabled=_env_or_yaml(
                "TOOL_GUARD_ENABLED", ("tool_guard", "enabled"), True, bool),
            # Adaptive Few-shot (YAML: adaptive_fewshot.*)
            adaptive_fewshot_enabled=_env_or_yaml(
                "ADAPTIVE_FEWSHOT_ENABLED", ("adaptive_fewshot", "enabled"), True, bool),
            adaptive_fewshot_limit=_env_or_yaml(
                "ADAPTIVE_FEWSHOT_LIMIT", ("adaptive_fewshot", "limit"), 3, int),
            adaptive_fewshot_min_results=_env_or_yaml(
                "ADAPTIVE_FEWSHOT_MIN_RESULTS", ("adaptive_fewshot", "min_results"), 1, int),
            # Self-Reflection (YAML: self_reflection.*)
            self_reflect_enabled=_env_or_yaml(
                "SELF_REFLECT_ENABLED", ("self_reflection", "enabled"), True, bool),
            self_reflect_threshold=_env_or_yaml(
                "SELF_REFLECT_THRESHOLD", ("self_reflection", "threshold"), 5, int),
            self_reflect_timeout=_env_or_yaml(
                "SELF_REFLECT_TIMEOUT", ("self_reflection", "timeout_seconds"), 5, int),
            # Memory Flush (YAML: memory.*)
            memory_flush_enabled=_env_or_yaml(
                "MEMORY_FLUSH_ENABLED", ("memory", "flush_enabled"), True, bool),
            memory_flush_learnings_ttl=_env_or_yaml(
                "MEMORY_FLUSH_LEARNINGS_TTL", ("memory", "learnings_ttl_seconds"), 86400, int),
            memory_flush_max_learnings=_env_or_yaml(
                "MEMORY_FLUSH_MAX_LEARNINGS", ("memory", "max_learnings"), 10, int),
            # Persistent Learning Store (YAML: learning.*)
            learning_persist_enabled=_env_or_yaml(
                "LEARNING_PERSIST_ENABLED", ("learning", "persist_enabled"), True, bool),
            learning_max_per_session=_env_or_yaml(
                "LEARNING_MAX_PER_SESSION", ("learning", "max_per_session"), 10, int),
            learning_inject_limit=_env_or_yaml(
                "LEARNING_INJECT_LIMIT", ("learning", "inject_limit"), 5, int),
            # 3-Tier Adaptive Compaction (YAML: compaction.*)
            compaction_tier1_timeout=_env_or_yaml(
                "COMPACTION_TIER1_TIMEOUT", ("compaction", "tier1_timeout_seconds"), 10, int),
            compaction_tier2_max_msg_chars=_env_or_yaml(
                "COMPACTION_TIER2_MAX_MSG_CHARS", ("compaction", "tier2_max_msg_chars"), 500, int),
            compaction_tier3_topic_limit=_env_or_yaml(
                "COMPACTION_TIER3_TOPIC_LIMIT", ("compaction", "tier3_topic_limit"), 10, int),
            # Semantic Pattern Matching (YAML: pattern_learner.semantic_*)
            pattern_semantic_enabled=_env_or_yaml(
                "PATTERN_SEMANTIC_ENABLED", ("pattern_learner", "semantic_enabled"), True, bool),
            pattern_semantic_threshold=_env_or_yaml(
                "PATTERN_SEMANTIC_THRESHOLD", ("pattern_learner", "semantic_threshold"), 0.85, float),
            pattern_semantic_top_k=_env_or_yaml(
                "PATTERN_SEMANTIC_TOP_K", ("pattern_learner", "semantic_top_k"), 5, int),
            # Adaptive Context Window (YAML: adaptive_context.*)
            adaptive_context_enabled=_env_or_yaml(
                "ADAPTIVE_CONTEXT_ENABLED", ("adaptive_context", "enabled"), True, bool),
            adaptive_context_simple=_env_or_yaml(
                "ADAPTIVE_CONTEXT_SIMPLE", ("adaptive_context", "simple_turns"), 2, int),
            adaptive_context_medium=_env_or_yaml(
                "ADAPTIVE_CONTEXT_MEDIUM", ("adaptive_context", "medium_turns"), 4, int),
            adaptive_context_complex=_env_or_yaml(
                "ADAPTIVE_CONTEXT_COMPLEX", ("adaptive_context", "complex_turns"), 6, int),
            adaptive_context_query_short=_env_or_yaml(
                "ADAPTIVE_CONTEXT_QUERY_SHORT", ("adaptive_context", "query_short_chars"), 20, int),
            adaptive_context_query_long=_env_or_yaml(
                "ADAPTIVE_CONTEXT_QUERY_LONG", ("adaptive_context", "query_long_chars"), 100, int),
            adaptive_context_tool_complex=_env_or_yaml(
                "ADAPTIVE_CONTEXT_TOOL_COMPLEX", ("adaptive_context", "tool_complex_threshold"), 3, int),
            # Evolution (YAML: evolution.*)
            evolution_trigger_every_n_queries=_env_or_yaml(
                "EVOLUTION_TRIGGER_N", ("evolution", "trigger_every_n_queries"), 50, int),
            evolution_trigger_interval_hours=_env_or_yaml(
                "EVOLUTION_INTERVAL_HOURS", ("evolution", "trigger_interval_hours"), 24, int),
            evolution_promote_min_hits=_env_or_yaml(
                "EVOLUTION_PROMOTE_MIN_HITS", ("evolution", "promote_min_hits"), 15, int),
            evolution_promote_min_success=_env_or_yaml(
                "EVOLUTION_PROMOTE_MIN_SUCCESS", ("evolution", "promote_min_success"), 0.90, float),
            evolution_demote_max_success=_env_or_yaml(
                "EVOLUTION_DEMOTE_MAX_SUCCESS", ("evolution", "demote_max_success"), 0.30, float),
            evolution_signal_batch_size=_env_or_yaml(
                "EVOLUTION_SIGNAL_BATCH", ("evolution", "signal_batch_size"), 100, int),
            # Capability (YAML: capability.*)
            capability_strong_threshold=_env_or_yaml(
                "CAPABILITY_STRONG_THRESHOLD", ("capability", "strong_threshold"), 0.70, float),
            capability_weak_threshold=_env_or_yaml(
                "CAPABILITY_WEAK_THRESHOLD", ("capability", "weak_threshold"), 0.50, float),
            capability_cache_ttl_seconds=_env_or_yaml(
                "CAPABILITY_CACHE_TTL", ("capability", "cache_ttl_seconds"), 300, int),
            # Vision (env overrides)
            vision_max_image_size=int(os.getenv("VISION_MAX_IMAGE_SIZE", "1024")),
            vision_max_tokens=int(os.getenv("VISION_MAX_TOKENS", "1024")),
            vision_temperature=float(os.getenv("VISION_TEMPERATURE", "0.3")),
        )
        # Attach resolved inference profiles & provider routing
        instance._inference_profiles = resolved_profiles
        instance._provider_routing = (policy.get("provider_routing") or {}) if policy else {}
        return instance

    @property
    def inference_profiles(self) -> dict:
        """Get resolved inference provider profiles."""
        return self._inference_profiles

    @property
    def provider_routing(self) -> dict:
        """Get provider routing preferences per task type."""
        return self._provider_routing

    def get_preferred_providers(self, task_type: str = "chat") -> list:
        """Get ordered provider list for a task type."""
        routing = self._provider_routing.get(task_type, {})
        return routing.get("preferred", ["groq", "nvidia", "ollama"])

    def should_prefer_local(self, task_type: str = "chat") -> bool:
        """Check if a task type should prefer local providers."""
        routing = self._provider_routing.get(task_type, {})
        return routing.get("prefer_local", False)


# 全域配置實例
_ai_config: Optional[AIConfig] = None


def get_ai_config() -> AIConfig:
    """獲取 AI 配置實例 (Singleton)"""
    global _ai_config
    if _ai_config is None:
        _ai_config = AIConfig.from_env()
    return _ai_config
