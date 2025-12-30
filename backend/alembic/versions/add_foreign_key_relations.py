"""Add foreign key relations for documents

Revision ID: add_foreign_key_relations
Revises:
Create Date: 2024-09-16 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_foreign_key_relations'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    升級資料庫 - 新增外鍵關聯欄位
    """

    # 新增外鍵欄位到 documents 表
    op.add_column('documents', sa.Column('contract_project_id', sa.Integer(), nullable=True, comment='關聯的承攬案件ID'))
    op.add_column('documents', sa.Column('sender_agency_id', sa.Integer(), nullable=True, comment='發文機關ID'))
    op.add_column('documents', sa.Column('receiver_agency_id', sa.Integer(), nullable=True, comment='受文機關ID'))

    # 創建外鍵約束
    op.create_foreign_key(
        'fk_documents_contract_project_id',
        'documents',
        'contract_projects',
        ['contract_project_id'],
        ['id'],
        ondelete='SET NULL'
    )

    op.create_foreign_key(
        'fk_documents_sender_agency_id',
        'documents',
        'government_agencies',
        ['sender_agency_id'],
        ['id'],
        ondelete='SET NULL'
    )

    op.create_foreign_key(
        'fk_documents_receiver_agency_id',
        'documents',
        'government_agencies',
        ['receiver_agency_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # 創建索引以提高查詢效能
    op.create_index('idx_documents_contract_project_id', 'documents', ['contract_project_id'])
    op.create_index('idx_documents_sender_agency_id', 'documents', ['sender_agency_id'])
    op.create_index('idx_documents_receiver_agency_id', 'documents', ['receiver_agency_id'])


def downgrade() -> None:
    """
    降級資料庫 - 移除外鍵關聯欄位
    """

    # 移除索引
    op.drop_index('idx_documents_receiver_agency_id', table_name='documents')
    op.drop_index('idx_documents_sender_agency_id', table_name='documents')
    op.drop_index('idx_documents_contract_project_id', table_name='documents')

    # 移除外鍵約束
    op.drop_constraint('fk_documents_receiver_agency_id', 'documents', type_='foreignkey')
    op.drop_constraint('fk_documents_sender_agency_id', 'documents', type_='foreignkey')
    op.drop_constraint('fk_documents_contract_project_id', 'documents', type_='foreignkey')

    # 移除欄位
    op.drop_column('documents', 'receiver_agency_id')
    op.drop_column('documents', 'sender_agency_id')
    op.drop_column('documents', 'contract_project_id')