"""add LINE Login fields to users table

Revision ID: 20260322a004
Revises: 20260322a003
Create Date: 2026-03-22

Phase M1-A: LINE Login 帳號綁定 — users 表加入 line_user_id, line_display_name
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "20260322a004"
down_revision = "20260322a003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "line_user_id",
            sa.String(64),
            nullable=True,
            unique=True,
            comment="LINE User ID (帳號綁定)",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "line_display_name",
            sa.String(100),
            nullable=True,
            comment="LINE 顯示名稱",
        ),
    )
    op.create_index("ix_users_line_user_id", "users", ["line_user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_line_user_id", table_name="users")
    op.drop_column("users", "line_display_name")
    op.drop_column("users", "line_user_id")
