"""Add dispatch_format and has_attachment columns

Revision ID: add_dispatch_format_attachment
Revises: implement_navigation_tree_structure
Create Date: 2025-01-05

新增欄位:
- dispatch_format: 發文形式 (電子/紙本/電子+紙本)
- has_attachment: 含附件 (Boolean)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_dispatch_format_attachment'
down_revision: Union[str, Sequence[str], None] = 'nav_tree_structure'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """新增 dispatch_format 和 has_attachment 欄位（冪等性設計）"""
    # 發文形式欄位 - 檢查是否存在
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'documents' AND column_name = 'dispatch_format'
            ) THEN
                ALTER TABLE documents ADD COLUMN dispatch_format VARCHAR(20) DEFAULT '電子';
                COMMENT ON COLUMN documents.dispatch_format IS '發文形式 (電子/紙本/電子+紙本)';
            END IF;
        END $$;
    """)

    # 含附件欄位 - 檢查是否存在
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'documents' AND column_name = 'has_attachment'
            ) THEN
                ALTER TABLE documents ADD COLUMN has_attachment BOOLEAN DEFAULT false;
                COMMENT ON COLUMN documents.has_attachment IS '是否含附件';
            END IF;
        END $$;
    """)

    # 建立索引（如不存在）
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes WHERE indexname = 'ix_documents_dispatch_format'
            ) THEN
                CREATE INDEX ix_documents_dispatch_format ON documents(dispatch_format);
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes WHERE indexname = 'ix_documents_has_attachment'
            ) THEN
                CREATE INDEX ix_documents_has_attachment ON documents(has_attachment);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """移除 dispatch_format 和 has_attachment 欄位"""
    op.drop_index('ix_documents_has_attachment', table_name='documents')
    op.drop_index('ix_documents_dispatch_format', table_name='documents')
    op.drop_column('documents', 'has_attachment')
    op.drop_column('documents', 'dispatch_format')
