"""create agent_learnings table

Revision ID: 20260316a001
Revises: 20260315a001
Create Date: 2026-03-16
"""
from alembic import op
import sqlalchemy as sa

revision = "20260316a001"
down_revision = "20260315a001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agent_learnings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("learning_type", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(32), nullable=False),
        sa.Column("source_question", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), server_default="1.0"),
        sa.Column("hit_count", sa.Integer(), server_default="1"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_learning_type", "agent_learnings", ["learning_type"])
    op.create_index("ix_learning_session", "agent_learnings", ["session_id"])
    op.create_index("ix_learning_active_type", "agent_learnings", ["is_active", "learning_type"])
    op.create_index(
        "ix_learning_content_hash", "agent_learnings", ["content_hash"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade():
    op.drop_table("agent_learnings")
