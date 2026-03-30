"""
AI 連接器管理功能 — 模型管理、健康檢查

從 ai_connector.py 拆分 (1017L → ~760L + 260L)

包含:
- ensure_models() — 自動拉取缺少模型
- warmup_models() — 模型預載入 GPU
- check_health() — 多 provider 健康檢查

Version: 1.0.0
Created: 2026-03-29 (拆分自 ai_connector.py)
"""

import logging
import os
from typing import Any, Dict

import httpx

logger = logging.getLogger(__name__)


class AIConnectorManagementMixin:
    """AI 連接器管理功能 Mixin — 模型生命週期與健康診斷"""

    # 由 AIConnector 提供的屬性
    ollama_base_url: str
    groq_api_key: str
    nvidia_api_key: str

    async def ensure_models(self) -> Dict[str, Any]:
        """檢查 Ollama 已安裝模型，自動拉取缺少的必要模型。"""
        from .ai_connector import REQUIRED_MODELS

        result: Dict[str, Any] = {"installed": [], "pulled": [], "failed": [], "ollama_available": False}

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.ollama_base_url}/api/tags", timeout=5)
                if resp.status_code != 200:
                    logger.warning("Ollama /api/tags 回應 HTTP %s", resp.status_code)
                    return result

                result["ollama_available"] = True
                installed_models = {m["name"] for m in resp.json().get("models", [])}
                installed_normalized = set()
                for m in installed_models:
                    installed_normalized.add(m)
                    if ":" in m:
                        installed_normalized.add(m.split(":")[0])
                    else:
                        installed_normalized.add(f"{m}:latest")
                result["installed"] = sorted(installed_models)

                for required in REQUIRED_MODELS:
                    req_norm = required.split(":")[0] if ":" in required else required
                    if required not in installed_normalized and req_norm not in installed_normalized:
                        logger.info("模型 '%s' 未安裝，開始拉取...", required)
                        try:
                            pull_resp = await client.post(
                                f"{self.ollama_base_url}/api/pull",
                                json={"name": required, "stream": False},
                                timeout=600,
                            )
                            if pull_resp.status_code == 200:
                                result["pulled"].append(required)
                                logger.info("模型 '%s' 拉取成功", required)
                            else:
                                result["failed"].append(required)
                                logger.warning("模型 '%s' 拉取失敗: HTTP %s", required, pull_resp.status_code)
                        except Exception as pull_err:
                            result["failed"].append(required)
                            logger.warning("模型 '%s' 拉取異常: %s", required, pull_err)
        except Exception as e:
            logger.warning("Ollama 模型檢查失敗: %s", e)

        return result

    async def warmup_models(self) -> Dict[str, bool]:
        """對每個必要模型發送最小請求，預載入 GPU 記憶體。"""
        from .ai_connector import REQUIRED_MODELS, TASK_MODEL_MAP

        results: Dict[str, bool] = {}

        for required_model in REQUIRED_MODELS:
            try:
                async with httpx.AsyncClient() as client:
                    if required_model == TASK_MODEL_MAP.get("embedding", "nomic-embed-text"):
                        resp = await client.post(
                            f"{self.ollama_base_url}/api/embed",
                            json={"model": required_model, "input": "warmup"},
                            timeout=60,
                        )
                    else:
                        resp = await client.post(
                            f"{self.ollama_base_url}/api/generate",
                            json={"model": required_model, "prompt": "hi", "stream": False, "options": {"num_predict": 1}},
                            timeout=120,
                        )

                    if resp.status_code == 200:
                        results[required_model] = True
                        logger.info("模型 '%s' warm-up 完成", required_model)
                    else:
                        results[required_model] = False
                        logger.warning("模型 '%s' warm-up 失敗: HTTP %s", required_model, resp.status_code)
            except Exception as e:
                results[required_model] = False
                logger.warning("模型 '%s' warm-up 異常: %s", required_model, e)

        return results

    async def check_health(self) -> Dict[str, Any]:
        """檢查 AI 服務健康狀態 — Groq + NVIDIA + vLLM + Ollama。"""
        from .ai_connector import NVIDIA_DEFAULT_MODEL, VLLM_LOCAL_MODEL, REQUIRED_MODELS

        status: Dict[str, Any] = {
            "groq": {"available": False, "message": ""},
            "nvidia_cloud": {"available": False, "message": ""},
            "ollama": {"available": False, "message": "", "models": [], "required_models_ready": False, "gpu_info": None},
        }

        # Groq
        if self.groq_api_key:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {self.groq_api_key}"}, timeout=10)
                    if response.status_code == 200:
                        status["groq"]["available"] = True
                        status["groq"]["message"] = "Groq API 可用"
                    else:
                        status["groq"]["message"] = f"HTTP {response.status_code}"
            except Exception as e:
                status["groq"]["message"] = str(e)
        else:
            status["groq"]["message"] = "未設定 GROQ_API_KEY"

        # NVIDIA Cloud
        if self.nvidia_api_key:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get("https://integrate.api.nvidia.com/v1/models", headers={"Authorization": f"Bearer {self.nvidia_api_key}"}, timeout=10)
                    if response.status_code == 200:
                        status["nvidia_cloud"]["available"] = True
                        status["nvidia_cloud"]["message"] = "NVIDIA Cloud API 可用"
                        status["nvidia_cloud"]["model"] = NVIDIA_DEFAULT_MODEL
                    else:
                        status["nvidia_cloud"]["message"] = f"HTTP {response.status_code}"
            except Exception as e:
                status["nvidia_cloud"]["message"] = str(e)
        else:
            status["nvidia_cloud"]["message"] = "未設定 NVIDIA_API_KEY"

        # vLLM
        status["vllm_local"] = {"available": False, "message": ""}
        if os.getenv("VLLM_ENABLED", "").lower() == "true":
            try:
                vllm_base = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
                vllm_health_url = vllm_base.rsplit("/v1", 1)[0] + "/health"
                async with httpx.AsyncClient() as client:
                    response = await client.get(vllm_health_url, timeout=5)
                    if response.status_code == 200:
                        status["vllm_local"]["available"] = True
                        status["vllm_local"]["message"] = "vLLM 本地可用"
                        status["vllm_local"]["model"] = VLLM_LOCAL_MODEL
                    else:
                        status["vllm_local"]["message"] = f"HTTP {response.status_code}"
            except Exception as e:
                status["vllm_local"]["message"] = str(e)
        else:
            status["vllm_local"]["message"] = "VLLM_ENABLED 未設定 (設為 true 啟用)"

        # Ollama
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.ollama_base_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    status["ollama"]["available"] = True
                    models = response.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    status["ollama"]["models"] = model_names
                    status["ollama"]["message"] = f"Ollama 可用，{len(models)} 個模型"

                    installed_set = set(model_names)
                    for m in list(installed_set):
                        installed_set.add(m.split(":")[0])
                    missing = [req for req in REQUIRED_MODELS if req not in installed_set and req.split(":")[0] not in installed_set]
                    status["ollama"]["required_models_ready"] = len(missing) == 0
                    if missing:
                        status["ollama"]["missing_models"] = missing
                else:
                    status["ollama"]["message"] = f"HTTP {response.status_code}"

                try:
                    ps_resp = await client.get(f"{self.ollama_base_url}/api/ps", timeout=3)
                    if ps_resp.status_code == 200:
                        ps_data = ps_resp.json()
                        running_models = ps_data.get("models", [])
                        status["ollama"]["gpu_info"] = {"loaded_models": [{"name": rm.get("name", ""), "size": rm.get("size", 0), "size_vram": rm.get("size_vram", 0)} for rm in running_models]}
                except Exception:
                    pass
        except Exception as e:
            status["ollama"]["message"] = str(e)

        return status
