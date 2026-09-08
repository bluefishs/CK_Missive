"""發票的聯式／抬頭／買受人統編／備註，與報價單的「總價是否含稅」

owner 2026-09-08 兩個要求，來源都是 `D:/報價單/115報價單彙整總表.xlsx`：

## ① 發票四欄（來源＝「發票明細」工作表）

那張工作表**已經有這些資料**，而系統沒有欄位存它們：

    發票種類  發票號碼      買受人              統一編號    備註
    二聯式    XX14671251   蔡蕙宇                          新光
    三聯式    XV19200164   樂昱建設有限公司    92602248    新光
    三聯式    XV19200159   鎮泓有限公司        83716494    新光

而 owner 提供的實體發票（EE15019500，買受人桃園市政府工務局）是**二聯式**且
課稅別勾**應稅** —— 也就是說「聯式」與「課稅別」是兩個維度，
此前系統把它們混成一個選項（「免稅／零稅率（二聯式）」），
照那個標籤選，機關的二聯式發票會被記成免稅而少掉 5% 的稅。

⚠️ **買受人不等於委託單位**：那五案的委託單位是「鎮泓有限公司」，
而發票抬頭有「蔡蕙宇」（個人）與「樂昱建設有限公司」。
此前只能塞在備註文字裡（總表備註寫著「發票抬頭:樂昱建設有限公司 統編:92602248」），
搜尋不到、也對不了帳。

`invoice_remark` 與既有的 `notes` 分開：`notes` 現在裝的是系統訊息
（「系統自動補建」），而發票備註是**寫在發票上的字**（例：
「訂購編號：XD-QA0132-00 台銀」）。兩者混在一起，任一方都會被另一方污染。

## ② `erp_quotations.tax_included`（來源＝總表 K 欄「稅內含」）

owner：「/erp/quotations/369?tab=items 其小計已含稅，故報價單需增列勾選
『總價是否含稅』」。

總表的 K 欄就是這個旗標，而匯入器**讀了它卻只丟進 notes**：

    稅內含 = v   ⇒ 報價金額**已含稅**，總價 ＝ 報價金額，稅額欄不另計
    稅內含 = 空  ⇒ 報價金額是**未稅**，總價 ＝ 報價金額 ＋ 稅額

09-08 的 12 筆「總價欄存的是未稅」就是漏了這個旗標的後果之一；
而工項小計的 ×1.05 對「稅內含」的案是錯的（會多算一次稅）。

預設 `false`（沿用現行行為：小計未稅、總價含稅），存量不動 ——
**要不要標成含稅是逐案的事實，不能用一句 SQL 猜**。
"""
from alembic import op
import sqlalchemy as sa

revision = '20260908a001'
down_revision = '20260907a002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 發票四欄 ──────────────────────────────────────────────
    op.add_column("erp_invoices", sa.Column(
        "invoice_kind", sa.String(length=10), nullable=True,
        comment="發票種類：triplicate=三聯式／duplicate=二聯式（由買受人身分決定，不影響稅額）"))
    op.add_column("erp_invoices", sa.Column(
        "buyer_name", sa.String(length=200), nullable=True,
        comment="發票抬頭（買受人）—— 可能不等於委託單位"))
    op.add_column("erp_invoices", sa.Column(
        "buyer_tax_id", sa.String(length=20), nullable=True,
        comment="買受人統一編號；二聯式（非營業人）可為空"))
    op.add_column("erp_invoices", sa.Column(
        "invoice_remark", sa.String(length=200), nullable=True,
        comment="寫在發票上的備註（例：訂購編號：XD-QA0132-00 台銀）——與系統用的 notes 分開"))

    # ── 報價單：總價是否含稅 ──────────────────────────────────
    op.add_column("erp_quotations", sa.Column(
        "tax_included", sa.Boolean(), nullable=False, server_default=sa.false(),
        comment="總價是否已含稅（總表 K 欄「稅內含」）。true ⇒ 工項小計即為總價、不再 ×1.05"))

    # 查詢用：依聯式統計、依買受人統編對帳
    op.create_index("ix_erp_invoices_invoice_kind", "erp_invoices", ["invoice_kind"])
    op.create_index("ix_erp_invoices_buyer_tax_id", "erp_invoices", ["buyer_tax_id"])


def downgrade() -> None:
    op.drop_index("ix_erp_invoices_buyer_tax_id", table_name="erp_invoices")
    op.drop_index("ix_erp_invoices_invoice_kind", table_name="erp_invoices")
    op.drop_column("erp_quotations", "tax_included")
    for c in ("invoice_remark", "buyer_tax_id", "buyer_name", "invoice_kind"):
        op.drop_column("erp_invoices", c)
