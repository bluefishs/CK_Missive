# -*- coding: utf-8 -*-
"""WikiFacade - Wiki context 對外唯一入口

v6.10 P1 Phase B（2026-05-18）

解 step 29 揭發：
  - ai -> wiki (7 imports)
  - memory -> wiki (2 imports)
  - document -> wiki (1 import)

統一封 LLM Wiki 4-Phase（Ingest / Compile / Query / Lint）操作。
"""
from __future__ import annotations

from typing import Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class WikiFacade:
    """Wiki bounded context 對外唯一入口

    使用範例：
        facade = WikiFacade(db)
        pages = await facade.search_pages("query")
        coverage = await facade.get_coverage_stats()
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        """v6.12 B 方案 (2026-05-30): db 改 Optional

        理由：search_wiki / read_page / get_stats 走 get_wiki_service() singleton 不需 db
        只有 search_pages / get_page_by_kg_entity / compile_incremental 需 db
        放寬讓 agent_synthesis 等 stateless caller 也能用 (caller +1 trial 推進)
        """
        self._db = db

    # === Public API ===

    async def search_pages(
        self,
        query: str,
        limit: int = 10,
        *,
        entity_type: Optional[str] = None,
    ) -> List[dict]:
        """搜尋 wiki pages (使用 wiki_compiler search)

        取代 ai/agent_synthesis.py 直 import wiki/service.py
        """
        try:
            from app.services.wiki.service import WikiService
            svc = WikiService(self._db)
            return await svc.search(query, limit=limit, entity_type=entity_type)
        except (ImportError, AttributeError):
            return []

    async def get_page_by_kg_entity(
        self,
        kg_entity_id: int,
    ) -> Optional[dict]:
        """從 KG entity ID 拿 wiki page (含 markdown)"""
        try:
            from app.services.wiki.service import WikiService
            svc = WikiService(self._db)
            return await svc.get_by_kg_entity_id(kg_entity_id)
        except (ImportError, AttributeError):
            return None

    async def get_coverage_stats(self) -> dict:
        """wiki coverage 統計 (entity type / link rate / KG match)"""
        try:
            from app.services.wiki.coverage import WikiCoverageService
            svc = WikiCoverageService(self._db)
            return await svc.compute_coverage()
        except (ImportError, AttributeError):
            return {"total_pages": 0, "linked_pct": 0.0}

    async def compile_incremental(
        self,
        min_doc_count: int = 5,
    ) -> dict:
        """Phase 2 Compile - 增量重編有新 document 的 entity"""
        try:
            from app.services.wiki.compiler import WikiCompiler
            compiler = WikiCompiler(self._db)
            return await compiler.compile_incremental(min_doc_count=min_doc_count)
        except (ImportError, AttributeError):
            return {"compiled": False, "reason": "WikiCompiler unavailable"}

    async def get_recent_topics(self, days: int = 7) -> List[dict]:
        """近期熱門 topics (給 AI agent 提示用)"""
        try:
            from app.services.wiki.service import WikiService
            svc = WikiService(self._db)
            return await svc.get_recent_topics(days=days)
        except (ImportError, AttributeError):
            return []

    # === v6.10 P1 真採用擴展（ai/agent/* 11 處 migration 配套） ===

    async def search_wiki(
        self,
        query: str,
        limit: int = 10,
    ) -> List[dict]:
        """LLM Wiki 全文搜尋（含 narrative + entity）

        取代 ai/agent_synthesis.py:486 + agent_tools.py:444 直 import wiki/service
        """
        try:
            from app.services.wiki.service import get_wiki_service
            return await get_wiki_service().search_wiki(query, limit=limit)
        except (ImportError, AttributeError):
            return []
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                "WikiFacade.search_wiki failed: %s", e, exc_info=True,
                extra={"query": query, "limit": limit},
            )
            return []

    async def read_page(
        self,
        page_path: str,
    ) -> Optional[str]:
        """讀單一 wiki page 完整 markdown 內容

        取代 ai/agent_tools.py:454 直 import wiki/service
        """
        try:
            from app.services.wiki.service import get_wiki_service
            return await get_wiki_service().read_page(page_path)
        except (ImportError, AttributeError):
            return None
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                "WikiFacade.read_page failed: %s", e, exc_info=True,
                extra={"page_path": page_path},
            )
            return None

    async def get_stats(self) -> dict:
        """wiki 統計（total / by_type / latest_updated）

        agent_synthesis.py 用於判斷 wiki 是否有內容
        """
        try:
            from app.services.wiki.service import get_wiki_service
            stats = get_wiki_service().get_stats()
            return stats or {"total": 0}
        except (ImportError, AttributeError):
            return {"total": 0}
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                "WikiFacade.get_stats failed: %s", e, exc_info=True,
            )
            return {"total": 0}

    async def ingest(
        self,
        *,
        page_type: str,
        title: str,
        content: str,
        sources: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> dict:
        """寫入 wiki — agent 自主進化核心

        取代 ai/agent_tools.py:466 直 import wiki/service
        page_type: entity / source / synthesis
        """
        try:
            from app.services.wiki.service import get_wiki_service
            svc = get_wiki_service()
            srcs = sources or []
            tg = tags or []
            if page_type == "entity":
                return await svc.ingest_entity(
                    name=title, entity_type="general",
                    description=content, sources=srcs, tags=tg,
                )
            elif page_type == "source":
                return await svc.ingest_source(
                    title=title, source_type="agent_analysis",
                    summary=content, key_points=[], entities_mentioned=[], tags=tg,
                )
            return await svc.save_synthesis(
                title=title, content_md=content, sources=srcs, tags=tg,
            )
        except (ImportError, AttributeError) as e:
            return {"error": str(e), "ok": False}
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                "WikiFacade.ingest failed: %s", e, exc_info=True,
                extra={"page_type": page_type, "title": title[:60]},
            )
            return {"error": str(e), "ok": False}

    async def auto_ingest_synthesis(
        self,
        *,
        question: str,
        answer: str,
        tools_used: List[str],
    ) -> bool:
        """非阻塞 agent 自動 wiki 寫入（fire-and-forget 場景）

        取代 ai/agent_orchestrator.py:633 直 import wiki/service
        """
        try:
            from app.services.wiki.service import get_wiki_service
            svc = get_wiki_service()
            title = question[:60].strip()
            tags = list(set(tools_used))[:5]
            await svc.save_synthesis(
                title=title,
                content_md=f"## 問題\n\n{question}\n\n## 分析\n\n{answer}",
                sources=[f"agent:{','.join(tools_used)}"],
                tags=tags,
            )
            await svc.rebuild_index()
            return True
        except (ImportError, AttributeError):
            return False
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                "WikiFacade.auto_ingest_synthesis failed: %s", e, exc_info=True,
                extra={"question_prefix": question[:60], "tools_count": len(tools_used)},
            )
            return False


__all__ = ["WikiFacade"]
