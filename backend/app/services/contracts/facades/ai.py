# -*- coding: utf-8 -*-
"""AIFacade - AI context 對外唯一入口

v6.10 P1 Phase B (2026-05-18)

解 step 29 揭發最大宗 cross-context 依賴：
  - integration -> ai (12 imports, 最大宗)
  - agency -> ai (1)
  - erp -> ai (3)
  - document -> ai (3)
  - memory -> ai (4)

統一封 RAG / Agent / Embedding / Synthesis 等 AI 操作。
"""
from __future__ import annotations

from typing import Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class AIFacade:
    """AI bounded context 對外唯一入口

    使用範例：
        facade = AIFacade(db)
        answer = await facade.query("query example")
        embeddings = await facade.embed_text("文字內容")
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    # === Public API ===

    async def query(
        self,
        question: str,
        *,
        user_id: Optional[int] = None,
        channel: str = "web",
        max_tokens: int = 1024,
    ) -> dict:
        """執行 Agentic Query (RAG + 工具 + synthesis)

        取代 anti-pattern:
          from app.services.ai.agent.agent_orchestrator import run_query
        """
        try:
            from app.services.ai.agent.agent_orchestrator import AgentOrchestrator
            orchestrator = AgentOrchestrator(self._db)
            return await orchestrator.run(
                question=question,
                user_id=user_id,
                channel=channel,
                max_tokens=max_tokens,
            )
        except (ImportError, AttributeError):
            return {"answer": "", "error": "AgentOrchestrator unavailable"}

    async def embed_text(
        self,
        text: str,
        *,
        model: Optional[str] = None,
    ) -> Optional[List[float]]:
        """產生 text embedding (預設 nomic 768D)"""
        try:
            from app.services.ai.core.embedding_manager import get_embedding
            return await get_embedding(text, model=model)
        except (ImportError, AttributeError):
            return None

    async def synthesize(
        self,
        sources: List[dict],
        question: str,
        *,
        max_tokens: int = 512,
    ) -> dict:
        """從多來源合成回答（取代 ai/agent_synthesis 直 import）"""
        try:
            from app.services.ai.agent.agent_synthesis import synthesize_response
            return await synthesize_response(self._db, sources=sources, question=question, max_tokens=max_tokens)
        except (ImportError, AttributeError):
            return {"text": "", "error": "synthesis unavailable"}

    async def extract_entities(
        self,
        text: str,
    ) -> List[dict]:
        """從文字抽取實體 (NER)"""
        try:
            from app.services.ai.document.entity_extraction import extract_entities
            return await extract_entities(self._db, text)
        except (ImportError, AttributeError):
            return []

    async def get_tool_manifest(self) -> dict:
        """取得當前可用工具清單（Hermes bridge 用）"""
        try:
            from app.services.ai.tools.tool_registry import get_tool_manifest
            return get_tool_manifest()
        except (ImportError, AttributeError):
            return {"tools": [], "error": "tool_registry unavailable"}


__all__ = ["AIFacade"]
