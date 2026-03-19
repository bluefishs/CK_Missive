"""add budget_limit to erp_quotations

Revision ID: 20260317a002
Revises: 20260317a001
Create Date: 2026-03-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260317a002"
down_revision = "20260317a001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "erp_quotations",
        sa.Column("budget_limit", sa.Numeric(15, 2), nullable=True, comment="預算上限"),
    )


def downgrade() -> None:
    op.drop_column("erp_quotations", "budget_limit")
