"""add graduation fields to agent_learnings and improvement_hint to traces

Graduation system: track consecutive success/failure to graduate or flag
chronic learnings. After-action improvement hints on query traces.

Revision ID: 20260405a007
Revises: 20260405a006
Create Date: 2026-04-05
"""
from alembic import op
import sqlalchemy as sa

revision = '20260405a007'
down_revision = '20260405a006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- agent_learnings: graduation system columns ---
    op.add_column(
        'agent_learnings',
        sa.Column(
            'graduation_status', sa.String(20),
            nullable=False, server_default='active',
            comment='active=in use, graduated=internalized(7+ success), chronic=needs structural fix',
        ),
    )
    op.add_column(
        'agent_learnings',
        sa.Column(
            'consecutive_success_count', sa.Integer(),
            nullable=False, server_default='0',
            comment='Consecutive successful applications; reset to 0 on failure',
        ),
    )
    op.add_column(
        'agent_learnings',
        sa.Column(
            'failure_count', sa.Integer(),
            nullable=False, server_default='0',
            comment='Total times this learning failed to help',
        ),
    )
    op.add_column(
        'agent_learnings',
        sa.Column(
            'last_applied_at', sa.DateTime(), nullable=True,
            comment='Last time this learning was applied',
        ),
    )
    op.create_index(
        'ix_learning_graduation_status',
        'agent_learnings',
        ['graduation_status'],
    )

    # --- agent_query_traces: after-action improvement hint ---
    op.add_column(
        'agent_query_traces',
        sa.Column(
            'improvement_hint', sa.Text(), nullable=True,
            comment='After-action: what to improve next time',
        ),
    )

    # --- agent_evolution_history: graduation counters ---
    op.add_column(
        'agent_evolution_history',
        sa.Column(
            'patterns_graduated', sa.Integer(),
            nullable=False, server_default='0',
            comment='Learnings graduated (internalized)',
        ),
    )
    op.add_column(
        'agent_evolution_history',
        sa.Column(
            'patterns_chronic', sa.Integer(),
            nullable=False, server_default='0',
            comment='Learnings flagged as chronic',
        ),
    )


def downgrade() -> None:
    op.drop_column('agent_evolution_history', 'patterns_chronic')
    op.drop_column('agent_evolution_history', 'patterns_graduated')
    op.drop_column('agent_query_traces', 'improvement_hint')
    op.drop_index('ix_learning_graduation_status', table_name='agent_learnings')
    op.drop_column('agent_learnings', 'last_applied_at')
    op.drop_column('agent_learnings', 'failure_count')
    op.drop_column('agent_learnings', 'consecutive_success_count')
    op.drop_column('agent_learnings', 'graduation_status')
