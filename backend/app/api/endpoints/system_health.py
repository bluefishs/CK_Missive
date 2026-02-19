"""
系統健康檢查 API 端點
提供系統狀態監控和健康檢查功能
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Any
from datetime import datetime
import json
import time

from app.db.database import get_async_db
from app.api.endpoints.auth import get_current_user
from app.extended.models import (
    User, OfficialDocument, GovernmentAgency, PartnerVendor,
    SiteNavigationItem, UserSession
)
from sqlalchemy import select, func, case

router = APIRouter()

async def check_database_connection(db: AsyncSession) -> Dict[str, Any]:
    """檢查資料庫連接"""
    try:
        start_time = time.time()
        result = await db.execute(select(func.now()))
        response_time = time.time() - start_time

        return {
            "status": "healthy",
            "response_time": round(response_time * 1000, 2),  # ms
            "message": "資料庫連接正常"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "response_time": None,
            "message": f"資料庫連接失敗: {str(e)}"
        }

async def check_critical_tables(db: AsyncSession) -> Dict[str, Any]:
    """檢查關鍵資料表（使用 ORM 查詢，避免 SQL 注入風險）"""
    # ORM 模型白名單：表名 → Model 對應
    critical_table_models = {
        "users": User,
        "user_sessions": UserSession,
        "documents": OfficialDocument,
        "agencies": GovernmentAgency,
        "partner_vendors": PartnerVendor,
        "site_navigation_items": SiteNavigationItem,
    }

    table_status = {}
    overall_healthy = True

    for table_name, model in critical_table_models.items():
        try:
            start_time = time.time()
            result = await db.execute(select(func.count()).select_from(model))
            count = result.scalar()
            response_time = time.time() - start_time

            table_status[table_name] = {
                "status": "healthy",
                "count": count,
                "response_time": round(response_time * 1000, 2)
            }
        except Exception as e:
            overall_healthy = False
            table_status[table_name] = {
                "status": "unhealthy",
                "error": str(e),
                "response_time": None
            }

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "tables": table_status
    }

@router.get("/health", summary="基本健康檢查")
async def basic_health_check():
    """
    基本健康檢查端點
    返回服務狀態和基本資訊
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "CK Missive API",
        "version": "2.0.0"
    }

@router.get("/health/detailed", summary="詳細健康檢查")
async def detailed_health_check(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    詳細健康檢查
    需要認證，提供完整的系統狀態
    """
    try:
        # 檢查資料庫連接
        db_check = await check_database_connection(db)

        # 檢查關鍵資料表
        tables_check = await check_critical_tables(db)

        # 計算整體狀態
        overall_status = "healthy"
        if db_check["status"] != "healthy" or tables_check["status"] == "unhealthy":
            overall_status = "unhealthy"
        elif tables_check["status"] == "degraded":
            overall_status = "degraded"

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": db_check,
                "tables": tables_check
            },
            "system_info": {
                "authenticated_user": current_user.username,
                "user_permissions_count": len(json.loads(current_user.permissions)) if current_user.permissions else 0
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"健康檢查失敗: {str(e)}"
        )

@router.get("/health/navigation", summary="導覽系統健康檢查")
async def navigation_health_check(
    db: AsyncSession = Depends(get_async_db)
):
    """
    專門檢查導覽系統的健康狀態
    """
    try:
        start_time = time.time()

        # 檢查導覽項目數量（ORM 查詢）
        result = await db.execute(
            select(
                func.count().label("total_items"),
                func.count(case((SiteNavigationItem.parent_id.is_(None), 1))).label("root_items"),
                func.count(case((SiteNavigationItem.parent_id.isnot(None), 1))).label("child_items"),
            ).where(SiteNavigationItem.is_enabled == True)  # noqa: E712
        )
        stats = result.fetchone()

        response_time = time.time() - start_time

        # 檢查是否有基本的導覽項目
        has_basic_navigation = stats.total_items >= 5  # 至少要有基本的導覽項目

        return {
            "status": "healthy" if has_basic_navigation else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "navigation_stats": {
                "total_items": stats.total_items,
                "root_items": stats.root_items,
                "child_items": stats.child_items,
                "response_time": round(response_time * 1000, 2)
            },
            "message": "導覽系統正常" if has_basic_navigation else "導覽項目數量不足"
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "message": "導覽系統檢查失敗"
        }

@router.get("/metrics", summary="系統指標")
async def system_metrics(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    獲取系統運行指標
    """
    try:
        # 統計各種數據（ORM 查詢）
        metrics_orm = {
            "total_users": select(func.count()).select_from(User).where(User.is_active == True),  # noqa: E712
            "total_documents": select(func.count()).select_from(OfficialDocument),
            "total_agencies": select(func.count()).select_from(GovernmentAgency),
            "total_vendors": select(func.count()).select_from(PartnerVendor),
            "active_sessions": select(func.count()).select_from(UserSession).where(UserSession.is_active == True),  # noqa: E712
            "navigation_items": select(func.count()).select_from(SiteNavigationItem).where(SiteNavigationItem.is_enabled == True),  # noqa: E712
        }

        metrics = {}
        for metric_name, query in metrics_orm.items():
            try:
                result = await db.execute(query)
                metrics[metric_name] = result.scalar() or 0
            except Exception:
                metrics[metric_name] = -1  # 表示查詢失敗

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics,
            "checked_by": current_user.username
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取系統指標失敗: {str(e)}"
        )