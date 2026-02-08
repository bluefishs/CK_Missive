"""新增帳號鎖定欄位到 users 表

新增 failed_login_attempts 和 locked_until 欄位，
支援 5 次密碼錯誤後鎖定帳號 15 分鐘的安全機制。

Revision ID: add_account_lockout
Revises: add_missing_trgm
Create Date: 2026-02-08
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'add_account_lockout'
down_revision = 'add_missing_trgm'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """新增帳號鎖定欄位（冪等性設計）"""
    # 新增 failed_login_attempts 欄位
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'failed_login_attempts'
            ) THEN
                ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER NOT NULL DEFAULT 0;
                COMMENT ON COLUMN users.failed_login_attempts IS '連續登入失敗次數';
            END IF;
        END $$;
    """)

    # 新增 locked_until 欄位
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'locked_until'
            ) THEN
                ALTER TABLE users ADD COLUMN locked_until TIMESTAMPTZ;
                COMMENT ON COLUMN users.locked_until IS '帳號鎖定到期時間';
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """移除帳號鎖定欄位"""
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
