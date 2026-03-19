"""create agent_query_traces and agent_tool_call_logs tables

Phase 1 of 乾坤智能體自動學習架構：
- agent_query_traces: 每次問答完整追蹤記錄
- agent_tool_call_logs: 工具呼叫明細（trace 子表）

Revision ID: 20260315a001
Revises: 20260313a003
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260315a001"
down_revision = "20260313a003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === agent_query_traces ===
    op.create_table(
        "agent_query_traces",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("query_id", sa.String(64), nullable=False, comment="會話 ID 或 UUID"),
        sa.Column("question", sa.Text(), nullable=False, comment="原始問題"),
        sa.Column("context", sa.String(20), nullable=True, comment="角色上下文"),
        sa.Column("route_type", sa.String(20), nullable=False, server_default="llm", comment="路由類型"),
        sa.Column("plan_tool_count", sa.Integer(), server_default="0", comment="規劃的工具數量"),
        sa.Column("hint_count", sa.Integer(), server_default="0", comment="意圖提取 hints 數量"),
        sa.Column("iterations", sa.Integer(), server_default="0", comment="工具迴圈輪次"),
        sa.Column("total_results", sa.Integer(), server_default="0", comment="累計結果數"),
        sa.Column("correction_triggered", sa.Boolean(), server_default="false", comment="是否觸發自動修正"),
        sa.Column("react_triggered", sa.Boolean(), server_default="false", comment="是否觸發 ReAct"),
        sa.Column("citation_count", sa.Integer(), server_default="0", comment="引用數量"),
        sa.Column("citation_verified", sa.Integer(), server_default="0", comment="驗證通過引用數"),
        sa.Column("answer_length", sa.Integer(), server_default="0", comment="答案字數"),
        sa.Column("total_ms", sa.Integer(), server_default="0", comment="總延遲 ms"),
        sa.Column("model_used", sa.String(50), nullable=True, comment="使用的模型"),
        sa.Column("feedback_score", sa.SmallInteger(), nullable=True, comment="1=good, -1=bad"),
        sa.Column("feedback_text", sa.String(500), nullable=True, comment="文字回饋"),
        sa.Column("feedback_at", sa.DateTime(timezone=True), nullable=True, comment="回饋時間"),
        sa.Column("answer_preview", sa.String(500), nullable=True, comment="答案前 500 字"),
        sa.Column("tools_used", postgresql.JSONB(), nullable=True, comment="使用的工具名稱列表"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("query_id"),
    )
    op.create_index("ix_agent_query_traces_query_id", "agent_query_traces", ["query_id"])
    op.create_index("ix_trace_created", "agent_query_traces", ["created_at"])
    op.create_index("ix_trace_context", "agent_query_traces", ["context", "created_at"])
    op.create_index("ix_trace_route", "agent_query_traces", ["route_type", "created_at"])
    op.create_index(
        "ix_trace_feedback", "agent_query_traces", ["feedback_score"],
        postgresql_where=sa.text("feedback_score IS NOT NULL"),
    )

    # === agent_tool_call_logs ===
    op.create_table(
        "agent_tool_call_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("trace_id", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(50), nullable=False, comment="工具名稱"),
        sa.Column("params", postgresql.JSONB(), nullable=True, comment="工具參數"),
        sa.Column("success", sa.Boolean(), nullable=False, server_default="true", comment="是否成功"),
        sa.Column("result_count", sa.Integer(), server_default="0", comment="結果數量"),
        sa.Column("duration_ms", sa.Integer(), server_default="0", comment="執行耗時 ms"),
        sa.Column("error_message", sa.String(500), nullable=True, comment="錯誤訊息"),
        sa.Column("call_order", sa.SmallInteger(), server_default="0", comment="呼叫順序"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["trace_id"], ["agent_query_traces.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_agent_tool_call_logs_trace_id", "agent_tool_call_logs", ["trace_id"])
    op.create_index("ix_tool_log_name", "agent_tool_call_logs", ["tool_name", "created_at"])
    op.create_index("ix_tool_log_success", "agent_tool_call_logs", ["tool_name", "success"])


def downgrade() -> None:
    op.drop_table("agent_tool_call_logs")
    op.drop_table("agent_query_traces")
