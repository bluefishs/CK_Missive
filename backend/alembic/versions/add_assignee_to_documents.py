"""Add assignee column to documents

新增承辦人欄位以支援「承案人資」功能

Revision ID: add_assignee_column
Revises: add_performance_indexes
Create Date: 2026-01-07
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_assignee_column'
down_revision = 'add_performance_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """新增 assignee 欄位（冪等性設計）"""
    # 檢查欄位是否已存在
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'documents' AND column_name = 'assignee'
            ) THEN
                ALTER TABLE documents ADD COLUMN assignee VARCHAR(500);
                COMMENT ON COLUMN documents.assignee IS '承辦人（多人以逗號分隔）';
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """移除 assignee 欄位"""
    op.drop_column('documents', 'assignee')
