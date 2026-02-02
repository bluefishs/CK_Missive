"""
部署管理 API

提供系統部署狀態監控、部署歷史查詢、觸發部署和回滾操作等功能。

@version 1.0.0
@date 2026-02-02
"""

import os
import httpx
import asyncio
import subprocess
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from enum import Enum
import logging

from app.core.dependencies import require_admin
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deploy", tags=["部署管理"])


# =============================================================================
# 資料模型
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


# =============================================================================
# GitHub API 配置
# =============================================================================

GITHUB_API_BASE = "https://api.github.com"
GITHUB_REPO = os.getenv("GITHUB_REPO", "bluefishs/CK_Missive")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
WORKFLOW_FILE = "deploy-production.yml"


def get_github_headers() -> dict:
    """取得 GitHub API 標頭"""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


# =============================================================================
# API 端點
# =============================================================================

@router.post("/status", response_model=SystemStatusResponse, summary="取得系統狀態")
async def get_system_status(
    _: dict = Depends(require_admin)
):
    """
    取得當前系統部署狀態，包括各服務健康狀態。

    需要管理員權限。
    """
    services = []
    overall_status = ServiceStatus.RUNNING

    # 檢查後端服務
    backend_status = ServiceStatus.RUNNING
    backend_version = None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8001/health")
            if response.status_code == 200:
                health_data = response.json()
                backend_version = health_data.get("version", "unknown")
            else:
                backend_status = ServiceStatus.ERROR
    except Exception as e:
        logger.warning(f"後端健康檢查失敗: {e}")
        backend_status = ServiceStatus.ERROR
        overall_status = ServiceStatus.ERROR

    services.append(ServiceHealth(
        name="Backend API",
        status=backend_status,
        version=backend_version,
        last_check=datetime.now()
    ))

    # 檢查前端服務
    frontend_status = ServiceStatus.RUNNING
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:3000")
            if response.status_code != 200:
                frontend_status = ServiceStatus.ERROR
    except Exception as e:
        logger.warning(f"前端健康檢查失敗: {e}")
        frontend_status = ServiceStatus.ERROR
        if overall_status == ServiceStatus.RUNNING:
            overall_status = ServiceStatus.ERROR

    services.append(ServiceHealth(
        name="Frontend",
        status=frontend_status,
        last_check=datetime.now()
    ))

    # 檢查資料庫服務
    db_status = ServiceStatus.RUNNING
    try:
        # 透過後端 health 端點檢查資料庫
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8001/health")
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get("database") != "connected":
                    db_status = ServiceStatus.ERROR
    except Exception:
        db_status = ServiceStatus.UNKNOWN

    services.append(ServiceHealth(
        name="PostgreSQL",
        status=db_status,
        last_check=datetime.now()
    ))

    # 取得最後部署時間
    last_deployment = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/actions/workflows/{WORKFLOW_FILE}/runs",
                headers=get_github_headers(),
                params={"per_page": 1, "status": "completed"}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("workflow_runs"):
                    last_run = data["workflow_runs"][0]
                    last_deployment = datetime.fromisoformat(
                        last_run["updated_at"].replace("Z", "+00:00")
                    )
    except Exception as e:
        logger.warning(f"取得最後部署時間失敗: {e}")

    return SystemStatusResponse(
        overall_status=overall_status,
        services=services,
        current_version=backend_version,
        last_deployment=last_deployment,
        environment=os.getenv("ENVIRONMENT", "production")
    )


@router.post("/history", response_model=DeploymentHistoryResponse, summary="取得部署歷史")
async def get_deployment_history(
    page: int = Query(1, ge=1, description="頁碼"),
    page_size: int = Query(10, ge=1, le=50, description="每頁數量"),
    status: Optional[str] = Query(None, description="篩選狀態"),
    _: dict = Depends(require_admin)
):
    """
    取得部署歷史記錄，從 GitHub Actions 工作流執行記錄中獲取。

    需要管理員權限。
    """
    if not GITHUB_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="未配置 GitHub Token，無法取得部署歷史"
        )

    try:
        params = {
            "per_page": page_size,
            "page": page
        }
        if status:
            params["status"] = status

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/actions/workflows/{WORKFLOW_FILE}/runs",
                headers=get_github_headers(),
                params=params
            )

            if response.status_code == 404:
                return DeploymentHistoryResponse(total=0, records=[])

            response.raise_for_status()
            data = response.json()

        records = []
        for run in data.get("workflow_runs", []):
            # 計算持續時間
            duration = None
            started_at = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
            completed_at = None

            if run.get("updated_at"):
                completed_at = datetime.fromisoformat(run["updated_at"].replace("Z", "+00:00"))
                if run["status"] == "completed":
                    duration = int((completed_at - started_at).total_seconds())

            # 轉換狀態
            status_map = {
                "completed": DeploymentStatus.SUCCESS if run.get("conclusion") == "success" else DeploymentStatus.FAILURE,
                "in_progress": DeploymentStatus.IN_PROGRESS,
                "queued": DeploymentStatus.PENDING,
                "cancelled": DeploymentStatus.CANCELLED,
            }
            deployment_status = status_map.get(run["status"], DeploymentStatus.PENDING)

            records.append(DeploymentRecord(
                id=run["id"],
                run_number=run["run_number"],
                status=deployment_status,
                conclusion=run.get("conclusion"),
                branch=run["head_branch"],
                commit_sha=run["head_sha"][:7],
                commit_message=run.get("head_commit", {}).get("message", "")[:100] if run.get("head_commit") else None,
                triggered_by=run["triggering_actor"]["login"] if run.get("triggering_actor") else "unknown",
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                url=run["html_url"]
            ))

        return DeploymentHistoryResponse(
            total=data.get("total_count", len(records)),
            records=records
        )

    except httpx.HTTPStatusError as e:
        logger.error(f"GitHub API 錯誤: {e}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"GitHub API 錯誤: {e.response.text}"
        )
    except Exception as e:
        logger.error(f"取得部署歷史失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"取得部署歷史失敗: {str(e)}"
        )


@router.post("/trigger", response_model=TriggerDeploymentResponse, summary="觸發部署")
async def trigger_deployment(
    request: TriggerDeploymentRequest,
    _: dict = Depends(require_admin)
):
    """
    觸發 GitHub Actions 部署工作流。

    需要管理員權限。
    """
    if not GITHUB_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="未配置 GitHub Token，無法觸發部署"
        )

    try:
        # 觸發 workflow_dispatch 事件
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches",
                headers=get_github_headers(),
                json={
                    "ref": request.ref,
                    "inputs": {
                        "force_rebuild": str(request.force_rebuild).lower(),
                        "skip_backup": str(request.skip_backup).lower()
                    }
                }
            )

            if response.status_code == 204:
                # 等待一下讓 workflow 開始
                await asyncio.sleep(2)

                # 取得剛觸發的 workflow run
                runs_response = await client.get(
                    f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/actions/workflows/{WORKFLOW_FILE}/runs",
                    headers=get_github_headers(),
                    params={"per_page": 1}
                )

                workflow_run_id = None
                url = None
                if runs_response.status_code == 200:
                    runs_data = runs_response.json()
                    if runs_data.get("workflow_runs"):
                        latest_run = runs_data["workflow_runs"][0]
                        workflow_run_id = latest_run["id"]
                        url = latest_run["html_url"]

                return TriggerDeploymentResponse(
                    success=True,
                    message=f"已觸發部署工作流 (ref: {request.ref})",
                    workflow_run_id=workflow_run_id,
                    url=url
                )
            else:
                error_detail = response.text
                logger.error(f"觸發部署失敗: {response.status_code} - {error_detail}")
                return TriggerDeploymentResponse(
                    success=False,
                    message=f"觸發部署失敗: {error_detail}"
                )

    except Exception as e:
        logger.error(f"觸發部署異常: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"觸發部署失敗: {str(e)}"
        )


@router.post("/rollback", response_model=RollbackResponse, summary="回滾部署")
async def rollback_deployment(
    request: RollbackRequest,
    _: dict = Depends(require_admin)
):
    """
    回滾到上一個版本。

    需要管理員權限，且必須確認操作。
    """
    if not request.confirm:
        raise HTTPException(
            status_code=400,
            detail="請確認回滾操作 (confirm: true)"
        )

    try:
        # 執行 Docker 回滾命令
        # 注意：這需要在有 Docker 權限的環境中執行
        rollback_commands = [
            "docker tag ck-missive-backend:rollback ck-missive-backend:latest",
            "docker tag ck-missive-frontend:rollback ck-missive-frontend:latest",
        ]

        for cmd in rollback_commands:
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                logger.warning(f"回滾命令警告: {cmd} - {result.stderr}")

        # 重啟服務
        restart_cmd = "docker compose -f docker-compose.production.yml up -d"
        result = subprocess.run(
            restart_cmd.split(),
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.getenv("DEPLOY_PATH", "/share/CACHEDEV1_DATA/Container/ck-missive")
        )

        if result.returncode == 0:
            return RollbackResponse(
                success=True,
                message="回滾成功，服務已重啟",
                previous_version="rollback",
                current_version="latest"
            )
        else:
            return RollbackResponse(
                success=False,
                message=f"回滾失敗: {result.stderr}"
            )

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="回滾操作超時"
        )
    except Exception as e:
        logger.error(f"回滾異常: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"回滾失敗: {str(e)}"
        )


@router.post("/logs/{run_id}", response_model=DeploymentLogsResponse, summary="取得部署日誌")
async def get_deployment_logs(
    run_id: int,
    _: dict = Depends(require_admin)
):
    """
    取得指定部署的日誌。

    需要管理員權限。
    """
    if not GITHUB_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="未配置 GitHub Token，無法取得部署日誌"
        )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 取得 workflow run 資訊
            run_response = await client.get(
                f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/actions/runs/{run_id}",
                headers=get_github_headers()
            )
            run_response.raise_for_status()
            run_data = run_response.json()

            # 取得 jobs
            jobs_response = await client.get(
                f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/actions/runs/{run_id}/jobs",
                headers=get_github_headers()
            )
            jobs_response.raise_for_status()
            jobs_data = jobs_response.json()

            jobs = []
            for job in jobs_data.get("jobs", []):
                # 取得 job 日誌 (簡化版，只取得步驟摘要)
                steps_summary = []
                for step in job.get("steps", []):
                    status_icon = "✅" if step["conclusion"] == "success" else "❌" if step["conclusion"] == "failure" else "⏳"
                    steps_summary.append(f"{status_icon} {step['name']}")

                jobs.append(DeploymentLog(
                    job_name=job["name"],
                    status=job["conclusion"] or job["status"],
                    logs="\n".join(steps_summary)
                ))

            return DeploymentLogsResponse(
                run_id=run_id,
                status=run_data["conclusion"] or run_data["status"],
                jobs=jobs
            )

    except httpx.HTTPStatusError as e:
        logger.error(f"GitHub API 錯誤: {e}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"取得日誌失敗: {e.response.text}"
        )
    except Exception as e:
        logger.error(f"取得部署日誌失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"取得部署日誌失敗: {str(e)}"
        )


@router.post("/config", summary="取得部署配置")
async def get_deployment_config(
    _: dict = Depends(require_admin)
):
    """
    取得當前部署配置資訊。

    需要管理員權限。
    """
    return {
        "github_repo": GITHUB_REPO,
        "workflow_file": WORKFLOW_FILE,
        "github_token_configured": bool(GITHUB_TOKEN),
        "deploy_path": os.getenv("DEPLOY_PATH", "未配置"),
        "environment": os.getenv("ENVIRONMENT", "production"),
    }
