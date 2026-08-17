"""報價單編號與版次（線上報價單機制）

2026-08-17 owner：「編號統整等標的」。

`erp_quotations` **沒有自己的編號** —— 只有 `case_code`（邀標案號）
與 `project_code`（成案編號）。對外報價單必須有可引用的單號：
客戶回覆時說的是「你們那張 QT-…」，而不是我們內部的案號。

編號規則沿用系統既有形狀（`CK{年}_{類別}_{序}` → `QT{年}_{序}`），不另造體系。

版次（`revision`）：議價後重報是 v2，**不是新單號** ——
客戶引用的是同一張報價單，版次是內部的。

Revision ID: 20260817a002
Revises: 20260817a001
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260817a002"
down_revision: Union[str, Sequence[str], None] = "20260817a001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE erp_quotations "
        "ADD COLUMN IF NOT EXISTS quotation_no VARCHAR(30)"
    )
    op.execute(
        "ALTER TABLE erp_quotations "
        "ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1"
    )
    op.execute(
        "ALTER TABLE erp_quotations "
        "ADD COLUMN IF NOT EXISTS quoted_at TIMESTAMP"
    )
    op.execute(
        "COMMENT ON COLUMN erp_quotations.quotation_no IS "
        "'對外報價單號 QT{年}_{序}。客戶引用的就是這個號；版次變更不換號'"
    )
    op.execute(
        "COMMENT ON COLUMN erp_quotations.revision IS "
        "'版次。議價後重報 +1，單號不變（客戶引用的是同一張）'"
    )
    op.execute(
        "COMMENT ON COLUMN erp_quotations.quoted_at IS "
        "'報價送出時間（status 轉 confirmed 時填）。NULL＝還在草稿'"
    )

    # 回填既有 76 張：依 id 順序給號，年份取 `year` 欄位（沒有就用 case_code 裡的年）。
    #
    # ⚠️ 既有報價全部是**已成案**的（實測 project_code 皆非 NULL），
    # 嚴格說它們不是「對外報價單」而是成本主檔。但給號的成本很低，
    # 而缺號會讓「所有報價都該有號」這條規則從第一天就有例外
    # —— 有例外的規則很快就會變成建議（本專案 08-17 剛記過這件事）。
    op.execute("""
        WITH numbered AS (
            SELECT id,
                   COALESCE(
                       NULLIF(year, 0),
                       NULLIF(substring(case_code from 3 for 4), '')::int,
                       EXTRACT(year FROM COALESCE(created_at, NOW()))::int
                   ) AS yr,
                   row_number() OVER (
                       PARTITION BY COALESCE(
                           NULLIF(year, 0),
                           NULLIF(substring(case_code from 3 for 4), '')::int,
                           EXTRACT(year FROM COALESCE(created_at, NOW()))::int
                       )
                       ORDER BY id
                   ) AS rn
            FROM erp_quotations
            WHERE quotation_no IS NULL
        )
        UPDATE erp_quotations q
        SET quotation_no = 'QT' || n.yr::text || '_' || lpad(n.rn::text, 3, '0')
        FROM numbered n
        WHERE q.id = n.id
    """)

    # 唯一約束：同一個報價單號不得重複。
    # 用 partial index（排除 NULL）—— 未來若有暫時無號的列不會被鎖死。
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_erp_quotations_quotation_no "
        "ON erp_quotations (quotation_no) WHERE quotation_no IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_erp_quotations_quotation_no")
    for col in ("quoted_at", "revision", "quotation_no"):
        op.execute(f"ALTER TABLE erp_quotations DROP COLUMN IF EXISTS {col}")
