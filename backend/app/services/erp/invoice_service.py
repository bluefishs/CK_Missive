"""ERP 發票服務

Version: 1.2.0
- v1.2.0: 新增 create_from_billing — 從請款記錄開立發票
- v1.1.0: CRUD 改用 Repository 方法 (合規修正)
"""
import logging
from typing import Optional, List
from datetime import datetime, date as date_type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.erp import ERPInvoiceRepository
from app.schemas.erp import ERPInvoiceCreate, ERPInvoiceUpdate, ERPInvoiceResponse
from app.services.audit.mixin import AuditableServiceMixin

logger = logging.getLogger(__name__)


class ERPInvoiceService(AuditableServiceMixin):
    """發票管理服務"""

    AUDIT_TABLE = "erp_invoices"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ERPInvoiceRepository(db)

    async def _validate_and_link(self, data) -> None:
        """填報當下的檢核與自動關聯（就地改寫 data 的 billing_id）。

        自動關聯的判準刻意保守：**同一張報價單、金額相同、且還沒有人綁**的請款只有一期時才自動綁。
        有兩期同額就不猜 —— 猜錯的代價是把錢算到別期，而那在報表上看不出來。
        """
        from decimal import Decimal
        from sqlalchemy import select as _sel, func as _fn
        from app.extended.models.erp import ERPBilling, ERPInvoice

        amount = Decimal(str(getattr(data, "amount", 0) or 0))
        tax = Decimal(str(getattr(data, "tax_amount", 0) or 0))

        # ② 稅額：0（免稅／未稅開立）或 amount 的 5%（±1 元容差）
        if tax and amount:
            expect = (amount - amount / Decimal("1.05")).quantize(Decimal("1"))
            if abs(tax - expect) > 1:
                raise ValueError(
                    f"稅額 {tax:,.0f} 與金額 {amount:,.0f} 不相稱 —— 含稅金額的稅額應為 "
                    f"{expect:,.0f}（5%）或 0（免稅）。請確認填的是含稅總額還是未稅。"
                )

        bid = getattr(data, "billing_id", None)
        qid = getattr(data, "erp_quotation_id", None)
        if bid is None and qid:
            # ③ 自動關聯：同報價單、金額相同、尚未被綁的請款
            rows = (await self.db.execute(_sel(ERPBilling).where(
                ERPBilling.erp_quotation_id == qid))).scalars().all()
            taken = set((await self.db.execute(_sel(ERPInvoice.billing_id).where(
                ERPInvoice.billing_id.isnot(None)))).scalars().all())
            same = [b for b in rows
                    if b.id not in taken and Decimal(str(b.billing_amount or 0)) == amount]
            if len(same) == 1:
                data.billing_id = same[0].id
            bid = getattr(data, "billing_id", None)

        # ④ 發票已開 ⇒ 請款已成立：綁到（或唯一同額）的無日期佔位補上請款日期＝發票日期（一份實作在 billing_service）
        inv_date = getattr(data, "invoice_date", None)
        if qid and inv_date:
            from app.services.erp.billing_service import settle_placeholder_for_invoice
            settled = await settle_placeholder_for_invoice(
                self.db, quotation_id=qid, invoice_date=inv_date, amount=amount, billing_id=bid)
            if settled and bid is None:
                data.billing_id = settled
                bid = settled

        # ①-a 一票多案：帶了分攤就以分攤為準，且合計必須等於發票金額。
        # 沒有這一層時，一張跨兩案的發票只能挑一個案掛上去 —— 另一個案在帳上看不到那筆收入。
        allocs = getattr(data, "allocations", None)
        if allocs:
            total = sum(Decimal(str(a.get("amount", 0) if isinstance(a, dict) else a.amount)) for a in allocs)
            if abs(total - amount) > 1:
                raise ValueError(
                    f"分攤合計 {total:,.0f} 與發票金額 {amount:,.0f} 不符 —— "
                    "一票多案時每一分錢都要落在某一個案上，否則那個案的收入會憑空少掉。"
                )
            qids = [a.get("erp_quotation_id") if isinstance(a, dict) else a.erp_quotation_id for a in allocs]
            if len(set(qids)) != len(qids):
                raise ValueError("同一張發票對同一個案只能有一列分攤 —— 要改金額請改那一列，不要疊加。")

        # ① 金額不得超過所屬請款（超過就是兩邊有一邊填錯，不該靜靜存下去）
        if bid:
            b = (await self.db.execute(_sel(ERPBilling).where(ERPBilling.id == bid))).scalars().first()
            if b is None:
                raise ValueError(f"請款 #{bid} 不存在")
            billed = Decimal(str(b.billing_amount or 0))
            if amount - billed > 1:
                raise ValueError(
                    f"發票額 {amount:,.0f} 超過所屬請款 {billed:,.0f}（{b.billing_period or ''}）"
                    " —— 兩者必有一邊填錯：若是追加請先改請款額，若是打錯請改發票。"
                )

    async def create(self, data: ERPInvoiceCreate) -> ERPInvoiceResponse:
        """建立發票 (ADR-0013 Phase 2: 自動生成 invoice_ref + 併發 retry)

        invoice_ref 為系統內部參照碼，非法定統一發票號碼 (invoice_number)。
        """
        from app.services.contract import CaseCodeService
        from app.services.coding_helpers import retry_on_code_conflict

        # 2026-09-07 owner：「發票在填報時就要有檢核與自動關聯」。
        # 事後才發現的三種形狀（weekly 104 ②⑤⑦）都能在這裡擋掉：
        #   ① 發票額 > 請款額（09-06 有兩筆，因為請款被更正而發票沒跟）
        #   ② 稅額不是 0 也不是 5%（誤把未稅當含稅填）
        #   ③ 沒有綁請款 ⇒ 「這張發票對哪一期」答不出來（weekly 99 同族）
        await self._validate_and_link(data)

        async def _create_op():
            dump = data.model_dump()
            if not dump.get("invoice_ref"):
                code_svc = CaseCodeService(self.db)
                dump["invoice_ref"] = await code_svc.generate_invoice_ref(
                    year=datetime.now().year
                )
            # 2026-08-17：**必須 auto_commit=False**。
            # 這裡跑在 `retry_on_code_conflict` 的 SAVEPOINT 內，
            # 而 `BaseRepository.create` 預設 `auto_commit=True` 會直接 commit
            # → 外層交易被關掉 → `sp.commit()` 拋
            # `ResourceClosedError: This transaction is closed`
            # → 使用者看到「新增紀錄失敗」（owner 2026-08-17 於
            # /erp/quotations/152/accounts/receivable/create 回報）。
            #
            # 對照組：`asset_service` 用的 `create_asset` 只 flush、
            # 由外層自己 commit —— 那才是 savepoint 內該有的寫法。
            invoice = await self.repo.create(dump, auto_commit=False)
            await self.audit_create(invoice.id, dump)
            return invoice

        invoice = await retry_on_code_conflict(
            self.db, _create_op, unique_field="invoice_ref"
        )
        # savepoint commit 只是釋放 SAVEPOINT，**外層交易仍未落地** ——
        # 少了這一行會變成「不報錯但資料沒存進去」，比原本的錯誤更糟
        # （使用者以為成功了）。asset_service 的寫法就是這樣：
        # retry_on_code_conflict 之後自己 commit。
        await self.db.commit()
        return ERPInvoiceResponse.model_validate(invoice)

    async def get_by_quotation(self, quotation_id: int) -> List[ERPInvoiceResponse]:
        """取得報價單所有發票"""
        items = await self.repo.get_by_quotation_id(quotation_id)
        return [ERPInvoiceResponse.model_validate(i) for i in items]

    async def update(self, invoice_id: int, data: ERPInvoiceUpdate) -> Optional[ERPInvoiceResponse]:
        """更新發票"""
        invoice = await self.repo.get_by_id(invoice_id)
        if not invoice:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # 作廢處理
        if update_data.get("status") == "voided" and invoice.status != "voided":
            update_data["voided_at"] = datetime.utcnow()

        invoice = await self.repo.update(invoice_id, update_data)
        await self.audit_update(invoice_id, update_data)
        return ERPInvoiceResponse.model_validate(invoice)

    async def get_invoice_summary(
        self,
        invoice_type: Optional[str] = None,
        year: Optional[int] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = "desc",
        skip: int = 0,
        limit: int = 50,
    ) -> dict:
        """跨案件發票彙總（`search` 一次搜發票號／案號／報價單號／案名）"""
        items, total, totals = await self.repo.get_invoice_summary(
            invoice_type=invoice_type, year=year, search=search,
            sort_by=sort_by, sort_order=sort_order,
            accessible_case_codes=accessible_case_codes, skip=skip, limit=limit,
        )
        # totals＝分頁前全量合計（統計卡分母，2026-08-29）
        return {"items": items, "total": total, "totals": totals}

    async def delete(self, invoice_id: int) -> bool:
        """刪除發票"""
        result = await self.repo.delete(invoice_id)
        if result:
            await self.audit_delete(invoice_id)
        return result

    async def link_to_billing(self, invoice_id: int, billing_id: int) -> ERPInvoiceResponse:
        """把「登錄了但沒掛到請款」的發票關聯到某期請款。

        2026-09-04 owner：/erp/quotations/152 應收分頁警示「已收款尚未登錄發票」，而發票列表明明有
        ZZ00000001——它的 billing_id 是 NULL（從發票頁直接建的），分頁只認 billing_id。
        規則：同一張報價單／該請款尚無發票／該發票尚未關聯；金額不同不擋（分批開票是合法的），但回訊息提醒。
        """
        from app.extended.models.erp import ERPBilling, ERPInvoice
        inv = (await self.db.execute(select(ERPInvoice).where(ERPInvoice.id == invoice_id))).scalars().first()
        if not inv:
            raise ValueError("發票不存在")
        if inv.billing_id:
            raise ValueError(f"發票 {inv.invoice_number} 已關聯到請款 #{inv.billing_id}")
        billing = (await self.db.execute(select(ERPBilling).where(ERPBilling.id == billing_id))).scalars().first()
        if not billing:
            raise ValueError("請款記錄不存在")
        if billing.erp_quotation_id != inv.erp_quotation_id:
            raise ValueError("發票與請款不屬於同一張報價單，不能關聯")
        taken = (await self.db.execute(
            select(ERPInvoice.id).where(ERPInvoice.billing_id == billing_id, ERPInvoice.id != invoice_id).limit(1)
        )).scalar_one_or_none()
        if taken:
            raise ValueError("此請款記錄已有關聯發票")
        inv.billing_id = billing_id
        await self.db.commit()
        await self.db.refresh(inv)
        await self.audit_update(inv.id, {"billing_id": billing_id, "source": "link_to_billing"})
        return ERPInvoiceResponse.model_validate(inv)

    @staticmethod
    def derive_tax(gross, tax_mode: str = "taxable"):
        """由**含稅**額推導稅額（FIELD_SEMANTICS：`erp_invoices.amount` 是含稅）。

        2026-09-08：此前這裡是一行 `"tax_amount": 0` —— 於是走「開立發票」按鈕
        開出來的**每一張**都是免稅，而畫面照著印「免稅」，owner 因此問
        「/erp/quotations/571 為何會顯示免稅」。查全庫：157 張的稅額 ≈ amount/21
        （＝含稅推導，正確），16 張是 0；那 16 張裡 13 張是佔位號碼的系統補建，
        真發票只有 2 張，而**兩張的含稅額都能被 1.05 整除**（29,925＝28,500＋1,425、
        369,600＝352,000＋17,600）⇒ 它們是應稅而漏記，不是免稅。

        ⇒ 「整除」是判斷「這張到底該不該有稅」的可驗證訊號，不是猜的。
        """
        from decimal import Decimal, ROUND_HALF_UP
        g = Decimal(str(gross or 0))
        if tax_mode == "exempt" or g <= 0:
            return Decimal("0")
        # ⚠️ 2026-09-08（第二版）：改為**四捨五入到元**再相減，與總表的實例一致 ——
        # MT18585759 金額 15,000 ⇒ 銷售額 14,286（15,000/1.05＝14,285.71 進位）、稅額 714。
        # 原本 quantize 到分（14,285.71）會得到稅額 714.29，而發票上不會出現角分。
        net = (g / Decimal("1.05")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return g - net

    async def create_from_billing(
        self,
        billing_id: int,
        invoice_number: str,
        invoice_date: Optional[date_type] = None,
        notes: Optional[str] = None,
        tax_mode: str = "taxable",
        invoice_kind: str = "triplicate",
        buyer_name: Optional[str] = None,
        buyer_tax_id: Optional[str] = None,
        invoice_remark: Optional[str] = None,
    ) -> ERPInvoiceResponse:
        """從請款記錄建立銷項發票"""
        from app.extended.models.erp import ERPBilling

        result = await self.db.execute(
            select(ERPBilling).where(ERPBilling.id == billing_id)
        )
        billing = result.scalars().first()
        if not billing:
            raise ValueError("請款記錄不存在")

        # 檢查是否已有關聯發票 (透過 Invoice.billing_id 反查)
        from app.extended.models.erp import ERPInvoice
        existing_invoice = await self.db.execute(
            select(ERPInvoice.id).where(ERPInvoice.billing_id == billing_id).limit(1)
        )
        if existing_invoice.scalar_one_or_none():
            raise ValueError("此請款記錄已有關聯發票")
        # 2026-09-04 owner「發票已填報但無防呆」：①統一發票號碼＝2 大寫英文＋8 碼數字（FIELD_SEMANTICS）
        # ②全庫重複——此前直接撞 unique index，使用者看到的是 500 而不是「這個號碼已經開給誰」
        import re as _re
        invoice_number = (invoice_number or "").strip().upper()
        if not _re.fullmatch(r"[A-Z]{2}\d{8}", invoice_number):
            raise ValueError(f"發票號碼格式不對：「{invoice_number}」——統一發票為 2 個英文字母＋8 碼數字（例 EE15019500）")
        dup = (await self.db.execute(
            select(ERPInvoice.id, ERPInvoice.erp_quotation_id, ERPInvoice.billing_id)
            .where(ERPInvoice.invoice_number == invoice_number).limit(1)
        )).first()
        if dup:
            raise ValueError(f"發票號碼 {invoice_number} 已登錄在報價單 #{dup.erp_quotation_id}（發票 #{dup.id}）——同一號碼不能開兩次")

        invoice_data = {
            "erp_quotation_id": billing.erp_quotation_id,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date or date_type.today(),
            "amount": billing.billing_amount,
            # 2026-09-08：由含稅額推導，不再硬寫 0（見 derive_tax 的說明）
            "tax_amount": self.derive_tax(billing.billing_amount, tax_mode),
            # 聯式與買受人 —— 總表的「發票明細」本來就有這些，系統此前沒有欄位可放
            "invoice_kind": invoice_kind,
            "buyer_name": buyer_name,
            "buyer_tax_id": buyer_tax_id,
            "invoice_remark": invoice_remark,
            "invoice_type": "sales",
            "description": f"請款期別: {billing.billing_period or '-'}",
            "status": "issued",
            "billing_id": billing_id,
            "notes": notes,
        }

        invoice = await self.repo.create(invoice_data)
        await self.audit_create(invoice.id, invoice_data)

        return ERPInvoiceResponse.model_validate(invoice)
