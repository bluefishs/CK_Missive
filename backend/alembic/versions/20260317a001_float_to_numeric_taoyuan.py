"""Float to Numeric(15,2) for taoyuan money columns

Revision ID: 20260317a001
Revises: 20260316b002
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa

revision = "20260317a001"
down_revision = "20260316b002"
branch_labels = None
depends_on = None

# TaoyuanProject: 金額/長度欄位
PROJECT_COLUMNS = [
    "road_length",
    "current_width",
    "planned_width",
    "construction_cost",
    "land_cost",
    "compensation_cost",
    "total_cost",
]

# TaoyuanContractPayment: 派工金額欄位
PAYMENT_COLUMNS = [
    "work_01_amount",
    "work_02_amount",
    "work_03_amount",
    "work_04_amount",
    "work_05_amount",
    "work_06_amount",
    "work_07_amount",
    "current_amount",
    "cumulative_amount",
    "remaining_amount",
]


def upgrade() -> None:
    for col in PROJECT_COLUMNS:
        op.alter_column(
            "taoyuan_projects",
            col,
            existing_type=sa.Float(),
            type_=sa.Numeric(precision=15, scale=2),
            existing_nullable=True,
            postgresql_using=f"{col}::numeric(15,2)",
        )

    for col in PAYMENT_COLUMNS:
        op.alter_column(
            "taoyuan_contract_payments",
            col,
            existing_type=sa.Float(),
            type_=sa.Numeric(precision=15, scale=2),
            existing_nullable=True,
            postgresql_using=f"{col}::numeric(15,2)",
        )


def downgrade() -> None:
    for col in PROJECT_COLUMNS:
        op.alter_column(
            "taoyuan_projects",
            col,
            existing_type=sa.Numeric(precision=15, scale=2),
            type_=sa.Float(),
            existing_nullable=True,
        )

    for col in PAYMENT_COLUMNS:
        op.alter_column(
            "taoyuan_contract_payments",
            col,
            existing_type=sa.Numeric(precision=15, scale=2),
            type_=sa.Float(),
            existing_nullable=True,
        )
