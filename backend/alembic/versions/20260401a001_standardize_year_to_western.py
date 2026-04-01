"""standardize erp_quotations.year from ROC to western calendar

Revision ID: 20260401a001
Revises: 20260331a002
Create Date: 2026-04-01

NOTE: Data migration already applied via direct SQL on 2026-04-01.
This migration exists for auditability — the upgrade is idempotent.
"""
from alembic import op
import sqlalchemy as sa

revision = '20260401a001'
down_revision = '20260331a002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Convert ROC year (e.g., 114) to western year (e.g., 2025)
    # Idempotent: only converts values < 1911
    op.execute(
        "UPDATE erp_quotations SET year = year + 1911 "
        "WHERE year IS NOT NULL AND year < 1911"
    )


def downgrade() -> None:
    # Convert western year back to ROC year
    op.execute(
        "UPDATE erp_quotations SET year = year - 1911 "
        "WHERE year IS NOT NULL AND year > 1911"
    )
