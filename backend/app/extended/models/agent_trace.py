"""
11. Agent 追蹤持久化模組 (Agent Trace Persistence)

Phase 1 of 乾坤智能體自動學習架構：
- AgentQueryTrace: 每次問答完整軌跡
- AgentToolCallLog: 工具呼叫明細（trace 子表）

對標 OpenClaw 的 Tool Success Logging + Feedback Loop，
將 Redis-only 的 in-memory trace 持久化到 PostgreSQL，
為後續 Reflection Loop / Adaptive Few-shot / Memory Consolidation 提供資料基礎。

Version: 1.0.0
Created: 2026-03-14
"""
from ._base import *
from sqlalchemy import SmallInteger, text


class AgentQueryTrace(Base):
    """Agent 問答追蹤記錄（每次問答一筆）"""
    __tablename__ = "agent_query_traces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(
        String(64), nullable=False, unique=True, index=True,
        comment="會話 ID 或 UUID",
    )
    question = Column(Text, nullable=False, comment="原始問題")
    context = Column(String(20), nullable=True, comment="角色上下文 (doc/agent/dev/dispatch)")

    # === 路由決策 ===
    route_type = Column(String(20), nullable=False, default="llm", comment="路由類型 (chitchat/pattern/llm)")

    # === 規劃結果 ===
    plan_tool_count = Column(Integer, default=0, comment="規劃的工具數量")
    hint_count = Column(Integer, default=0, comment="意圖提取 hints 數量")

    # === 執行結果 ===
    iterations = Column(Integer, default=0, comment="工具迴圈輪次")
    total_results = Column(Integer, default=0, comment="累計結果數")
    correction_triggered = Column(Boolean, default=False, comment="是否觸發自動修正")
    react_triggered = Column(Boolean, default=False, comment="是否觸發 ReAct")

    # === 品質指標 ===
    citation_count = Column(Integer, default=0, comment="引用數量")
    citation_verified = Column(Integer, default=0, comment="驗證通過引用數")
    answer_length = Column(Integer, default=0, comment="答案字數")

    # === 效能 ===
    total_ms = Column(Integer, default=0, comment="總延遲 ms")
    model_used = Column(String(50), nullable=True, comment="使用的模型 (ollama/fallback/error)")

    # === 回饋（Phase 1 關聯） ===
    feedback_score = Column(SmallInteger, nullable=True, comment="1=good, -1=bad, NULL=未評")
    feedback_text = Column(String(500), nullable=True, comment="文字回饋")
    feedback_at = Column(DateTime(timezone=True), nullable=True, comment="回饋時間")

    # === 合成結果 ===
    answer_preview = Column(String(500), nullable=True, comment="答案前 500 字")
    tools_used = Column(JSONB, nullable=True, comment="使用的工具名稱列表")

    # === After-action improvement ===
    improvement_hint = Column(Text, nullable=True, comment="After-action: what to improve next time")

    # === 時間戳 ===
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # === 關聯 ===
    tool_calls = relationship(
        "AgentToolCallLog",
        back_populates="trace",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        Index("ix_trace_created", "created_at"),
        Index("ix_trace_context", "context", "created_at"),
        Index("ix_trace_route", "route_type", "created_at"),
        Index("ix_trace_feedback", "feedback_score", postgresql_where=text("feedback_score IS NOT NULL")),
    )


class AgentToolCallLog(Base):
    """工具呼叫明細（每次工具呼叫一筆，多對一 trace）"""
    __tablename__ = "agent_tool_call_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trace_id = Column(
        Integer,
        ForeignKey("agent_query_traces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_name = Column(String(50), nullable=False, comment="工具名稱")
    params = Column(JSONB, nullable=True, comment="工具參數")
    success = Column(Boolean, nullable=False, default=True, comment="是否成功")
    result_count = Column(Integer, default=0, comment="結果數量")
    duration_ms = Column(Integer, default=0, comment="執行耗時 ms")
    error_message = Column(String(500), nullable=True, comment="錯誤訊息")
    call_order = Column(SmallInteger, default=0, comment="呼叫順序")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # === 關聯 ===
    trace = relationship("AgentQueryTrace", back_populates="tool_calls")

    __table_args__ = (
        Index("ix_tool_log_name", "tool_name", "created_at"),
        Index("ix_tool_log_success", "tool_name", "success"),
    )
