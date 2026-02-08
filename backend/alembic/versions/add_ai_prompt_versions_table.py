"""新增 AI Prompt 版本控制表

新增 ai_prompt_versions 表，支援 prompt 版本管理、啟用/停用。

Revision ID: add_ai_prompt_versions
Revises: add_password_reset
Create Date: 2026-02-08
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'add_ai_prompt_versions'
down_revision = 'add_password_reset'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ai_prompt_versions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('feature', sa.String(50), nullable=False, comment='功能名稱 (summary, classify, keywords, search_intent, match_agency)'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1', comment='版本號'),
        sa.Column('system_prompt', sa.Text(), nullable=False, comment='系統提示詞'),
        sa.Column('user_template', sa.Text(), nullable=True, comment='使用者提示詞模板'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false', comment='是否為啟用版本'),
        sa.Column('description', sa.String(500), nullable=True, comment='版本說明'),
        sa.Column('created_by', sa.String(100), nullable=True, comment='建立者'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='建立時間'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_prompt_feature_active', 'ai_prompt_versions', ['feature', 'is_active'])
    op.create_index('ix_prompt_feature_version', 'ai_prompt_versions', ['feature', 'version'])


def downgrade() -> None:
    op.drop_index('ix_prompt_feature_version', table_name='ai_prompt_versions')
    op.drop_index('ix_prompt_feature_active', table_name='ai_prompt_versions')
    op.drop_table('ai_prompt_versions')
