"""
AI Config 單元測試

測試 AIConfig 的配置載入、環境變數覆寫、YAML 整合等核心功能。
覆蓋 core 子包的基礎配置層。
"""
import os
import pytest
from unittest.mock import patch

from app.services.ai.core.ai_config import AIConfig, get_ai_config, _CONFIG_DIR


class TestAIConfigDefaults:
    """測試預設配置值"""

    def test_default_values(self):
        config = AIConfig()
        assert config.enabled is True
        assert config.groq_model == "llama-3.3-70b-versatile"
        assert config.ollama_model == "gemma4"
        assert config.cloud_timeout == 30
        assert config.local_timeout == 60
        assert config.rate_limit_requests == 30
        assert config.cache_enabled is True

    def test_rag_defaults(self):
        config = AIConfig()
        assert config.rag_top_k == 5
        assert config.rag_similarity_threshold == 0.3
        assert config.rag_max_context_chars == 6000
        assert config.rag_temperature == 0.3

    def test_agent_defaults(self):
        config = AIConfig()
        assert config.agent_max_iterations == 3
        assert config.agent_tool_timeout == 15
        assert config.agent_stream_timeout == 60

    def test_evolution_defaults(self):
        config = AIConfig()
        assert config.evolution_trigger_every_n_queries == 50
        assert config.evolution_promote_min_hits == 15
        assert config.evolution_promote_min_success == 0.90
        assert config.evolution_demote_max_success == 0.30


class TestAIConfigFromEnv:
    """測試環境變數覆寫"""

    def test_env_override_basic(self):
        with patch.dict(os.environ, {
            "AI_ENABLED": "false",
            "GROQ_API_KEY": "test-key",
            "AI_DEFAULT_MODEL": "test-model",
        }):
            import app.services.ai.core.ai_config as mod
            mod._ai_config = None  # reset singleton
            config = AIConfig.from_env()
            assert config.enabled is False
            assert config.groq_api_key == "test-key"
            assert config.groq_model == "test-model"

    def test_env_override_numeric(self):
        with patch.dict(os.environ, {
            "AI_CLOUD_TIMEOUT": "60",
            "RAG_TOP_K": "10",
        }):
            config = AIConfig.from_env()
            assert config.cloud_timeout == 60
            assert config.rag_top_k == 10

    def test_env_override_boolean(self):
        with patch.dict(os.environ, {"AI_CACHE_ENABLED": "false"}):
            config = AIConfig.from_env()
            assert config.cache_enabled is False


class TestAIConfigHelpers:
    """測試靜態工具方法"""

    def test_resolve_env_vars(self):
        with patch.dict(os.environ, {"MY_VAR": "hello"}):
            result = AIConfig._resolve_env_vars("prefix_${MY_VAR}_suffix")
            assert result == "prefix_hello_suffix"

    def test_resolve_env_vars_missing(self):
        result = AIConfig._resolve_env_vars("${NONEXISTENT_VAR_12345}")
        assert result == "${NONEXISTENT_VAR_12345}"

    def test_yaml_get_nested(self):
        data = {"a": {"b": {"c": 42}}}
        assert AIConfig._yaml_get(data, "a", "b", "c") == 42
        assert AIConfig._yaml_get(data, "a", "b", "d", default="x") == "x"
        assert AIConfig._yaml_get(data, "x", default=None) is None

    def test_yaml_get_non_dict(self):
        assert AIConfig._yaml_get("not_a_dict", "key", default=99) == 99

    def test_load_yaml_missing_file(self):
        result = AIConfig._load_yaml("nonexistent_file_12345.yaml")
        assert result == {}


class TestAIConfigProviderRouting:
    """測試 Provider 路由"""

    def test_get_preferred_providers_default(self):
        config = AIConfig()
        providers = config.get_preferred_providers("chat")
        assert providers == ["groq", "nvidia", "ollama"]

    def test_should_prefer_local_default(self):
        config = AIConfig()
        assert config.should_prefer_local("chat") is False

    def test_inference_profiles_empty(self):
        config = AIConfig()
        assert config.inference_profiles == {}


class TestGetAIConfigSingleton:
    """測試 Singleton"""

    def test_singleton_returns_same_instance(self):
        import app.services.ai.core.ai_config as mod
        mod._ai_config = None
        c1 = get_ai_config()
        c2 = get_ai_config()
        assert c1 is c2
        mod._ai_config = None  # cleanup
