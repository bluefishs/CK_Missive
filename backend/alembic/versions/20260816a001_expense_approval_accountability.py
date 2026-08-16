"""核銷審核加上「誰核的」與「何時核的」

2026-08-16：查證發現 `ExpenseApprovalService.approve(invoice_id)` **根本不接收使用者** ——
系統不知道也不記錄是誰核准的，而四層審批的每一層都只要 `projects:write`
（11 個在職帳號都有），且**沒有防自核**。
也就是說「四層審批」實際上是同一個人點四次，不產生任何控制效果 ——
9 筆核銷只有 2 筆走完，不是大家偷懶，是這個流程做了也沒意義。

這支遷移只做**記錄**（誰、何時），純加法：
- `approved_by`：核准者（SET NULL，人離職不該讓歷史單據壞掉）
- `approved_at`：核准時間

擋自核與低額自動通過屬行為變更，寫在 service，不在這裡。

Revision ID: 20260816a001
Revises: 20260805a001
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260816a001"
down_revision: Union[str, Sequence[str], None] = "20260805a001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # IF NOT EXISTS：這支可能在已手動加過欄位的環境重跑
    op.execute(
        "ALTER TABLE expense_invoices "
        "ADD COLUMN IF NOT EXISTS approved_by INTEGER REFERENCES users(id) ON DELETE SET NULL"
    )
    op.execute(
        "ALTER TABLE expense_invoices "
        "ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP"
    )
    op.execute(
        "COMMENT ON COLUMN expense_invoices.approved_by IS "
        "'最後一次推進審核的人 —— 2026-08-16 前完全沒有記錄'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE expense_invoices DROP COLUMN IF EXISTS approved_at")
    op.execute("ALTER TABLE expense_invoices DROP COLUMN IF EXISTS approved_by")
