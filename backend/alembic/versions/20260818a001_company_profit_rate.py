"""新增公司固定利潤率設定（預設 0，不改變任何既有數字）

Revision ID: 20260818a001
Revises: 20260817a003
Create Date: 2026-08-18

owner 2026-08-18：「若可設定公司固定利潤如 10%，那總金額扣除前述才應該是專案毛利」。

# 這是什麼

公司在每個案子上先保留一筆固定比例的利潤（公司留成），
專案毛利要在扣掉它之後才算：

    營收       = 總價 − 稅額
    公司留成   = 營收 × 比率            ← 政策，本設定值
    專案可用   = 營收 − 公司留成
    專案毛利   = 專案可用 − 成本

**與 `overhead_fee`（管銷費）不同**：管銷費是逐案填的成本欄位，
公司留成是一條全公司政策比率，不該讓每個案子各填一次
（各填一次就會出現「這個案子抽 8%、那個案子抽 12%」而沒有人知道為什麼）。

# 為什麼預設 0

比率一旦生效，**每一張報價的毛利數字都會變**。預設 0 時
`專案可用 == 營收`，計算結果與 08-18 之前完全相同 ——
也就是這個 migration 不改變畫面上任何一個數字。

要生效請到 `/admin/site-management` → 系統設定 改為 `10`。
刻意不預設 10：那會讓 77 張報價的毛利在沒有人按下任何按鈕的情況下集體下降，
而事後查不出是哪一次變更造成的。

# 為什麼存百分比字串而不是小數

這張表的值是給人在 UI 上直接編輯的（`site_configurations.value` 是 text）。
`10` 比 `0.1` 不容易填錯 —— 而填錯 10 倍在這裡的後果是毛利整體算錯。
讀取端負責驗證與換算（見 `services/erp/company_profit.py`）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260818a001"
down_revision: Union[str, Sequence[str], None] = "20260817a003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONFIG_KEY = "erp_company_profit_rate"


def upgrade() -> None:
    conn = op.get_bind()

    exists = conn.execute(
        sa.text("SELECT 1 FROM site_configurations WHERE key = :k"),
        {"k": CONFIG_KEY},
    ).scalar()
    if exists:
        print(f"[20260818a001] {CONFIG_KEY} 已存在，不覆寫（可能已由人設過值）")
        return

    conn.execute(
        sa.text("""
            INSERT INTO site_configurations (key, value, description, category, is_active)
            VALUES (:k, :v, :d, 'erp', true)
        """),
        {
            "k": CONFIG_KEY,
            "v": "0",
            "d": "公司固定利潤率（%）— 專案毛利＝(總價−稅)×(1−此比率)−成本；0 表示不扣",
        },
    )
    print(f"[20260818a001] 已新增 {CONFIG_KEY} = 0（預設不扣，設為 10 即代表 10%）")


def downgrade() -> None:
    op.get_bind().execute(
        sa.text("DELETE FROM site_configurations WHERE key = :k"), {"k": CONFIG_KEY}
    )
