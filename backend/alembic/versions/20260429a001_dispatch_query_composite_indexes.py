"""dispatch query composite indexes (DDD: dispatch query domain)

Revision ID: 20260429a001
Revises: 20260424a002
Create Date: 2026-04-29

依「派工查詢領域」DDD 視角補複合索引（v5.10.x 架構覆盤產出）。

設計原則：按查詢需求設計，而非「行數驅動」、「FK 全標 index 即可」。

新增索引：
  1. (contract_project_id, created_at DESC) on taoyuan_dispatch_orders
     場景：派工列表「按承攬案件 + 時間軸」分頁
     查詢：filter_dispatch_orders WHERE contract_project_id = X ORDER BY created_at DESC

  2. (dispatch_order_id, sort_order, record_date) on taoyuan_work_records
     場景：派工詳情頁作業歷程時間軸顯示
     查詢：WHERE dispatch_order_id = X ORDER BY sort_order, record_date

注意：
  - taoyuan_dispatch_orders.contract_project_id 已有單欄 index（保留）
  - taoyuan_work_records.dispatch_order_id 已有單欄 index（保留 — 純 IN 查詢仍受惠）
  - 新複合索引提供 left-prefix scan 能力，不衝突
"""
from typing import Sequence, Union

from alembic import op


revision: str = '20260429a001'
down_revision: Union[str, Sequence[str], None] = '20260424a002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 索引 1: 派工列表「按案件 + 時間」分頁領域
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_dispatch_orders_project_created "
        "ON taoyuan_dispatch_orders (contract_project_id, created_at DESC)"
    )

    # 索引 2: 派工詳情頁作業歷程時間軸領域
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_work_records_dispatch_sort_date "
        "ON taoyuan_work_records (dispatch_order_id, sort_order, record_date)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_work_records_dispatch_sort_date")
    op.execute("DROP INDEX IF EXISTS ix_dispatch_orders_project_created")
