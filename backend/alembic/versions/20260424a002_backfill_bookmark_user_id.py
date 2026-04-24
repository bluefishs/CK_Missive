"""Backfill tender_bookmarks.user_id for pre-v5.9.3 records

Revision ID: 20260424a002
Revises: 20260424a001
Create Date: 2026-04-24

v5.9.3 改 bookmarks 為 per-user，但舊資料的 user_id 仍為 NULL，造成
使用者登入後看不到自己先前收藏的案件。

此 migration 將所有 NULL user_id 回填到 user_id=1（系統首位 superuser
admin@example.com，v5.9.3 以前僅有此帳號在收藏）。
"""
from alembic import op


revision = "20260424a002"
down_revision = "20260424a001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE tender_bookmarks
        SET user_id = 1
        WHERE user_id IS NULL
          AND EXISTS (SELECT 1 FROM users WHERE id = 1);
    """)


def downgrade() -> None:
    # 無法還原「哪些是原 NULL 哪些是原本就 user_id=1」，downgrade no-op
    pass
