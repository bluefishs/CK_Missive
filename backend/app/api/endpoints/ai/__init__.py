"""
AI API 端點模組

Version: 1.6.0
Created: 2026-02-04
Updated: 2026-02-26 - 新增 Agentic 問答端點
"""

from fastapi import APIRouter

from .document_ai import router as document_ai_router
from .ai_stats import router as ai_stats_router
from .synonyms import router as synonyms_router
from .prompts import router as prompts_router
from .search_history import router as search_history_router
from .relation_graph import router as relation_graph_router
from .embedding_pipeline import router as embedding_pipeline_router
from .entity_extraction import router as entity_extraction_router
from .graph_query import router as graph_query_router
from .ollama_management import router as ollama_management_router
from .rag_query import router as rag_query_router
from .agent_query import router as agent_query_router
from .ai_feedback import router as ai_feedback_router
from .document_analysis import router as document_analysis_router

router = APIRouter(prefix="/ai", tags=["AI"])

# 註冊子路由
router.include_router(document_ai_router)
router.include_router(ai_stats_router)
router.include_router(ai_feedback_router)
router.include_router(synonyms_router)
router.include_router(prompts_router)
router.include_router(search_history_router)
router.include_router(relation_graph_router)
router.include_router(embedding_pipeline_router)
router.include_router(entity_extraction_router)
router.include_router(graph_query_router)
router.include_router(ollama_management_router)
router.include_router(rag_query_router)
router.include_router(agent_query_router)
router.include_router(document_analysis_router)
