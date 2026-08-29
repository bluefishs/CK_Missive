"""user_sessions.created_at 改為 UTC —— 同一張表原本有兩種時間基準

Revision ID: 20260829b001
Revises: 20260829a002
Create Date: 2026-08-29

## 為什麼

`expires_at` 由 Python 寫入 `datetime.utcnow()`（naive UTC），
而 `created_at` 的 server_default 是 `now()` ＝ **PostgreSQL 本地時間
（Asia/Taipei）**。同一列的兩個時間戳因此相差 8 小時。

實測（2026-08-29）：2,263 筆中有 **1,185 筆** 的
`expires_at - created_at` 是 **-7 小時 45 分** —— 看起來像「寫入當下就過期」。

## 使用者沒有受影響，但有兩處真實傷害

`session_repository` 驗證時同樣用 `utcnow()`（:65 / :359），與寫入一致
⇒ **登入與 session 判定都是正確的**。真正的傷害：

1. 同一列的兩個時間戳無法相減 —— 任何算 session 壽命的分析都是錯的。
2. 在 DB 層比對 `expires_at > NOW()` 的工具**永遠看到 0 個有效 session**。
   實測：本地時間判定 **0 筆**／UTC 判定 **15 筆**。
   那正是 `admin_backup_smoke_test` 每次都強制重新插入 session 的原因
   （冗餘寫入，且它自己看不出為什麼）。

## 這個 migration 做什麼、不做什麼

**做**：把 `created_at` 的 server_default 換成 UTC，讓兩欄同基準。

**不做**：不回填既有的 1,185 筆。它們是已過期的歷史 session，
回填等於改寫稽核軌跡；而且「哪些是舊基準」本身是有用的資訊 ——
判準是 `created_at` 是否早於本次部署。

**不動認證邏輯**：它是自洽的、在運作的，改它才會傷到使用者。
（同族教訓：修一個不一致時，先問「哪一邊是對的」，不是讓兩邊看起來一樣。）
"""
from alembic import op
import sqlalchemy as sa

revision = "20260829b001"
down_revision = "20260829a002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "user_sessions",
        "created_at",
        server_default=sa.text("timezone('UTC', now())"),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "user_sessions",
        "created_at",
        server_default=sa.text("now()"),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )
