"""所有 ORM mapper 必須能初始化 —— 否則整個系統無法登入。

2026-08-16 事故：加 `expense_invoices.approved_by` 後，
`ExpenseInvoice` 有兩個指向 `users` 的外鍵（user_id＝送出者、approved_by＝核准者），
SQLAlchemy 無法判斷 `User.expense_invoices` 該走哪一條，
拋 `AmbiguousForeignKeysError`。

**症狀是「系統無法登入」** —— mapper 初始化失敗會讓所有碰到 User 的查詢爆掉，
`POST /api/auth/google` 回 500。而 `/health` 與首頁**仍然是 200**，
因為它們不觸發 ORM mapper 設定 —— 又一次「服務層綠、業務層死」。

⚠️ 事故被放大的原因：我修好程式碼後只做 `docker cp` **沒有重建**，
而 `docker cp` 不會重載已匯入的模組 —— 行程仍載著舊 mapper。
**改 ORM 一律要重建容器，不能只複製檔案。**
"""


def test_all_mappers_configure():
    """一次觸發全部 mapper 設定 —— 有任何關聯定義不完整就會在這裡爆。"""
    from sqlalchemy.orm import configure_mappers
    import app.extended.models  # noqa: F401  匯入以註冊所有 model
    configure_mappers()


def test_expense_invoice_has_two_user_fks_and_both_are_disambiguated():
    """這是事故的具體形狀：兩個外鍵指向同一張表，兩端都必須指明 foreign_keys。"""
    from app.extended.models.invoice import ExpenseInvoice
    from app.extended.models.core import User

    fks = [c for c in ExpenseInvoice.__table__.columns
           if any(fk.column.table.name == "users" for fk in c.foreign_keys)]
    assert len(fks) >= 2, "外鍵少於 2 個 —— 這條測試的前提不再成立，請確認是否已改設計"

    assert ExpenseInvoice.user.property.local_remote_pairs, "invoice 端關聯未設定"
    assert User.expense_invoices.property.local_remote_pairs, "user 端關聯未設定"
