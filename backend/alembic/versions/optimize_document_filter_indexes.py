"""
優化公文篩選相關資料庫索引

此遷移建立複合索引以優化常用的篩選查詢效能

Revision ID: optimize_doc_filter_idx
Revises:
Create Date: 2026-01-08
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'optimize_doc_filter_idx'
down_revision = None  # 設定為上一個遷移的 revision ID
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    建立複合索引以優化篩選查詢

    優化的查詢場景：
    1. 依 category + doc_date 篩選 (Tab 分類 + 日期範圍)
    2. 依 delivery_method + category 篩選 (發文形式 + 分類)
    3. 全文搜尋 subject, doc_number (關鍵字搜尋)
    """
    # 檢查並建立 category + doc_date 複合索引
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_category_doc_date
        ON documents (category, doc_date DESC NULLS LAST)
    """)

    # 檢查並建立 delivery_method + category 複合索引
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_delivery_category
        ON documents (delivery_method, category)
    """)

    # 建立 sender 的部分索引 (排除 NULL)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_sender_partial
        ON documents (sender)
        WHERE sender IS NOT NULL AND sender != ''
    """)

    # 建立 receiver 的部分索引 (排除 NULL)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_receiver_partial
        ON documents (receiver)
        WHERE receiver IS NOT NULL AND receiver != ''
    """)

    # 建立 contract_project_id 與 doc_date 的複合索引 (案件篩選優化)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_project_date
        ON documents (contract_project_id, doc_date DESC NULLS LAST)
        WHERE contract_project_id IS NOT NULL
    """)

    # 建立 pg_trgm 擴展 (如果尚未存在) - 用於模糊搜尋優化
    op.execute("""
        CREATE EXTENSION IF NOT EXISTS pg_trgm
    """)

    # 建立 subject 的 GIN 索引 (使用 pg_trgm 進行模糊搜尋優化)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_subject_trgm
        ON documents USING gin (subject gin_trgm_ops)
    """)

    # 建立 doc_number 的 GIN 索引
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_doc_number_trgm
        ON documents USING gin (doc_number gin_trgm_ops)
    """)


def downgrade() -> None:
    """移除建立的索引"""
    op.execute("DROP INDEX IF EXISTS ix_documents_category_doc_date")
    op.execute("DROP INDEX IF EXISTS ix_documents_delivery_category")
    op.execute("DROP INDEX IF EXISTS ix_documents_sender_partial")
    op.execute("DROP INDEX IF EXISTS ix_documents_receiver_partial")
    op.execute("DROP INDEX IF EXISTS ix_documents_project_date")
    op.execute("DROP INDEX IF EXISTS ix_documents_subject_trgm")
    op.execute("DROP INDEX IF EXISTS ix_documents_doc_number_trgm")
