"""應付帳款補期別欄位（與應收對稱）

Revision ID: 20260818a002
Revises: 20260818a001
Create Date: 2026-08-18

owner 2026-08-18：「`/erp/quotations/167/accounts/payable/65/edit` 仍無法編輯期別
—— 應收與應付兩者設計不一致」。

# 前一次我判錯了方向

08-18 稍早 owner 第一次回報「編輯無期別」時，我查出
`erp_vendor_payables` 根本沒有這個欄位，於是回答「不是藏欄位，
是資料模型沒有」，並把「要不要加」列為待決定。

那個回答**只答了一半**：欄位不存在是事實，但兩張表用同一個填報頁、
同一種業務語意（分期收款 vs 分期付款），卻只有一邊有期別 ——
這本身就是缺陷，不需要等人決定。使用者在同一個表單的兩個方向之間
切換時，看到的欄位不一樣而沒有任何理由。

# 命名

`payable_period` 平行於同表既有的 `payable_amount`。

**不叫 `payment_period`**：同表已有 `payment_status` / `paid_date`，
那組指的是「實際付款」，而期別講的是「這筆應付屬於第幾期」——
兩件事，名字不該讓人混淆。

# 詞彙表共用

值域與應收完全相同（`schemas/erp/billing.py: BillingPeriod`）——
分期就是分期，沒有理由讓應收的「第一期」與應付的「第一期」
是兩份各自維護的清單。

# 既有 37 筆一律 NULL

不猜。應付目前沒有任何期別資訊（`description` 存的是
「案名 外包費用」不是期別），憑空填一個「第一期」會讓
「真的是第一期」與「我猜的」在資料裡分不出來。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260818a002"
down_revision: Union[str, Sequence[str], None] = "20260818a001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE erp_vendor_payables "
        "ADD COLUMN IF NOT EXISTS payable_period VARCHAR(50)"
    )
    n = op.get_bind().execute(
        sa.text("SELECT count(*) FROM erp_vendor_payables")
    ).scalar()
    print(f"[20260818a002] erp_vendor_payables 補 payable_period（既有 {n} 筆維持 NULL）")


def downgrade() -> None:
    op.execute("ALTER TABLE erp_vendor_payables DROP COLUMN IF EXISTS payable_period")
