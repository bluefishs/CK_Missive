"""
搜尋品質基準測試 API — Search Quality Benchmark 領域（admin only）

從 ai_stats.py 抽出（領域驅動分治）。
這不是 stats，是搜尋品質的 benchmark 工具。

端點:
- POST /ai/stats/search/benchmark — 30 筆 ground truth 評估，支援 v1/v2/A/B 比較
"""

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import optional_auth, get_async_db
from app.schemas.ai.stats import BenchmarkRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/stats/search/benchmark")
async def run_search_benchmark(
    request: BenchmarkRequest = BenchmarkRequest(),
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
):
    """
    搜尋品質基準測試（admin only）

    使用 30 筆 ground truth 查詢評估搜尋品質，
    支援 v1 (rule-based) / v2 (Gemma4 rerank) / both (A/B 比較)。
    回傳 Precision@K, MRR, nDCG@K, keyword hit rate, latency 等指標。
    """
    try:
        from tests.benchmarks.reranker_benchmark import SearchBenchmark

        benchmark = SearchBenchmark()
        results = await benchmark.run_benchmark(
            db_session=db,
            mode=request.mode,
            top_k=request.top_k,
            categories=request.categories,
        )
        return JSONResponse(
            {"success": True, "data": results},
            media_type="application/json; charset=utf-8",
        )
    except Exception as e:
        logger.error("Search benchmark failed: %s", e, exc_info=True)
        return JSONResponse(
            {"success": False, "error": "基準測試執行失敗，請稍後再試"},
            status_code=500,
            media_type="application/json; charset=utf-8",
        )
