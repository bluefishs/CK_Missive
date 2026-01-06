"""enhance document_attachments table

新增欄位：
- storage_type: 儲存類型 (local/network/s3)
- original_name: 原始檔案名稱
- checksum: SHA256 校驗碼
- uploaded_by: 上傳者 ID

Revision ID: enhance_attachments_001
Revises: add_dispatch_format_and_attachment
Create Date: 2026-01-06

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'enhance_attachments_001'
down_revision = 'allow_null_doc_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """新增 document_attachments 擴充欄位"""

    # 檢查並新增 storage_type 欄位
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'document_attachments' AND column_name = 'storage_type'
            ) THEN
                ALTER TABLE document_attachments
                ADD COLUMN storage_type VARCHAR(20) DEFAULT 'local';
                COMMENT ON COLUMN document_attachments.storage_type IS '儲存類型: local/network/s3';
            END IF;
        END $$;
    """)

    # 檢查並新增 original_name 欄位
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'document_attachments' AND column_name = 'original_name'
            ) THEN
                ALTER TABLE document_attachments
                ADD COLUMN original_name VARCHAR(255);
                COMMENT ON COLUMN document_attachments.original_name IS '原始檔案名稱';
            END IF;
        END $$;
    """)

    # 檢查並新增 checksum 欄位
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'document_attachments' AND column_name = 'checksum'
            ) THEN
                ALTER TABLE document_attachments
                ADD COLUMN checksum VARCHAR(64);
                COMMENT ON COLUMN document_attachments.checksum IS 'SHA256 校驗碼';
            END IF;
        END $$;
    """)

    # 檢查並新增 uploaded_by 欄位
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'document_attachments' AND column_name = 'uploaded_by'
            ) THEN
                ALTER TABLE document_attachments
                ADD COLUMN uploaded_by INTEGER;
                COMMENT ON COLUMN document_attachments.uploaded_by IS '上傳者 ID';
            END IF;
        END $$;
    """)

    # 新增外鍵約束 (如果 users 表存在)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'users'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'document_attachments_uploaded_by_fkey'
            ) THEN
                ALTER TABLE document_attachments
                ADD CONSTRAINT document_attachments_uploaded_by_fkey
                FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE SET NULL;
            END IF;
        END $$;
    """)

    # 為 checksum 建立索引（用於重複檔案檢測）
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE indexname = 'ix_document_attachments_checksum'
            ) THEN
                CREATE INDEX ix_document_attachments_checksum
                ON document_attachments(checksum);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """移除 document_attachments 擴充欄位"""

    # 移除索引
    op.execute("""
        DROP INDEX IF EXISTS ix_document_attachments_checksum;
    """)

    # 移除外鍵約束
    op.execute("""
        ALTER TABLE document_attachments
        DROP CONSTRAINT IF EXISTS document_attachments_uploaded_by_fkey;
    """)

    # 移除欄位
    op.execute("""
        ALTER TABLE document_attachments
        DROP COLUMN IF EXISTS storage_type,
        DROP COLUMN IF EXISTS original_name,
        DROP COLUMN IF EXISTS checksum,
        DROP COLUMN IF EXISTS uploaded_by;
    """)
