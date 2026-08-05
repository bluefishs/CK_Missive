"""contact_note 由 VARCHAR(500) 改為 TEXT

Revision ID: 20260805a001
Revises: 20260731a001
Create Date: 2026-08-05

## 為什麼

2026-08-05 owner 儲存派工單 159 的聯絡備註時連續 5 次 HTTP 500。
根因：`contact_note` 是 `VARCHAR(500)`，而該欄位的**實際用途**是持續累積的
通聯紀錄（「11:01 (乾坤測繪)李昭德先生 查估後回報…」一路往下加），
owner 那筆已約 1,200 字。500 字對這個用途本來就不對。

而使用者看到的是一個沒有任何訊息的 500 —— 所以他又按了四次。
「欄位太長」是可以講清楚的事，不該以 500 呈現（另見同批修法：
把 StringDataRightTruncationError 轉成帶欄位名的 400）。

## 安全性

PostgreSQL 的 varchar(n) → text 是 binary-coercible，**不需要重寫資料表**，
也不會有資料遺失（text 是 varchar 的超集）。現存最長值 271 字元。
回滾方向會截斷超過 500 字元者，故 downgrade 明確擋下並要求人工決定。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260805a001"
down_revision: Union[str, Sequence[str], None] = "20260731a001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "taoyuan_dispatch_orders",
        "contact_note",
        existing_type=sa.String(length=500),
        type_=sa.Text(),
        existing_comment="聯絡備註",
        existing_nullable=True,
    )


def downgrade() -> None:
    # 回滾會截斷超過 500 字元的資料 —— 不靜默執行。
    # 真要回滾，請先確認 `SELECT count(*) FROM taoyuan_dispatch_orders
    # WHERE length(contact_note) > 500` 為 0，再手動移除這個防護。
    conn = op.get_bind()
    over = conn.execute(
        sa.text(
            "SELECT count(*) FROM taoyuan_dispatch_orders "
            "WHERE length(contact_note) > 500"
        )
    ).scalar()
    if over:
        raise RuntimeError(
            f"有 {over} 筆 contact_note 超過 500 字元，回滾會截斷它們。"
            f"請先處理那些資料，或明確決定要接受截斷後再移除此防護。"
        )
    op.alter_column(
        "taoyuan_dispatch_orders",
        "contact_note",
        existing_type=sa.Text(),
        type_=sa.String(length=500),
        existing_comment="聯絡備註",
        existing_nullable=True,
    )
