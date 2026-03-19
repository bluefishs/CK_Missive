"""
12. Agent 學習持久化模組 (Agent Learning Persistence)

Phase 3A of 乾坤智能體自動學習架構：
- AgentLearning: 持久化學習記錄（對標 OpenClaw agent-reflect 永久編碼）

將 Redis TTL 學習升級為 DB 持久化，
學習記錄存活無期限，支援去重、強化、注入 planner prompt。

Version: 1.0.0
Created: 2026-03-15
"""
from ._base import *
from sqlalchemy import text


class AgentLearning(Base):
    """Agent 學習記錄（每條學習一筆，跨 session 累積）"""
    __tablename__ = "agent_learnings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, comment="來源 session ID")
    learning_type = Column(
        String(20), nullable=False,
        comment="學習類型: preference|entity|tool_combo|correction",
    )
    content = Column(Text, nullable=False, comment="學習內容")
    content_hash = Column(
        String(32), nullable=False,
        comment="內容 MD5 hash（去重用）",
    )
    source_question = Column(Text, nullable=True, comment="觸發學習的原始問題")
    confidence = Column(Float, default=1.0, comment="信心度")
    hit_count = Column(Integer, default=1, comment="被強化次數")
    is_active = Column(Boolean, default=True, comment="是否啟用")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )

    __table_args__ = (
        Index("ix_learning_type", "learning_type"),
        Index("ix_learning_session", "session_id"),
        Index("ix_learning_active_type", "is_active", "learning_type"),
        Index(
            "ix_learning_content_hash", "content_hash",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )
