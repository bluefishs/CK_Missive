"""
Agent Trace Repository — 追蹤記錄持久化

Phase 1 of 乾坤智能體自動學習架構。
將 in-memory AgentTrace 持久化到 PostgreSQL。

Version: 1.0.0
Created: 2026-03-14
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Integer, select, update, func, and_, or_, cast
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.agent_trace import AgentQueryTrace, AgentToolCallLog

logger = logging.getLogger(__name__)


class AgentTraceRepository:
    """Agent 追蹤記錄 Repository"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_trace(self, trace_data: Dict[str, Any]) -> Optional[int]:
        """
        持久化一筆 AgentTrace 記錄（含工具呼叫明細）。

        Args:
            trace_data: AgentTrace.to_db_dict() 的輸出

        Returns:
            trace id，失敗回傳 None
        """
        try:
            query_id = trace_data.get("query_id", "")
            if not query_id:
                return None

            trace_record = AgentQueryTrace(
                query_id=query_id,
                question=trace_data.get("question", "")[:2000],
                context=trace_data.get("context"),
                route_type=trace_data.get("route_type", "llm"),
                plan_tool_count=trace_data.get("plan_tool_count", 0),
                hint_count=trace_data.get("hint_count", 0),
                iterations=trace_data.get("iterations", 0),
                total_results=trace_data.get("total_results", 0),
                correction_triggered=trace_data.get("correction_triggered", False),
                react_triggered=trace_data.get("react_triggered", False),
                citation_count=trace_data.get("citation_count", 0),
                citation_verified=trace_data.get("citation_verified", 0),
                answer_length=trace_data.get("answer_length", 0),
                total_ms=trace_data.get("total_ms", 0),
                model_used=trace_data.get("model_used"),
                answer_preview=trace_data.get("answer_preview", "")[:500] if trace_data.get("answer_preview") else None,
                tools_used=trace_data.get("tools_used"),
            )

            self.db.add(trace_record)
            await self.db.flush()

            # 寫入工具呼叫明細
            tool_calls = trace_data.get("tool_calls", [])
            for i, tc in enumerate(tool_calls):
                log = AgentToolCallLog(
                    trace_id=trace_record.id,
                    tool_name=tc.get("tool_name", ""),
                    params=tc.get("params"),
                    success=tc.get("success", True),
                    result_count=tc.get("result_count", 0),
                    duration_ms=tc.get("duration_ms", 0),
                    error_message=tc.get("error_message"),
                    call_order=i,
                )
                self.db.add(log)

            await self.db.commit()
            return trace_record.id

        except Exception as e:
            logger.warning("save_trace failed: %s", e)
            await self.db.rollback()
            return None

    async def link_feedback(
        self,
        conversation_id: str,
        score: int,
        feedback_text: Optional[str] = None,
    ) -> bool:
        """
        將使用者回饋關聯到最近的 trace 記錄。

        Args:
            conversation_id: 對話 ID（= trace.query_id）
            score: 1=good, -1=bad
            feedback_text: 文字回饋

        Returns:
            是否成功關聯
        """
        try:
            stmt = (
                update(AgentQueryTrace)
                .where(AgentQueryTrace.query_id == conversation_id)
                .values(
                    feedback_score=score,
                    feedback_text=feedback_text[:500] if feedback_text else None,
                    feedback_at=datetime.now(timezone.utc),
                )
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.rowcount > 0
        except Exception as e:
            logger.warning("link_feedback failed: %s", e)
            await self.db.rollback()
            return False

    async def get_trace_detail(self, trace_id: int) -> Optional[Dict[str, Any]]:
        """取得單筆 trace 詳情含 tool_calls（V-1.2 Timeline 用）"""
        try:
            stmt = select(AgentQueryTrace).where(AgentQueryTrace.id == trace_id)
            result = await self.db.execute(stmt)
            trace = result.scalar_one_or_none()
            if not trace:
                return None

            # 取得 tool call logs
            tc_stmt = (
                select(AgentToolCallLog)
                .where(AgentToolCallLog.trace_id == trace_id)
                .order_by(AgentToolCallLog.call_order)
            )
            tc_result = await self.db.execute(tc_stmt)
            tool_calls = [
                {
                    "tool_name": tc.tool_name,
                    "call_order": tc.call_order,
                    "duration_ms": tc.duration_ms,
                    "success": tc.success,
                    "result_count": tc.result_count,
                    "error_message": tc.error_message,
                    "created_at": tc.created_at.isoformat() if tc.created_at else None,
                }
                for tc in tc_result.scalars().all()
            ]

            return {
                "id": trace.id,
                "query_id": trace.query_id,
                "question": trace.question,
                "context": trace.context,
                "route_type": trace.route_type,
                "total_ms": trace.total_ms,
                "iterations": trace.iterations,
                "total_results": trace.total_results,
                "correction_triggered": trace.correction_triggered,
                "react_triggered": trace.react_triggered,
                "plan_tool_count": trace.plan_tool_count,
                "model_used": trace.model_used,
                "tools_used": trace.tools_used,
                "answer_preview": trace.answer_preview,
                "feedback_score": trace.feedback_score,
                "created_at": trace.created_at.isoformat() if trace.created_at else None,
                "tool_calls": tool_calls,
            }
        except Exception as e:
            logger.warning("get_trace_detail failed: %s", e)
            return None

    async def get_recent_traces(
        self,
        context: Optional[str] = None,
        limit: int = 50,
        feedback_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """查詢近期 trace 記錄（供分析/統計用）"""
        conditions = []
        if context:
            conditions.append(AgentQueryTrace.context == context)
        if feedback_only:
            conditions.append(AgentQueryTrace.feedback_score.isnot(None))

        stmt = (
            select(AgentQueryTrace)
            .where(and_(*conditions) if conditions else True)
            .order_by(AgentQueryTrace.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        traces = result.scalars().all()

        return [
            {
                "id": t.id,
                "query_id": t.query_id,
                "question": t.question[:100],
                "context": t.context,
                "route_type": t.route_type,
                "total_ms": t.total_ms,
                "total_results": t.total_results,
                "iterations": t.iterations,
                "feedback_score": t.feedback_score,
                "tools_used": t.tools_used,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in traces
        ]

    async def find_similar_successful_traces(
        self,
        question: str,
        context: Optional[str] = None,
        limit: int = 3,
        min_results: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        查詢與當前問題相似的歷史成功 trace，供 Adaptive Few-shot 使用。

        使用 ILIKE 關鍵字匹配（CJK 相容，不依賴 zhparser 擴展）。
        過濾條件：有結果 + 無負面回饋 + 有使用工具。
        """
        try:
            # 提取 2-4 字關鍵詞（簡易中文分詞）
            import re
            keywords = re.findall(r'[\u4e00-\u9fff]{2,4}', question)
            if not keywords:
                # 無中文關鍵字，嘗試英文
                keywords = re.findall(r'[a-zA-Z]{3,}', question)
            if not keywords:
                return []

            conditions = [
                AgentQueryTrace.total_results >= min_results,
                AgentQueryTrace.tools_used.isnot(None),
                # 排除負面回饋
                (AgentQueryTrace.feedback_score.is_(None)) | (AgentQueryTrace.feedback_score >= 0),
            ]
            if context:
                conditions.append(AgentQueryTrace.context == context)

            # ILIKE 關鍵字匹配（取前 3 個關鍵字 OR 匹配）
            keyword_filters = [
                AgentQueryTrace.question.ilike(f"%{kw}%")
                for kw in keywords[:3]
            ]
            conditions.append(or_(*keyword_filters))

            stmt = (
                select(AgentQueryTrace)
                .where(and_(*conditions))
                .order_by(AgentQueryTrace.total_results.desc())
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            traces = result.scalars().all()

            return [
                {
                    "question": t.question[:100],
                    "tools_used": t.tools_used,
                    "total_results": t.total_results,
                    "answer_preview": t.answer_preview[:200] if t.answer_preview else None,
                }
                for t in traces
            ]
        except Exception as e:
            logger.warning("find_similar_successful_traces failed: %s", e)
            return []

    async def get_daily_trend(
        self, days: int = 14
    ) -> List[Dict[str, Any]]:
        """取得每日 Agent 查詢趨勢（查詢量/平均延遲/平均結果數）"""
        try:
            cutoff = func.now() - func.cast(
                f"{days} days", func.literal_column("INTERVAL")
            )
            date_col = func.date(AgentQueryTrace.created_at).label("date")
            stmt = (
                select(
                    date_col,
                    func.count().label("query_count"),
                    func.avg(AgentQueryTrace.total_ms).label("avg_latency_ms"),
                    func.avg(AgentQueryTrace.total_results).label("avg_results"),
                    func.avg(
                        func.cast(AgentQueryTrace.feedback_score, Integer)
                    ).label("avg_feedback"),
                )
                .where(AgentQueryTrace.created_at >= cutoff)
                .group_by(date_col)
                .order_by(date_col)
            )
            result = await self.db.execute(stmt)
            rows = result.all()
            return [
                {
                    "date": str(r.date),
                    "query_count": r.query_count,
                    "avg_latency_ms": round(r.avg_latency_ms or 0, 0),
                    "avg_results": round(r.avg_results or 0, 1),
                    "avg_feedback": round(r.avg_feedback or 0, 2) if r.avg_feedback else None,
                }
                for r in rows
            ]
        except Exception as e:
            logger.warning("get_daily_trend failed: %s", e)
            return []

    async def get_tool_success_stats(
        self, days: int = 7
    ) -> List[Dict[str, Any]]:
        """取得近 N 天的工具成功率統計"""
        cutoff = func.now() - func.cast(f"{days} days", func.literal_column("INTERVAL"))
        stmt = (
            select(
                AgentToolCallLog.tool_name,
                func.count().label("total_calls"),
                func.sum(func.cast(AgentToolCallLog.success, Integer)).label("success_count"),
                func.avg(AgentToolCallLog.duration_ms).label("avg_latency_ms"),
                func.avg(AgentToolCallLog.result_count).label("avg_result_count"),
            )
            .where(AgentToolCallLog.created_at >= cutoff)
            .group_by(AgentToolCallLog.tool_name)
            .order_by(func.count().desc())
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            {
                "tool_name": r.tool_name,
                "total_calls": r.total_calls,
                "success_count": r.success_count or 0,
                "success_rate": round((r.success_count or 0) / r.total_calls, 3) if r.total_calls else 0,
                "avg_latency_ms": round(r.avg_latency_ms or 0, 1),
                "avg_result_count": round(r.avg_result_count or 0, 1),
            }
            for r in rows
        ]
