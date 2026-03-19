"""
NemoClaw 代理人 — 自覺型 Agent

與傳統智能體的差異:
- 傳統: 問→查→答 (被動工具)
- NemoClaw: 感知自己→理解上下文→問自己→答→反思→記住 (主動代理人)

每次回答的流程:
1. 載入自我檔案 (我擅長什麼/不擅長什麼)
2. 載入用戶歷史 (上次聊什麼/偏好)
3. 檢查主動提醒 (有沒有該告訴用戶的事)
4. 規劃+執行 (走原有 Agent pipeline)
5. 人格化回覆 (口語+記住上下文)
6. 自省+記錄教訓

Version: 1.0.0
"""

import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_connector import get_ai_connector
from app.services.ai.agent_orchestrator import AgentOrchestrator
from app.services.ai.agent_utils import sse

logger = logging.getLogger(__name__)


class NemoClawAgent:
    """
    NemoClaw 代理人 — 包裝 AgentOrchestrator，加入自覺層

    SSE 事件新增:
      data: {"type":"self_awareness","profile":{...},"alerts":[...]}
      data: {"type":"user_context","history_summary":"...","preferences":{...}}
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.orchestrator = AgentOrchestrator(db)

    async def stream_query(
        self,
        question: str,
        history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None,
        context: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        NemoClaw 代理人串流問答

        在 AgentOrchestrator 的基礎上，加入:
        1. 自我覺察 (self-awareness)
        2. 用戶上下文 (user context)
        3. 主動提醒 (proactive alerts)
        """
        t0 = time.time()

        # ── Step 0: 自我覺察 (非阻塞並行) ──
        self_profile = {}
        proactive_alerts = []
        user_prefs = {}

        try:
            from app.services.ai.agent_self_profile import get_self_profile
            from app.services.ai.agent_proactive_scanner import scan_agent_alerts

            profile_task = asyncio.create_task(get_self_profile(self.db))
            alerts_task = asyncio.create_task(scan_agent_alerts(self.db))

            # 載入用戶偏好
            if session_id:
                try:
                    from app.services.ai.user_preference_extractor import load_preferences
                    user_prefs = await load_preferences(session_id)
                except Exception:
                    pass

            self_profile = await profile_task
            proactive_alerts = (await alerts_task).get("alerts", [])
        except Exception as e:
            logger.debug("NemoClaw self-awareness failed: %s", e)

        # 發送自我覺察事件
        yield sse(
            type="self_awareness",
            identity=self_profile.get("identity", "乾坤"),
            total_queries=self_profile.get("total_queries", 0),
            personality=self_profile.get("personality_hint", ""),
            strengths=self_profile.get("top_domains", []),
            alert_count=len(proactive_alerts),
        )

        # ── Step 0.5: 主動提醒 (如果有緊急事項) ──
        urgent_alerts = [a for a in proactive_alerts if a.get("severity") == "high"]
        if urgent_alerts and not self._is_alert_related(question):
            alert_text = "；".join(a.get("message", "")[:50] for a in urgent_alerts[:3])
            yield sse(
                type="proactive_alert",
                message=f"提醒：{alert_text}",
                count=len(urgent_alerts),
            )

        # ── Step 1-5: 委派給 AgentOrchestrator ──
        # 注入自我覺察到 context
        enhanced_context = self._build_enhanced_context(
            context, self_profile, user_prefs,
        )

        async for event in self.orchestrator.stream_agent_query(
            question=question,
            history=history,
            session_id=session_id,
            context=enhanced_context,
        ):
            yield event

    def _build_enhanced_context(
        self,
        original_context: Optional[str],
        profile: dict,
        user_prefs: dict,
    ) -> str:
        """將自我覺察注入到 context 中，影響角色選擇和規劃"""
        parts = []

        if original_context:
            parts.append(original_context)

        # 注入能力自覺
        personality = profile.get("personality_hint", "")
        if personality:
            parts.append(f"[自我覺察] {personality}")

        # 注入用戶偏好
        if user_prefs:
            pref_text = user_prefs.get("summary", "")
            if pref_text:
                parts.append(f"[用戶偏好] {pref_text}")

        return " | ".join(parts) if parts else "agent"

    @staticmethod
    def _is_alert_related(question: str) -> bool:
        """判斷問題是否已經和提醒相關（避免重複提醒）"""
        alert_keywords = {"截止", "到期", "逾期", "提醒", "通知", "警報", "健康", "異常"}
        return any(kw in question for kw in alert_keywords)
