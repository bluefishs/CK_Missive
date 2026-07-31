"""案件 ← 標案 來源回指欄位（L3 回指斷）

背景（2026-07-31 全鏈路架構檢視 §2-D）：
標案與案件之間**雙向都看不到對方** —— 案件不知道自己從哪個標案來，
標案也不知道已經建過哪個案。即使人工建立了對應關係，下次進來還是看不出來。

新增 `source_tender_id`（指向 tender_records.id）到兩張案件表：
  * pm_cases（邀標/報價階段）
  * contract_projects（承攬案件）

同時讓「建案查重」有了可靠依據 —— 原本查重只比對 job_number，
而 ezbid 來源 37,980 筆 job_number 全為 NULL → 查重整段被跳過 → 可無限重複建案。

nullable + ADD COLUMN IF NOT EXISTS（冪等、零刪除、DB 安全，比照 20260617a001）。
不加 FK 約束：tender_records 會被 scraper 週期性重整，硬 FK 會使清理受阻；
以應用層維護參照即可（同 repo 既有 case_code/project_code 弱關聯慣例）。

Revision ID: 20260731a001
Revises: 20260617a001
Create Date: 2026-07-31
"""
from alembic import op

revision = '20260731a001'
down_revision = '20260617a001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE pm_cases "
        "ADD COLUMN IF NOT EXISTS source_tender_id INTEGER"
    )
    op.execute(
        "ALTER TABLE contract_projects "
        "ADD COLUMN IF NOT EXISTS source_tender_id INTEGER"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pm_cases_source_tender_id "
        "ON pm_cases (source_tender_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_contract_projects_source_tender_id "
        "ON contract_projects (source_tender_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_contract_projects_source_tender_id")
    op.execute("DROP INDEX IF EXISTS ix_pm_cases_source_tender_id")
    op.execute("ALTER TABLE contract_projects DROP COLUMN IF EXISTS source_tender_id")
    op.execute("ALTER TABLE pm_cases DROP COLUMN IF EXISTS source_tender_id")
