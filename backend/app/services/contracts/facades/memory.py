# -*- coding: utf-8 -*-
"""MemoryFacade - Memory wiki context 對外唯一入口

v6.10 P1 Phase B (2026-05-18)

解 step 29 揭發：
  - memory <- N (12 imports total — ai/notification/integration 多處)
  - ai -> memory (5)
  - memory -> integration (7)

統一封 diary / pattern / proposal / crystal / soul 等坤哥意識體操作。
"""
from __future__ import annotations

from datetime import date
from typing import Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class MemoryFacade:
    """Memory wiki bounded context 對外唯一入口

    使用範例：
        facade = MemoryFacade(db)
        await facade.append_diary("今日事件描述")
        patterns = await facade.get_recent_patterns(days=7)
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        """db 可選 — 多數 facade method 委派至 module-level service (內含自己的 session)"""
        self._db = db

    # === Public API ===

    async def append_diary(
        self,
        content: str,
        *,
        category: str = "general",
        target_date: Optional[date] = None,
    ) -> bool:
        """append 內容到 diary

        取代 anti-pattern:
          from app.services.memory.diary_service import DiaryService
        """
        try:
            from app.services.memory.diary_service import append_diary_entry
            return await append_diary_entry(
                content=content, category=category, target_date=target_date,
            )
        except (ImportError, AttributeError):
            return False

    async def get_recent_patterns(
        self,
        days: int = 7,
    ) -> List[dict]:
        """取近 N 天 patterns（給 agent 學習用）"""
        try:
            from app.services.memory.pattern_extractor import get_recent_patterns
            return await get_recent_patterns(self._db, days=days)
        except (ImportError, AttributeError):
            return []

    async def get_active_crystals(self) -> List[dict]:
        """取目前已批准的 crystals (active 規則)"""
        try:
            from app.services.memory.crystal_applier import get_active_crystals
            return await get_active_crystals(self._db)
        except (ImportError, AttributeError):
            return []

    async def get_soul_definition(self) -> Optional[str]:
        """取 SOUL.md 當前內容（給 agent prompt 注入用）

        取代 ai/agent_roles.py 直 import soul_loader
        """
        try:
            from app.services.memory.soul_loader import SOUL_PATH
            if SOUL_PATH.exists():
                return SOUL_PATH.read_text(encoding="utf-8")
            return None
        except (ImportError, AttributeError):
            return None

    async def trigger_self_diagnosis(self) -> dict:
        """觸發 agent 自我診斷"""
        try:
            from app.services.memory.self_diagnosis import SelfDiagnosis
            diagnoser = SelfDiagnosis(self._db)
            return await diagnoser.run()
        except (ImportError, AttributeError):
            return {"status": "skipped", "reason": "SelfDiagnosis unavailable"}

    async def get_anti_echo_status(self) -> dict:
        """取得反迴聲偵測狀態（給 agent 用以避免重複輸出）"""
        try:
            from app.services.memory.anti_echo import get_recent_anti_echo_records
            records = await get_recent_anti_echo_records()
            return {"records": records, "count": len(records)}
        except (ImportError, AttributeError):
            return {"records": [], "count": 0}

    # === v6.10 P1 真採用擴展（ai/agent/* 11 處 migration 配套） ===

    async def summarize_yesterday_for_context(
        self,
        max_chars: int = 500,
    ) -> str:
        """取昨日 diary 摘要供 agent context 注入

        取代 ai/agent_orchestrator.py:227 直 import diary_service
        """
        try:
            from app.services.memory.diary_service import get_diary_service
            return await get_diary_service().summarize_yesterday_for_context(
                max_chars=max_chars,
            )
        except (ImportError, AttributeError):
            return ""
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                "MemoryFacade.summarize_yesterday_for_context failed: %s",
                e, exc_info=True,
            )
            return ""

    async def get_defensive_rules_block(
        self,
        max_items: int = 5,
    ) -> str:
        """取近期失敗教訓防禦規則 block（給 planner prompt 注入）

        取代 ai/agent_planner.py:224 直 import auto_defense
        """
        try:
            from app.services.memory.auto_defense import get_defensive_rules_block
            return await get_defensive_rules_block(max_items=max_items)
        except (ImportError, AttributeError):
            return ""
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                "MemoryFacade.get_defensive_rules_block failed: %s",
                e, exc_info=True,
            )
            return ""

    async def get_recent_reflections_block(
        self,
        days: int = 7,
        max_items: int = 3,
    ) -> str:
        """取近期反迴聲反思 block

        取代 ai/agent_planner.py:234 直 import anti_echo
        """
        try:
            from app.services.memory.anti_echo import get_recent_reflections_block
            return await get_recent_reflections_block(days=days, max_items=max_items)
        except (ImportError, AttributeError):
            return ""
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                "MemoryFacade.get_recent_reflections_block failed: %s",
                e, exc_info=True,
            )
            return ""

    async def append_diary_entry(
        self,
        *,
        question: str,
        answer: str,
        tools_used: List[str],
        success: bool,
        latency_ms: int,
        session_id: Optional[str] = None,
        channel: Optional[str] = None,
        route_type: str = "llm",
    ) -> bool:
        """append 完整 query trace 到 diary

        取代 ai/agent_post_processing.py:436 直 import diary_service
        """
        try:
            from app.services.memory.diary_service import get_diary_service
            await get_diary_service().append_entry(
                question=question,
                answer=answer,
                tools_used=tools_used,
                success=success,
                latency_ms=latency_ms,
                session_id=session_id,
                channel=channel,
                route_type=route_type,
            )
            return True
        except (ImportError, AttributeError) as e:
            import logging
            logging.getLogger(__name__).warning(
                "MemoryFacade.append_diary_entry: diary_service unavailable: %s", e,
            )
            return False
        except Exception as e:
            # L29 教訓 + ADR-0028 錯誤合約：不可 silent swallow
            import logging
            logging.getLogger(__name__).error(
                "MemoryFacade.append_diary_entry failed: %s",
                e, exc_info=True,
                extra={"session_id": session_id, "channel": channel, "success": success},
            )
            try:
                from app.core.memory_wiki_metrics import get_memory_wiki_metrics
                get_memory_wiki_metrics().diary_append_failures.labels(
                    error_type="facade_unknown",
                ).inc()
            except Exception:
                pass
            return False

    async def build_role_system_prompt(
        self,
        *,
        role_context: str,
        role_specific_block: str,
    ) -> Optional[str]:
        """組 SOUL.md + role-specific 段 → 完整 system prompt

        取代 ai/agent_roles.py:338 直 import soul_loader
        """
        try:
            from app.services.memory.soul_loader import get_soul_loader
            soul = await get_soul_loader().load_soul()
            return soul.build_system_prompt(
                role_context=role_context,
                role_specific_block=role_specific_block,
            )
        except (ImportError, AttributeError):
            return None
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                "MemoryFacade.build_role_system_prompt failed: %s",
                e, exc_info=True,
            )
            return None


__all__ = ["MemoryFacade"]
