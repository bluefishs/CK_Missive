"""tender_records add detail enrichment columns (P2 — 標案詳情 enrichment)

智能職能篩選 + 詳情頁補齊：從 PCC searchTenderDetail(取 orgId) → openfun API 取乾淨詳情。
新增欄位皆 nullable、ADD COLUMN IF NOT EXISTS（冪等、零刪除、DB 安全）。

- org_id: PCC/openfun 點分機關代碼（如 A.13.6.20，cache 避免重抓 PCC 頁）
- procurement_nature: 採購性質（財物/工程/勞務/非屬財物之工程或勞務）← 智能篩選核心
- base_price: 底價
- award_result: 決標結果摘要
- bidders: 投標/得標廠商 (jsonb)
- detail_enriched_at: enrichment 時間（freshness audit）

Revision ID: 20260617a001
Revises: 20260529a001
Create Date: 2026-06-17
"""
from alembic import op


revision = '20260617a001'
down_revision = '20260529a001'
branch_labels = None
depends_on = None


def upgrade():
    # ADD COLUMN IF NOT EXISTS — 冪等、不影響既有資料（DB 安全：純新增）
    op.execute("ALTER TABLE tender_records ADD COLUMN IF NOT EXISTS org_id VARCHAR(30)")
    op.execute("ALTER TABLE tender_records ADD COLUMN IF NOT EXISTS procurement_nature VARCHAR(60)")
    op.execute("ALTER TABLE tender_records ADD COLUMN IF NOT EXISTS base_price VARCHAR(40)")
    op.execute("ALTER TABLE tender_records ADD COLUMN IF NOT EXISTS award_result TEXT")
    op.execute("ALTER TABLE tender_records ADD COLUMN IF NOT EXISTS bidders JSONB")
    op.execute("ALTER TABLE tender_records ADD COLUMN IF NOT EXISTS detail_enriched_at TIMESTAMP")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tender_enriched "
        "ON tender_records (detail_enriched_at) WHERE detail_enriched_at IS NOT NULL"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_tender_enriched")
    for col in ("detail_enriched_at", "bidders", "award_result", "base_price",
                "procurement_nature", "org_id"):
        op.execute(f"ALTER TABLE tender_records DROP COLUMN IF EXISTS {col}")
