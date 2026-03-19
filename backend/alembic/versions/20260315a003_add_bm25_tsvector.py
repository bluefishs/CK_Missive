"""add BM25 tsvector search support

Revision ID: 20260315a003
Revises: 20260315a002
Create Date: 2026-03-15

新增 tsvector 欄位 + GIN 索引支援 BM25 全文搜尋
使用 simple 分詞器 (適用中日韓字元逐字索引)
"""
from alembic import op
import sqlalchemy as sa

revision = "20260315a003"
down_revision = "20260315a002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 新增 tsvector 欄位
    op.add_column(
        "documents",
        sa.Column("search_vector", sa.Column(sa.Text()), nullable=True),
    )

    # 使用 raw SQL 建立 tsvector 和 GIN index
    op.execute("""
        -- 刪除舊欄位（如果上面的 add_column 不適用 tsvector 型別）
        ALTER TABLE documents DROP COLUMN IF EXISTS search_vector;

        -- 新增 tsvector 欄位
        ALTER TABLE documents ADD COLUMN search_vector tsvector;

        -- 建立 GIN 索引
        CREATE INDEX ix_documents_search_vector
            ON documents USING GIN (search_vector);

        -- 填充 tsvector (使用 simple 分詞器，對中文逐字索引)
        UPDATE documents SET search_vector =
            setweight(to_tsvector('simple', COALESCE(subject, '')), 'A') ||
            setweight(to_tsvector('simple', COALESCE(sender, '')), 'B') ||
            setweight(to_tsvector('simple', COALESCE(receiver, '')), 'B') ||
            setweight(to_tsvector('simple', COALESCE(doc_number, '')), 'A') ||
            setweight(to_tsvector('simple', COALESCE(ck_note, '')), 'C');

        -- 建立自動更新觸發器
        CREATE OR REPLACE FUNCTION documents_search_vector_trigger()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('simple', COALESCE(NEW.subject, '')), 'A') ||
                setweight(to_tsvector('simple', COALESCE(NEW.sender, '')), 'B') ||
                setweight(to_tsvector('simple', COALESCE(NEW.receiver, '')), 'B') ||
                setweight(to_tsvector('simple', COALESCE(NEW.doc_number, '')), 'A') ||
                setweight(to_tsvector('simple', COALESCE(NEW.ck_note, '')), 'C');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS tsvector_update ON documents;
        CREATE TRIGGER tsvector_update
            BEFORE INSERT OR UPDATE ON documents
            FOR EACH ROW EXECUTE FUNCTION documents_search_vector_trigger();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tsvector_update ON documents;")
    op.execute("DROP FUNCTION IF EXISTS documents_search_vector_trigger();")
    op.execute("DROP INDEX IF EXISTS ix_documents_search_vector;")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS search_vector;")
