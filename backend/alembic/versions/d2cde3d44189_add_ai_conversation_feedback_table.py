"""add_ai_conversation_feedback_table

Revision ID: d2cde3d44189
Revises: fix_vector_dims_hnsw
Create Date: 2026-02-27 21:34:41.831946

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd2cde3d44189'
down_revision: Union[str, Sequence[str], None] = 'fix_vector_dims_hnsw'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """新增 AI 對話回饋表"""
    op.create_table(
        'ai_conversation_feedback',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True, comment='使用者 ID'),
        sa.Column('conversation_id', sa.String(length=64), nullable=False, comment='對話 ID (前端生成)'),
        sa.Column('message_index', sa.Integer(), nullable=False, comment='訊息序號'),
        sa.Column('feature_type', sa.String(length=20), nullable=False, comment='功能類型 (agent/rag)'),
        sa.Column('score', sa.Integer(), nullable=False, comment='評分 (1=有用, -1=無用)'),
        sa.Column('question', sa.Text(), nullable=True, comment='使用者問題'),
        sa.Column('answer_preview', sa.String(length=200), nullable=True, comment='回答前 200 字'),
        sa.Column('feedback_text', sa.String(length=500), nullable=True, comment='文字回饋 (可選)'),
        sa.Column('latency_ms', sa.Integer(), nullable=True, comment='回答延遲 ms'),
        sa.Column('model', sa.String(length=50), nullable=True, comment='使用的模型'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='建立時間'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_conv_feedback_conv', 'ai_conversation_feedback', ['conversation_id'], unique=False)
    op.create_index('ix_conv_feedback_feature', 'ai_conversation_feedback', ['feature_type', 'created_at'], unique=False)
    op.create_index('ix_conv_feedback_user', 'ai_conversation_feedback', ['user_id', 'created_at'], unique=False)


def downgrade() -> None:
    """移除 AI 對話回饋表"""
    op.drop_index('ix_conv_feedback_user', table_name='ai_conversation_feedback')
    op.drop_index('ix_conv_feedback_feature', table_name='ai_conversation_feedback')
    op.drop_index('ix_conv_feedback_conv', table_name='ai_conversation_feedback')
    op.drop_table('ai_conversation_feedback')
