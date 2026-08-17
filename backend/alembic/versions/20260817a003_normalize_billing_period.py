"""正規化請款期別（4 筆漂移值收斂為標準詞彙）

Revision ID: 20260817a003
Revises: 20260817a002
Create Date: 2026-08-17

owner：「建議期別採下拉選單，避免不同專案不一致，如 第一期款」。

# 現況：同一件事三種寫法

    第一期              47
    第一期款項           3
    資訊系統第一期款      1

三種都是「第一期」。任何以期別分組的統計都會算成三種，
而**沒有任何一方會報錯** —— 表格有列、數字有值，只是被切成三塊。

根因是表單用 `<Input placeholder="如 第1期" />` 收 ——
違反 `ENUM_STORAGE_CONVENTION.md` 規則 4，而那份文件是我 08-17 自己寫的。
（順帶：`enum_storage_convention_audit` 當時抓不到它，因為判準只認
欄名含 `category|status|type` —— `billing_period` 不長那個樣子，
整欄在座標系之外。已擴充 `period|level` 並收掉隨之而來的假陽性。）

# 為什麼要先正規化才收緊 schema

改成 `Literal[BILLING_PERIODS]` 之後，任何帶著舊值的更新請求會 422 ——
使用者只是想改金額，卻被期別擋住，而錯誤訊息指向一個他沒動過的欄位。
與 08-17 開 `extra='forbid'` 前先掃前端 payload 是同一個順序要求：
**先讓現實符合規則，再讓規則強制執行。**

# 「資訊系統第一期款」為什麼可以併

案名已經記在該筆請款所屬的報價上（`erp_quotations.case_name`），
期別欄再寫一次案名是重複，而重複的那份正是造成漂移的原因。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260817a003"
down_revision: Union[str, Sequence[str], None] = "20260817a002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 與 `app/schemas/erp/billing.py: BILLING_PERIOD_ALIASES` 同一份對照。
# ⚠️ 這裡刻意寫死而不 import：migration 必須能在未來任何時點重跑，
# 而它不該隨 schema 檔演進而改變已套用的結果（那會讓同一個 revision
# 在不同時間做不同的事）。
ALIASES = {
    "第一期款項": "第一期",
    "第一期款": "第一期",
    "第1期": "第一期",
    "第2期": "第二期",
    "第3期": "第三期",
}


def upgrade() -> None:
    conn = op.get_bind()

    for old, new in ALIASES.items():
        res = conn.execute(
            sa.text("UPDATE erp_billings SET billing_period = :new "
                    "WHERE billing_period = :old RETURNING id"),
            {"old": old, "new": new},
        )
        n = len(res.fetchall())
        if n:
            print(f"[20260817a003] 「{old}」→「{new}」：{n} 筆")

    # 含案名的那一筆：以 LIKE 收（不能列進 ALIASES —— 那是單一案件的特例值，
    # 寫進通用對照表會讓人以為往後還會出現同樣的字串）
    res = conn.execute(sa.text("""
        UPDATE erp_billings SET billing_period = '第一期'
         WHERE billing_period LIKE '%第一期%'
           AND billing_period <> '第一期'
        RETURNING id, billing_period
    """))
    rows = res.fetchall()
    if rows:
        print(f"[20260817a003] 含「第一期」字樣的其他寫法：{len(rows)} 筆")

    # 驗收：正規化後不得有標準清單外的值（空值允許 —— 「還沒填」是合法狀態）
    left = conn.execute(sa.text("""
        SELECT billing_period, count(*) FROM erp_billings
         WHERE billing_period IS NOT NULL AND billing_period <> ''
           AND billing_period NOT IN ('第一期','第二期','第三期','第四期','第五期','尾款','一次請領')
         GROUP BY 1
    """)).fetchall()
    if left:
        # 不 raise：可能有我沒預見的合理值，此時**擋住 migration 不如讓人看見**。
        # schema 的 Literal 收緊會在下一次寫入時把它擋下來，那時才需要決定。
        print(f"[20260817a003] ⚠️ 仍有清單外的期別值，未自動改：{left}")
    else:
        print("[20260817a003] ✓ 期別已全數落在標準詞彙內")


def downgrade() -> None:
    # 不還原：漂移值是被收斂掉的錯誤狀態，回去只會再把統計切成三塊。
    pass
