"""
Agent Trace — 結構化追蹤記錄

每次問答產生完整 Trace，用於：
- 效能分析（哪個工具最慢？）
- 規劃品質（規劃成功率、修正觸發率）
- 資源消耗（LLM 呼叫次數、token 用量估算）
- 異常偵測（超時率、錯誤率）

設計原則：
- 零侵入：Orchestrator 只呼叫 trace.record_*()
- 輕量：不額外呼叫 DB/Redis，僅 in-memory 收集
- 可擴展：未來可接 OpenTelemetry / Prometheus

Version: 1.0.0
Created: 2026-03-14
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TraceSpan:
    """單一操作追蹤"""
    name: str
    start_ms: float
    end_ms: float = 0.0
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "ok"  # ok | error | timeout | skipped

    def finish(self, status: str = "ok", **meta: Any) -> None:
        self.end_ms = time.time() * 1000
        self.duration_ms = self.end_ms - self.start_ms
        self.status = status
        self.metadata.update(meta)


@dataclass
class AgentTrace:
    """
    完整問答追蹤記錄。

    Usage:
        trace = AgentTrace(question="工務局的函")
        span = trace.start_span("planning")
        ...
        span.finish(tool_count=2)
        trace.finish()
        logger.info(trace.summary())
    """
    question: str
    context: Optional[str] = None
    query_id: str = ""
    role_identity: str = ""

    # 追蹤數據
    spans: List[TraceSpan] = field(default_factory=list)
    tools_called: List[str] = field(default_factory=list)
    tools_succeeded: List[str] = field(default_factory=list)
    tools_failed: List[str] = field(default_factory=list)

    # 決策追蹤
    chitchat_detected: bool = False
    correction_triggered: bool = False
    react_triggered: bool = False
    route_type: str = ""  # chitchat | pattern | llm
    multi_domain: bool = False  # Supervisor 多域協調
    iterations: int = 0
    total_results: int = 0

    # 品質指標
    synthesis_validated: bool = False
    citation_count: int = 0
    citation_verified: int = 0

    # 推理軌跡 (Reflexion trajectory)
    reasoning_trajectory: List[str] = field(default_factory=list)

    # 時間戳
    _start_time: float = field(default_factory=time.time)
    _end_time: float = 0.0
    total_ms: int = 0

    def start_span(self, name: str, **meta: Any) -> TraceSpan:
        """開始一個新的追蹤 span"""
        span = TraceSpan(
            name=name,
            start_ms=time.time() * 1000,
            metadata=meta,
        )
        self.spans.append(span)
        return span

    def record_tool_call(self, tool_name: str, success: bool, count: int = 0) -> None:
        """記錄工具呼叫結果"""
        self.tools_called.append(tool_name)
        if success:
            self.tools_succeeded.append(tool_name)
            self.total_results += count
        else:
            self.tools_failed.append(tool_name)

    def record_correction(self, correction_type: str) -> None:
        """記錄修正事件"""
        self.correction_triggered = True
        self.start_span("correction", type=correction_type).finish()

    def record_react(self, action: str, confidence: float) -> None:
        """記錄 ReAct 決策"""
        self.react_triggered = True
        self.start_span("react", action=action, confidence=confidence).finish()

    def record_synthesis_validation(
        self, citation_count: int, citation_verified: int,
    ) -> None:
        """記錄合成品質驗證結果"""
        self.synthesis_validated = True
        self.citation_count = citation_count
        self.citation_verified = citation_verified

    def finish(self) -> None:
        """完成追蹤"""
        self._end_time = time.time()
        self.total_ms = int((self._end_time - self._start_time) * 1000)

    @property
    def tool_success_rate(self) -> float:
        """工具成功率"""
        if not self.tools_called:
            return 1.0
        return len(self.tools_succeeded) / len(self.tools_called)

    @property
    def citation_accuracy(self) -> float:
        """引用準確率"""
        if self.citation_count == 0:
            return 1.0
        return self.citation_verified / self.citation_count

    def summary(self) -> Dict[str, Any]:
        """產生摘要 dict（供 logging / analytics）"""
        span_details = [
            {
                "name": s.name,
                "duration_ms": round(s.duration_ms, 1),
                "status": s.status,
                **{k: v for k, v in s.metadata.items()
                   if isinstance(v, (str, int, float, bool))},
            }
            for s in self.spans
        ]

        return {
            "query_id": self.query_id,
            "question": self.question[:100],
            "context": self.context,
            "role": self.role_identity,
            "total_ms": self.total_ms,
            "iterations": self.iterations,
            "tools_called": list(set(self.tools_called)),
            "tool_count": len(self.tools_called),
            "tool_success_rate": round(self.tool_success_rate, 2),
            "total_results": self.total_results,
            "chitchat": self.chitchat_detected,
            "route_type": self.route_type,
            "correction_triggered": self.correction_triggered,
            "react_triggered": self.react_triggered,
            "citation_accuracy": round(self.citation_accuracy, 2),
            "spans": span_details,
        }

    def log_summary(self) -> None:
        """輸出結構化日誌"""
        s = self.summary()
        logger.info(
            "AgentTrace: %dms | tools=%d (%.0f%% ok) | results=%d | "
            "corrections=%s | react=%s | citations=%d/%d | q=%s",
            s["total_ms"],
            s["tool_count"],
            s["tool_success_rate"] * 100,
            s["total_results"],
            s["correction_triggered"],
            s["react_triggered"],
            self.citation_verified,
            self.citation_count,
            s["question"][:60],
        )

    def to_db_dict(self) -> Dict[str, Any]:
        """
        轉換為 AgentTraceRepository.save_trace() 需要的 dict。

        包含主記錄欄位 + tool_calls 明細。
        """
        # 從 spans 中提取工具呼叫明細
        tool_calls = []
        for span in self.spans:
            if span.name.startswith("tool:"):
                tool_calls.append({
                    "tool_name": span.name[5:],
                    "params": {
                        k: v for k, v in span.metadata.items()
                        if k != "count" and isinstance(v, (str, int, float, bool, list, dict, type(None)))
                    } or None,
                    "success": span.status == "ok",
                    "result_count": span.metadata.get("count", 0),
                    "duration_ms": int(span.duration_ms),
                    "error_message": span.metadata.get("error") if span.status != "ok" else None,
                })

        return {
            "query_id": self.query_id,
            "question": self.question,
            "context": self.context,
            "route_type": self.route_type or "llm",
            "plan_tool_count": len(self.tools_called),
            "hint_count": 0,
            "iterations": self.iterations,
            "total_results": self.total_results,
            "correction_triggered": self.correction_triggered,
            "react_triggered": self.react_triggered,
            "citation_count": self.citation_count,
            "citation_verified": self.citation_verified,
            "answer_length": getattr(self, "_answer_length", 0),
            "total_ms": self.total_ms,
            "model_used": getattr(self, "_model_used", None),
            "answer_preview": getattr(self, "_answer_preview", None),
            "tools_used": list(set(self.tools_called)) if self.tools_called else None,
            "tool_calls": tool_calls,
            "reasoning_trajectory": self.reasoning_trajectory if self.reasoning_trajectory else None,
        }

    async def flush_to_db(self, db: Any) -> Optional[int]:
        """
        非阻塞持久化至 PostgreSQL。

        Args:
            db: AsyncSession 實例

        Returns:
            trace record id，失敗回傳 None
        """
        try:
            from app.repositories.agent_trace_repository import AgentTraceRepository
            repo = AgentTraceRepository(db)
            return await repo.save_trace(self.to_db_dict())
        except Exception as e:
            logger.warning("flush_to_db failed: %s", e)
            return None

    async def flush_to_monitor(self) -> None:
        """將工具呼叫資料推送至 ToolSuccessMonitor"""
        try:
            from app.services.ai.agent.agent_tool_monitor import get_tool_monitor

            monitor = get_tool_monitor()
            for span in self.spans:
                if span.name.startswith("tool:"):
                    tool_name = span.name[5:]
                    success = span.status == "ok"
                    count = span.metadata.get("count", 0)
                    await monitor.record(
                        tool_name, success, span.duration_ms, count,
                    )
        except Exception as e:
            logger.debug("flush_to_monitor failed: %s", e)
