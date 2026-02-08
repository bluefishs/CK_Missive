"""新增密碼重設欄位到 users 表

新增 password_reset_token 和 password_reset_expires 欄位，
支援密碼重設 token 儲存與過期控制。

Revision ID: add_password_reset
Revises: add_account_lockout
Create Date: 2026-02-08
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'add_password_reset'
down_revision = 'add_account_lockout'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """新增密碼重設欄位（冪等性設計）"""
    # 新增 password_reset_token 欄位
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'password_reset_token'
            ) THEN
                ALTER TABLE users ADD COLUMN password_reset_token VARCHAR(128);
                COMMENT ON COLUMN users.password_reset_token IS '密碼重設 token (SHA-256 hash)';
            END IF;
        END $$;
    """)

    # 新增 password_reset_expires 欄位
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'password_reset_expires'
            ) THEN
                ALTER TABLE users ADD COLUMN password_reset_expires TIMESTAMPTZ;
                COMMENT ON COLUMN users.password_reset_expires IS '密碼重設 token 過期時間';
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """移除密碼重設欄位"""
    op.drop_column('users', 'password_reset_expires')
    op.drop_column('users', 'password_reset_token')
