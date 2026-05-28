"""tender_records add pcc_match_* columns (ADR-0046 Phase 3)

L50 lesson 落地 — ezbid → PCC link 用 4 個新欄位記錄 fuzzy match 結果。

Revision ID: 20260528_tender_pcc_match
Revises: 20260521a001
Create Date: 2026-05-28

設計:
- pcc_match_unit_id: PCC 對應 unit_id (nullable, ezbid 才有值)
- pcc_match_job_number: PCC 對應 job_number
- pcc_match_confidence: 0-1.0 信心分數 (0.5×title + 0.3×agency + 0.2×date)
- pcc_match_at: 自動 match 時間（給 enrichment_freshness_audit 用）
- partial index on (unit_id, job_number) WHERE matched — 不浪費空間
"""
from alembic import op
import sqlalchemy as sa


revision = '20260528_tender_pcc_match'
down_revision = '20260521a001'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tender_records', sa.Column('pcc_match_unit_id', sa.String(50), nullable=True))
    op.add_column('tender_records', sa.Column('pcc_match_job_number', sa.String(50), nullable=True))
    op.add_column('tender_records', sa.Column('pcc_match_confidence', sa.Float, nullable=True))
    op.add_column('tender_records', sa.Column('pcc_match_at', sa.DateTime, nullable=True))

    # Partial index — 只索引 matched records（避空間浪費）
    op.create_index(
        'idx_tender_pcc_match',
        'tender_records',
        ['pcc_match_unit_id', 'pcc_match_job_number'],
        postgresql_where=sa.text('pcc_match_unit_id IS NOT NULL'),
    )


def downgrade():
    op.drop_index('idx_tender_pcc_match', table_name='tender_records')
    op.drop_column('tender_records', 'pcc_match_at')
    op.drop_column('tender_records', 'pcc_match_confidence')
    op.drop_column('tender_records', 'pcc_match_job_number')
    op.drop_column('tender_records', 'pcc_match_unit_id')
