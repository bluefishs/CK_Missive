"""Add taoyuan_document_project_link table

建立公文-工程直接關聯表，用於將公文直接關聯到工程（不經過派工單）

Revision ID: add_doc_proj_link
Revises: a1b2c3d4e5f6
Create Date: 2026-01-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_doc_proj_link'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # 建立公文-工程關聯表
    op.create_table('taoyuan_document_project_link',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('taoyuan_project_id', sa.Integer(), nullable=False),
        sa.Column('link_type', sa.String(length=20), nullable=True, comment='關聯類型：agency_incoming/company_outgoing'),
        sa.Column('notes', sa.String(length=500), nullable=True, comment='關聯備註'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['taoyuan_project_id'], ['taoyuan_projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_taoyuan_document_project_link_document_id'), 'taoyuan_document_project_link', ['document_id'], unique=False)
    op.create_index(op.f('ix_taoyuan_document_project_link_id'), 'taoyuan_document_project_link', ['id'], unique=False)
    op.create_index(op.f('ix_taoyuan_document_project_link_taoyuan_project_id'), 'taoyuan_document_project_link', ['taoyuan_project_id'], unique=False)


def downgrade():
    # 移除索引
    op.drop_index(op.f('ix_taoyuan_document_project_link_taoyuan_project_id'), table_name='taoyuan_document_project_link')
    op.drop_index(op.f('ix_taoyuan_document_project_link_id'), table_name='taoyuan_document_project_link')
    op.drop_index(op.f('ix_taoyuan_document_project_link_document_id'), table_name='taoyuan_document_project_link')
    # 移除表
    op.drop_table('taoyuan_document_project_link')
