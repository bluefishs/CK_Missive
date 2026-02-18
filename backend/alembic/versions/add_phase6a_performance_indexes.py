"""add phase6a performance indexes

補建 3 個效能索引：
1. documents.assignee + doc_date — AI 搜尋 RLS 排序
2. taoyuan_dispatch_document_links 複合索引 — sync 腳本查詢
3. ai_search_history.query trgm — 搜尋歷史模糊查詢

Revision ID: phase6a_indexes
Create Date: 2026-02-18
"""
from alembic import op


# revision identifiers
revision = 'phase6a_indexes'
down_revision = None  # standalone migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. assignee + doc_date 複合索引（AI 搜尋 RLS 排序用）
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_assignee_date
        ON documents (assignee, doc_date DESC)
        WHERE assignee IS NOT NULL
    """)

    # 2. dispatch_document_links 複合索引（sync 腳本查詢用）
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_dispatch_doc_links_composite
        ON taoyuan_dispatch_document_links (dispatch_order_id, document_id, link_type)
    """)

    # 3. ai_search_history.query trgm 索引（模糊搜尋用，需 pg_trgm 擴展）
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm') THEN
                EXECUTE 'CREATE INDEX IF NOT EXISTS ix_ai_search_history_query_trgm
                    ON ai_search_history USING gin(query gin_trgm_ops)';
            END IF;
        END $$
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_documents_assignee_date")
    op.execute("DROP INDEX IF EXISTS ix_dispatch_doc_links_composite")
    op.execute("DROP INDEX IF EXISTS ix_ai_search_history_query_trgm")
