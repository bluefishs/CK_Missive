"""LLM Wiki 端點請求（2026-08-17 由 `api/endpoints/wiki.py` 搬入）

依 `.claude/rules/development-rules.md` §3。
"""
from typing import List, Optional

from pydantic import BaseModel, Field



class IngestEntityRequest(BaseModel):
    name: str
    entity_type: str
    description: str
    sources: List[str] = []
    tags: List[str] = []
    related_entities: List[str] = []
    confidence: str = "medium"


class IngestSourceRequest(BaseModel):
    title: str
    source_type: str
    summary: str
    key_points: List[str] = []
    entities_mentioned: List[str] = []
    source_id: Optional[str] = None
    tags: List[str] = []


class SaveSynthesisRequest(BaseModel):
    title: str
    content_md: str
    sources: List[str] = []
    tags: List[str] = []


class SearchRequest(BaseModel):
    query: str
    limit: int = 10


# ── Endpoints ──
