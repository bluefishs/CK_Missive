"""Identity Unification (ADR-0025): canonical_user_id + user_merge_log

Revision ID: 20260421a001
Revises: 20260416a003
Create Date: 2026-04-21

v5.8.0 坤哥意識體 Phase Identity — 方案 D (自引用) + 規則 B (權限隔離)。
"""
from alembic import op
import sqlalchemy as sa


revision = '20260421a001'
down_revision = '20260416a003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) users.canonical_user_id 自引用
    op.add_column(
        'users',
        sa.Column(
            'canonical_user_id',
            sa.Integer(),
            nullable=True,
            comment='Identity Unification: 指向真正代表本人的 user.id；NULL 代表本身即 canonical',
        ),
    )
    op.create_foreign_key(
        'fk_users_canonical_user_id',
        'users', 'users',
        ['canonical_user_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_users_canonical_user_id',
        'users', ['canonical_user_id'],
    )

    # 2) user_merge_log 審計表
    op.create_table(
        'user_merge_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('canonical_id', sa.Integer(), nullable=False, index=True),
        sa.Column('alias_id', sa.Integer(), nullable=False, index=True),
        sa.Column('canonical_role', sa.String(20), nullable=True),
        sa.Column('alias_role', sa.String(20), nullable=True),
        sa.Column(
            'role_harmonized', sa.Boolean(), nullable=False,
            server_default=sa.false(),
            comment='規則 B：合併時是否同時統一權限（預設 false）',
        ),
        sa.Column('merged_by', sa.Integer(), nullable=True, index=True),
        sa.Column('merged_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('reversed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reversed_by', sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('user_merge_log')
    op.drop_index('ix_users_canonical_user_id', table_name='users')
    op.drop_constraint('fk_users_canonical_user_id', 'users', type_='foreignkey')
    op.drop_column('users', 'canonical_user_id')
