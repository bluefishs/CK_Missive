"""
Ollama 管理 API 端點

提供 Ollama 服務狀態查詢、模型檢查/拉取、模型預熱功能。
供前端 Ollama 管理面板呼叫。

Version: 1.0.0
Created: 2026-02-25

端點:
- POST /ai/ollama/status       - Ollama 詳細狀態（含 GPU、模型驗證）
- POST /ai/ollama/ensure-models - 檢查並拉取缺少的必要模型
- POST /ai/ollama/warmup        - 預熱所有必要模型至 GPU
"""

import logging

from fastapi import APIRouter, Depends

from app.core.dependencies import require_admin
from app.core.ai_connector import get_ai_connector, AIConnector, REQUIRED_MODELS
from app.extended.models import User
from app.schemas.ai import (
    OllamaStatusResponse,
    OllamaGpuInfo,
    OllamaGpuLoadedModel,
    OllamaEnsureModelsResponse,
    OllamaWarmupResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ollama/status", response_model=OllamaStatusResponse)
async def get_ollama_status(
    current_user: User = Depends(require_admin()),
) -> OllamaStatusResponse:
    """
    取得 Ollama 詳細狀態

    回傳 Ollama 服務可用性、已安裝模型列表、必要模型檢查結果、
    GPU 已載入模型資訊，以及 Groq API 狀態。
    需要管理員權限。
    """
    logger.info(
        "Ollama 狀態查詢 (by %s)", current_user.full_name or current_user.email
    )

    connector: AIConnector = get_ai_connector()
    health = await connector.check_health()

    ollama_info = health.get("ollama", {})
    groq_info = health.get("groq", {})

    # 組裝 GPU 資訊
    gpu_info = None
    raw_gpu = ollama_info.get("gpu_info")
    if raw_gpu and isinstance(raw_gpu, dict):
        loaded_models = [
            OllamaGpuLoadedModel(
                name=m.get("name", ""),
                size=m.get("size", 0),
                size_vram=m.get("size_vram", 0),
            )
            for m in raw_gpu.get("loaded_models", [])
        ]
        gpu_info = OllamaGpuInfo(loaded_models=loaded_models)

    return OllamaStatusResponse(
        available=ollama_info.get("available", False),
        message=ollama_info.get("message", ""),
        models=ollama_info.get("models", []),
        required_models=sorted(REQUIRED_MODELS),
        required_models_ready=ollama_info.get("required_models_ready", False),
        missing_models=ollama_info.get("missing_models", []),
        gpu_info=gpu_info,
        groq_available=groq_info.get("available", False),
        groq_message=groq_info.get("message", ""),
    )


@router.post("/ollama/ensure-models", response_model=OllamaEnsureModelsResponse)
async def ensure_ollama_models(
    current_user: User = Depends(require_admin()),
) -> OllamaEnsureModelsResponse:
    """
    檢查並拉取缺少的必要模型

    掃描 Ollama 已安裝模型，與系統必要模型清單比對，
    自動拉取缺少的模型。拉取大型模型可能需要數分鐘。
    需要管理員權限。
    """
    logger.info(
        "Ollama 模型檢查與拉取 (by %s)",
        current_user.full_name or current_user.email,
    )

    connector: AIConnector = get_ai_connector()
    result = await connector.ensure_models()

    logger.info(
        "Ollama ensure_models 結果: installed=%s, pulled=%s, failed=%s",
        len(result.get("installed", [])),
        len(result.get("pulled", [])),
        len(result.get("failed", [])),
    )

    return OllamaEnsureModelsResponse(
        ollama_available=result.get("ollama_available", False),
        installed=result.get("installed", []),
        pulled=result.get("pulled", []),
        failed=result.get("failed", []),
    )


@router.post("/ollama/warmup", response_model=OllamaWarmupResponse)
async def warmup_ollama_models(
    current_user: User = Depends(require_admin()),
) -> OllamaWarmupResponse:
    """
    預熱所有必要模型

    對每個必要模型發送最小請求，將模型預載入 GPU 記憶體，
    消除後續使用時的冷啟動延遲。首次載入可能需要 1-2 分鐘。
    需要管理員權限。
    """
    logger.info(
        "Ollama 模型預熱 (by %s)", current_user.full_name or current_user.email
    )

    connector: AIConnector = get_ai_connector()
    results = await connector.warmup_models()

    all_success = bool(results) and all(results.values())

    logger.info(
        "Ollama warmup 結果: %s (all_success=%s)",
        results, all_success,
    )

    return OllamaWarmupResponse(
        results=results,
        all_success=all_success,
    )
