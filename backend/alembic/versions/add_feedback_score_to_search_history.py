"""新增 feedback_score 欄位到 ai_search_history 表

用於搜尋結果回饋學習機制，讓使用者對搜尋結果評分。

Revision ID: add_feedback_score
Revises: add_phase6a_performance_indexes
"""

from alembic import op
import sqlalchemy as sa

revision = 'add_feedback_score'
down_revision = ('phase6a_indexes', 'add_work_record_idx')
branch_labels = None
depends_on = None


def upgrade():
    """新增 feedback_score 欄位"""
    op.add_column(
        'ai_search_history',
        sa.Column(
            'feedback_score',
            sa.Integer(),
            nullable=True,
            comment='使用者回饋 (1=有用, -1=無用, NULL=未評)',
        ),
    )


def downgrade():
    """移除 feedback_score 欄位"""
    op.drop_column('ai_search_history', 'feedback_score')
