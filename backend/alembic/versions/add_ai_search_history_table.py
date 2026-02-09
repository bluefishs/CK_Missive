"""新增 AI 搜尋歷史記錄表

記錄所有 AI 自然語言搜尋的歷史，供統計分析與查詢優化使用。

Revision ID: add_ai_search_history
Revises: add_email_verification
Create Date: 2026-02-09
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'add_ai_search_history'
down_revision = 'add_email_verification'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ai_search_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True, comment='使用者 ID'),
        sa.Column('query', sa.Text(), nullable=False, comment='原始查詢文字'),
        sa.Column('parsed_intent', sa.JSON(), nullable=True, comment='解析後的意圖 JSON'),
        sa.Column('results_count', sa.Integer(), server_default='0', comment='搜尋結果數量'),
        sa.Column('search_strategy', sa.String(50), nullable=True, comment='搜尋策略 (keyword/similarity/hybrid)'),
        sa.Column('source', sa.String(50), nullable=True, comment='來源 (ai/rule_engine/fallback/merged)'),
        sa.Column('synonym_expanded', sa.Boolean(), server_default='false', comment='是否同義詞擴展'),
        sa.Column('related_entity', sa.String(50), nullable=True, comment='關聯實體 (dispatch_order/project)'),
        sa.Column('latency_ms', sa.Integer(), nullable=True, comment='回應時間 ms'),
        sa.Column('confidence', sa.Float(), nullable=True, comment='意圖信心度'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='建立時間'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_search_history_user_date', 'ai_search_history', ['user_id', 'created_at'])
    op.create_index('ix_search_history_created', 'ai_search_history', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_search_history_created', table_name='ai_search_history')
    op.drop_index('ix_search_history_user_date', table_name='ai_search_history')
    op.drop_table('ai_search_history')
