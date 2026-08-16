"""派工 deadline 加上真正的日期欄位（原文保留）

2026-08-16 owner：「deadline 格式也統一」。
盤點後發現**不能直接統一格式** —— 那個欄位同時裝了兩種東西：

    115/07/10                                    ← 純日期（補零）
    115/7/31                                     ← 純日期（未補零）
    115年01月15日                                 ← 中文日期
    115年02月08日前函覆(發文日起25日歷天内檢送成果)   ← 日期 ＋ **業務條件**

150 筆中 43 筆有值：41 筆解析得出日期、其中 **20 筆帶著額外說明文字**、
2 筆完全解析不出來。直接正規化成 `YYYY-MM-DD` 會**刪掉業務資訊**
（「發文日起 25 日曆天內檢送成果」是交辦條件，不是雜訊）。

作法：**加欄位不改原文**。
- `deadline_date`（DATE）：解析出來的日期，供排序／比較／逾期判定
- `deadline`（原欄位）：原文保留，繼續顯示給人看

這也解掉一個實際踩到的問題：`business_vital_signs` 想問「逾期未結案數」，
但 `deadline < CURRENT_DATE` 直接型別錯誤，而在檢核裡自己寫一套民國年解析
就是異質同工的起點（系統裡已有 `_parse_roc_date`）。

Revision ID: 20260816a002
Revises: 20260816a001
"""
from typing import Sequence, Union

from alembic import op

revision: str = "20260816a002"
down_revision: Union[str, Sequence[str], None] = "20260816a001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE taoyuan_dispatch_orders "
        "ADD COLUMN IF NOT EXISTS deadline_date DATE"
    )
    op.execute(
        "COMMENT ON COLUMN taoyuan_dispatch_orders.deadline_date IS "
        "'由 deadline 原文解析出的日期（民國年轉西元）。原文保留在 deadline，"
        "因為它可能帶著交辦條件如「發文日起25日曆天內檢送成果」'"
    )

    # 回填：民國年 → 西元。兩種寫法一次處理，且**只在解析得出時才寫**。
    # substring 取前三段數字，避開後面的說明文字。
    op.execute(r"""
        UPDATE taoyuan_dispatch_orders
        SET deadline_date = make_date(
            (substring(deadline from '^([0-9]{3})'))::int + 1911,
            (substring(deadline from '^[0-9]{3}[/年]([0-9]{1,2})'))::int,
            (substring(deadline from '^[0-9]{3}[/年][0-9]{1,2}[/月]([0-9]{1,2})'))::int
        )
        WHERE deadline ~ '^[0-9]{3}[/年][0-9]{1,2}[/月][0-9]{1,2}'
          AND deadline_date IS NULL
    """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_dispatch_deadline_date "
        "ON taoyuan_dispatch_orders (deadline_date)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_dispatch_deadline_date")
    op.execute("ALTER TABLE taoyuan_dispatch_orders DROP COLUMN IF EXISTS deadline_date")
