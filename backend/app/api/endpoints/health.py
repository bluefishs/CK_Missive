"""
API 健康監控端點
"""
import time
import psutil
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime

from app.db.database import get_async_db, engine
from app.extended.models import OfficialDocument, GovernmentAgency, PartnerVendor, ContractProject

router = APIRouter()

@router.get("/health", summary="基本健康檢查")
async def basic_health_check():
    """基本健康檢查端點"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "CK Missive API"
    }

@router.get("/health/detailed", summary="詳細健康檢查")
async def detailed_health_check(db: AsyncSession = Depends(get_async_db)) -> Dict[str, Any]:
    """詳細系統健康檢查"""
    start_time = time.time()
    health_data = {
        "timestamp": datetime.now().isoformat(),
        "service": "CK Missive API",
        "version": "3.0.0",
        "status": "healthy",
        "checks": {}
    }

    # 1. 資料庫連線檢查
    try:
        db_start = time.time()
        result = await db.execute(text("SELECT 1"))
        db_response_time = (time.time() - db_start) * 1000

        health_data["checks"]["database"] = {
            "status": "healthy",
            "response_time_ms": round(db_response_time, 2),
            "message": "Database connection successful"
        }
    except Exception as e:
        health_data["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e),
            "message": "Database connection failed"
        }
        health_data["status"] = "unhealthy"

    # 2. 核心資料表檢查
    tables_check = {}
    tables = [
        ("documents", OfficialDocument),
        ("agencies", GovernmentAgency),
        ("vendors", PartnerVendor),
        ("projects", ContractProject)
    ]

    for table_name, model in tables:
        try:
            table_start = time.time()
            result = await db.execute(text(f"SELECT COUNT(*) FROM {model.__tablename__}"))
            count = result.scalar()
            table_response_time = (time.time() - table_start) * 1000

            tables_check[table_name] = {
                "status": "healthy",
                "record_count": count,
                "response_time_ms": round(table_response_time, 2)
            }
        except Exception as e:
            tables_check[table_name] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_data["status"] = "unhealthy"

    health_data["checks"]["tables"] = tables_check

    # 3. 連線池狀態
    try:
        pool_info = {
            "size": engine.pool.size(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
            "checked_in": engine.pool.checkedin()
        }
        health_data["checks"]["connection_pool"] = {
            "status": "healthy",
            "pool_info": pool_info,
            "utilization_percent": round((pool_info["checked_out"] / pool_info["size"]) * 100, 2)
        }
    except Exception as e:
        health_data["checks"]["connection_pool"] = {
            "status": "unknown",
            "error": str(e)
        }

    # 4. 系統資源檢查
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        health_data["checks"]["system_resources"] = {
            "status": "healthy",
            "memory": {
                "used_percent": memory.percent,
                "available_gb": round(memory.available / (1024**3), 2),
                "total_gb": round(memory.total / (1024**3), 2)
            },
            "disk": {
                "used_percent": disk.percent,
                "free_gb": round(disk.free / (1024**3), 2),
                "total_gb": round(disk.total / (1024**3), 2)
            }
        }

        # 警告閾值檢查
        if memory.percent > 90 or disk.percent > 90:
            health_data["checks"]["system_resources"]["status"] = "warning"
            health_data["checks"]["system_resources"]["warnings"] = []

            if memory.percent > 90:
                health_data["checks"]["system_resources"]["warnings"].append("High memory usage")
            if disk.percent > 90:
                health_data["checks"]["system_resources"]["warnings"].append("High disk usage")

    except Exception as e:
        health_data["checks"]["system_resources"] = {
            "status": "unknown",
            "error": str(e)
        }

    # 5. API 回應時間
    total_response_time = (time.time() - start_time) * 1000
    health_data["total_response_time_ms"] = round(total_response_time, 2)

    # 6. 整體狀態評估
    if total_response_time > 5000:  # 5秒
        health_data["status"] = "slow"
        health_data["message"] = "API response time is slower than expected"
    elif health_data["status"] == "healthy":
        health_data["message"] = "All systems operational"

    return health_data

@router.get("/health/metrics", summary="效能指標")
async def get_performance_metrics(db: AsyncSession = Depends(get_async_db)):
    """獲取系統效能指標"""
    try:
        # 資料庫查詢效能測試
        metrics = {}

        # 測試各種查詢的效能
        queries = {
            "simple_count": "SELECT COUNT(*) FROM documents",
            "complex_join": """
                SELECT COUNT(d.id)
                FROM documents d
                LEFT JOIN government_agencies ga ON d.sender_agency_id = ga.id
                WHERE d.doc_date > CURRENT_DATE - INTERVAL '1 year'
            """,
            "aggregation": """
                SELECT EXTRACT(year FROM doc_date) as year, COUNT(*)
                FROM documents
                WHERE doc_date IS NOT NULL
                GROUP BY EXTRACT(year FROM doc_date)
            """
        }

        for query_name, query_sql in queries.items():
            start_time = time.time()
            try:
                result = await db.execute(text(query_sql))
                result.fetchall()  # 確保完全執行
                execution_time = (time.time() - start_time) * 1000

                metrics[query_name] = {
                    "execution_time_ms": round(execution_time, 2),
                    "status": "success"
                }
            except Exception as e:
                metrics[query_name] = {
                    "execution_time_ms": None,
                    "status": "error",
                    "error": str(e)
                }

        return {
            "timestamp": datetime.now().isoformat(),
            "database_metrics": metrics,
            "recommendations": _get_performance_recommendations(metrics)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"無法獲取效能指標: {str(e)}")

def _get_performance_recommendations(metrics: Dict[str, Any]) -> list:
    """根據效能指標提供優化建議"""
    recommendations = []

    for query_name, metric in metrics.items():
        if metric.get("execution_time_ms"):
            execution_time = metric["execution_time_ms"]

            if execution_time > 1000:  # 1秒
                recommendations.append(f"{query_name} 查詢耗時過長 ({execution_time:.2f}ms)，建議新增索引優化")
            elif execution_time > 500:  # 500ms
                recommendations.append(f"{query_name} 查詢可進一步優化 ({execution_time:.2f}ms)")

    if not recommendations:
        recommendations.append("所有查詢效能良好，無需優化")

    return recommendations

@router.get("/health/readiness", summary="就緒狀態檢查")
async def readiness_check(db: AsyncSession = Depends(get_async_db)):
    """檢查服務是否已準備好接受流量"""
    try:
        # 檢查資料庫連線
        await db.execute(text("SELECT 1"))

        # 檢查核心資料表
        await db.execute(text("SELECT COUNT(*) FROM documents LIMIT 1"))

        return {
            "status": "ready",
            "timestamp": datetime.now().isoformat(),
            "message": "Service is ready to accept traffic"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "message": "Service is not ready to accept traffic"
            }
        )

@router.get("/health/liveness", summary="存活狀態檢查")
async def liveness_check():
    """檢查服務是否存活"""
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "message": "Service is alive"
    }