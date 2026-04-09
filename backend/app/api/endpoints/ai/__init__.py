"""
AI API 端點模組

Version: 1.7.0
Created: 2026-02-04
Updated: 2026-03-27 - 新增數位分身路由
"""

from fastapi import APIRouter

from .document_ai import router as document_ai_router
from .ai_stats import router as ai_stats_router
from .ai_monitoring import router as ai_monitoring_router
from .synonyms import router as synonyms_router
from .prompts import router as prompts_router
from .search_history import router as search_history_router
from .relation_graph import router as relation_graph_router
from .embedding_pipeline import router as embedding_pipeline_router
from .entity_extraction import router as entity_extraction_router
from .graph_entity import router as graph_entity_router
from .graph_admin import router as graph_admin_router
from .graph_admin_code import router as graph_admin_code_router
from .graph_unified import router as graph_unified_router
from .graph_skills_map import router as graph_skills_map_router
from .agent_nemoclaw import router as agent_nemoclaw_router
from .ollama_management import router as ollama_management_router
from .rag_query import router as rag_query_router
from .agent_query import router as agent_query_router
from .agent_query_sync import router as agent_query_sync_router
from .ai_feedback import router as ai_feedback_router
from .document_analysis import router as document_analysis_router
from .voice_transcription import router as voice_transcription_router
from .digital_twin import router as digital_twin_router
from .agent_evolution import router as agent_evolution_router
from .tools_manifest import router as tools_manifest_router
from .diagram_analysis import router as diagram_analysis_router

router = APIRouter(prefix="/ai", tags=["AI"])

# 註冊子路由
router.include_router(document_ai_router)
router.include_router(ai_stats_router)
router.include_router(ai_monitoring_router)
router.include_router(ai_feedback_router)
router.include_router(synonyms_router)
router.include_router(prompts_router)
router.include_router(search_history_router)
router.include_router(relation_graph_router)
router.include_router(embedding_pipeline_router)
router.include_router(entity_extraction_router)
router.include_router(graph_entity_router)
router.include_router(graph_admin_router)
router.include_router(graph_admin_code_router)
router.include_router(graph_unified_router)
router.include_router(graph_skills_map_router)
router.include_router(agent_nemoclaw_router)
router.include_router(ollama_management_router)
router.include_router(rag_query_router)
router.include_router(agent_query_router)
router.include_router(agent_query_sync_router)
router.include_router(document_analysis_router)
router.include_router(voice_transcription_router)
router.include_router(digital_twin_router)
router.include_router(agent_evolution_router)
router.include_router(tools_manifest_router)
router.include_router(diagram_analysis_router)
