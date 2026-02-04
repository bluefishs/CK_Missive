"""
新增 doc_type + status + doc_date 複合索引

此索引優化常見的公文篩選查詢：
- 按公文類型篩選 (doc_type)
- 按狀態篩選 (status)
- 按日期排序 (doc_date DESC)

Revision ID: add_doctype_status_idx
Revises: optimize_doc_filter_idx
Create Date: 2026-02-04
"""
from alembic import op


# revision identifiers
revision = 'add_doctype_status_idx'
down_revision = 'increase_work_type_len'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    建立 doc_type + status + doc_date 複合索引

    優化的查詢場景：
    1. 篩選特定類型的公文 (WHERE doc_type = '函')
    2. 篩選特定狀態的公文 (WHERE status = '待處理')
    3. 組合篩選並按日期排序 (WHERE doc_type = '函' AND status = '待處理' ORDER BY doc_date DESC)
    """
    # 複合索引：doc_type + status + doc_date DESC
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_type_status_date
        ON documents (doc_type, status, doc_date DESC NULLS LAST)
    """)

    # 部分索引：僅包含待處理的公文（常見查詢）
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_pending_by_date
        ON documents (doc_date DESC NULLS LAST)
        WHERE status = '待處理'
    """)

    # 部分索引：僅包含收文（常見查詢）
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_received_by_date
        ON documents (doc_date DESC NULLS LAST)
        WHERE category = '收文'
    """)

    # 部分索引：僅包含發文（常見查詢）
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_sent_by_date
        ON documents (doc_date DESC NULLS LAST)
        WHERE category = '發文'
    """)


def downgrade() -> None:
    """移除建立的索引"""
    op.execute("DROP INDEX IF EXISTS ix_documents_type_status_date")
    op.execute("DROP INDEX IF EXISTS ix_documents_pending_by_date")
    op.execute("DROP INDEX IF EXISTS ix_documents_received_by_date")
    op.execute("DROP INDEX IF EXISTS ix_documents_sent_by_date")
