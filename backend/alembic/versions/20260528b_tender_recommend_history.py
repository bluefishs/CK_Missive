"""tender_recommendation_history table (L51 / ADR-0046 Phase 4 觀測閉環)

修補 business_recommendation.py 缺口：
- Redis 25h 去重 key 一過期就消失 → 沒長期歷史
- Prometheus counter 借用 subscription_check（不精準）
- 沒轉換率追蹤（admin 收到後是否變 bookmark）

Schema:
- 1:1 對應 push 事件
- status: pushed / skipped_duplicate / error
- bookmarked_at: 後續轉換率追蹤回填

Revision ID: 20260528b001
Revises: 20260528_tender_pcc_match
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa


revision = '20260528b001'
down_revision = '20260528_tender_pcc_match'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'tender_recommendation_history',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tender_record_id', sa.Integer,
                  sa.ForeignKey('tender_records.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('unit_id', sa.String(50), nullable=False),
        sa.Column('job_number', sa.String(100), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('unit_name', sa.String(200), nullable=True),
        sa.Column('budget', sa.Numeric(15, 2), nullable=True),
        sa.Column('agency_match_count', sa.Integer, server_default='0'),
        sa.Column('pushed_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('error_msg', sa.Text, nullable=True),
        sa.Column('channel', sa.String(20), server_default='line'),
        sa.Column('bookmarked_at', sa.DateTime, nullable=True),
    )
    op.create_index(
        'ix_tender_recommend_tender_id', 'tender_recommendation_history', ['tender_record_id']
    )
    op.create_index(
        'ix_tender_recommend_pushed_at', 'tender_recommendation_history', ['pushed_at']
    )
    op.create_index(
        'ix_tender_recommend_unit_jn', 'tender_recommendation_history', ['unit_id', 'job_number']
    )
    op.create_index(
        'ix_tender_recommend_status_pushed', 'tender_recommendation_history',
        ['status', 'pushed_at']
    )


def downgrade():
    op.drop_index('ix_tender_recommend_status_pushed', table_name='tender_recommendation_history')
    op.drop_index('ix_tender_recommend_unit_jn', table_name='tender_recommendation_history')
    op.drop_index('ix_tender_recommend_pushed_at', table_name='tender_recommendation_history')
    op.drop_index('ix_tender_recommend_tender_id', table_name='tender_recommendation_history')
    op.drop_table('tender_recommendation_history')
