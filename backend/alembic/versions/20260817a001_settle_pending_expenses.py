"""核准機制暫緩：結清 7 筆卡在審核的核銷並補入帳

2026-08-17 owner：「系統目前無財務獨立權限與人資，故先暫緩核准機制，
但應清楚表列紀錄」。

停用核准後，這 7 筆會**永遠出不去** —— 既沒有人能核准它們
（核准端點已明確拒絕），也就永遠不會入帳：

    id  1  AB12345678   50,500  pending           2026-04-04
    id  2  AB12345679   50,500  finance_approved  2026-04-04
    id  5  YX09766413      762  pending           2026-04-09
    id 10  DF87997182      290  manager_approved  2026-07-31
    id 11  DC09761665      940  pending           2026-07-31
    id 12  DR66349439    2,300  pending           2026-07-31
    id 13  DF87997156      312  pending           2026-07-31
                        ─────────
                        105,604  元，**7 筆全部未入帳**

## 為什麼是資料遷移而不是讓人一筆筆點

停用核准的當下，「送出即成立」對新的單子生效，但既有的卡在半路 ——
這是機制切換必然留下的邊界，不是使用者該自己收拾的東西。

## 這個遷移做什麼、不做什麼

**做**：狀態改 `verified`、`notes` 標註結清緣由（可追溯）、補寫統一帳本分錄。
**不做**：不動金額、不動分類、不動案號、不刪任何東西。

`notes` 一定要標 —— 否則日後看到這 7 筆會以為是正常核准通過的，
而它們其實是機制切換時一次性結清的。

Revision ID: 20260817a001
Revises: 20260816a003
"""
from typing import Sequence, Union

from alembic import op

revision: str = "20260817a001"
down_revision: Union[str, Sequence[str], None] = "20260816a003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_MARK = "[2026-08-17 核准機制暫緩，一次性結清]"


def upgrade() -> None:
    # ① 補入帳 —— **先入帳再改狀態**：
    #    若順序反過來而入帳失敗，就會留下「已完成卻沒有帳」的紀錄，
    #    而那種不一致沒有任何訊號會提醒人。
    #
    #    ⚠️ `ledger_code` 的既有慣例是 `FL_2026_00038`（FL_年份_五位序號），
    #    我第一版寫成 `EXP-{id}` —— 會造出格式與其他 38 筆完全不同的分錄，
    #    而那種不一致不會報錯，只會在報表排序或篩選時突然多出一群怪東西。
    #    這裡沿用同一格式，序號接在現有最大號之後。
    op.execute(f"""
        WITH seq AS (
            SELECT COALESCE(MAX(
                NULLIF(regexp_replace(ledger_code, '^FL_[0-9]{{4}}_', ''), '')::int
            ), 0) AS max_no
            FROM finance_ledgers
            WHERE ledger_code ~ '^FL_[0-9]{{4}}_[0-9]+$'
        ),
        pending AS (
            SELECT e.*, row_number() OVER (ORDER BY e.id) AS rn
            FROM expense_invoices e
            WHERE e.status NOT IN ('verified', 'rejected')
              AND NOT EXISTS (
                  SELECT 1 FROM finance_ledgers l
                  WHERE l.source_type = 'expense_invoice' AND l.source_id = e.id
              )
        )
        INSERT INTO finance_ledgers
            (ledger_code, entry_type, amount, category, description,
             case_code, transaction_date, source_type, source_id, user_id,
             created_at, updated_at)
        SELECT
            'FL_' || to_char(NOW(), 'YYYY') || '_' ||
                lpad((seq.max_no + e.rn)::text, 5, '0'),
            'expense',
            e.amount,
            COALESCE(e.category, '報銷及費用'),
            COALESCE(NULLIF(e.notes, ''), '費用核銷 ' || e.inv_num) || ' {_MARK}',
            e.case_code,
            COALESCE(e.date, e.created_at::date),
            'expense_invoice',
            e.id,
            e.user_id,
            NOW(), NOW()
        FROM pending e CROSS JOIN seq
    """)

    # ② 改狀態並留痕
    op.execute(f"""
        UPDATE expense_invoices
        SET status = 'verified',
            notes = COALESCE(NULLIF(notes, '') || ' | ', '') ||
                    '{_MARK} 原狀態: ' || status,
            updated_at = NOW()
        WHERE status NOT IN ('verified', 'rejected')
    """)


def downgrade() -> None:
    # 無法可靠還原「原本是哪個狀態」以外的資訊，但 notes 裡有記，
    # 所以這裡只把帳本分錄撤掉並依 notes 還原狀態。
    op.execute(f"""
        UPDATE expense_invoices
        SET status = split_part(notes, '{_MARK} 原狀態: ', 2)
        WHERE notes LIKE '%{_MARK}%'
          AND split_part(notes, '{_MARK} 原狀態: ', 2) <> ''
    """)
    op.execute(f"""
        DELETE FROM finance_ledgers
        WHERE source_type = 'expense_invoice' AND description LIKE '%{_MARK}%'
    """)
