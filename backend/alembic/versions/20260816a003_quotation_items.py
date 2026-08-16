"""報價明細（線上報價單）

2026-08-16 owner：「線上報價單機制」。

在此之前 `erp_quotations` **只有彙總金額** —— `total_price` 是一個
人手填的數字，沒有任何逐項資料。那不是報價單，是成本主檔。

實測 78 張報價裡 **23 張沒有總價（29%）**，而 78 張裡只有 40 張算得出毛利。
原因很直接：人手上真正有的是一份逐項的報價內容，
系統卻只給他一個空格叫他填總數。

有了明細之後 `total_price` 由小計加總得出，不再是獨立維護的第二份事實。

Revision ID: 20260816a003
Revises: 20260816a002
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260816a003"
down_revision: Union[str, Sequence[str], None] = "20260816a002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "erp_quotation_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quotation_id", sa.Integer(), nullable=False),
        sa.Column("item_name", sa.String(length=200), nullable=False, comment="工項名稱"),
        sa.Column("spec", sa.String(length=300), nullable=True, comment="規格/說明"),
        sa.Column("unit", sa.String(length=20), nullable=True, comment="單位"),
        sa.Column("qty", sa.Numeric(12, 2), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(15, 2), nullable=False, server_default="0"),
        # 小計存下來而不是每次算 —— 報價送出後單價可能調整，
        # 而已送出的那份報價金額不該跟著變。
        sa.Column("amount", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["quotation_id"], ["erp_quotations.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_erp_quotation_items_quotation_id", "erp_quotation_items", ["quotation_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_erp_quotation_items_quotation_id", table_name="erp_quotation_items")
    op.drop_table("erp_quotation_items")
