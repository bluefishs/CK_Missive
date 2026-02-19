#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署管理 Schema 定義

提供部署管理 API 的 Request/Response 型別定義。

@version 1.0.0
@date 2026-02-19
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


# =============================================================================
# 列舉型別
# =============================================================================

class ServiceStatus(str, Enum):
    """服務狀態"""
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    UNKNOWN = "unknown"


class DeploymentStatus(str, Enum):
    """部署狀態"""
    SUCCESS = "success"
    FAILURE = "failure"
    IN_PROGRESS = "in_progress"
    CANCELLED = "cancelled"
    PENDING = "pending"


# =============================================================================
# 回應模型
# =============================================================================

class ServiceHealth(BaseModel):
    """服務健康狀態"""
    name: str
    status: ServiceStatus
    version: Optional[str] = None
    uptime: Optional[str] = None
    last_check: datetime


class SystemStatusResponse(BaseModel):
    """系統狀態回應"""
    overall_status: ServiceStatus
    services: List[ServiceHealth]
    current_version: Optional[str] = None
    last_deployment: Optional[datetime] = None
    environment: str = "production"


class DeploymentRecord(BaseModel):
    """部署記錄"""
    id: int
    run_number: int
    status: DeploymentStatus
    conclusion: Optional[str] = None
    branch: str
    commit_sha: str
    commit_message: Optional[str] = None
    triggered_by: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    url: str


class DeploymentHistoryResponse(BaseModel):
    """部署歷史回應"""
    total: int
    records: List[DeploymentRecord]


# =============================================================================
# 請求模型
# =============================================================================

class TriggerDeploymentRequest(BaseModel):
    """觸發部署請求"""
    ref: str = Field(default="main", description="分支或標籤名稱")
    force_rebuild: bool = Field(default=False, description="強制重新建置")
    skip_backup: bool = Field(default=False, description="跳過備份")


class TriggerDeploymentResponse(BaseModel):
    """觸發部署回應"""
    success: bool
    message: str
    workflow_run_id: Optional[int] = None
    url: Optional[str] = None


class RollbackRequest(BaseModel):
    """回滾請求"""
    target_version: Optional[str] = Field(default=None, description="目標版本 (留空則回滾到上一版)")
    confirm: bool = Field(default=False, description="確認回滾")


class RollbackResponse(BaseModel):
    """回滾回應"""
    success: bool
    message: str
    previous_version: Optional[str] = None
    current_version: Optional[str] = None


# =============================================================================
# 日誌模型
# =============================================================================

class DeploymentLog(BaseModel):
    """部署日誌"""
    job_name: str
    status: str
    logs: str


class DeploymentLogsResponse(BaseModel):
    """部署日誌回應"""
    run_id: int
    status: str
    jobs: List[DeploymentLog]
