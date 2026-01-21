"""Add unique constraints to link tables

為關聯表添加唯一約束，避免重複關聯

Revision ID: add_link_unique_constraints
Revises: add_doc_proj_link
Create Date: 2026-01-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_link_unique_constraints'
down_revision = 'add_doc_proj_link'
branch_labels = None
depends_on = None


def upgrade():
    # 為 taoyuan_dispatch_project_link 添加唯一約束
    op.create_unique_constraint(
        'uq_dispatch_project',
        'taoyuan_dispatch_project_link',
        ['dispatch_order_id', 'taoyuan_project_id']
    )

    # 為 taoyuan_dispatch_document_link 添加唯一約束
    op.create_unique_constraint(
        'uq_dispatch_document',
        'taoyuan_dispatch_document_link',
        ['dispatch_order_id', 'document_id']
    )

    # 為 taoyuan_document_project_link 添加唯一約束
    op.create_unique_constraint(
        'uq_document_project',
        'taoyuan_document_project_link',
        ['document_id', 'taoyuan_project_id']
    )


def downgrade():
    # 移除唯一約束
    op.drop_constraint('uq_document_project', 'taoyuan_document_project_link', type_='unique')
    op.drop_constraint('uq_dispatch_document', 'taoyuan_dispatch_document_link', type_='unique')
    op.drop_constraint('uq_dispatch_project', 'taoyuan_dispatch_project_link', type_='unique')
