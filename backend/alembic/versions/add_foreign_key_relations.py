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
    升級資料庫 - 新增外鍵關聯欄位（冪等性設計）
    """

    # 新增外鍵欄位到 documents 表（檢查是否存在）
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'documents' AND column_name = 'contract_project_id') THEN
                ALTER TABLE documents ADD COLUMN contract_project_id INTEGER;
                COMMENT ON COLUMN documents.contract_project_id IS '關聯的承攬案件ID';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'documents' AND column_name = 'sender_agency_id') THEN
                ALTER TABLE documents ADD COLUMN sender_agency_id INTEGER;
                COMMENT ON COLUMN documents.sender_agency_id IS '發文機關ID';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'documents' AND column_name = 'receiver_agency_id') THEN
                ALTER TABLE documents ADD COLUMN receiver_agency_id INTEGER;
                COMMENT ON COLUMN documents.receiver_agency_id IS '受文機關ID';
            END IF;
        END $$;
    """)

    # 創建外鍵約束（檢查是否存在）
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'fk_documents_contract_project_id') THEN
                ALTER TABLE documents ADD CONSTRAINT fk_documents_contract_project_id FOREIGN KEY (contract_project_id) REFERENCES contract_projects(id) ON DELETE SET NULL;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'fk_documents_sender_agency_id') THEN
                ALTER TABLE documents ADD CONSTRAINT fk_documents_sender_agency_id FOREIGN KEY (sender_agency_id) REFERENCES government_agencies(id) ON DELETE SET NULL;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'fk_documents_receiver_agency_id') THEN
                ALTER TABLE documents ADD CONSTRAINT fk_documents_receiver_agency_id FOREIGN KEY (receiver_agency_id) REFERENCES government_agencies(id) ON DELETE SET NULL;
            END IF;
        END $$;
    """)

    # 創建索引以提高查詢效能（檢查是否存在）
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_documents_contract_project_id') THEN
                CREATE INDEX idx_documents_contract_project_id ON documents(contract_project_id);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_documents_sender_agency_id') THEN
                CREATE INDEX idx_documents_sender_agency_id ON documents(sender_agency_id);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_documents_receiver_agency_id') THEN
                CREATE INDEX idx_documents_receiver_agency_id ON documents(receiver_agency_id);
            END IF;
        END $$;
    """)


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