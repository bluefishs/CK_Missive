"""tender_match_review table (L51 / ADR-0046 task E: MEDIUM review queue)

修補 ADR-0046 缺口：MEDIUM (0.70-0.85 但未過 HIGH guard) 1,293 筆候選
原本被 enrichment skipped。新增 review queue 讓 admin 手動確認。

設計:
- 每筆 MEDIUM 寫入 review queue（pending status）
- admin approve → apply_match_to_record 寫 pcc_match_* 4 欄 + status=approved
- admin reject → status=rejected（不 auto-link）
- (ezbid_id, pcc_unit_id, pcc_job_number) 唯一約束防重複 insert

Revision ID: 20260529a001
Revises: 20260528b001
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa


revision = '20260529a001'
down_revision = '20260528b001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'tender_match_review',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('ezbid_record_id', sa.Integer,
                  sa.ForeignKey('tender_records.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('pcc_unit_id', sa.String(50), nullable=False),
        sa.Column('pcc_job_number', sa.String(100), nullable=False),
        sa.Column('confidence', sa.Float, nullable=False),
        sa.Column('title_sim', sa.Float, nullable=False),
        sa.Column('agency_match', sa.Float, nullable=False),
        sa.Column('date_proximity', sa.Float, nullable=False),
        sa.Column('ezbid_title', sa.String(500), nullable=True),
        sa.Column('pcc_title', sa.String(500), nullable=True),
        sa.Column('ezbid_unit_name', sa.String(200), nullable=True),
        sa.Column('pcc_unit_name', sa.String(200), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('reviewed_by', sa.Integer, nullable=True),
        sa.Column('reviewed_at', sa.DateTime, nullable=True),
        sa.Column('reviewer_note', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    # 防同一 ezbid×PCC 對應重複加入
    op.create_unique_constraint(
        'uq_tender_match_review_ezbid_pcc',
        'tender_match_review',
        ['ezbid_record_id', 'pcc_unit_id', 'pcc_job_number'],
    )
    # 查 pending list 用（admin UI 主入口）
    op.create_index(
        'ix_tender_match_review_status_conf',
        'tender_match_review',
        ['status', 'confidence'],
    )
    # 按 ezbid 反查（detail page 可能用）
    op.create_index(
        'ix_tender_match_review_ezbid',
        'tender_match_review',
        ['ezbid_record_id'],
    )


def downgrade():
    op.drop_index('ix_tender_match_review_ezbid', table_name='tender_match_review')
    op.drop_index('ix_tender_match_review_status_conf', table_name='tender_match_review')
    op.drop_constraint('uq_tender_match_review_ezbid_pcc', 'tender_match_review', type_='unique')
    op.drop_table('tender_match_review')
