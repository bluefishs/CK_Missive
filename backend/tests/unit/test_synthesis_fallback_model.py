# -*- coding: utf-8 -*-
"""
Synthesis Fallback Model Regression（2026-06-03 / L64 後續）

鎖定 synthesis 超時根因修法：

  agent_synthesis.py 指定 Groq `llama-3.3-70b`、synthesis_timeout=35s。
  當 Groq(429/TPM)+NVIDIA 雙失敗落 Ollama 時，ai_connector 依 task_type 從
  TASK_MODEL_MAP 取 fallback 模型；若 "synthesis" 不在 map → 落
  OLLAMA_DEFAULT_MODEL（prod OLLAMA_MODEL=qwen2.5:7b, p50 52.8s）→ 35s 必超時。

  修法：TASK_MODEL_MAP["synthesis"] = gemma4:e2b（~7s < 35s）。

本測試鎖定：
1. "synthesis" 必須在 TASK_MODEL_MAP（否則 fallback 落慢模型 → 必超時 regression）。
2. 模型選擇邏輯：傳 Groq-style model + task_type="synthesis" 時，
   Ollama fallback model 不得落到 qwen 系慢模型。
"""
import pytest


class TestSynthesisFallbackModel:
    def test_synthesis_in_task_model_map(self):
        """synthesis 必須有專屬 Ollama fallback 模型映射。"""
        from app.core.ai_connector import TASK_MODEL_MAP

        assert "synthesis" in TASK_MODEL_MAP, (
            "synthesis 不在 TASK_MODEL_MAP → Ollama fallback 落 OLLAMA_DEFAULT_MODEL"
            "（prod qwen2.5:7b 52.8s）→ 35s synthesis_timeout 必超時（L64）"
        )

    def test_synthesis_fallback_not_slow_default(self):
        """synthesis fallback 模型不得是 qwen 系慢模型（必須快於 35s timeout）。"""
        from app.core.ai_connector import TASK_MODEL_MAP

        model = TASK_MODEL_MAP["synthesis"].lower()
        assert "qwen" not in model, (
            f"synthesis fallback={model} 含 qwen → p50 52.8s > 35s timeout，"
            "違反 L64 修法。應為 gemma4:e2b 等快模型。"
        )

    def test_gemma_in_required_models(self):
        """gemma4:e2b（synthesis fallback + vision OCR）須在啟動必備模型清單。"""
        from app.core.ai_connector import REQUIRED_MODELS

        assert any("gemma4" in m for m in REQUIRED_MODELS), (
            "gemma4:e2b 不在 REQUIRED_MODELS → 啟動不會自動拉取 → "
            "synthesis fallback / vision OCR 可能 silent 404（L64）"
        )

    def test_ollama_fallback_selection_for_synthesis(self):
        """重現 ai_connector 模型選擇分支：Groq-style model + synthesis →
        Ollama fallback 應取 TASK_MODEL_MAP["synthesis"]，非 OLLAMA_DEFAULT_MODEL。"""
        from app.core.ai_connector import TASK_MODEL_MAP, OLLAMA_DEFAULT_MODEL

        # 模擬 chat_completion 內 ai_connector.py:175-186 的選擇邏輯
        model = "llama-3.3-70b-versatile"  # synthesis 指定的 Groq model
        task_type = "synthesis"
        _is_ollama_model = (not model) or (":" in model) or (model == OLLAMA_DEFAULT_MODEL)

        if _is_ollama_model and model:
            ollama_model = model
        elif task_type and task_type in TASK_MODEL_MAP:
            ollama_model = TASK_MODEL_MAP[task_type]
        else:
            ollama_model = OLLAMA_DEFAULT_MODEL

        assert _is_ollama_model is False  # Groq-style model 不是 ollama model
        assert ollama_model == TASK_MODEL_MAP["synthesis"]  # 走 task_type 映射
        assert "gemma4" in ollama_model  # 快模型，非慢 default
