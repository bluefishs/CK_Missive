"""add agent_evolution_history table

Revision ID: 20260405a005
Revises: 20260405a004
Create Date: 2026-04-05
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260405a005"
down_revision = "20260405a004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_evolution_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "evolution_id", sa.String(36), nullable=False,
            comment="UUID for this evolution event",
        ),
        sa.Column(
            "trigger_reason", sa.String(50), nullable=False,
            comment="query_count | daily_cycle | manual",
        ),
        sa.Column(
            "trigger_value", sa.Integer(), nullable=True,
            comment="e.g., query count that triggered evolution",
        ),
        # Signal batch
        sa.Column("signals_evaluated", sa.Integer(), server_default="0"),
        sa.Column("signals_critical", sa.Integer(), server_default="0"),
        sa.Column("signals_high", sa.Integer(), server_default="0"),
        sa.Column("signals_medium", sa.Integer(), server_default="0"),
        sa.Column("signals_low", sa.Integer(), server_default="0"),
        # Actions taken
        sa.Column("patterns_promoted", sa.Integer(), server_default="0"),
        sa.Column("patterns_demoted", sa.Integer(), server_default="0"),
        sa.Column("patterns_expired", sa.Integer(), server_default="0"),
        sa.Column(
            "thresholds_adjusted", sa.JSON(), nullable=True,
            comment="{'key': 'old->new'} changes",
        ),
        # State snapshot
        sa.Column("total_patterns_before", sa.Integer(), server_default="0"),
        sa.Column("total_patterns_after", sa.Integer(), server_default="0"),
        sa.Column("avg_score_before", sa.Float(), nullable=True),
        sa.Column("avg_score_after", sa.Float(), nullable=True),
        # Effectiveness
        sa.Column(
            "effectiveness_score", sa.Float(), nullable=True,
            comment="Computed post-hoc",
        ),
        sa.Column("effectiveness_computed_at", sa.DateTime(), nullable=True),
        # Meta
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_evolution_id", "agent_evolution_history", ["evolution_id"], unique=True,
    )
    op.create_index(
        "ix_evolution_trigger", "agent_evolution_history", ["trigger_reason"],
    )
    op.create_index(
        "ix_evolution_created", "agent_evolution_history", ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_evolution_created", table_name="agent_evolution_history")
    op.drop_index("ix_evolution_trigger", table_name="agent_evolution_history")
    op.drop_index("ix_evolution_id", table_name="agent_evolution_history")
    op.drop_table("agent_evolution_history")
