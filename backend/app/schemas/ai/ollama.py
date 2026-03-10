"""Ollama 管理 Schema"""
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class OllamaGpuLoadedModel(BaseModel):
    """GPU 已載入模型資訊"""
    name: str = Field(..., description="模型名稱")
    size: int = Field(default=0, description="模型大小 (bytes)")
    size_vram: int = Field(default=0, description="VRAM 使用量 (bytes)")


class OllamaGpuInfo(BaseModel):
    """Ollama GPU 資訊"""
    loaded_models: List[OllamaGpuLoadedModel] = Field(
        default=[], description="已載入至 GPU 的模型列表"
    )


class OllamaStatusResponse(BaseModel):
    """Ollama 詳細狀態回應"""
    available: bool = Field(default=False, description="Ollama 服務是否可用")
    message: str = Field(default="", description="狀態訊息")
    models: List[str] = Field(default=[], description="已安裝的模型列表")
    required_models: List[str] = Field(default=[], description="系統必要模型列表")
    required_models_ready: bool = Field(default=False, description="所有必要模型是否就緒")
    missing_models: List[str] = Field(default=[], description="缺少的必要模型列表")
    gpu_info: Optional[OllamaGpuInfo] = Field(None, description="GPU 使用資訊")
    groq_available: bool = Field(default=False, description="Groq API 是否可用")
    groq_message: str = Field(default="", description="Groq 狀態訊息")


class OllamaEnsureModelsResponse(BaseModel):
    """Ollama 模型檢查與拉取回應"""
    ollama_available: bool = Field(default=False, description="Ollama 服務是否可用")
    installed: List[str] = Field(default=[], description="已安裝的模型列表")
    pulled: List[str] = Field(default=[], description="本次新拉取成功的模型列表")
    failed: List[str] = Field(default=[], description="拉取失敗的模型列表")


class OllamaWarmupResponse(BaseModel):
    """Ollama 模型預熱回應"""
    results: Dict[str, bool] = Field(
        default_factory=dict,
        description="每個模型的預熱結果 {model_name: success}"
    )
    all_success: bool = Field(default=False, description="是否全部模型預熱成功")
