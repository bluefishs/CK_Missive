"""公文補齊 6 個 schema 宣告了而 ORM 沒有的欄位

Revision ID: 20260829b002
Revises: 20260829b001
Create Date: 2026-08-29

## 為什麼

`DocumentBase` / `DocumentUpdate` 宣告了 6 個業務欄位，而
`OfficialDocument` ORM 與 DB **一個對應欄都沒有**（weekly 83 架構驗證抓到）：

    contract_case（承攬案件）／doc_word（公文字）／doc_class（公文類別）
    priority_level（速別）／creator（建立者）／user_confirm（使用者確認）

⇒ **API 收得到但存不進去，回應也永遠不含它們。**

實測後果（不是推論）：`DocumentDetailPage` 與行事曆的 `useIntegratedEvent`
都在**讀** `document.priority_level`，而它永遠 undefined ⇒ 每次落到
預設值 `|| 3`。**畫面上的速別從來不是真的，而畫面上看不出來。**

這是 weekly 61（ORM 欄位沒到達 API）的**反方向**：API 欄位沒到達 ORM。

## owner 決定

2026-08-29 owner 裁示「公文欄位增列」＝ 補齊 ORM 與 DB，
而不是從 Pydantic schema 移除。

## ⚠️ 補完之後仍未完成的事

前端**沒有這些欄位的輸入介面**（實測 grep 只有讀取、沒有 Select/Input）。
所以補完 ORM 之後，它們仍然只有在 API 直接寫入時才會有值。
要讓使用者填得到還需要前端表單 —— **那不在本 migration 範圍**。
寫在這裡是為了避免日後有人看到欄位存在就以為功能完整。

## 既有 26,000+ 筆公文

不回填。`priority_level` 有 server_default「普通」，
新舊列讀起來一致；其餘四個文字欄與 `user_confirm` 為 NULL/false，
語意就是「沒有這筆資料」—— 那是事實，不該用預設值假裝有。
"""
from alembic import op
import sqlalchemy as sa

revision = "20260829b002"
down_revision = "20260829b001"
branch_labels = None
depends_on = None

_COLUMNS = [
    ("contract_case", sa.String(200), None, "承攬案件名稱或編號"),
    ("doc_word", sa.String(50), None, "公文字（例：府、院、部）"),
    ("doc_class", sa.String(50), None, "公文類別（例：函、令、公告）"),
    ("priority_level", sa.String(20), "普通", "速別（普通/速件/最速件）"),
    ("creator", sa.String(100), None, "建立者"),
    ("user_confirm", sa.Boolean(), "false", "使用者確認狀態"),
]


def upgrade() -> None:
    for name, type_, default, comment in _COLUMNS:
        op.add_column(
            "documents",
            sa.Column(
                name, type_,
                nullable=True,
                server_default=default,
                comment=comment,
            ),
        )


def downgrade() -> None:
    for name, *_ in reversed(_COLUMNS):
        op.drop_column("documents", name)
