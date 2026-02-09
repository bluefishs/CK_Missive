"""新增 Email 驗證欄位到 users 表

新增 email_verification_token 和 email_verification_expires 欄位，
用於支援 Email 驗證流程。

Revision ID: add_email_verification
Revises: merge_phase4_heads
Create Date: 2026-02-09
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'add_email_verification'
down_revision = 'merge_phase4_heads'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """新增 email 驗證欄位（冪等設計）"""
    conn = op.get_bind()

    # 檢查欄位是否已存在
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'users' AND column_name = 'email_verification_token'"
    ))
    if result.scalar() is None:
        op.add_column('users', sa.Column(
            'email_verification_token',
            sa.String(128),
            nullable=True,
            comment='Email 驗證 token (SHA-256 hash)',
        ))

    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'users' AND column_name = 'email_verification_expires'"
    ))
    if result.scalar() is None:
        op.add_column('users', sa.Column(
            'email_verification_expires',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Email 驗證 token 過期時間',
        ))


def downgrade() -> None:
    """移除 email 驗證欄位"""
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'email_verification_token'
            ) THEN
                ALTER TABLE users DROP COLUMN email_verification_token;
            END IF;
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'email_verification_expires'
            ) THEN
                ALTER TABLE users DROP COLUMN email_verification_expires;
            END IF;
        END $$;
    """)
