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
down_revision: Union[str, Sequence[str], None] = 'implement_navigation_tree_structure'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """新增 dispatch_format 和 has_attachment 欄位"""
    # 發文形式欄位
    op.add_column('documents', sa.Column(
        'dispatch_format',
        sa.String(length=20),
        nullable=True,
        comment='發文形式 (電子/紙本/電子+紙本)',
        server_default='電子'
    ))

    # 含附件欄位
    op.add_column('documents', sa.Column(
        'has_attachment',
        sa.Boolean(),
        nullable=True,
        comment='是否含附件',
        server_default='false'
    ))

    # 建立索引以加速查詢
    op.create_index(
        'ix_documents_dispatch_format',
        'documents',
        ['dispatch_format'],
        unique=False
    )
    op.create_index(
        'ix_documents_has_attachment',
        'documents',
        ['has_attachment'],
        unique=False
    )


def downgrade() -> None:
    """移除 dispatch_format 和 has_attachment 欄位"""
    op.drop_index('ix_documents_has_attachment', table_name='documents')
    op.drop_index('ix_documents_dispatch_format', table_name='documents')
    op.drop_column('documents', 'has_attachment')
    op.drop_column('documents', 'dispatch_format')
